"""
Script untuk reklasifikasi artikel dengan category = NULL.
- 31 artikel yang URL-nya sudah punya kategori lain → dihapus (duplikat)
- 74 artikel yang URL-nya unik → di-reklasifikasi dengan _classify_article_categories()
"""

import pyodbc
import json
import uuid

settings_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\local.settings.json'
with open(settings_path, 'r') as f:
    data = json.load(f)
    conn_str = data.get('Values', {}).get('SQL_SERVER_CONNECTION_STRING')

conn_str = conn_str.replace("Encrypt=yes", "Encrypt=no").replace("TrustServerCertificate=no", "TrustServerCertificate=yes")

# ── Keyword classifier (sama persis dengan orchestrator_function.py) ──────────
CATEGORY_KEYWORDS = {
    'indeks risiko geopolitik': [
        'indeks risiko geopolitik', 'tekanan geopolitik', 'geopolitik'],
    'indeks volatilitas': [
        'indeks volatilitas', 'volatilitas'],
    'Kurs': [
        'kurs', 'nilai tukar rupiah', 'kurs rupiah', 'kurs dolar'],
    'IHSG': [
        'ihsg', 'pasar saham'],
    'Inflasi': [
        'inflasi'],
    'BI Rate': [
        'bi rate', 'suku bunga', 'bunga bi'],
    'Indonia': [
        'indonia'],
    'Crackspread_BBM': [
        'ron 92', 'pertamax', 'ron 95', 'ron 97', 'residual fo',
        'fuel oil', 'jet fuel', 'avtur', 'kerosene', 'refinery',
        'refined products', 'refining', 'oil products',
        'gasoline', 'heavy oil', 'diesel', 'gasoil',
        'naphtha', 'lpg', 'biodiesel', 'biogasoline', 'petroleum coke',
        'oil price', 'fuel cost', 'fuel price'],
    'Crackspread_NonBBM': [
        'petro', 'chemical', 'petrochemical', 'aromatic', 'olefin', 'polymer',
        'lpg', 'paraxylene', 'propylene', 'benzene', 'green coke'],
}

def _classify_article_categories(title: str, content: str) -> list:
    text = f"{title} {content}".lower()
    matched = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                matched.append(category)
                break
    return matched


# ── Main logic ────────────────────────────────────────────────────────────────
conn = pyodbc.connect(conn_str, timeout=10)
cursor = conn.cursor()

print("=== REKLASIFIKASI ARTIKEL NULL CATEGORY ===\n")

# Langkah 1: Hapus 31 duplikat (URL sudah punya kategori lain)
print("Langkah 1: Menghapus duplikat NULL (URL sudah punya kategori lain)...")
cursor.execute("""
    DELETE FROM news_articles
    WHERE category IS NULL
      AND EXISTS (
        SELECT 1 FROM news_articles na2
        WHERE na2.url = news_articles.url
          AND na2.category IS NOT NULL
      )
""")
deleted = cursor.rowcount
conn.commit()
print(f"  → {deleted} artikel duplikat dihapus.\n")

# Langkah 2: Fetch 74 artikel NULL yang perlu di-reklasifikasi
print("Langkah 2: Mengambil artikel NULL untuk reklasifikasi...")
cursor.execute("""
    SELECT id, title, content, url, source_id, published_date,
           scraped_date, language, author
    FROM news_articles
    WHERE category IS NULL
""")
null_articles = cursor.fetchall()
print(f"  → {len(null_articles)} artikel ditemukan.\n")

# Langkah 3: Reklasifikasi dan insert row baru per kategori
print("Langkah 3: Reklasifikasi dan insert...")
reclassified = 0
skipped = 0
errors = 0

for row in null_articles:
    art_id, title, content, url, source_id, published_date, scraped_date, language, author = row

    categories = _classify_article_categories(title or '', content or '')

    for category in categories:
        # Cek apakah (url, category) sudah ada
        cursor.execute(
            "SELECT 1 FROM news_articles WHERE url = ? AND category = ?",
            (url, category)
        )
        if cursor.fetchone():
            skipped += 1
            continue

        new_id = str(uuid.uuid4())
        try:
            cursor.execute("""
                INSERT INTO news_articles
                (id, title, content, url, source_id, published_date,
                 scraped_date, language, author, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (new_id, title, content, url, source_id, published_date,
                  scraped_date, language, author, category))
            reclassified += 1
        except Exception as e:
            print(f"  ✗ Error insert {url[:60]} [{category}]: {e}")
            errors += 1

conn.commit()
print(f"  → {reclassified} row baru di-insert.")
print(f"  → {skipped} sudah ada (skip).")
print(f"  → {errors} error.\n")

# Langkah 4: Hapus semua row NULL yang tersisa
print("Langkah 4: Menghapus row NULL asli...")
cursor.execute("DELETE FROM news_articles WHERE category IS NULL")
deleted_null = cursor.rowcount
conn.commit()
print(f"  → {deleted_null} row NULL dihapus.\n")

# Verifikasi akhir
cursor.execute("SELECT COUNT(*) FROM news_articles WHERE category IS NULL")
remaining_null = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM news_articles")
total = cursor.fetchone()[0]

print("=== SELESAI ===")
print(f"Total artikel: {total}")
print(f"Sisa NULL category: {remaining_null}")

conn.close()
