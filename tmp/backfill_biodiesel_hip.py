"""
Backfill data_biodiesel_hip menggunakan scraper yang sudah diperbaiki.
"""
import asyncio, sys, pyodbc, json
sys.path.insert(0, r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions')

from scrapers.biodiesel_esdm_scraper import BiodieselESDMScraper
from datetime import datetime

DRY_RUN = '--dry-run' in sys.argv

settings_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\local.settings.json'
with open(settings_path) as f:
    conn_str = json.load(f)['Values']['SQL_SERVER_CONNECTION_STRING']
conn_str = conn_str.replace("Encrypt=yes","Encrypt=no").replace("TrustServerCertificate=no","TrustServerCertificate=yes")

async def main():
    conn = pyodbc.connect(conn_str, timeout=30)
    cursor = conn.cursor()

    cursor.execute("SELECT hip_month FROM data_biodiesel_hip")
    existing_months = {r[0] for r in cursor.fetchall()}
    print(f"Existing months in DB: {len(existing_months)}")
    print(f"Max: {max(existing_months)}")

    async with BiodieselESDMScraper() as scraper:
        results = await scraper._scrape_articles_from_source(
            keywords=[],
            start_date=datetime.now(),
            end_date=datetime.now(),
            max_articles=50,
            existing_months=existing_months
        )

    if not results:
        print("No results from scraper")
        conn.close()
        return

    all_data = results[0].get('data', [])
    print(f"\nNew entries to insert: {len(all_data)}")
    for d in all_data:
        print(f"  {d['hip_month']:20}  {d['price_idr_liter']}  published={str(d['published_date'])[:10]}")

    if DRY_RUN:
        print("\nDRY-RUN: no insert")
        conn.close()
        return

    inserted = 0
    for d in all_data:
        try:
            cursor.execute("""
                INSERT INTO data_biodiesel_hip (published_date, hip_month, price_idr_liter, scraped_at)
                VALUES (?, ?, ?, GETDATE())
            """, d['published_date'], d['hip_month'], d['price_idr_liter'])
            inserted += 1
        except Exception as e:
            print(f"  ERROR {d['hip_month']}: {e}")

    conn.commit()

    cursor.execute("SELECT COUNT(*), MAX(hip_month) FROM data_biodiesel_hip")
    r = cursor.fetchone()
    print(f"\nSelesai: +{inserted} inserted")
    print(f"DB sekarang: {r[0]} rows, max={r[1]}")
    conn.close()

asyncio.run(main())
