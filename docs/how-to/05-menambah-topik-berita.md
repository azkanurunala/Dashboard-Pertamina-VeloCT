#### How-To 5: Menambah / Mengaktifkan Topik Berita

Dua kasus: (A) topik sudah ada tapi nonaktif (dikomentari) — paling sering; (B) topik benar-benar baru.

##### A. Mengaktifkan Topik yang Dikomentari

Contoh: mengaktifkan kembali `(News)IHSG` di pipeline lokal.

1. Buka [src/orchestrators/main_news_scraping_lokal.py](../../src/orchestrators/main_news_scraping_lokal.py) (atau `_internasional.py` untuk topik intl).
2. Un-comment baris topik di **tiga** tempat (semuanya di file yang sama, sekitar baris 393–510):
   - `SUMBER_DICT` — keyword → daftar scraper
   - `SHEET_TO_KEYWORD` — sheet → keyword
   - `ACTIVE_SHEETS` — daftar sheet aktif
3. Bila ingin summary-nya juga: un-comment blok topik di `TOPICS` pada orchestrator sentiment terkait (`main_sentiment_news_lokal_harian.py` / `_internasional_harian.py` / `_mingguan.py`).
4. Uji lokal satu keyword (tanpa menunggu jadwal):
   ```bash
   set STORAGE_BACKEND=onedrive
   python -c "import sys; sys.path.append('src'); from orchestrators.main_news_scraping_lokal import scrape_keyword; df=scrape_keyword('ihsg ', '2026-07-03'); print(len(df) if df is not None else 0)"
   ```
   **Verifikasi:** jumlah baris > 0 untuk tanggal dengan berita.
5. Commit → merge ke `main`. Mulai run terjadwal berikutnya topik ikut ter-scrape.
6. Isi data historisnya: [How-To 4](04-backfill-data-bolong.md) bagian B lalu C.

> Tidak perlu perubahan database — semua topik berita masuk tabel `news_articles` (kolom `topic`), summary masuk `news_sentiment`.

##### B. Topik Benar-Benar Baru

1. Tentukan: nama sheet `(News)Nama Topik`, keyword pencarian (akhiri spasi, konsisten dengan pola existing), scraper mana yang relevan.
2. Tambahkan entri **baru** di `SUMBER_DICT`, `SHEET_TO_KEYWORD`, `ACTIVE_SHEETS` (file orchestrator lokal dan/atau intl).
3. (Opsional summary) tambah blok di `TOPICS` orchestrator sentiment dengan `output_sheet: "(Summary)Nama Topik"` — pola blok tinggal copy dari topik lain.
4. Uji seperti langkah A.4, commit, merge ke `main`.
5. Power BI: buat query baru dari `news_articles` filter `[topic] = "(News)Nama Topik"` ([How-To 7](07-koneksi-power-bi-neon.md) pola M-code), dan dari `news_sentiment` untuk summary-nya.
6. Catat topik baru di [docs/05-sumber-data.md](../05-sumber-data.md).

##### Menambah Scraper Situs Baru (bila sumbernya belum ada)

1. Buat `src/news/nama_situs.py` meniru scraper serupa: sitemap → contoh `cnn.py`; RSS → `oilprice.py`; halaman pencarian → `bisnis_indonesia.py`.
2. Kontrak fungsi: terima `(keyword, tanggal_filter)`, kembalikan DataFrame kolom `title, date, url, content, source, keyword`.
3. Import + daftarkan di `SUMBER_DICT` orchestrator.
4. Uji: panggil fungsinya langsung dengan satu keyword + tanggal kemarin; pastikan kolom lengkap dan `date` sesuai filter.
