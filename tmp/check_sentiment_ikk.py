import pyodbc, json

settings_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\local.settings.json'
with open(settings_path) as f:
    conn_str = json.load(f)['Values']['SQL_SERVER_CONNECTION_STRING']
conn_str = conn_str.replace("Encrypt=yes","Encrypt=no").replace("TrustServerCertificate=no","TrustServerCertificate=yes")

conn = pyodbc.connect(conn_str, timeout=10)
cursor = conn.cursor()

# 1. Cek semua role_context yang ada di sentiment_analyses
print("=== ROLE_CONTEXT di sentiment_analyses ===")
cursor.execute("SELECT role_context, COUNT(*) as total FROM sentiment_analyses GROUP BY role_context ORDER BY total DESC")
for r in cursor.fetchall():
    print(f"  '{r[0]}': {r[1]} rows")

# 2. Cek apakah ada entry untuk 'Idx Keyakinan Konsumen'
print("\n=== ENTRIES untuk 'Idx Keyakinan Konsumen' ===")
cursor.execute("""
    SELECT date_range_start, date_range_end, role_context,
           LEFT(CAST(summary AS NVARCHAR(200)), 80) as summary_preview
    FROM sentiment_analyses
    WHERE role_context = 'Idx Keyakinan Konsumen'
    ORDER BY date_range_start DESC
""")
rows = cursor.fetchall()
if rows:
    for r in rows:
        print(f"  {str(r[0])[:10]} s/d {str(r[1])[:10]} | {r[2]}")
else:
    print("  TIDAK ADA entry dengan role_context = 'Idx Keyakinan Konsumen'")

# 3. Cek news articles untuk range 12/15-12/21/2025
print("\n=== NEWS ARTICLES 'indeks kepercayaan knsmn' bulan Des 2025 ===")
cursor.execute("""
    SELECT published_date, title
    FROM news_articles
    WHERE category = 'indeks kepercayaan knsmn'
      AND published_date BETWEEN '2025-12-01' AND '2025-12-31'
    ORDER BY published_date DESC
""")
rows = cursor.fetchall()
if rows:
    for r in rows:
        print(f"  {str(r[0])[:10]} | {r[1][:70]}")
else:
    print("  Tidak ada artikel untuk Desember 2025")

# 4. Cek rentang tanggal semua entries sentiment untuk role yg mirip
print("\n=== SEMUA role_context yang mengandung 'keyakinan' atau 'konsumen' ===")
cursor.execute("""
    SELECT role_context, date_range_start, date_range_end
    FROM sentiment_analyses
    WHERE LOWER(role_context) LIKE '%keyakinan%'
       OR LOWER(role_context) LIKE '%konsumen%'
       OR LOWER(role_context) LIKE '%ikk%'
    ORDER BY date_range_start DESC
""")
rows = cursor.fetchall()
if rows:
    for r in rows:
        print(f"  '{r[0]}' | {str(r[1])[:10]} s/d {str(r[2])[:10]}")
else:
    print("  Tidak ada")

conn.close()
