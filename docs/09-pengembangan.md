# 09 — Panduan Pengembangan Lanjutan

## Setup Lokal

```bash
git clone https://github.com/shelmasalsa17/Dashboard-Pertamina-VeloCT.git
cd Dashboard-Pertamina-VeloCT
python -m venv .venv
.venv\Scripts\activate                      # Windows (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt psycopg2-binary
# hanya bila mengerjakan OCR ESDM:
pip install -r requirements-ocr.txt --extra-index-url https://download.pytorch.org/whl/cpu
copy .env.example .env                       # isi kredensial (minta lewat jalur aman)
```

Python 3.11 (samakan dengan CI). Chrome terpasang lokal diperlukan untuk scraper Selenium (IAEA, beberapa berita).

### Pilih backend saat dev

- `STORAGE_BACKEND=onedrive` (default) — aman untuk eksperimen, menulis ke Excel OneDrive, tidak menyentuh DB produksi. Butuh kredensial `MS_*`.
- `STORAGE_BACKEND=neon` — menulis ke database produksi. **Hati-hati**: tidak ada database staging. Untuk uji tulis yang aman, buat [branch database di Neon](https://neon.tech/docs/introduction/branching) dan arahkan `NEON_DB_URL` ke branch itu.

### Menjalankan komponen secara terpisah

```bash
python src/scheduler/scheduling_day_morning.py     # pipeline penuh
# satu scraper saja:
python -c "import sys; sys.path.append('src'); from structured_data.migas_eia import main_eia; main_eia()"
```

Perhatikan: di lokal (tanpa `CI=true`) orchestrator berita memakai `START_DATE`/`END_DATE` hardcoded — sesuaikan dulu di file orchestrator.

## Checklist: Menambah Sumber Data Terstruktur Baru

Ikuti pola scraper yang ada (contoh paling sederhana: `cpo_gapki.py`; dengan auth API: `migas_eia.py`).

1. **Scraper** — buat `src/structured_data/nama_sumber.py`:
   - Fungsi `main_*()` sebagai entry point.
   - Hasil akhir: DataFrame dengan nama kolom final (kapitalisasi bebas — akan di-quote di SQL).
   - Simpan: `storage.write_structured_sheet("(Data)NamaSheet", df)`.
2. **Registrasi mapping** — di [src/helpers/storage_backend.py](../src/helpers/storage_backend.py):
   - `SHEET_TO_TABLE`: `"(Data)NamaSheet": "data_nama_sumber"`.
   - `SHEET_CONFLICT_COLS`: kolom kunci upsert (kolom yang mengidentifikasi baris unik, mis. tanggal/periode).
3. **DDL** — tambah `CREATE TABLE IF NOT EXISTS data_nama_sumber (...)` di [scripts/create_tables.sql](../scripts/create_tables.sql) **dengan `UNIQUE (...)` yang sama persis dengan conflict cols** (upsert gagal tanpa itu). Jalankan `python scripts/run_schema.py`.
4. **View** — tambah `CREATE OR REPLACE VIEW vw_nama_sumber AS SELECT <kolom tanpa id> FROM data_nama_sumber;` di [scripts/create_views.sql](../scripts/create_views.sql), jalankan via psql.
5. **Scheduler** — panggil `main_*()` dari scheduler yang sesuai (`scheduling_month.py` dst.) dengan pola `try/except` + banner step yang sama. Bila perlu jadwal tanggal khusus, tambah konstanta `DAY_*` dan sinkronkan cron `monthly.yml` ([04-pipeline-scheduling.md](04-pipeline-scheduling.md)).
6. **Secrets** (bila sumber butuh auth) — tambah env var di `.env.example`, `.env`, GitHub Secrets, dan blok `env:` workflow terkait.
7. **Power BI** — buat query M baru dari `vw_nama_sumber` ([07-power-bi.md](07-power-bi.md)) dan catat di `scripts/power_query_migrated.txt`.
8. **Monitoring/backfill** (opsional) — tambahkan ke `scripts/backfill.py` bila butuh pengisian historis.
9. **Dokumentasi** — daftarkan di tabel [05-sumber-data.md](05-sumber-data.md) dan [03-database.md](03-database.md).

## Checklist: Menambah Scraper / Topik Berita

- **Situs berita baru:** buat `src/news/nama_situs.py` meniru scraper serupa (sitemap → `kompas.py`/`cnn.py`; RSS → `tempo.py`/`oilprice.py`; search → `bisnis_indonesia.py`). Kontrak: fungsi menerima `(keyword, date_filter)` dan mengembalikan DataFrame `title, date, url, content, source, keyword`.
- **Registrasi:** tambahkan ke dict keyword → scraper di `main_news_scraping_lokal.py` atau `_internasional.py`.
- **Topik baru:** tambah nilai sheet `(News)Topik Baru` di daftar sheet aktif orchestrator + mapping keyword. Tidak perlu DDL — semua topik masuk `news_articles`.
- **Mengaktifkan topik nonaktif:** banyak topik sudah ada tapi dikomentari di dict orchestrator (lihat [05-sumber-data.md](05-sumber-data.md)) — cukup uncomment.
- **Sentimen untuk topik baru:** daftarkan sheet `(Summary)Topik` di orchestrator sentimen yang sesuai (harian lokal/intl atau mingguan; di mingguan banyak yang tinggal di-uncomment).

## Mengubah Jadwal / Menambah Workflow

Lihat [04-pipeline-scheduling.md](04-pipeline-scheduling.md) bagian "Mengubah Jadwal". Ingat 3 hal: cron dalam UTC, hanya jalan dari `main`, dan update `scripts/check_workflow_schedules.py` agar monitoring mengikuti.

## Mengganti Model / Provider AI

Lihat [06-ai-sentiment.md](06-ai-sentiment.md). Ganti model Gemini = satu baris di `summary_helper.py:34`. Ganti provider = rewrite `setup_gemini()`/`summarize_all_news()` + secrets workflow.

## Konvensi Kode Proyek Ini

- **Logging = `print`** dengan prefix `[Main]`/`[NamaScraper]` + banner `===`/`---`. Tidak ada modul `logging`. Konsisten saja dengan pola ini (log terbaca di GitHub Actions).
- **Error handling:** `try/except Exception` per step/scraper + `traceback.print_exc()`; jangan biarkan satu sumber mematikan pipeline. Exit code ≠ 0 hanya untuk kegagalan fatal seluruh pipeline.
- **Idempoten:** semua tulis harus upsert-safe. Jangan pernah `INSERT` polos ke tabel ber-UNIQUE; selalu lewat `storage.write_*` yang memakai `upsert_df`.
- **Nama kolom = kontrak dengan Power BI.** Mengubah nama/kapitalisasi kolom akan memutus Power Query dan view. Bila terpaksa, ubah serempak: scraper → DDL → view → M-code.
- **Ejaan `crackspread` vs `crackspeed` disengaja** ([03-database.md](03-database.md)) — jangan diseragamkan.
- **Import path:** scheduler menambah `src/` ke `sys.path`; modul saling import tanpa prefix `src.` (`from helpers.storage_backend import storage`). Jalankan script dari root repo.
- **Branch:** kerja di `dev`, merge ke `main` untuk produksi (cron hanya membaca `main`). PR ke `main`.

## Ide Pengembangan Prioritas (backlog saran)

1. **Scraper seri makroekonomi** (BI-Rate, Kurs, Inflasi, dst.) → Neon, supaya SharePoint bisa dipensiunkan sepenuhnya ([07-power-bi.md](07-power-bi.md)). Sebagian sumber sudah ada scraper-nya (BI, BPS) tinggal diarahkan ke tabel data.
2. **Notifikasi kegagalan** — step terakhir workflow yang mengirim alert (email/Telegram) bila ada step gagal, atau jadwalkan `check_workflow_schedules.py` sebagai workflow tersendiri.
3. **UNIQUE untuk `data_harga_ebt`** + registrasi conflict key.
4. **Bersihkan legacy:** folder `src/code_scrapping/`, env Google Sheets, secrets OneDrive di workflow (setelah dipastikan tak dipakai).
5. **Database staging** via Neon branching untuk pengujian pipeline tanpa risiko ke produksi.
