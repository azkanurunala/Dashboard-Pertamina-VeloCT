"""
Sync data_saf_uco_prices dari CSV SharePoint.
513 baris dari CSV (s/d 2026-01-05) dibandingkan dengan DB, lalu UPDATE jika berbeda.
"""
import sys, pyodbc, json, csv, math

DRY_RUN = '--dry-run' in sys.argv

settings_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\local.settings.json'
with open(settings_path) as f:
    vals = json.load(f)['Values']
conn_str = vals['SQL_SERVER_CONNECTION_STRING']
conn_str = conn_str.replace("Encrypt=yes","Encrypt=no").replace("TrustServerCertificate=no","TrustServerCertificate=yes")

CSV_PATH = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\tmp\Pergerakan Harga SAF dan Harga UCO.csv'
SAF_COL = 'SAF (HEFA-SPK) FOB Straits $/mt (mirror)'
UCO_COL = 'UCO FOB Straits $/mt'
DATE_COL = 'Earliest Date'

def parse_float(s):
    s = s.strip()
    if not s:
        return None
    try:
        return float(s.replace(',', ''))
    except:
        return None

def approx_equal(a, b, tol=0.01):
    """True if both None, or both equal within tolerance."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) < tol

# Load CSV
csv_data = {}
with open(CSV_PATH, encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        date_str = row[DATE_COL].strip()[:10]  # take YYYY-MM-DD
        csv_data[date_str] = {
            'value_saf': parse_float(row[SAF_COL]),
            'value_uco': parse_float(row[UCO_COL]),
        }
print(f"CSV rows: {len(csv_data)}")

# Load DB
conn = pyodbc.connect(conn_str, timeout=30)
cursor = conn.cursor()
cursor.execute("SELECT CONVERT(VARCHAR, assess_date, 23), value_uco, value_saf FROM data_saf_uco_prices")
db_data = {r[0]: {'value_uco': r[1], 'value_saf': r[2]} for r in cursor.fetchall()}
print(f"DB rows:  {len(db_data)}")

# Compare
to_update = []    # (date_str, new_uco, new_saf)
to_insert = []    # dates in CSV not in DB
ok = mismatch = 0

for date_str, csv_row in csv_data.items():
    csv_uco = csv_row['value_uco']
    csv_saf = csv_row['value_saf']

    if date_str not in db_data:
        to_insert.append((date_str, csv_uco, csv_saf))
        continue

    db_row = db_data[date_str]
    db_uco = db_row['value_uco']
    db_saf = db_row['value_saf']

    uco_ok = approx_equal(csv_uco, db_uco)
    saf_ok = approx_equal(csv_saf, db_saf)

    if uco_ok and saf_ok:
        ok += 1
    else:
        mismatch += 1
        to_update.append((date_str, csv_uco, csv_saf, db_uco, db_saf))

print(f"\nMatch:    {ok}")
print(f"Mismatch: {mismatch}")
print(f"Missing:  {len(to_insert)}")

if mismatch:
    print("\nSample mismatches (first 10):")
    for date_str, cu, cs, du, ds in to_update[:10]:
        print(f"  {date_str}  uco: {du} -> {cu}  saf: {ds} -> {cs}")

if DRY_RUN:
    print("\nDRY-RUN: no changes")
    conn.close()
    exit()

# UPDATE mismatches
updated = errors = 0
for date_str, csv_uco, csv_saf, _, _ in to_update:
    try:
        cursor.execute("""
            UPDATE data_saf_uco_prices
            SET value_uco = ?, value_saf = ?
            WHERE CONVERT(VARCHAR, assess_date, 23) = ?
        """, csv_uco, csv_saf, date_str)
        updated += 1
    except Exception as e:
        print(f"  ERROR update {date_str}: {e}")
        errors += 1

# INSERT missing (dates in CSV not in DB — shouldn't happen but handle anyway)
inserted = 0
for date_str, csv_uco, csv_saf in to_insert:
    try:
        cursor.execute("""
            INSERT INTO data_saf_uco_prices (assess_date, value_uco, value_saf, scraped_at)
            VALUES (?, ?, ?, GETDATE())
        """, date_str, csv_uco, csv_saf)
        inserted += 1
    except Exception as e:
        print(f"  ERROR insert {date_str}: {e}")

conn.commit()
cursor.execute("SELECT COUNT(*), MIN(assess_date), MAX(assess_date) FROM data_saf_uco_prices")
r = cursor.fetchone()
cursor.execute("SELECT COUNT(*) FROM data_saf_uco_prices WHERE value_uco = 0 OR value_saf = 0")
zeros = cursor.fetchone()[0]
print(f"\nSelesai: {updated} updated, {inserted} inserted, {errors} errors")
print(f"DB sekarang: {r[0]} rows, range: {r[1]} to {r[2]}")
print(f"Remaining 0-value rows: {zeros}")
conn.close()
