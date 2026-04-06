"""
Backfill data_cpo_prices dari GAPKI untuk semua data setelah 2026-01-13.
"""
import asyncio, sys, pyodbc, json
sys.path.insert(0, r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions')

from scrapers.cpo_scraper import CPOPriceScraper
from datetime import datetime

DRY_RUN = '--dry-run' in sys.argv
LAST_DATE = "2026-01-13"

settings_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\local.settings.json'
with open(settings_path) as f:
    conn_str = json.load(f)['Values']['SQL_SERVER_CONNECTION_STRING']
conn_str = conn_str.replace("Encrypt=yes","Encrypt=no").replace("TrustServerCertificate=no","TrustServerCertificate=yes")

async def main():
    print(f"{'DRY-RUN: ' if DRY_RUN else ''}Backfill GAPKI CPO data setelah {LAST_DATE}")
    print("=" * 60)

    async with CPOPriceScraper() as scraper:
        results = await scraper._scrape_articles_from_source(
            keywords=[],
            start_date=datetime.strptime(LAST_DATE, "%Y-%m-%d"),
            end_date=datetime.now(),
            last_date=LAST_DATE
        )

    if not results:
        print("Tidak ada data baru dari scraper!")
        return

    all_data = results[0].get('data', [])
    articles_count = results[0].get('articles_count', 0)
    print(f"\nFound {articles_count} artikel, {len(all_data)} price entries")

    if not all_data:
        print("Tidak ada price data yang berhasil di-extract!")
        return

    print("\nSample data (10 pertama):")
    for d in all_data[:10]:
        print(f"  upload={d['upload_date']}  price_date={d['price_date']}  px_last={d['px_last']}")

    if DRY_RUN:
        print(f"\nDRY-RUN: would insert {len(all_data)} rows")
        return

    # Insert ke DB
    conn = pyodbc.connect(conn_str, timeout=30)
    cursor = conn.cursor()

    # Load existing price_date untuk dedup
    cursor.execute("SELECT CONVERT(VARCHAR, price_date, 23) FROM data_cpo_prices")
    existing = {r[0] for r in cursor.fetchall()}
    print(f"\nExisting price_dates in DB: {len(existing)}")

    inserted = 0
    skipped = 0
    for d in all_data:
        pd_str = str(d['price_date'])[:10] if d['price_date'] else None
        if pd_str in existing:
            skipped += 1
            continue
        try:
            cursor.execute("""
                INSERT INTO data_cpo_prices (upload_date, price_date, px_last, scraped_at)
                VALUES (?, ?, ?, GETDATE())
            """, d['upload_date'], d['price_date'], float(d['px_last']))
            inserted += 1
            if pd_str:
                existing.add(pd_str)
        except Exception as e:
            print(f"  ERROR insert {d}: {e}")

    conn.commit()
    conn.close()

    print(f"\nSelesai: +{inserted} inserted, {skipped} skipped (already exist)")

    # Verify
    conn2 = pyodbc.connect(conn_str.replace("Encrypt=yes","Encrypt=no").replace("TrustServerCertificate=no","TrustServerCertificate=yes"), timeout=10)
    c2 = conn2.cursor()
    c2.execute("SELECT COUNT(*), MAX(price_date) FROM data_cpo_prices")
    r = c2.fetchone()
    print(f"DB sekarang: {r[0]} rows, max date={r[1]}")
    conn2.close()

asyncio.run(main())
