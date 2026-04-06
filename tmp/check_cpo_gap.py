"""
Cek gap antara data_cpo_prices di Azure SQL vs SharePoint Excel.
"""
import pyodbc, json, openpyxl
from datetime import date, datetime

settings_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\local.settings.json'
with open(settings_path) as f:
    conn_str = json.load(f)['Values']['SQL_SERVER_CONNECTION_STRING']
conn_str = conn_str.replace("Encrypt=yes","Encrypt=no").replace("TrustServerCertificate=no","TrustServerCertificate=yes")
conn = pyodbc.connect(conn_str, timeout=30)
cursor = conn.cursor()

# 1. Statistik DB
print("=" * 60)
print("Azure SQL data_cpo_prices:")
print("=" * 60)
cursor.execute("SELECT COUNT(*), MIN(price_date), MAX(price_date) FROM data_cpo_prices")
r = cursor.fetchone()
print(f"  Total rows  : {r[0]}")
print(f"  Min date    : {r[1]}")
print(f"  Max date    : {r[2]}")

cursor.execute("SELECT CONVERT(VARCHAR, price_date, 23), px_last FROM data_cpo_prices ORDER BY price_date DESC")
db_rows = {r[0]: r[1] for r in cursor.fetchall()}

# 2. Baca SharePoint Excel — headers: Upload_Dates(0), Dates(1), PX_LAST(2)
print("\n" + "=" * 60)
print("SharePoint (Terstruktur)Data Scrapping.xlsx sheet (Data)CPO:")
print("=" * 60)

wb = openpyxl.load_workbook(
    r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\sharepoint_data\(Terstruktur)Data Scrapping.xlsx',
    read_only=True, data_only=True
)
ws = wb['(Data)CPO']
header = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
print(f"  Headers: {list(header)}")

sp_rows = {}  # price_date → (upload_date, px_last)
for row in ws.iter_rows(min_row=2, values_only=True):
    upload_raw, date_raw, px_raw = row[0], row[1], row[2]
    if date_raw is None:
        continue
    # Normalize date
    if isinstance(date_raw, (datetime, date)):
        dt_str = str(date_raw)[:10]
    else:
        dt_str = str(date_raw).strip()[:10]
    if isinstance(upload_raw, (datetime, date)):
        up_str = str(upload_raw)[:10]
    else:
        up_str = str(upload_raw).strip()[:10] if upload_raw else None
    sp_rows[dt_str] = (up_str, px_raw)

sp_dates_sorted = sorted(sp_rows.keys(), reverse=True)
print(f"  Total rows  : {len(sp_rows)}")
print(f"  Min date    : {min(sp_rows.keys())}")
print(f"  Max date    : {max(sp_rows.keys())}")

print(f"\n  10 terbaru di SharePoint:")
for dt in sp_dates_sorted[:10]:
    up, px = sp_rows[dt]
    print(f"  Dates={dt}  Upload={up}  PX_LAST={px}")

wb.close()

# 3. GAP analisis
print("\n" + "=" * 60)
print("GAP: tanggal di SharePoint tapi TIDAK di Azure SQL:")
print("=" * 60)
missing = {dt: sp_rows[dt] for dt in sp_rows if dt not in db_rows}
print(f"  Total missing: {len(missing)}")
for dt in sorted(missing.keys(), reverse=True)[:30]:
    up, px = missing[dt]
    print(f"  price_date={dt}  upload={up}  px_last={px}")

print("\n" + "=" * 60)
print("GAP: tanggal di Azure SQL tapi TIDAK di SharePoint:")
print("=" * 60)
extra = {dt: db_rows[dt] for dt in db_rows if dt not in sp_rows}
print(f"  Total extra in DB: {len(extra)}")
for dt in sorted(extra.keys(), reverse=True)[:10]:
    print(f"  price_date={dt}  px_last={extra[dt]}")

conn.close()
