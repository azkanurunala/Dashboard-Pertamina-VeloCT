# Panduan News Scraping dengan Google RSS Fallback

## 📋 Overview

Sistem ini menggabungkan scraping dari platform berita (CNBC, Kompas, Tempo, dll) dengan Google News RSS sebagai backup untuk mengatasi artikel yang hilang dari indexing platform.

### Alur Kerja:
1. **Scrape dari platform asli** (CNBC, Kompas, Tempo, dll)
2. **Scrape dari Google News RSS** untuk keyword yang sama
3. **Merge & Deduplikasi** - jika ada URL duplicate, yang dari platform asli dipertahankan

## 🚀 Cara Penggunaan

### 1. Import Module

```python
from helpers.news_scraper_helper import (
    scrape_cnbc_with_rss,
    scrape_kompas_with_rss,
    scrape_tempo_with_rss,
    scrape_all_platforms_with_rss,
    save_to_excel
)
```

### 2. Scraping Single Platform

#### CNBC + Google RSS
```python
df = scrape_cnbc_with_rss(
    keyword="pertamina",
    tanggal="2025-12-30"  # Optional, bisa None
)
```

#### Kompas + Google RSS
```python
df = scrape_kompas_with_rss(
    keyword="biodiesel",
    tanggal="2025-12-30"
)
```

#### Tempo + Google RSS
```python
df = scrape_tempo_with_rss(
    keyword="migas",
    tanggal="2025-12-30"
)
```

### 3. Scraping Multiple Platform Sekaligus

```python
df = scrape_all_platforms_with_rss(
    keyword="pertamina",
    tanggal="2025-12-30",
    platforms=['cnbc', 'kompas', 'tempo']  # Optional, default semua
)

# Save hasil
save_to_excel(df, keyword="pertamina")
```

## 📊 Format Data Output

DataFrame hasil scraping memiliki kolom:

| Column | Description | Source |
|--------|-------------|--------|
| `title` | Judul artikel | Platform/RSS |
| `date` | Tanggal publikasi (YYYY-MM-DD) | Platform/RSS |
| `url` | URL artikel asli | Platform/RSS |
| `content` | Konten artikel | Platform only |
| `platform` | Sumber platform (cnbc/kompas/tempo/google_rss) | System |
| `source` | Nama media (hanya untuk Google RSS) | RSS only |

## 🔧 Konfigurasi

### Format Tanggal

Sistem mendukung berbagai format tanggal:
- `"2025-12-30"` (YYYY-MM-DD) ✅ Recommended
- `"30 Dec 2025"` (DD MMM YYYY)
- `datetime` object
- `None` untuk semua tanggal

### Platform yang Didukung

Saat ini sistem mendukung:
- ✅ `cnbc` - CNBC Indonesia
- ✅ `kompas` - Kompas.com
- ✅ `tempo` - Tempo.co
- 🔄 Google News RSS (automatic fallback)

## 🎯 Fitur Utama

### 1. Auto-Scraping Konten (NEW! 🔥)

Sistem otomatis scrape konten untuk artikel dari Google RSS yang tidak punya konten:
- ✅ **URL Resolution** - Follow redirect dari Google News untuk mendapatkan URL artikel asli
- ✅ Deteksi artikel dengan konten kosong (dari Google RSS)
- ✅ Smart content scraper berdasarkan domain URL
- ✅ Support untuk CNBC, Kompas, Tempo, dan platform lainnya
- ✅ Fallback ke generic scraper untuk platform tidak dikenal
- ✅ Rate limiting otomatis untuk menghindari blocking

**Cara kerja:**
```
Google RSS → Follow Redirect → Get Real URL → Detect domain → Use specific scraper → Fill content
```

**Contoh URL Resolution:**
```
Input:  https://news.google.com/rss/articles/CBMiWkFV...
Output: https://www.bbc.com/news/articles/c3rxl4p8w79o
                     ↑
              Real article URL!
```

