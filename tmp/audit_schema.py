"""
Cek 2 hal:
1. Kolom aktual tabel data struktural yang error
2. Kenapa scraper berhenti 2026-02-12
"""
import pyodbc, json

settings_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\local.settings.json'
with open(settings_path) as f:
    conn_str = json.load(f)['Values']['SQL_SERVER_CONNECTION_STRING']
conn_str = conn_str.replace("Encrypt=yes","Encrypt=no").replace("TrustServerCertificate=no","TrustServerCertificate=yes")

conn = pyodbc.connect(conn_str, timeout=10)
cursor = conn.cursor()

# 1. Cek kolom aktual tabel yang error
error_tables = [
    'data_biodiesel_hip', 'data_cpo_prices', 'data_fossil',
    'data_ebt_prices', 'data_market_indicators', 'data_renewable_energy',
    'data_fossil_prediction', 'data_geopolitical_risk_index', 'data_volatility_index',
    'data_wte_timbulan', 'data_wte_komposisi', 'data_wte_sumber',
    'data_ruptl_projects', 'data_saf_uco_prices', 'data_petrochemical_prices',
    'data_oil_crackspreads'
]

print("=== KOLOM AKTUAL TABEL DATA STRUKTURAL ===\n")
for tbl in error_tables:
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = ?
        ORDER BY ORDINAL_POSITION
    """, tbl)
    cols = cursor.fetchall()
    if cols:
        col_str = ', '.join([f"{c[0]}({c[1]})" for c in cols])
        cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
        count = cursor.fetchone()[0]
        print(f"  {tbl}: {count} rows")
        print(f"    Kolom: {col_str}\n")
    else:
        print(f"  {tbl}: TABEL TIDAK ADA\n")

# 2. Cek kenapa scraper berhenti di 2026-02-12
print("\n=== ARTIKEL SEKITAR 2026-02-12 (per source) ===\n")
cursor.execute("""
    SELECT ns.name,
           COUNT(CASE WHEN na.scraped_date >= '2026-02-10' AND na.scraped_date <= '2026-02-14' THEN 1 END) as around_cutoff,
           MAX(na.scraped_date) as last_scraped
    FROM news_articles na
    JOIN news_sources ns ON na.source_id = ns.id
    GROUP BY ns.name
    HAVING MAX(na.scraped_date) < '2026-02-20'
    ORDER BY last_scraped DESC
""")
for r in cursor.fetchall():
    print(f"  {r[0]:30} | last scraped: {str(r[2])[:19]} | articles around cutoff: {r[1]}")

# 3. Cek execution_logs di sekitar tanggal itu
print("\n=== EXECUTION LOGS SEKITAR 2026-02-12 ===\n")
cursor.execute("""
    SELECT TOP 10 function_name, status, start_time, error_message
    FROM execution_logs
    WHERE start_time BETWEEN '2026-02-10' AND '2026-02-15'
    ORDER BY start_time DESC
""")
logs = cursor.fetchall()
if logs:
    for r in logs:
        print(f"  {r[0]:30} | {r[1]:10} | {str(r[2])[:19]}")
        if r[3]:
            print(f"    Error: {str(r[3])[:100]}")
else:
    print("  Tidak ada log di execution_logs untuk periode ini")

conn.close()
