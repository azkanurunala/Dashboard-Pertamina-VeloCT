"""
Audit gap data di setiap tabel untuk Jan 2025 - Apr 2026.
"""
import pyodbc, json

settings_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\local.settings.json'
with open(settings_path) as f:
    conn_str = json.load(f)['Values']['SQL_SERVER_CONNECTION_STRING']
conn_str = conn_str.replace("Encrypt=yes","Encrypt=no").replace("TrustServerCertificate=no","TrustServerCertificate=yes")

conn = pyodbc.connect(conn_str, timeout=10)
cursor = conn.cursor()

print("=" * 70)
print("AUDIT GAP DATA: Jan 2025 - Apr 2026")
print("=" * 70)

# 1. news_articles per source per bulan
print("\n--- NEWS ARTICLES per source (total & rentang tanggal) ---")
cursor.execute("""
    SELECT ns.name, COUNT(*) as total,
           MIN(na.published_date) as oldest,
           MAX(na.published_date) as newest
    FROM news_articles na
    JOIN news_sources ns ON na.source_id = ns.id
    GROUP BY ns.name
    ORDER BY newest DESC
""")
for r in cursor.fetchall():
    print(f"  {r[0]:35} | {r[1]:5} artikel | {str(r[2])[:10]} s/d {str(r[3])[:10]}")

# 2. Tabel data struktural
print("\n--- TABEL DATA STRUKTURAL ---")
data_tables = {
    'data_oil_prices':          'SELECT MIN(year), MAX(year), COUNT(*) FROM data_oil_prices',
    'data_biodiesel_hip':       'SELECT MIN(date), MAX(date), COUNT(*) FROM data_biodiesel_hip',
    'data_bioetanol_hip':       'SELECT MIN(date), MAX(date), COUNT(*) FROM data_bioetanol_hip',
    'data_cpo_prices':          'SELECT MIN(date), MAX(date), COUNT(*) FROM data_cpo_prices',
    'data_fossil':              'SELECT MIN(date), MAX(date), COUNT(*) FROM data_fossil',
    'data_iaea_nuclear_capacity':'SELECT MIN(year), MAX(year), COUNT(*) FROM data_iaea_nuclear_capacity',
    'data_ebt_capacity':        'SELECT MIN(tahun), MAX(tahun), COUNT(*) FROM data_ebt_capacity',
    'data_eia_market':          'SELECT MIN(tahun), MAX(tahun), COUNT(*) FROM data_eia_market',
    'data_ebt_prices':          'SELECT MIN(date), MAX(date), COUNT(*) FROM data_ebt_prices',
    'data_market_indicators':   'SELECT MIN(date), MAX(date), COUNT(*) FROM data_market_indicators',
    'data_renewable_energy':    'SELECT MIN(year), MAX(year), COUNT(*) FROM data_renewable_energy',
    'data_fossil_prediction':   'SELECT MIN(year), MAX(year), COUNT(*) FROM data_fossil_prediction',
    'data_geopolitical_risk_index': 'SELECT MIN(date), MAX(date), COUNT(*) FROM data_geopolitical_risk_index',
    'data_volatility_index':    'SELECT MIN(date), MAX(date), COUNT(*) FROM data_volatility_index',
    'data_wte_timbulan':        'SELECT MIN(tahun), MAX(tahun), COUNT(*) FROM data_wte_timbulan',
    'data_wte_komposisi':       'SELECT MIN(tahun), MAX(tahun), COUNT(*) FROM data_wte_komposisi',
    'data_wte_sumber':          'SELECT MIN(tahun), MAX(tahun), COUNT(*) FROM data_wte_sumber',
    'data_ruptl_projects':      'SELECT MIN(year), MAX(year), COUNT(*) FROM data_ruptl_projects',
    'data_saf_uco_prices':      'SELECT MIN(date), MAX(date), COUNT(*) FROM data_saf_uco_prices',
    'data_petrochemical_prices':'SELECT MIN(date), MAX(date), COUNT(*) FROM data_petrochemical_prices',
    'data_oil_crackspreads':    'SELECT MIN(date), MAX(date), COUNT(*) FROM data_oil_crackspreads',
}

for tbl, q in data_tables.items():
    try:
        cursor.execute(q)
        r = cursor.fetchone()
        print(f"  {tbl:35} | {r[2]:5} rows | {str(r[0])[:10]} s/d {str(r[1])[:10]}")
    except Exception as e:
        print(f"  {tbl:35} | ERROR: {e}")

conn.close()