**Contoh:**
```python
# Auto-scrape content (default)
df = scrape_cnbc_with_rss(keyword="pertamina", tanggal="2025-12-30")
# Artikel dari Google RSS akan otomatis di-scrape kontennya

# Skip content scraping (lebih cepat, tapi konten Google RSS kosong)
df = scrape_cnbc_with_rss(keyword="pertamina", tanggal="2025-12-30", scrape_content=False)
```

### 2. Deduplication Otomatis

Sistem otomatis menghapus artikel duplicate berdasarkan URL yang dinormalisasi:
- Menghapus protocol (`http://`, `https://`)
- Menghapus `www.`
- Menghapus query parameters (`?...`)
- Menghapus trailing slash
- Case-insensitive

**Contoh URL yang dianggap sama:**
```
https://www.cnbcindonesia.com/news/article-123
http://cnbcindonesia.com/news/article-123/
cnbcindonesia.com/news/article-123?utm_source=google
```

### 3. Prioritas Platform Asli

Jika artikel ditemukan di:
- ✅ **Platform asli (CNBC, Kompas, dll)** → Dipertahankan (dengan konten lengkap)
- ❌ **Google RSS** → Di-drop jika duplicate

### 4. Google RSS sebagai Safety Net

Artikel yang **HANYA** ada di Google RSS tetap diambil jika:
- Tidak ditemukan di platform asli
- Sudah hilang dari indexing platform

## 💡 Use Cases

### Use Case 1: Scraping Harian

```python
from datetime import datetime
from helpers.news_scraper_helper import scrape_all_platforms_with_rss, save_to_excel

# Scraping untuk hari ini
today = datetime.now().strftime('%Y-%m-%d')

df = scrape_all_platforms_with_rss(
    keyword="pertamina",
    tanggal=today
)

if df is not None:
    save_to_excel(df, keyword="pertamina")
    print(f"Total artikel: {len(df)}")
    print(f"Breakdown: {df['platform'].value_counts()}")
```

### Use Case 2: Scraping Mingguan (Tanpa Filter Tanggal)

```python
df = scrape_all_platforms_with_rss(
    keyword="biodiesel",
    tanggal=None  # Ambil semua artikel yang tersedia
)
```

### Use Case 3: Compare Platform vs Google RSS

```python
from code_scrapping.cnbc_id import main_cnbc
from code_scrapping.scrapping_google_news import main_google_news

# Scrape dari CNBC saja
df_cnbc = main_cnbc(keyword="pertamina", tanggal="2025-12-30")

# Scrape dari Google RSS saja
df_google = main_google_news(keyword="pertamina", tanggal="2025-12-30")

print(f"CNBC: {len(df_cnbc) if df_cnbc is not None else 0} artikel")
print(f"Google RSS: {len(df_google) if df_google is not None else 0} artikel")

# Bandingkan URL
if df_cnbc is not None and df_google is not None:
    cnbc_urls = set(df_cnbc['url'])
    google_urls = set(df_google['url'])

    print(f"Hanya di CNBC: {len(cnbc_urls - google_urls)}")
    print(f"Hanya di Google: {len(google_urls - cnbc_urls)}")
    print(f"Di kedua-duanya: {len(cnbc_urls & google_urls)}")
```

## ⚙️ Integrasi dengan Existing Code

### Update Main Sentiment Analysis

Untuk mengintegrasikan dengan main sentiment analysis yang sudah ada:

```python
# main_sentiment_news_harian.py atau main_sentiment_news_mingguan.py

# Before (tanpa Google RSS):
from code_scrapping.cnbc_id import main_cnbc
df = main_cnbc(keyword=keyword, tanggal=tanggal)

# After (dengan Google RSS fallback):
from helpers.news_scraper_helper import scrape_cnbc_with_rss
df = scrape_cnbc_with_rss(keyword=keyword, tanggal=tanggal)
```

Atau untuk scraping dari multiple platform:

```python
from helpers.news_scraper_helper import scrape_all_platforms_with_rss

df = scrape_all_platforms_with_rss(
    keyword=keyword,
    tanggal=tanggal,
    platforms=['cnbc', 'kompas', 'tempo']
)
```

