"""
Fix data_saf_uco_prices:
  - 7 rows UCO=0  -> UPDATE dengan nilai benar dari S&P API
  - 194 rows SAF=0 -> UPDATE dengan nilai API jika ada, atau SET NULL jika API tidak punya data
    (SAF assessment S&P baru ada mulai Oktober 2024)
"""
import asyncio, sys, pyodbc, json, math
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

def is_valid(v):
    """True if v is a real number (not None, NaN, 0)."""
    if v is None:
        return False
    try:
        return not math.isnan(float(v)) and float(v) != 0
    except:
        return False

def to_null_or_val(v):
    """Return None if value is NaN/invalid, else the float value."""
    if v is None:
        return None
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except:
        return None

async def main():
    conn = pyodbc.connect(conn_str, timeout=30)
    cursor = conn.cursor()

    # Load all 0-value rows
    cursor.execute('''
        SELECT CONVERT(VARCHAR, assess_date, 23), value_uco, value_saf
        FROM data_saf_uco_prices
        WHERE value_uco = 0 OR value_saf = 0
        ORDER BY assess_date
    ''')
    zero_rows = {r[0]: (r[1], r[2]) for r in cursor.fetchall()}
    print(f"0-value rows in DB: {len(zero_rows)}")

    # Fetch full history from S&P API
    start_str = "2023-12-31"
    end_str   = "2026-01-06"
    print(f"Fetching from S&P API: {start_str} -> {end_str} ...")

    async with SAndPDataScraper() as scraper:
        await scraper._login()
        symbols = list(scraper.SAF_SYMBOLS.keys())
        df = await scraper.get_historical_data(symbols, start_str, end_str)
        if df is None or df.empty:
            print("ERROR: No data from API")
            conn.close()
            return
        df_pivoted = scraper.pivot_saf_uco_data(df)

    api_data = {str(row['assess_date'])[:10]: row for row in df_pivoted.to_dict('records')}
    print(f"API returned {len(api_data)} rows")

    # Build list of updates
    updates = []   # (date_str, new_uco, new_saf)
    not_in_api = []

    for date_str, (db_uco, db_saf) in zero_rows.items():
        if date_str not in api_data:
            not_in_api.append(date_str)
            continue

        api_row = api_data[date_str]
        api_uco = api_row.get('value_uco')
        api_saf = api_row.get('value_saf')

        # Determine new values:
        # - If DB has 0, use API value (could be a real number OR None/NaN -> NULL)
        # - If DB is not 0, keep DB value unchanged
        new_uco = to_null_or_val(api_uco) if db_uco == 0 else db_uco
        new_saf = to_null_or_val(api_saf) if db_saf == 0 else db_saf

        updates.append((date_str, new_uco, new_saf, db_uco, db_saf))

    print(f"\nRows to update: {len(updates)}")
    print(f"Rows not in API: {len(not_in_api)}")

    # Categorize updates
    uco_fixed  = [(d, nu, ns) for d, nu, ns, du, ds in updates if du == 0 and nu is not None and nu != 0]
    saf_fixed  = [(d, nu, ns) for d, nu, ns, du, ds in updates if ds == 0 and ns is not None and ns != 0]
    saf_nulled = [(d, nu, ns) for d, nu, ns, du, ds in updates if ds == 0 and (ns is None or ns == 0)]

    print(f"  UCO=0 -> real value (from API):  {len(uco_fixed)}")
    print(f"  SAF=0 -> real value (from API):  {len(saf_fixed)}")
    print(f"  SAF=0 -> NULL (API has no data): {len(saf_nulled)}")

    if DRY_RUN:
        print("\nDRY-RUN: no update")
        print("\nSample UCO fixes:")
        for d, nu, ns, du, ds in [(d, nu, ns, du, ds) for d, nu, ns, du, ds in updates if du == 0 and nu][:5]:
            print(f"  {d}  uco: {du} -> {nu}")
        print("\nSample SAF fixes (2025, where API has data):")
        for d, nu, ns, du, ds in [(d, nu, ns, du, ds) for d, nu, ns, du, ds in updates if ds == 0 and ns][:5]:
            print(f"  {d}  saf: {ds} -> {ns}")
        print("\nSample SAF->NULL (2024, API has no data):")
        for d, nu, ns, du, ds in [(d, nu, ns, du, ds) for d, nu, ns, du, ds in updates if ds == 0 and not ns][:5]:
            print(f"  {d}  saf: {ds} -> NULL")
        conn.close()
        return

    updated = errors = 0
    for date_str, new_uco, new_saf, _, _ in updates:
        try:
            cursor.execute('''
                UPDATE data_saf_uco_prices
                SET value_uco = ?, value_saf = ?
                WHERE CONVERT(VARCHAR, assess_date, 23) = ?
            ''', new_uco, new_saf, date_str)
            updated += 1
        except Exception as e:
            print(f"  ERROR {date_str}: {e}")
            errors += 1

    conn.commit()

    # Verify
    cursor.execute('SELECT COUNT(*) FROM data_saf_uco_prices WHERE value_uco = 0 OR value_saf = 0')
    remaining_zeros = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM data_saf_uco_prices WHERE value_uco IS NULL OR value_saf IS NULL')
    remaining_nulls = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*), MIN(assess_date), MAX(assess_date) FROM data_saf_uco_prices')
    r = cursor.fetchone()

    print(f"\nSelesai: {updated} updated, {errors} errors")
    print(f"Remaining 0-value rows: {remaining_zeros}")
    print(f"Rows with NULL (no S&P data for that date): {remaining_nulls}")
    print(f"Total rows: {r[0]}, range: {r[1]} to {r[2]}")
    conn.close()

asyncio.run(main())
