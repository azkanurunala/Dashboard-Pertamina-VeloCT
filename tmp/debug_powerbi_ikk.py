"""
Debug Power BI: data tidak muncul untuk range 12/15/2025 - 12/21/2025
Cek (News)indeks kepercayaan knsmn dan (Summary)Idx Keyakinan Konsumen
"""
import pyodbc, json

settings_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\local.settings.json'
with open(settings_path) as f:
    conn_str = json.load(f)['Values']['SQL_SERVER_CONNECTION_STRING']
conn_str = conn_str.replace("Encrypt=yes","Encrypt=no").replace("TrustServerCertificate=no","TrustServerCertificate=yes")

conn = pyodbc.connect(conn_str, timeout=10)
cursor = conn.cursor()

print("=" * 60)
print("DEBUG: Power BI range 12/15/2025 - 12/21/2025")
print("=" * 60)

# 1. Cek artikel IKK per minggu Des 2025
print("\n1. Artikel 'indeks kepercayaan knsmn' per minggu Des 2025:")
cursor.execute("""
    SELECT
        CAST(published_date AS DATE) as tgl,
        COUNT(*) as jumlah,
        ns.name as source
    FROM news_articles na
    JOIN news_sources ns ON na.source_id = ns.id
    WHERE na.category = 'indeks kepercayaan knsmn'
      AND na.published_date BETWEEN '2025-12-01' AND '2025-12-31'
    GROUP BY CAST(published_date AS DATE), ns.name
    ORDER BY tgl
""")
rows = cursor.fetchall()
if rows:
    for r in rows:
        print(f"  {r[0]} | {r[1]} artikel | {r[2]}")
else:
    print("  TIDAK ADA artikel IKK di Des 2025!")

# 2. Total artikel IKK per bulan
print("\n2. Total artikel IKK per bulan:")
cursor.execute("""
    SELECT
        FORMAT(published_date, 'yyyy-MM') as bulan,
        COUNT(*) as jumlah
    FROM news_articles
    WHERE category = 'indeks kepercayaan knsmn'
    GROUP BY FORMAT(published_date, 'yyyy-MM')
    ORDER BY bulan
""")
for r in cursor.fetchall():
    print(f"  {r[0]}: {r[1]} artikel")

# 3. Cek sentiment_analyses untuk IKK
print("\n3. sentiment_analyses dengan role_context = 'Idx Keyakinan Konsumen':")
cursor.execute("""
    SELECT TOP 20
        date_range_start, date_range_end,
        LEFT(CAST(summary AS VARCHAR(100)), 80) as summary_preview
    FROM sentiment_analyses
    WHERE role_context = 'Idx Keyakinan Konsumen'
    ORDER BY date_range_start DESC
""")
rows = cursor.fetchall()
if rows:
    for r in rows:
        print(f"  {str(r[0])[:10]} - {str(r[1])[:10]} | {r[2]}")
else:
    print("  TIDAK ADA data di sentiment_analyses untuk 'Idx Keyakinan Konsumen'!")
    # Cek role_context apa saja yang ada
    cursor.execute("SELECT DISTINCT role_context, COUNT(*) as total FROM sentiment_analyses GROUP BY role_context ORDER BY total DESC")
    rows2 = cursor.fetchall()
    print("\n  Role contexts yang tersedia:")
    for r in rows2:
        print(f"    '{r[0]}': {r[1]} rows")

# 4. Cek apakah ada artikel IKK di range 15-21 Des 2025
print("\n4. Artikel IKK di range 15-21 Des 2025 (exact range yg bermasalah):")
cursor.execute("""
    SELECT na.title, CAST(na.published_date AS DATE) as tgl, ns.name as source
    FROM news_articles na
    JOIN news_sources ns ON na.source_id = ns.id
    WHERE na.category = 'indeks kepercayaan knsmn'
      AND na.published_date BETWEEN '2025-12-15' AND '2025-12-21'
    ORDER BY na.published_date
""")
rows = cursor.fetchall()
if rows:
    for r in rows:
        print(f"  {r[1]} | {r[2]} | {r[0][:70]}")
else:
    print("  Tidak ada artikel IKK di range 15-21 Des 2025")

conn.close()