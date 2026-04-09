"""
Backfill data_saf_uco_prices dari S&P API untuk data setelah 2026-01-05.
"""
import asyncio, sys, pyodbc, json
from datetime import datetime, timedelta
sys.path.insert(0, r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions')

from scrapers.sandp_data_scraper import SAndPDataScraper

DRY_RUN = '--dry-run' in sys.argv

settings_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\local.settings.json'
with open(settings_path) as f:
    vals = json.load(f)['Values']
conn_str = vals['SQL_SERVER_CONNECTION_STRING']
conn_str = conn_str.replace("Encrypt=yes","Encrypt=no").replace("TrustServerCertificate=no","TrustServerCertificate=yes")

import os
os.environ['SP_USERNAME'] = vals.get('SP_USERNAME','')
os.environ['SP_PASSWORD'] = vals.get('SP_PASSWORD','')

async def main():
    conn = pyodbc.connect(conn_str, timeout=30)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(assess_date) FROM data_saf_uco_prices")
    last_date = cursor.fetchone()[0]
    print(f"Last date in DB: {last_date}")

    start_dt = last_date + timedelta(days=1)
    end_dt   = datetime.now()
    start_str = start_dt.strftime('%Y-%m-%d')
    end_str   = end_dt.strftime('%Y-%m-%d')
    print(f"Fetching S&P SAF/UCO data: {start_str} -> {end_str}")

    async with SAndPDataScraper() as scraper:
        await scraper._login()
        symbols = list(scraper.SAF_SYMBOLS.keys())
        # Call get_historical_data directly to bypass the hardcoded 30-day window
        df = await scraper.get_historical_data(symbols, start_str, end_str)
        if df is None or df.empty:
            print("No results from S&P API")
            conn.close()
            return
        df_pivoted = scraper.pivot_saf_uco_data(df)

    all_data = df_pivoted.to_dict('records')
    print(f"\nFetched {len(all_data)} rows from S&P API")
    if all_data:
        print("Sample (first 5):")
        for d in all_data[:5]:
            print(f"  {d}")

    if DRY_RUN:
        print("\nDRY-RUN: no insert")
        conn.close()
        return

    # Load existing assess_dates for dedup
    cursor.execute("SELECT CONVERT(VARCHAR, assess_date, 23) FROM data_saf_uco_prices")
    existing = {r[0] for r in cursor.fetchall()}

    inserted = skipped = 0
    for d in all_data:
        ad = str(d.get('assess_date',''))[:10]
        if ad in existing:
            skipped += 1
            continue
        try:
            cursor.execute("""
                INSERT INTO data_saf_uco_prices (assess_date, value_uco, value_saf, mod_date_uco, mod_date_saf, scraped_at)
                VALUES (?, ?, ?, ?, ?, GETDATE())
            """, d.get('assess_date'), d.get('value_uco'), d.get('value_saf'),
                 d.get('mod_date_uco'), d.get('mod_date_saf'))
            inserted += 1
            existing.add(ad)
        except Exception as e:
            print(f"  ERROR {ad}: {e}")

    conn.commit()
    cursor.execute("SELECT COUNT(*), MAX(assess_date) FROM data_saf_uco_prices")
    r = cursor.fetchone()
    print(f"\nSelesai: +{inserted} inserted, {skipped} skipped")
    print(f"DB sekarang: {r[0]} rows, max={r[1]}")
    conn.close()

asyncio.run(main())