## 🐛 Troubleshooting

### Issue: Google RSS tidak mengembalikan hasil

**Penyebab:**
- Keyword terlalu spesifik
- Google News belum mengindex artikel
- Rate limiting

**Solusi:**
```python
# Coba keyword yang lebih general
df = scrape_cnbc_with_rss(
    keyword="pertamina",  # Instead of "pertamina hulu rokan"
    tanggal=tanggal
)
```

### Issue: Terlalu banyak duplicate

**Penyebab:**
- Artikel sama dipublikasikan di multiple platform

**Solusi:**
Sistem sudah otomatis handle deduplication. Untuk custom handling:

```python
df = scrape_all_platforms_with_rss(...)

# Manual deduplication berdasarkan title similarity
df = df.drop_duplicates(subset=['title'], keep='first')
```

### Issue: Konten artikel kosong dari Google RSS

**SUDAH TERATASI! ✅**

Sistem sekarang otomatis scrape konten untuk artikel Google RSS:

```python
# Auto-scrape content (default behavior)
df = scrape_cnbc_with_rss(keyword="pertamina", tanggal="2025-12-30")
# Artikel dari Google RSS akan otomatis di-scrape kontennya!

# Jika ingin skip content scraping (lebih cepat):
df = scrape_cnbc_with_rss(keyword="pertamina", tanggal="2025-12-30", scrape_content=False)
```

**Manual scraping (jika diperlukan):**
```python
from helpers.content_scraper_helper import scrape_article_content

for idx, row in df.iterrows():
    if row['content'] == '':
        content = scrape_article_content(row['url'])
        df.at[idx, 'content'] = content
```

## 📈 Performance Tips

1. **Gunakan tanggal filter** untuk mengurangi waktu scraping
2. **Pilih platform spesifik** daripada scrape semua platform
3. **Skip content scraping** jika hanya butuh metadata (lebih cepat 5-10x):
   ```python
   df = scrape_cnbc_with_rss(keyword="pertamina", scrape_content=False)
   ```
4. **Cache hasil** untuk keyword yang sering digunakan
5. **Rate limiting** otomatis sudah diimplementasikan (0.5s delay per artikel)

## 🔐 Best Practices

1. ✅ Selalu gunakan tanggal filter untuk scraping harian
2. ✅ Validasi hasil sebelum save ke database/Excel
3. ✅ Log semua error untuk monitoring
4. ✅ Respect rate limits dari platform
5. ✅ Backup hasil scraping secara berkala

## 📝 Example: Complete Workflow

```python
from datetime import datetime
from helpers.news_scraper_helper import scrape_all_platforms_with_rss, save_to_excel

def daily_news_scraping(keywords):
    """
    Scraping harian untuk multiple keywords
    """
    today = datetime.now().strftime('%Y-%m-%d')
    results = {}

    for keyword in keywords:
        print(f"\n{'='*80}")
        print(f"Scraping keyword: {keyword}")
        print(f"{'='*80}")

        df = scrape_all_platforms_with_rss(
            keyword=keyword,
            tanggal=today,
            platforms=['cnbc', 'kompas', 'tempo']
        )

        if df is not None and not df.empty:
            filename = save_to_excel(df, keyword=keyword)
            results[keyword] = {
                'total': len(df),
                'filename': filename,
                'platforms': df['platform'].value_counts().to_dict()
            }
        else:
            results[keyword] = None

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    for keyword, result in results.items():
        if result:
            print(f"\n{keyword}:")
            print(f"  Total: {result['total']} articles")
            print(f"  File: {result['filename']}")
            print(f"  Platforms: {result['platforms']}")
        else:
            print(f"\n{keyword}: No results")

    return results

# Run
keywords = ["pertamina", "biodiesel", "migas", "kurs"]
results = daily_news_scraping(keywords)
```

---

**Created:** 2025-12-31
**Version:** 1.0.0
**Author:** VeloCT Development Team
