"""
Import data struktural dari SharePoint Excel ke Azure SQL.

Yang diimport:
1. data_market_indicators: IHSG, Inflasi, PMI, Indonia, IKK, BI Rate, Sales Ritel,
                           Neraca Perdagangan, GDP dari (Data)Makro.xlsx
2. data_fossil_prediction: clean up 58 duplikat 2026 dari scraper

Yang SKIP (sudah ada lebih banyak di DB):
- Volatilitas, Geopolitik, Kurs (scraper sudah isi lebih banyak)
- sentiment_analyses (sudah cocok)
- Semua tabel struktural lain (SAF, Biodiesel, CPO, dll - sudah sama)
"""
import pyodbc, json, sys, openpyxl
from datetime import datetime, date

DRY_RUN = '--dry-run' in sys.argv

settings_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\local.settings.json'
with open(settings_path) as f:
    conn_str = json.load(f)['Values']['SQL_SERVER_CONNECTION_STRING']
conn_str = conn_str.replace("Encrypt=yes","Encrypt=no").replace("TrustServerCertificate=no","TrustServerCertificate=yes")
conn = pyodbc.connect(conn_str, timeout=30)
cursor = conn.cursor()


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def parse_date(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
            try:
                return datetime.strptime(val[:10], fmt).date()
            except:
                pass
    return None

def to_float(val):
    if val is None:
        return None
    try:
        return float(val)
    except:
        return None

def find_data_start(ws):
    """Find first row where column 0 is a datetime (CEIC format)."""
    for i, row in enumerate(ws.iter_rows(min_row=1, values_only=True), 1):
        if row[0] and isinstance(row[0], (datetime, date)):
            return i
    return None

def get_ceic_headers(ws):
    """Get actual indicator column names from row 1 of CEIC sheet."""
    row1 = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    return [str(v).strip() if v else None for v in row1]


# ─────────────────────────────────────────────
# 1. Clean up data_fossil_prediction duplicates
# ─────────────────────────────────────────────
print("=" * 60)
print("1. Clean up data_fossil_prediction duplicates (year 2026)")
print("=" * 60)
cursor.execute("SELECT COUNT(*) FROM data_fossil_prediction WHERE prediction_year = 2026")
count_before = cursor.fetchone()[0]
print(f"   Rows for 2026 before cleanup: {count_before}")

if count_before > 1:
    # Keep the row with the most recent scraped_at (or first id)
    cursor.execute("""
        DELETE FROM data_fossil_prediction
        WHERE prediction_year = 2026
          AND id NOT IN (
              SELECT TOP 1 id FROM data_fossil_prediction
              WHERE prediction_year = 2026
              ORDER BY scraped_at DESC
          )
    """)
    if not DRY_RUN:
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM data_fossil_prediction WHERE prediction_year = 2026")
        count_after = cursor.fetchone()[0]
        print(f"   Deleted {count_before - count_after} duplicate rows. Remaining: {count_after}")
    else:
        print(f"   DRY-RUN: would delete {count_before - 1} rows")
        conn.rollback()


# ─────────────────────────────────────────────
# 2. data_market_indicators from (Data)Makro.xlsx
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("2. Import data_market_indicators from (Data)Makro.xlsx")
print("=" * 60)

# Mapping: sheet_name → list of (col_index, category, indicator_name)
# col_index is 1-based offset from date column (col 0)
SHEET_MAPPINGS = {
    '(Data)IHSG': [
        (1, 'IHSG', 'IDX Composite'),
    ],
    '(Data)Inflasi': [
        (1, 'Inflasi', 'CPI YoY Volatile'),
        (2, 'Inflasi', 'CPI YoY Administered'),
        (3, 'Inflasi', 'CPI YoY Core'),
        (4, 'Inflasi', 'CPI YoY'),
    ],
    '(Data)PMI': [
        (1, 'PMI', 'Manufacturing PMI'),
    ],
    '(Data)Indonia': [
        (1, 'Indonia', 'IndONIA Rate'),
    ],
    '(Data)Indeks Konsumen BI': [
        (1, 'Idx Keyakinan Konsumen', 'IKK Ekspektasi'),
        (2, 'Idx Keyakinan Konsumen', 'IKK Kondisi Saat Ini'),
        (3, 'Idx Keyakinan Konsumen', 'IKK'),
    ],
    '(Data)BI-Rate': [
        (1, 'BI Rate', 'BI-Rate'),
    ],
    '(Data)Sales Ritel': [
        (1, 'Sales Ritel', 'Retail Sales Index'),
    ],
    '(Data)Neraca Perdagangan': [
        (1, 'Neraca Perdagangan', 'Ekspor USD mn'),
        (2, 'Neraca Perdagangan', 'Impor USD mn'),
        (3, 'Neraca Perdagangan', 'Neraca Perdagangan'),
    ],
    '(Data)GDP yoy': [
        (1, 'PDB', 'GDP YoY %'),
    ],
}

# Load existing (indicator_date, category, indicator_name) from DB for dedup
print("   Loading existing market indicator keys from DB...")
cursor.execute("""
    SELECT CONVERT(VARCHAR, indicator_date, 23), category, indicator_name
    FROM data_market_indicators
""")
existing_keys = set()
for r in cursor.fetchall():
    existing_keys.add((r[0], r[1], r[2]))
print(f"   {len(existing_keys)} existing keys loaded")

wb = openpyxl.load_workbook('sharepoint_data/(Data)Makro.xlsx', read_only=True, data_only=True)
total_inserted = 0
total_skipped = 0

for sheet_name, col_mappings in SHEET_MAPPINGS.items():
    if sheet_name not in wb.sheetnames:
        print(f"   SKIP {sheet_name} - not found in workbook")
        continue

    ws = wb[sheet_name]
    data_start_row = find_data_start(ws)
    if not data_start_row:
        print(f"   SKIP {sheet_name} - no date data found")
        continue

    rows_to_insert = []
    for row in ws.iter_rows(min_row=data_start_row, values_only=True):
        dt = parse_date(row[0])
        if not dt:
            continue
        dt_str = dt.strftime('%Y-%m-%d')
        for col_idx, category, indicator_name in col_mappings:
            if col_idx >= len(row):
                continue
            val = to_float(row[col_idx])
            if val is None:
                continue
            key = (dt_str, category, indicator_name)
            if key in existing_keys:
                total_skipped += 1
                continue
            rows_to_insert.append((dt, category, indicator_name, val))
            existing_keys.add(key)

    # Batch insert
    inserted = 0
    if not DRY_RUN:
        for dt, cat, ind_name, val in rows_to_insert:
            cursor.execute("""
                INSERT INTO data_market_indicators (indicator_date, category, indicator_name, value, scraped_at)
                VALUES (?, ?, ?, ?, GETDATE())
            """, dt, cat, ind_name, val)
            inserted += 1
        if inserted:
            conn.commit()
    else:
        inserted = len(rows_to_insert)

    total_inserted += inserted
    categories = set(c for _, c, _ in col_mappings)
    print(f"   {'DRY-RUN ' if DRY_RUN else ''}[OK] {sheet_name:30} | +{inserted:5} inserted | {total_skipped:5} skipped")

wb.close()

print(f"\n   Total inserted: {total_inserted}")
print(f"   Total skipped : {total_skipped}")


# ─────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("SELESAI" + (" (DRY RUN)" if DRY_RUN else ""))
print("=" * 60)

if not DRY_RUN:
    cursor.execute("SELECT category, indicator_name, COUNT(*), MIN(indicator_date), MAX(indicator_date) FROM data_market_indicators GROUP BY category, indicator_name ORDER BY category, indicator_name")
    print("\ndata_market_indicators setelah import:")
    for r in cursor.fetchall():
        print(f"  {r[0]:30} | {r[1]:30} | {r[2]:6} rows | {str(r[3])[:10]} - {str(r[4])[:10]}")

conn.close()
