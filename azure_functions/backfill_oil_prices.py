"""
Backfill data_oil_prices dari data OneDrive Excel (Data)Harga Minyak.
Hanya insert row yang belum ada (berdasarkan year + month).
"""

import pyodbc
import json

settings_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\local.settings.json'
with open(settings_path, 'r') as f:
    data = json.load(f)
    conn_str = data.get('Values', {}).get('SQL_SERVER_CONNECTION_STRING')

conn_str = conn_str.replace("Encrypt=yes", "Encrypt=no").replace("TrustServerCertificate=no", "TrustServerCertificate=yes")

# Data dari OneDrive Excel sheet "(Data)Harga Minyak"
# Kolom: year, month, price (ICP USD/bbl), date_raw, brent_price
HISTORICAL_DATA = [
    {'year': 2025, 'month': 'Januari',   'price': 56.55, 'date_raw': '1 Februari',   'brent_price': 79.23},
    {'year': 2025, 'month': 'Februari',  'price': 74.29, 'date_raw': '11 Maret',     'brent_price': 75.16},
    {'year': 2025, 'month': 'Maret',     'price': 71.11, 'date_raw': '16 April',     'brent_price': 72.60},
    {'year': 2025, 'month': 'April',     'price': 65.29, 'date_raw': '19 Mei',       'brent_price': 67.79},
    {'year': 2025, 'month': 'Mei',       'price': 62.75, 'date_raw': '10 Juni',      'brent_price': 64.22},
    {'year': 2025, 'month': 'Juni',      'price': 69.33, 'date_raw': '3 Juli',       'brent_price': 71.46},
    {'year': 2025, 'month': 'Juli',      'price': 68.59, 'date_raw': '8 Agustus',    'brent_price': 70.99},
    {'year': 2025, 'month': 'Agustus',   'price': 66.07, 'date_raw': '10 September', 'brent_price': 68.21},
    {'year': 2025, 'month': 'September', 'price': 66.81, 'date_raw': '8 Oktober',    'brent_price': 68.02},
    {'year': 2025, 'month': 'Oktober',   'price': 63.62, 'date_raw': '10 November',  'brent_price': 64.75},
    {'year': 2025, 'month': 'November',  'price': 62.83, 'date_raw': '10 Desember',  'brent_price': 63.65},
    {'year': 2025, 'month': 'Desember',  'price': 61.10, 'date_raw': '9 Januari',    'brent_price': 62.68},
]

conn = pyodbc.connect(conn_str, timeout=10)
cursor = conn.cursor()

print("=== BACKFILL data_oil_prices ===\n")

# Ambil (year, month) yang sudah ada
cursor.execute("SELECT year, month FROM data_oil_prices")
existing = {(r[0], r[1]) for r in cursor.fetchall()}
print(f"Row yang sudah ada di DB: {len(existing)}")
for e in sorted(existing):
    print(f"  - {e[0]} {e[1]}")
print()

inserted = 0
skipped = 0

for row in HISTORICAL_DATA:
    key = (row['year'], row['month'])
    if key in existing:
        print(f"  SKIP  {row['year']} {row['month']} (sudah ada)")
        skipped += 1
        continue

    cursor.execute("""
        INSERT INTO data_oil_prices (year, month, price, date_raw, brent_price)
        VALUES (?, ?, ?, ?, ?)
    """, (row['year'], row['month'], row['price'], row['date_raw'], row['brent_price']))
    print(f"  INSERT {row['year']} {row['month']} — ICP: {row['price']}, Brent: {row['brent_price']}")
    inserted += 1

conn.commit()
conn.close()

print(f"\n=== SELESAI: {inserted} row di-insert, {skipped} row di-skip ===")

# Verifikasi
conn2 = pyodbc.connect(conn_str, timeout=10)
cursor2 = conn2.cursor()
cursor2.execute("SELECT year, month, price, brent_price FROM data_oil_prices ORDER BY year, month")
rows = cursor2.fetchall()
conn2.close()

print(f"\nTotal data_oil_prices sekarang: {len(rows)} row")
for r in rows:
    print(f"  {r[0]} {r[1]:10} — ICP: {r[2]}, Brent: {r[3]}")
