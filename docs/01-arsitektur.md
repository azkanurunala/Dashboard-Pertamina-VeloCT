#### 01 — Arsitektur Sistem

Dokumen ini menjelaskan arsitektur end-to-end Dashboard SPEED Pertamina Energy Institute: dari scraping sumber data sampai konsumsi di Power BI.

##### Gambaran Umum

Sistem terdiri dari 4 lapisan:

1. **Scheduler** (`src/scheduler/`) — entry point yang dipanggil GitHub Actions. Satu file per workflow. Tugasnya hanya memanggil orchestrator/scraper secara berurutan dengan `try/except` per step (satu step gagal tidak menghentikan step berikutnya).
2. **Orchestrator** (`src/orchestrators/`) — logika pipeline berita dan sentimen: daftar keyword/topik, routing keyword → scraper, filter tanggal, deduplikasi, lalu pemanggilan Gemini untuk ringkasan sentimen.
3. **Scraper** (`src/news/` dan `src/structured_data/`) — satu file per sumber data. Scraper berita mengembalikan DataFrame artikel; scraper terstruktur mengembalikan DataFrame tabular.
4. **Storage** (`src/helpers/storage_backend.py`) — abstraksi penyimpanan tunggal. Semua orchestrator dan scraper terstruktur menulis/membaca lewat singleton `storage`, tidak pernah menyentuh database/Excel langsung.

```
GitHub Actions (cron)
  └─ src/scheduler/scheduling_*.py          ← entry point per workflow
       ├─ src/orchestrators/main_news_scraping_lokal.py
       │    └─ src/news/*.py                ← ±20 scraper berita
       ├─ src/orchestrators/main_sentiment_news_*.py
       │    └─ src/helpers/summary_helper.py (Gemini)
       └─ src/structured_data/*.py          ← 9 scraper data terstruktur
            └─ src/helpers/storage_backend.py
                 ├─ _NeonBackend    → src/helpers/neon_helper.py (psycopg2)
                 └─ _OneDriveBackend→ src/helpers/onedrive_helper.py (MS Graph)
```

##### Struktur Folder

| Path | Fungsi |
|---|---|
| `.github/workflows/` | 4 workflow cron: `daily_morning.yml`, `daily_afternoon.yml`, `weekly.yml`, `monthly.yml`. Semua set `STORAGE_BACKEND: neon`, Python 3.11, Chrome (Selenium). |
| `src/scheduler/` | Entry point pipeline: `scheduling_day_morning.py`, `scheduling_day_afternoon.py`, `scheduling_week.py`, `scheduling_month.py`. |
| `src/orchestrators/` | `main_news_scraping_lokal.py`, `main_news_scraping_internasional.py` (scraping berita), `main_sentiment_news_lokal_harian.py`, `main_sentiment_news_internasional_harian.py`, `main_sentiment_news_mingguan.py` (ringkasan sentimen). Berisi peta keyword → scraper dan sheet/topik. |
| `src/news/` | Scraper per situs berita (Kompas, Kontan, CNBC, CNN, Tempo, Bloomberg Technoz, Bisnis Indonesia, BPS, Bank Indonesia, S&P Global, OilPrice, SCMP, The Guardian, dll). |
| `src/structured_data/` | Scraper data tabular: `cpo_gapki.py`, `spglobal_data.py`, `migas_eia.py`, `migas_esdm.py` (OCR), `biodiesel_esdm.py`, `bioetanol_esdm.py`, `kapasitas_esdm.py`, `nuclear_iaea_pris.py`, `wte_sipsn.py`. |
| `src/helpers/` | Infrastruktur lintas modul: `storage_backend.py` (abstraksi storage — file paling penting), `neon_helper.py` (PostgreSQL), `onedrive_helper.py` (MS Graph Excel), `summary_helper.py` (Gemini), `scraping_helper.py`, `scraping_utils.py`. |
| `src/results/` | Workbook Excel seed/target backend OneDrive: `(News)Scrapping.xlsx`, `(News)Sentiment.xlsx`, `(Terstruktur)Data Scrapping.xlsx`, `(Data)Input_Manual.xlsx`. |
| `scripts/` | Tooling operasional: DDL SQL, migrasi, backfill, monitoring scheduler, referensi Power Query. Lihat [02-migrasi-storage.md](02-migrasi-storage.md) dan [08-maintenance.md](08-maintenance.md). |
| `logs/` | Artefak run backfill lokal (`backfill.log`, `backfill.pid`). Pipeline produksi log ke stdout GitHub Actions. |
| `src/code_scrapping/` | **Legacy mati** — hanya berisi `.pyc` tanpa sumber `.py`. Kandidat dihapus. |

##### Alur Data End-to-End

###### Berita → sentimen

1. Orchestrator berita (`main_news_scraping_lokal.py` / `_internasional.py`) membaca sheet berita existing via `storage.read_all_news_sheets()`, menjalankan scraper per keyword/topik, dedup terhadap URL yang sudah ada, lalu `storage.write_news_file()` → tabel `news_articles` (kolom `topic` = nama sheet Excel, mis. `(News)Harga Minyak`).
2. Orchestrator sentimen membaca artikel terbaru per topik, membangun prompt analis berbahasa Indonesia, memanggil Gemini (`summary_helper.py`), lalu `storage.write_sentiment_file()` → tabel `news_sentiment` (kolom `topic` = nama sheet `(Summary)...`).

###### Data terstruktur

Setiap scraper `structured_data/*.py` mengambil data dari situs/API sumber, membentuk DataFrame dengan kolom persis seperti sheet Excel aslinya, lalu `storage.write_structured_sheet("(Data)Nama", df)` → upsert ke tabel `data_*` sesuai peta `SHEET_TO_TABLE`.

###### Konsumsi Power BI

Power BI (mode Import) membaca tabel `news_articles`/`news_sentiment` (difilter per `topic`) dan view `vw_*` untuk data terstruktur. Detail di [07-power-bi.md](07-power-bi.md).

##### Prinsip Desain Penting

- **Backend-agnostic:** kode scraper tidak tahu datanya masuk ke PostgreSQL atau Excel. Satu-satunya switch adalah env `STORAGE_BACKEND` (lihat [02-migrasi-storage.md](02-migrasi-storage.md)).
- **Idempoten via upsert:** semua tulis ke Neon memakai `INSERT ... ON CONFLICT ... DO UPDATE` dengan conflict key per tabel ([03-database.md](03-database.md)). Menjalankan ulang pipeline tidak menggandakan data.
- **Kompatibilitas nama Excel:** nama sheet, nama kolom (termasuk huruf besar/spasi, di-quote di SQL), dan bentuk data dipertahankan persis seperti era Excel supaya Power Query hanya perlu ganti sumber, bukan ganti transformasi.
- **Toleransi kegagalan per step:** scheduler membungkus tiap step dengan `try/except` + `traceback.print_exc()`; kegagalan satu scraper tidak membatalkan scraper lain.
- **Mode CI vs lokal:** env `CI=true` (diset workflow) membuat orchestrator berita men-scrape "kemarin"; di lokal memakai rentang `START_DATE`/`END_DATE` yang di-hardcode di orchestrator.
