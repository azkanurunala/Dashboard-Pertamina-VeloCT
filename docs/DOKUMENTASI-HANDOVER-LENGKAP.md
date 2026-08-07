#### Dokumentasi Lengkap — Dashboard SPEED Pertamina Energy Institute

> Dokumen gabungan (auto-generated oleh `scripts/generate_mega_doc.py`) dari 24 file di `docs/`, `docs/how-to/`, `docs/handover/`. Sumber kebenaran tetap file per-topik; jalankan ulang script bila ada perubahan.

##### Daftar Isi

**Referensi Teknis**

- [01 — Arsitektur Sistem](#sec-01-arsitektur-md)
- [02 — Migrasi Storage: OneDrive Excel → Neon PostgreSQL](#sec-02-migrasi-storage-md)
- [03 — Database Neon PostgreSQL](#sec-03-database-md)
- [04 — Pipeline & Scheduling (GitHub Actions)](#sec-04-pipeline-scheduling-md)
- [05 — Sumber Data & Scraper](#sec-05-sumber-data-md)
- [06 — AI & Analisis Sentimen Berita](#sec-06-ai-sentiment-md)
- [07 — Power BI & Power Query](#sec-07-power-bi-md)
- [08 — Runbook Maintenance](#sec-08-maintenance-md)
- [09 — Panduan Pengembangan Lanjutan](#sec-09-pengembangan-md)

**How-To (Langkah-demi-Langkah)**

- [How-To: Panduan Langkah-demi-Langkah](#sec-how-to-readme-md)
- [How-To 1: Setup Lokal dari Nol](#sec-how-to-01-setup-lokal-dari-nol-md)
- [How-To 2: Menjalankan Pipeline Manual](#sec-how-to-02-menjalankan-pipeline-manual-md)
- [How-To 3: Cek Kesehatan Scheduler](#sec-how-to-03-cek-kesehatan-scheduler-md)
- [How-To 4: Backfill Data Bolong](#sec-how-to-04-backfill-data-bolong-md)
- [How-To 5: Menambah / Mengaktifkan Topik Berita](#sec-how-to-05-menambah-topik-berita-md)
- [How-To 6: Menambah Sumber Data Terstruktur](#sec-how-to-06-menambah-sumber-terstruktur-md)
- [How-To 7: Menyambungkan Power BI ke Neon](#sec-how-to-07-koneksi-power-bi-neon-md)
- [How-To 8: Rotasi Kredensial](#sec-how-to-08-rotasi-kredensial-md)
- [How-To 9: Backup & Restore Database Neon](#sec-how-to-09-backup-restore-neon-md)

**Paket Serah Terima (Handover)**

- [Berita Acara Serah Terima (BAST)](#sec-handover-01-bast-md)
- [Inventaris Aset & Akses](#sec-handover-02-inventaris-aset-akses-md)
- [Runbook Operator Hari Pertama](#sec-handover-03-runbook-hari-pertama-md)
- [Biaya & Lisensi](#sec-handover-04-biaya-lisensi-md)
- [Diagram Alur Data End-to-End](#sec-handover-05-diagram-alur-data-md)

---

<a id="sec-01-arsitektur-md"></a>

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
| `scripts/` | Tooling operasional: DDL SQL, migrasi, backfill, monitoring scheduler, referensi Power Query. Lihat [bagian “02 — Migrasi Storage: OneDrive Excel → Neon PostgreSQL”](#sec-02-migrasi-storage-md) dan [bagian “08 — Runbook Maintenance”](#sec-08-maintenance-md). |
| `logs/` | Artefak run backfill lokal (`backfill.log`, `backfill.pid`). Pipeline produksi log ke stdout GitHub Actions. |
| `src/code_scrapping/` | **Legacy mati** — hanya berisi `.pyc` tanpa sumber `.py`. Kandidat dihapus. |

##### Alur Data End-to-End

###### Berita → sentimen

1. Orchestrator berita (`main_news_scraping_lokal.py` / `_internasional.py`) membaca sheet berita existing via `storage.read_all_news_sheets()`, menjalankan scraper per keyword/topik, dedup terhadap URL yang sudah ada, lalu `storage.write_news_file()` → tabel `news_articles` (kolom `topic` = nama sheet Excel, mis. `(News)Harga Minyak`).
2. Orchestrator sentimen membaca artikel terbaru per topik, membangun prompt analis berbahasa Indonesia, memanggil Gemini (`summary_helper.py`), lalu `storage.write_sentiment_file()` → tabel `news_sentiment` (kolom `topic` = nama sheet `(Summary)...`).

###### Data terstruktur

Setiap scraper `structured_data/*.py` mengambil data dari situs/API sumber, membentuk DataFrame dengan kolom persis seperti sheet Excel aslinya, lalu `storage.write_structured_sheet("(Data)Nama", df)` → upsert ke tabel `data_*` sesuai peta `SHEET_TO_TABLE`.

###### Konsumsi Power BI

Power BI (mode Import) membaca tabel `news_articles`/`news_sentiment` (difilter per `topic`) dan view `vw_*` untuk data terstruktur. Detail di [bagian “07 — Power BI & Power Query”](#sec-07-power-bi-md).

##### Prinsip Desain Penting

- **Backend-agnostic:** kode scraper tidak tahu datanya masuk ke PostgreSQL atau Excel. Satu-satunya switch adalah env `STORAGE_BACKEND` (lihat [bagian “02 — Migrasi Storage: OneDrive Excel → Neon PostgreSQL”](#sec-02-migrasi-storage-md)).
- **Idempoten via upsert:** semua tulis ke Neon memakai `INSERT ... ON CONFLICT ... DO UPDATE` dengan conflict key per tabel ([bagian “03 — Database Neon PostgreSQL”](#sec-03-database-md)). Menjalankan ulang pipeline tidak menggandakan data.
- **Kompatibilitas nama Excel:** nama sheet, nama kolom (termasuk huruf besar/spasi, di-quote di SQL), dan bentuk data dipertahankan persis seperti era Excel supaya Power Query hanya perlu ganti sumber, bukan ganti transformasi.
- **Toleransi kegagalan per step:** scheduler membungkus tiap step dengan `try/except` + `traceback.print_exc()`; kegagalan satu scraper tidak membatalkan scraper lain.
- **Mode CI vs lokal:** env `CI=true` (diset workflow) membuat orchestrator berita men-scrape "kemarin"; di lokal memakai rentang `START_DATE`/`END_DATE` yang di-hardcode di orchestrator.


---

<a id="sec-02-migrasi-storage-md"></a>

#### 02 — Migrasi Storage: OneDrive Excel → Neon PostgreSQL

##### Latar Belakang

Sampai pertengahan 2026, seluruh hasil scraping disimpan sebagai 3 file Excel di OneDrive/SharePoint (via MS Graph API):

| File Excel (OneDrive) | Isi | Env path |
|---|---|---|
| `(News)Scrapping.xlsx` | Artikel berita, 1 sheet per topik `(News)...` | `ONEDRIVE_FILE_PATH` |
| `(News)Sentiment.xlsx` | Ringkasan sentimen, 1 sheet per topik `(Summary)...` | `ONEDRIVE_SENTIMENT_PATH` |
| `(Terstruktur)Data Scrapping.xlsx` | Data tabular, 1 sheet per dataset `(Data)...` | `ONEDRIVE_DATA_PATH` |

Masalahnya: file Excel sebagai "database" rapuh (lock, corrupt, race antar pipeline), lambat, dan menyulitkan query. Pada awal Juli 2026 (commit `508e3cda`, 2026-07-02) storage produksi dipindah ke **Neon PostgreSQL**.

**Kenapa Neon:** free tier 512 MB cukup, compute auto-suspend dan resume <1 detik (dibanding Supabase yang mem-pause seluruh project setelah 1 minggu tidak aktif — fatal untuk pipeline harian).

##### Mekanisme Switch: `STORAGE_BACKEND`

Semua baca/tulis lewat satu modul: [src/helpers/storage_backend.py](../src/helpers/storage_backend.py).

```
STORAGE_BACKEND=onedrive  → _OneDriveBackend (default; dev lokal / legacy)
STORAGE_BACKEND=neon      → _NeonBackend     (produksi; semua GitHub Actions)
```

Modul mengekspor singleton `storage` yang dipakai semua orchestrator dan scraper terstruktur:

```python
from helpers.storage_backend import storage

# Berita
all_sheets = storage.read_all_news_sheets(ACTIVE_SHEETS)  # dict[str, DataFrame]
df = storage.read_news_sheet(sheet_name)
storage.write_news_file(all_sheets)                       # upsert (neon) / upload (onedrive)

# Sentimen
all_sheets = storage.read_all_sentiment_sheets(sheet_names)
df = storage.read_sentiment_sheet(sheet_name)
storage.write_sentiment_file(all_sheets)

# Data terstruktur
df = storage.read_structured_sheet("(Data)Biodesel")
storage.write_structured_sheet("(Data)Biodesel", df)
```

Kedua backend mengimplementasikan interface yang sama, jadi scraper tidak perlu tahu backend aktif.

###### Pemetaan sheet → tabel

Di backend Neon, nama sheet Excel dipetakan ke tabel PostgreSQL lewat dict `SHEET_TO_TABLE` dan kunci upsert `SHEET_CONFLICT_COLS` (keduanya di `storage_backend.py`). Daftar lengkap ada di [bagian “03 — Database Neon PostgreSQL”](#sec-03-database-md). Ringkas:

- Semua sheet `(News)*` → **satu** tabel `news_articles`, dibedakan kolom `topic`.
- Semua sheet `(Summary)*` → **satu** tabel `news_sentiment`, dibedakan kolom `topic`.
- Tiap sheet `(Data)*` → tabel `data_*` masing-masing.

###### Transformasi khusus di backend Neon

- **IAEA wide↔long:** sheet `(Data)IAEA_Nuclear_Capacity` dan `(Data)IAEA_Electrical` di Excel berbentuk wide (baris = tahun, kolom = negara). Di PostgreSQL disimpan long (`year, country, value_mw/value_twh`). Fungsi `_melt_iaea` (saat tulis) dan `_pivot_iaea` (saat baca) di `storage_backend.py` membuat transformasi ini transparan — scraper tetap bekerja dengan format wide.
- **WTE dynamic schema:** kolom data SIPSN berubah-ubah, jadi tabel `data_wte_*` dibuat/di-ALTER otomatis dari dtype DataFrame via `create_table_if_needed()` di [src/helpers/neon_helper.py](../src/helpers/neon_helper.py).

##### Apa yang Sudah Migrasi vs Belum

| Kategori | Status |
|---|---|
| Berita (`news_articles`) | ✅ Neon |
| Sentimen (`news_sentiment`) | ✅ Neon |
| Semua data terstruktur hasil scraping (`data_*`) | ✅ Neon |
| Tabel statis `data_ruptl`, `data_harga_ebt` | ✅ Neon (diisi sekali dari Excel) |
| **Seri makroekonomi** (BI-Rate, Kurs, PMI, Inflasi, IHSG, PDB, Neraca Perdagangan, Geopolitik, Volatilitas, dst. dari `(Data)Makro.xlsx`) | ❌ **Masih SharePoint** — tidak ada scraper-nya, diupdate manual. Power Query-nya bertanda `[UNCHANGED]`. |
| `(Data)Input_Fosil_Prediction` dari `(Data)Input_Manual.xlsx` | ❌ Masih SharePoint (input manual) |

Konsekuensi: **OneDrive/SharePoint belum bisa dimatikan total.** Secrets `MS_*` dan `ONEDRIVE_*` masih diinject ke semua workflow (dipakai bila fallback ke backend onedrive dan oleh script migrasi).

##### Script Migrasi & Backfill

###### Setup skema (sekali per database)

```bash
python scripts/run_schema.py            # menjalankan scripts/create_tables.sql
psql $NEON_DB_URL -f scripts/create_views.sql
```

###### Migrasi data Excel → Neon (one-time)

[scripts/migrate_excel_to_neon.py](../scripts/migrate_excel_to_neon.py) membaca semua sheet dari OneDrive lalu upsert ke Neon. Tabel WTE dikecualikan (kolom dinamis) — jalankan `wte_sipsn.py` dengan `STORAGE_BACKEND=neon` sebagai gantinya.

```bash
# butuh .env lengkap (kredensial MS Graph + NEON_DB_URL)
python scripts/migrate_excel_to_neon.py
```

###### Backfill historis (gap Okt 2025 – Jun 2026)

[scripts/backfill.py](../scripts/backfill.py) mengisi kekosongan data historis. Dapat di-interrupt dan di-resume — progres disimpan ke `scripts/backfill_progress.json` setelah tiap unit kerja.

```bash
python scripts/backfill.py                                        # semua sumber
python scripts/backfill.py --sources eia spglobal_saf news_lokal  # sumber tertentu
python scripts/backfill.py --start 2025-10-01 --end 2025-12-31    # rentang custom
python scripts/backfill.py --sources news_lokal --resume-from 2026-01-15
python scripts/backfill.py --delay 5.0                            # rate-limit lebih pelan
```

Tier sumber (lihat docstring file untuk daftar penuh):
- **Tier 1** (self-healing, cukup sekali): `eia`, `biodiesel_esdm`, `bioetanol_esdm`, `migas_esdm`, `iaea`, `wte`, `cpo`
- **Tier 2** (S&P dengan rentang tanggal): `spglobal_saf`
- **Tier 3** (berita, loop harian): `news_lokal`, `news_intl`
- **Tier 4** (sitemap historis Kompas, loop bulanan): `kompas_monthly`

Format `backfill_progress.json`: `completed_sources[]`, `last_completed_date_lokal`, `last_completed_date_intl`, `completed_kompas_months[]`. Hapus entri untuk memaksa jalan ulang sumber tertentu.

##### Status OneDrive Legacy

- [src/helpers/onedrive_helper.py](../src/helpers/onedrive_helper.py) **dipertahankan** — dipakai internal `_OneDriveBackend` dan `migrate_excel_to_neon.py`. Token MS Graph di-refresh otomatis pada tiap operasi tulis.
- Backend onedrive masih berfungsi penuh; berguna untuk dev lokal tanpa akses Neon, atau rollback darurat (set `STORAGE_BACKEND=onedrive` di workflow — data akan menyimpang dari Neon sejak saat itu, perlu migrasi ulang saat kembali).
- File `token.json` di root adalah cache OAuth lokal — **jangan di-commit**, lihat peringatan di [bagian “08 — Runbook Maintenance”](#sec-08-maintenance-md).


---

<a id="sec-03-database-md"></a>

#### 03 — Database Neon PostgreSQL

##### Koneksi

- Provider: [Neon](https://neon.tech) (serverless PostgreSQL), region `ap-southeast-1`.
- Server: `ep-winter-cell-aoi4t802.c-2.ap-southeast-1.aws.neon.tech`, database `neondb`.
- Env var: `NEON_DB_URL` — connection string format `postgresql://user:password@ep-xxx.region.aws.neon.tech/dbname?sslmode=require` (ambil dari Neon Console → Connection Details).
- Batasan free tier: **512 MB storage**; compute auto-suspend saat idle (resume otomatis <1 detik, tidak perlu penanganan khusus di kode).
- Akses dari kode hanya lewat [src/helpers/neon_helper.py](../src/helpers/neon_helper.py) (psycopg2): `read_table()`, `upsert_df()` (`INSERT ... ON CONFLICT ... DO UPDATE SET`), `create_table_if_needed()` (khusus WTE), dengan commit/rollback otomatis.

Query manual cepat:

```bash
psql $NEON_DB_URL -c "SELECT topic, COUNT(*) FROM news_articles GROUP BY topic ORDER BY 2 DESC;"
```

##### Setup Skema

```bash
python scripts/run_schema.py                      # scripts/create_tables.sql (CREATE TABLE IF NOT EXISTS — aman diulang)
psql $NEON_DB_URL -f scripts/create_views.sql     # 20 view vw_* untuk Power BI
```

##### Daftar Tabel (22 tabel)

Sumber kebenaran: [scripts/create_tables.sql](../scripts/create_tables.sql) dan `SHEET_TO_TABLE`/`SHEET_CONFLICT_COLS` di [src/helpers/storage_backend.py](../src/helpers/storage_backend.py). Kolom ber-huruf-besar/spasi di-quote (`"Bulan HIP"`) — dipertahankan persis dari Excel agar Power Query tidak berubah.

###### Berita & sentimen (topic-discriminated)

| Tabel | Sumber sheet Excel | Conflict key (UNIQUE) |
|---|---|---|
| `news_articles` | semua sheet `(News)*` | `(url, topic)` |
| `news_sentiment` | semua sheet `(Summary)*` | `(topic, "Tanggal awal")` |

Kolom `news_articles`: `title, date, url, content, source, keyword` + `topic` (nama sheet asal). Kolom `news_sentiment`: `"Tanggal awal", "Tanggal akhir", "Summary", "Summary Data"` + `topic`.

###### Data terstruktur

| Sheet Excel | Tabel | Conflict key | Penulis | Jadwal |
|---|---|---|---|---|
| (Data)Biodesel | `data_biodiesel` | `"Bulan HIP"` | `biodiesel_esdm.py` | monthly tgl 1 |
| (Data)Bioetanol | `data_bioetanol` | `"Bulan HIP"` | `bioetanol_esdm.py` | monthly tgl 1 |
| (Data)Harga Minyak | `data_harga_minyak` | `"Tahun","Bulan"` | `migas_esdm.py` (OCR) | monthly tgl 1 |
| (Data)EIA | `data_eia` | `"Tahun","Bulan"` | `migas_eia.py` | monthly tgl 1 |
| (Data)CPO | `data_cpo` | `"Dates"` | `cpo_gapki.py` | daily morning |
| (Data)SAF | `data_saf` | `"assessDate"` | `spglobal_data.py` | daily afternoon + weekly |
| (Data)Kapasitas_EBT | `data_kapasitas_ebt` | `tahun, bulan` | `kapasitas_esdm.py` | monthly tgl 28 |
| (Data)WTE_Sumber | `data_wte_sumber` | `tahun,"Nama Provinsi","Nama Kota/Kabupaten"` | `wte_sipsn.py` | monthly tgl 15 |
| (Data)WTE_Komposisi | `data_wte_komposisi` | sama | `wte_sipsn.py` | monthly tgl 15 |
| (Data)WTE_Timbulan | `data_wte_timbulan` | sama | `wte_sipsn.py` | monthly tgl 15 |
| (Data)IAEA_Nuclear_Capacity | `data_iaea_nuclear_capacity` | `year, country` | `nuclear_iaea_pris.py` | monthly tgl 15 |
| (Data)IAEA_Electrical | `data_iaea_electrical` | `year, country` | `nuclear_iaea_pris.py` | monthly tgl 15 |
| (Data)IAEA_Country_Stats | `data_iaea_country_stats` | `"CountryCode"` | `nuclear_iaea_pris.py` | monthly tgl 15 |
| (Data)Crackspread_BBM | `data_crackspread_bbm` | `year, month` | `spglobal_data.py` | monthly tgl 12 |
| (Data)Crackspread_NON_BBM | `data_crackspread_non_bbm` | `"Year","Month"` | `spglobal_data.py` | monthly tgl 12 |
| (Data)Crackspread_BBM_YEAR | `data_crackspread_bbm_year` | `year` | `spglobal_data.py` | monthly tgl 12 |

###### Tabel statis (diisi sekali dari Excel, tanpa scraper)

| Tabel | Conflict key | Catatan |
|---|---|---|
| `data_ruptl` | `"ID"` | Data RUPTL |
| `data_harga_ebt` | **tidak ada UNIQUE** | ⚠️ Tidak bisa di-upsert — load ulang akan menduplikasi baris. Bila perlu reload: `TRUNCATE data_harga_ebt;` dulu, atau tambahkan UNIQUE constraint. |

##### Kasus Khusus

###### IAEA wide↔long

Excel/Power BI memakai format wide (baris = tahun, kolom = negara); PostgreSQL menyimpan long: `year INTEGER, country TEXT, value_mw/value_twh NUMERIC`, UNIQUE `(year, country)`. Transformasi otomatis di `storage_backend.py` (`_melt_iaea`/`_pivot_iaea`). View `vw_iaea_nuclear_capacity_long` dan `vw_iaea_electrical_long` mengekspos format long ke Power BI, yang kemudian melakukan `Table.Pivot` sendiri.

###### WTE dynamic schema

Kolom data SIPSN berubah antar tahun. `neon_helper.create_table_if_needed()` membuat tabel dari dtype DataFrame dan menambah kolom baru via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` saat kolom baru muncul. Nilai numerik tersimpan sebagai teks dengan pemisah ribuan koma — view `vw_wte_*` yang membersihkannya (`REPLACE(...,',','')::numeric`).

Untuk melihat kolom aktual dari API: `python scripts/sample_wte_columns.py`.

##### Views (20, untuk Power BI)

Didefinisikan di [scripts/create_views.sql](../scripts/create_views.sql). Konvensi: view mengecualikan kolom `id`, mempertahankan urutan dan kapitalisasi kolom Excel (alias `price_ron92 AS "price_RON92"` dsb.), dan menangani pembersihan tipe (WTE).

`vw_biodiesel, vw_bioetanol, vw_harga_minyak, vw_eia, vw_cpo, vw_saf, vw_kapasitas_ebt, vw_iaea_country_stats, vw_iaea_nuclear_capacity_long, vw_iaea_electrical_long, vw_crackspread_bbm, vw_crackspread_non_bbm, vw_crackspread_bbm_year, vw_wte_komposisi, vw_wte_sumber, vw_wte_timbulan, vw_ruptl, vw_harga_ebt`

`news_articles` dan `news_sentiment` dibaca Power BI langsung dari tabel (filter per `topic`), bukan lewat view.

##### Menambah Tabel Baru

Checklist lengkap ada di [bagian “09 — Panduan Pengembangan Lanjutan”](#sec-09-pengembangan-md). Ringkas: tambah DDL di `create_tables.sql` (dengan UNIQUE constraint = conflict key) → daftarkan di `SHEET_TO_TABLE` + `SHEET_CONFLICT_COLS` → tambah view di `create_views.sql` → jalankan `run_schema.py`.


---

<a id="sec-04-pipeline-scheduling-md"></a>

#### 04 — Pipeline & Scheduling (GitHub Actions)

##### Ringkasan 4 Workflow

Semua workflow: `runs-on: ubuntu-latest`, Python 3.11, Chrome via `browser-actions/setup-chrome` (untuk Selenium), `STORAGE_BACKEND: neon`, `CI: "true"`, pip cache. Semua bisa dijalankan manual via **workflow_dispatch** (tab Actions → pilih workflow → Run workflow).

| Workflow | Cron (UTC) | WIB | Entry script | Timeout |
|---|---|---|---|---|
| `daily_morning.yml` | `0 1 * * 1-5` | Sen–Jum 08:00 | `src/scheduler/scheduling_day_morning.py` | default |
| `daily_afternoon.yml` | `0 7 * * 1-5` | Sen–Jum 14:00 | `src/scheduler/scheduling_day_afternoon.py` | default |
| `weekly.yml` | `0 1 * * 1` | Senin 08:00 | `src/scheduler/scheduling_week.py` | default |
| `monthly.yml` | `0 1 1,12,15,28 * *` | tgl 1/12/15/28 08:00 | `src/scheduler/scheduling_month.py` | 180 menit |

##### Urutan Step per Pipeline

Setiap step dibungkus `try/except` — kegagalan satu step tidak menghentikan step berikutnya. Ada jeda `time.sleep(60)` antar step di pipeline harian.

###### Daily Morning
1. **News lokal** — `orchestrators.main_news_scraping_lokal` (Kontan, Kompas, Tempo, Bisnis Indonesia, CNBC Indonesia, Bank Indonesia, BPS, Bloomberg Technoz, S&P, CNN/CNBC via Google News) → `news_articles`
2. **CPO GAPKI** — `structured_data.cpo_gapki.main_scraper_cpo` → `data_cpo`
3. **Sentiment lokal harian** — `orchestrators.main_sentiment_news_lokal_harian` (Gemini) → `news_sentiment`

###### Daily Afternoon
1. **News internasional** — `orchestrators.main_news_scraping_internasional` (BioenergyTimes, CNBC, CNN, EnergiesMedia, OilPrice, S&P, SCMP, The Guardian) → `news_articles`
2. **Sentiment internasional harian** → `news_sentiment`
3. **SAF daily** — `spglobal_data.main_saf_daily` → `data_saf` (butuh `SPGLOBAL_USERNAME/PASSWORD`)

###### Weekly
1. **Sentiment mingguan** — `orchestrators.main_sentiment_news_mingguan` (jendela 6 hari, gabungan sentimen berita + tren data terstruktur) → `news_sentiment`
2. **S&P weekly** — `main_saf_weekly` → `data_saf`

###### Monthly — gating per tanggal

Cron fire tanggal **1, 12, 15, 28**; [scheduling_month.py](../src/scheduler/scheduling_month.py) memilih step berdasarkan `datetime.now().day`:

| Tanggal | Step yang jalan |
|---|---|
| 1 (atau dispatch manual di tanggal selain 12/15/28) | Step 1–4: EIA (`data_eia`), ESDM OCR harga minyak (`data_harga_minyak`), biodiesel (`data_biodiesel`), bioetanol (`data_bioetanol`) |
| 12 | Step 5: petrochemical short-term + BBM price forecast → `data_crackspread_non_bbm`, `data_crackspread_bbm`, `data_crackspread_bbm_year` |
| 15 | Step 6: WTE SIPSN (`data_wte_*`) + IAEA PRIS (`data_iaea_*`, Selenium) |
| 28 | Step 7: kapasitas EBT (`data_kapasitas_ebt`) |

Pada tanggal 12/15/28, step 1–4 **dilewati** (supaya scraping berat + OCR tidak berulang 4× sebulan). Konstanta tanggal: `DAY_PETROCHEMICAL=12`, `DAY_NUCLEAR=15`, `DAY_EBT=28`.

> **Riwayat bug (diperbaiki Jul 2026):** sebelumnya cron monthly hanya fire tanggal 1, sehingga step tanggal 12/15/28 tidak pernah jalan otomatis — hanya via dispatch manual. Bila data petrokimia/WTE/IAEA/EBT bolong di periode sebelum Jul 2026, ini penyebabnya; isi dengan dispatch manual pada tanggal yang sesuai atau `scripts/backfill.py`.

##### Dependensi & Instalasi di CI

- **`requirements.txt`** (~137 paket): dipasang semua workflow (`pip install -r requirements.txt psycopg2-binary`). Scraping (selenium, undetected-chromedriver, beautifulsoup4, feedparser), data (pandas, openpyxl), Gemini, MSAL, PDF ringan.
- **`requirements-ocr.txt`**: torch CPU (`--extra-index-url https://download.pytorch.org/whl/cpu`), easyocr, opencv — **hanya monthly** (OCR PDF harga minyak ESDM). Dipisah karena ~GB; pernah menyebabkan disk-full di runner (commit `56e3e652`, `4ef9009e`).
- Pip cache per workflow; monthly punya key cache sendiri yang mencakup kedua file requirements.

##### Perilaku Cron GitHub — Penting

1. **Delay 3–5 jam adalah normal.** Cron GitHub Actions free tier best-effort; run tercatat mulai pukul ~11:40–13:00 WIB untuk jadwal 08:00 WIB. Jangan dianggap gagal. (Mitigasi parsial: geser menit cron dari `:00`, mis. `23 0 * * 1-5`.)
2. **Auto-disable setelah 60 hari repo tidak aktif.** GitHub menonaktifkan scheduled workflow bila tidak ada commit 60 hari. Re-enable manual di tab Actions. Script monitoring (di bawah) mendeteksi kondisi ini.
3. **Cron hanya jalan dari default branch (`main`).** Perubahan workflow di branch `dev` tidak mempengaruhi jadwal sampai di-merge ke `main`. Workflow terdaftar di GitHub sejak 2026-07-02 — tidak ada scheduled run sebelum tanggal itu.

##### Monitoring: `scripts/check_workflow_schedules.py`

Membandingkan waktu fire cron yang diharapkan vs run `event=schedule` aktual dari GitHub API.

```bash
python scripts/check_workflow_schedules.py            # lookback default per workflow (14/35/120 hari)
python scripts/check_workflow_schedules.py --days 30  # override lookback
```

- Token: env `GITHUB_TOKEN`/`GH_TOKEN`, fallback otomatis ke git credential helper (kredensial `git push`). Tanpa dependensi eksternal (stdlib).
- Output per workflow: `OK` (jalan, dengan delay menit + conclusion), `XX MISSED` (tidak ada run), `XX failed` (+ URL run), `!!` bila workflow di-disable GitHub, `pending` bila masih dalam jendela toleransi 6 jam.
- **Exit code 0** = semua sehat; **1** = ada masalah — cocok dipakai di automasi.
- Jendela pencocokan 6 jam (menampung delay GitHub). Lookback dipotong otomatis ke tanggal registrasi workflow.

Jalankan minimal **sebulan sekali** (sekaligus menangkal auto-disable-60-hari lewat aktivitas repo). Runbook lengkap: [bagian “08 — Runbook Maintenance”](#sec-08-maintenance-md).

##### Menjalankan Ulang Manual

- **Via GitHub:** Actions → pilih workflow → Run workflow (branch `main`). Untuk monthly, ingat gating tanggal: dispatch pada tanggal 12/15/28 hanya menjalankan step tanggal itu; dispatch tanggal lain menjalankan step 1–4.
- **Via lokal:** `python src/scheduler/scheduling_month.py` dengan `.env` lengkap dan `STORAGE_BACKEND=neon`. Gating tanggal tetap berlaku (pakai tanggal hari ini).

##### Mengubah Jadwal

1. Edit `cron` di `.github/workflows/*.yml` (UTC; WIB = UTC+7).
2. Bila menyentuh gating monthly, sinkronkan konstanta `DAY_*` di `scheduling_month.py`.
3. Update tabel `WORKFLOWS` di `scripts/check_workflow_schedules.py` (cron + lookback) agar monitoring tetap akurat.
4. Merge ke `main` — cron baru aktif setelah itu.


---

<a id="sec-05-sumber-data-md"></a>

#### 05 — Sumber Data & Scraper

Dua kelompok: **data terstruktur** (`src/structured_data/`, output tabel `data_*`) dan **berita** (`src/news/`, output `news_articles`).

##### Data Terstruktur

| Sumber | File | Endpoint / situs | Auth (env) | Output tabel | Jadwal |
|---|---|---|---|---|---|
| CPO (GAPKI) | `cpo_gapki.py` | `gapki.id/posisi-harga-komoditas/` (HTML) | — | `data_cpo` | daily morning |
| SAF + forecast (S&P Global Platts) | `spglobal_data.py` | `api.ci.spglobal.com` (auth `/auth/api`, market-data v3, odata petchem, energy-price-forecast) | `SPGLOBAL_USERNAME`, `SPGLOBAL_PASSWORD` | `data_saf`, `data_crackspread_bbm`, `data_crackspread_non_bbm`, `data_crackspread_bbm_year` | daily PM / weekly / monthly tgl 12 |
| EIA STEO | `migas_eia.py` | `api.eia.gov/v2/steo/data/` + scrape release date | `EIA_API_KEY` (gratis dari eia.gov/opendata) | `data_eia` | monthly tgl 1 |
| Harga minyak mentah ESDM (OCR) | `migas_esdm.py` | `migas.esdm.go.id/post/read/harga-minyak-mentah` → PDF → easyocr + PyMuPDF | — | `data_harga_minyak` | monthly tgl 1 |
| Biodiesel HIP (EBTKE ESDM) | `biodiesel_esdm.py` | `ebtke.esdm.go.id/api/api/artikel` + pdfplumber | — | `data_biodiesel` | monthly tgl 1 |
| Bioetanol HIP (EBTKE ESDM) | `bioetanol_esdm.py` | `ebtke.esdm.go.id/api/api/artikel` + pdfplumber | — | `data_bioetanol` | monthly tgl 1 |
| Kapasitas EBT (EBTKE ESDM) | `kapasitas_esdm.py` | `ebtke.esdm.go.id/api/api/konten/data-angka` (JSON) | — | `data_kapasitas_ebt` | monthly tgl 28 |
| Nuklir (IAEA PRIS) | `nuclear_iaea_pris.py` | `pris.iaea.org/PRIS/...` (Selenium/Chrome, 4 halaman) | — | `data_iaea_nuclear_capacity`, `data_iaea_electrical`, `data_iaea_country_stats` | monthly tgl 15 |
| Sampah / WTE (SIPSN KemenLH) | `wte_sipsn.py` | `sampahnasional.kemenlh.go.id/indikatif/public/home/ajax_list` (JSON) | — | `data_wte_sumber/komposisi/timbulan` (kolom dinamis) | monthly tgl 15 |

Catatan:
- **SIPSN:** domain lama `sipsn.kemenlh.go.id` mati sejak Okt 2024 — sudah dipindah ke `sampahnasional.kemenlh.go.id`. Bila mati lagi, cari domain penerus dan update konstanta URL di `wte_sipsn.py`.
- **S&P Global** satu-satunya sumber terstruktur berbayar/berkredensial; kegagalan auth mematikan SAF + semua crackspread sekaligus.
- **ESDM OCR** paling rapuh: bergantung format PDF pengumuman + akurasi OCR. Perubahan layout PDF = perlu penyesuaian parsing di `migas_esdm.py`.

##### Berita

Semua scraper berita ada di `src/news/`, dipanggil orchestrator dengan `(keyword, date_filter)`, hasil digabung → dedup per `(url, topic)` → `news_articles`.

###### Scraper lokal (dipakai `main_news_scraping_lokal.py`)

| File | Situs / endpoint |
|---|---|
| `kompas.py` | `kompas.com/sitemap*.xml` |
| `kontan.py`, `kontan_bbm.py`, `kontan_biodiesel.py` | `kontan.co.id/sitemap.xml` |
| `tempo.py` | `rss.tempo.co` + pencarian |
| `bisnis_indonesia.py` | `search.bisnis.com` |
| `cnbc_id.py` | `cnbcindonesia.com` |
| `bloomberg_technoz.py` | `bloombergtechnoz.com` |
| `bank_indonesia.py` | `bi.go.id` news release |
| `bps.py` | `webapi.bps.go.id/v1/api/` |
| `google_news.py` | `news.google.com/rss/search` + sitemap CNN/CNBC (pre-filter keyword sebelum fetch konten — lihat commit `301cf6e2`) |
| `spglobal_news.py` | `api.ci.spglobal.com/news-insights/v1/` (butuh `SPGLOBAL_*`) |

###### Scraper internasional (dipakai `main_news_scraping_internasional.py`)

| File | Situs / endpoint |
|---|---|
| `cnn.py` | `cnn.com/sitemap/news.xml` |
| `cnbc.py` | `cnbc.com/sitemap_news.xml` |
| `oilprice.py` | `oilprice.com/googlenews.xml` |
| `the_guardian.py` | `theguardian.com/sitemaps/news.xml` |
| `scmp.py` | `scmp.com/search` |
| `bioenergytimes.py` | `bioenergytimes.com` |
| `energiesmedia.py` | `energiesmedia.com` |
| `spglobal_news.py` | (sama dengan lokal) |

###### Topik berita (nilai `topic` di `news_articles`)

25 topik lokal, format `(News)<Topik>`:

```
Indeks Risiko Geopolitik, Indeks Volatilitas, Kurs, IHSG, Inflasi, BI Rate,
Indonia, Indeks Penjualan Ritel, Indeks Kepercayaan Knsmn, Indeks Kinerja
Manufaktur, Indeks Kinerja Jasa, Neraca Perdagangan, PDB, Harga Minyak,
Volume Minyak, Harga Produk Kilang, Volume Produk Kilang, Crackspread BBM,
Biodiesel, SAF, Bioetanol, RUPTL, EBT, WTE, Nuklir
```

Scraper internasional menulis ke tabel yang sama dengan nilai topic versi internasionalnya.

###### Routing keyword → scraper

Peta keyword → daftar scraper dan keyword → sheet/topik ada di dict besar dalam `main_news_scraping_lokal.py` dan `main_news_scraping_internasional.py`. **Sebagian besar topik sedang dinonaktifkan (dikomentari)** — periksa dict aktif di file tersebut untuk tahu topik apa yang benar-benar jalan sekarang. Mengaktifkan topik = uncomment entri di dict + pastikan sheet/topik terdaftar di daftar sheet aktif orchestrator.

###### Perilaku tanggal

- Di CI (`CI=true`): scrape berita "kemarin" (H-1).
- Di lokal: rentang `START_DATE`/`END_DATE` hardcoded di masing-masing orchestrator — sesuaikan sebelum run manual.
- Backfill historis berita: `scripts/backfill.py --sources news_lokal news_intl` (loop harian) atau `kompas_monthly` (sitemap bulanan Kompas).

##### Menambah Sumber Baru

Checklist lengkap di [bagian “09 — Panduan Pengembangan Lanjutan”](#sec-09-pengembangan-md).


---

<a id="sec-06-ai-sentiment-md"></a>

#### 06 — AI & Analisis Sentimen Berita

##### Provider Aktif: Google Gemini

Satu-satunya titik pemanggilan AI di seluruh repo: [src/helpers/summary_helper.py](../src/helpers/summary_helper.py).

- `setup_gemini()` — baca `GEMINI_API_KEY` dari env, konfigurasi `google.generativeai`, kembalikan `GenerativeModel("gemini-2.5-flash-lite")` (model di-hardcode di `summary_helper.py:34`; varian `gemini-2.5-flash` tersedia sebagai komentar).
- `summarize_all_news(model, ...)` — bangun prompt analis berbahasa Indonesia (ringkasan 3 poin per topik), panggil `model.generate_content()`, kembalikan teks ringkasan.

> ⚠️ **Klarifikasi konfigurasi:** `.env.example` memuat `AI_TYPE=OPENAI`, `OPENAI_API_KEY`, `OPENAI_MODEL_NAME=gpt-4o` — **tidak ada kode yang membacanya**. Ini sisa scaffold rencana migrasi provider yang belum pernah dieksekusi. Provider produksi tetap Gemini; workflow CI hanya menginject `GEMINI_API_KEY`. Jangan bingung karenanya.

##### Alur Sentimen

Tiga orchestrator memakai `setup_gemini` + `summarize_all_news`:

| Orchestrator | Jadwal | Cakupan |
|---|---|---|
| `main_sentiment_news_lokal_harian.py` | daily morning | Topik lokal harian: Nilai Tukar Rupiah, IHSG, Indonia |
| `main_sentiment_news_internasional_harian.py` | daily afternoon | Topik internasional harian: Indeks Volatilitas |
| `main_sentiment_news_mingguan.py` | weekly (Senin) | Topik mingguan (aktif: Crackspread BBM; banyak topik lain dikomentari). Jendela 6 hari, maks 200 berita per topik. |

Langkah umum tiap orchestrator:

1. Baca artikel terbaru per topik dari `news_articles` (via `storage`).
2. Khusus **mingguan**: hitung juga "sentimen data" dari tren data terstruktur (mis. arah harga crackspread) dan masukkan ke prompt bersama berita.
3. Panggil Gemini → hasil ringkasan.
4. Tulis ke `news_sentiment` via `storage.write_sentiment_file()`; kolom: `"Tanggal awal"`, `"Tanggal akhir"`, `"Summary"`, `"Summary Data"`, dengan `topic` = nama sheet `(Summary)...`. Upsert key `(topic, "Tanggal awal")` — menjalankan ulang di hari yang sama menimpa ringkasan, bukan menduplikasi.

Nilai `topic` yang aktif saat ini: `(Summary)Nilai Tukar Rupiah`, `(Summary)IHSG`, `(Summary)Indonia` (lokal harian), `(Summary)Idx Volatilitas` (internasional), `(Summary)Crackspread BBM` (mingguan). Topik mingguan lain (Inflasi, BI-Rate, PDB, Biodiesel, SAF, dst.) ada di kode tapi dikomentari — mengaktifkannya cukup uncomment di `main_sentiment_news_mingguan.py`.

##### Catatan Operasional

- **Start date hardcoded:** orchestrator sentimen punya default tanggal awal yang di-hardcode (era backfill, `2026-04-17`). Di CI perilaku mengikuti `CI=true` (harian). Bila menjalankan lokal dan hasilnya aneh, cek konstanta tanggal di file orchestrator.
- **Kuota/limit Gemini:** free tier punya rate limit; kegagalan API hanya menggagalkan step sentimen (step lain jalan terus). Ringkasan yang bolong bisa diisi ulang dengan menjalankan orchestrator sentimen secara manual di tanggal yang sama (upsert menimpa).
- **Biaya:** `gemini-2.5-flash-lite` dipilih karena murah/cepat; volume panggilan kecil (≤ jumlah topik aktif per hari).

##### Mengganti Provider AI (mis. ke OpenAI/Azure OpenAI)

Titik ubah minimal:

1. **`src/helpers/summary_helper.py`** — ganti `setup_gemini()` dan pemanggilan `generate_content()` dengan SDK provider baru. Pertahankan signature `summarize_all_news(...)` agar 3 orchestrator tidak perlu berubah (mereka hanya `from helpers.summary_helper import setup_gemini, summarize_all_news`). Idealnya buat fungsi `setup_model()` yang branching pada `AI_TYPE`.
2. **`requirements.txt`** — tambah SDK baru (mis. `openai`).
3. **`.env` / `.env.example`** — isi `AI_TYPE`, `OPENAI_API_KEY`, `OPENAI_MODEL_NAME` (var-nya sudah disiapkan).
4. **GitHub Secrets + workflow YAML** — tambahkan secret baru dan inject di blok `env:` `daily_morning.yml`, `daily_afternoon.yml`, `weekly.yml` (monthly tidak memanggil AI).
5. Uji lokal: jalankan salah satu orchestrator sentimen dengan `STORAGE_BACKEND=onedrive` (atau neon dev) dan periksa baris baru di `news_sentiment`.

Gotcha umum bila memakai model GPT-5.x/o-series: parameter `temperature`/`max_tokens` klasik ditolak (pakai `max_completion_tokens`), dan Azure OpenAI memakai header `api-key:` bukan `Authorization: Bearer`.


---

<a id="sec-07-power-bi-md"></a>

#### 07 — Power BI & Power Query

##### Dua File Referensi

| File | Isi |
|---|---|
| [power_query_names.txt](../power_query_names.txt) (root) | Snapshot **asli** semua M-query Power BI era SharePoint (semua query membaca `SharePoint.Files(...)` → `Excel.Workbook`). Berfungsi sebagai inventaris & arsip pra-migrasi. |
| [scripts/power_query_migrated.txt](../scripts/power_query_migrated.txt) | M-query **pengganti** pasca-migrasi. Tiap query bertanda `[NEON]` (sudah dipindah ke PostgreSQL — ganti M-code-nya) atau `[UNCHANGED]` (tetap SharePoint — **jangan diganti**). |

##### Prasyarat Koneksi (sekali per file .pbix)

1. Skema Neon sudah terpasang: `scripts/create_tables.sql` + `scripts/create_views.sql` (lihat [bagian “03 — Database Neon PostgreSQL”](#sec-03-database-md)).
2. Tabel statis `data_ruptl` dan `data_harga_ebt` sudah diisi (one-time dari Excel).
3. Di Power BI Desktop: **Get Data → PostgreSQL database**
   - Server: `ep-winter-cell-aoi4t802.c-2.ap-southeast-1.aws.neon.tech`
   - Database: `neondb`
   - Mode: **Import** (JANGAN DirectQuery — Neon auto-suspend membuat DirectQuery lambat/gagal; Import hanya menyentuh DB saat refresh)
   - Kredensial: user/password dari `NEON_DB_URL` (Neon Console → Connection Details). Power BI menyimpan kredensial per-server, jadi cukup sekali isi.
   - Bila muncul error enkripsi, gunakan koneksi terenkripsi (Neon mewajibkan SSL).

##### Prosedur Mengganti Query (migrasi per query)

1. Power BI Desktop → **Transform Data** (Power Query Editor).
2. Pilih query yang bertanda `[NEON]` di `power_query_migrated.txt`.
3. **Advanced Editor** → hapus seluruh M-code lama → paste M-code baru dari file tersebut → Done.
4. Ulangi untuk semua query `[NEON]`; biarkan yang `[UNCHANGED]`.
5. **Close & Apply** → refresh penuh → simpan .pbix.

##### Pola M-code Neon

```m
let
    Source = PostgreSQL.Database("ep-winter-cell-aoi4t802.c-2.ap-southeast-1.aws.neon.tech", "neondb"),
    tabel = Source{[Schema="public", Item="news_articles"]}[Data],
    difilter = Table.SelectRows(tabel, each [topic] = "(News)Harga Minyak"),
    bersih = Table.RemoveColumns(difilter, {"id", "topic"})
in
    bersih
```

Pola per jenis data:
- **Berita:** baca `news_articles`, filter `[topic] = "(News)X"`, buang `id`/`topic` → hasil identik dengan sheet Excel lama.
- **Sentimen:** sama, dari `news_sentiment` dengan `[topic] = "(Summary)X"`.
- **Terstruktur:** baca view `vw_*` (bukan tabel) — view sudah membuang `id`, memulihkan kapitalisasi kolom, dan membersihkan tipe. IAEA: baca view long (`vw_iaea_*_long`) lalu `Table.Pivot` kolom `country` untuk kembali ke bentuk wide.

##### Yang Tetap di SharePoint (`[UNCHANGED]`)

- Semua seri makroekonomi dari `(Data)Makro.xlsx`: BI-Rate, Kurs, PMI, Inflasi, IHSG, PDB, Geopolitik, Volatilitas, Neraca Perdagangan, dll. **Tidak ada scraper untuk data ini** — diupdate manual di SharePoint (`<tenant>-my.sharepoint.com`).
- `(Data)Input_Fosil_Prediction` dari `(Data)Input_Manual.xlsx` (input manual).
- Tabel literal statis di M (mis. `Kategori eia`, `Kategori Harga Kilang`).

Konsekuensi: refresh dashboard tetap butuh kredensial SharePoint **dan** Neon. SharePoint baru bisa dilepas bila seri makro dipindahkan (dibuatkan scraper/loader ke Neon — kandidat pengembangan, lihat [bagian “09 — Panduan Pengembangan Lanjutan”](#sec-09-pengembangan-md)).

##### Menambah Query Baru dari Neon

1. Pastikan tabel/view-nya ada (untuk data terstruktur baru, buat view di `create_views.sql`).
2. Power Query: **New Source → PostgreSQL** (server/db sama) atau duplikasi query Neon yang ada lalu ganti `Item="nama_view"`.
3. Ikuti konvensi: pakai view untuk data terstruktur; buang kolom `id`; jangan lakukan agregasi berat di M bila bisa di view SQL.
4. Catat query baru di `scripts/power_query_migrated.txt` supaya file itu tetap menjadi sumber kebenaran M-code.

##### Troubleshooting Refresh

| Gejala | Kemungkinan penyebab |
|---|---|
| Kolom tidak ditemukan setelah refresh | Skema tabel berubah tanpa update view/M-code ([bagian “03 — Database Neon PostgreSQL”](#sec-03-database-md)) |
| Refresh lambat sekali di awal | Neon compute baru resume dari suspend — normal, coba lagi |
| Data kosong untuk topik tertentu | Pipeline scraping topik itu gagal/nonaktif — cek `SELECT MAX(date) FROM news_articles WHERE topic='(News)X'` dan log Actions ([bagian “08 — Runbook Maintenance”](#sec-08-maintenance-md)) |
| Error kredensial PostgreSQL | Password Neon dirotasi — perbarui di Data source settings |


---

<a id="sec-08-maintenance-md"></a>

#### 08 — Runbook Maintenance

##### Checklist Rutin

###### Harian (opsional, 2 menit)
- Lihat tab **Actions** di GitHub: run terakhir daily morning/afternoon hijau?
- Ingat: delay 3–5 jam dari jadwal itu normal (free tier).

###### Mingguan
- `python scripts/check_workflow_schedules.py` — exit 0 & "ALL SCHEDULERS HEALTHY" = beres.
- Spot-check data terbaru:
  ```sql
  SELECT MAX("Upload_Dates") FROM data_cpo;
  SELECT topic, MAX(date) FROM news_articles GROUP BY topic;
  SELECT topic, MAX("Tanggal awal") FROM news_sentiment GROUP BY topic;
  ```

###### Bulanan
- Cek run monthly tanggal 1/12/15/28 sukses (Actions atau script monitoring).
- Cek ukuran database vs limit 512 MB free tier:
  ```sql
  SELECT pg_size_pretty(pg_database_size('neondb'));
  SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
  FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 10;
  ```
  (Pertumbuhan terbesar biasanya `news_articles` karena kolom `content`. Bila mendekati limit: arsip/hapus artikel lama, atau upgrade plan.)
- **Pastikan ada aktivitas repo dalam 60 hari terakhir** — GitHub menonaktifkan scheduled workflow setelah 60 hari tanpa aktivitas. Commit apa pun mereset timer; script monitoring mendeteksi state `disabled_inactivity`.

##### Monitoring Scheduler

```bash
python scripts/check_workflow_schedules.py            # default
python scripts/check_workflow_schedules.py --days 30  # lookback custom
```

Interpretasi output:
- `OK ... ran +236min, success` — jalan & sukses; `+menit` = delay dari jadwal (normal sampai ±5 jam).
- `XX ... MISSED` — cron tidak fire. Penyebab umum: workflow di-disable (lihat `!!`), file workflow belum ada di `main` pada tanggal itu, atau outage GitHub.
- `XX ... failure <URL>` — jalan tapi gagal; buka URL untuk log.
- `!! WORKFLOW STATE: disabled_inactivity` — re-enable di tab Actions (klik workflow → "Enable workflow").
- Exit code: 0 sehat, 1 ada masalah (bisa dipakai untuk alert otomatis).

##### Menangani Run Gagal

1. Buka log run di Actions. Struktur log jelas per step: `>>> STEP n: ...` diikuti error + traceback. Satu step gagal **tidak** membatalkan step lain — periksa seluruh log, jangan cuma step pertama yang merah.
2. Identifikasi step gagal → lihat tabel scraper di [bagian “05 — Sumber Data & Scraper”](#sec-05-sumber-data-md) untuk tahu file & sumber datanya.
3. Re-run: **Actions → workflow → Run workflow** (dispatch). Aman diulang — semua tulisan idempoten (upsert). Untuk monthly perhatikan gating tanggal ([bagian “04 — Pipeline & Scheduling (GitHub Actions)”](#sec-04-pipeline-scheduling-md)).
4. Bila gap data beberapa hari: gunakan `scripts/backfill.py --sources <sumber> --start ... --end ...` ([bagian “02 — Migrasi Storage: OneDrive Excel → Neon PostgreSQL”](#sec-02-migrasi-storage-md)).

##### Diagnosis Scraper Rusak (situs berubah)

Pola kegagalan umum dan langkahnya:

| Gejala di log | Diagnosis | Tindakan |
|---|---|---|
| HTTP 404/301 pada URL sumber | Situs pindah/ubah struktur URL | Cari URL baru, update konstanta di file scraper |
| HTTP 403/429 | Diblokir/rate-limit | Tambah delay, cek User-Agent, pertimbangkan `undetected-chromedriver` |
| Parsing kosong (0 baris) tanpa error | Struktur HTML/selector berubah | Buka situs manual, sesuaikan selector BeautifulSoup/Selenium |
| Auth error S&P Global | Password expired/dirotasi | Perbarui secret `SPGLOBAL_PASSWORD` |
| OCR hasil ngaco (`data_harga_minyak`) | Layout PDF ESDM berubah | Sesuaikan parsing di `migas_esdm.py`; bandingkan dengan PDF aslinya |
| SIPSN timeout/404 | Domain KemenLH pindah (sudah terjadi Okt 2024) | Cari domain baru, update `wte_sipsn.py` |

Cara uji satu scraper secara terisolasi (tanpa menjalankan seluruh pipeline):

```bash
# contoh: uji CPO saja, tulis ke Neon
set STORAGE_BACKEND=neon
python -c "import sys; sys.path.append('src'); from structured_data.cpo_gapki import main_scraper_cpo; main_scraper_cpo()"
```

##### Secrets & Kredensial

###### Daftar GitHub Secrets (Settings → Secrets and variables → Actions)

| Secret | Dipakai oleh | Workflow |
|---|---|---|
| `NEON_DB_URL` | `neon_helper.py` | semua |
| `GEMINI_API_KEY` | `summary_helper.py` | morning, afternoon, weekly |
| `SPGLOBAL_USERNAME`, `SPGLOBAL_PASSWORD` | `spglobal_data.py`, `spglobal_news.py` | afternoon, weekly, monthly |
| `EIA_API_KEY` | `migas_eia.py` | monthly |
| `MS_CLIENT_ID`, `MS_CLIENT_SECRET`, `MS_TENANT_ID`, `MS_USER_EMAIL` | `onedrive_helper.py` | semua (legacy/fallback) |
| `ONEDRIVE_FILE_PATH`, `ONEDRIVE_SENTIMENT_PATH`, `ONEDRIVE_DATA_PATH` | `storage_backend.py` | semua (legacy/fallback) |

Rotasi: perbarui nilai di GitHub Secrets **dan** `.env` lokal. Khusus `NEON_DB_URL`, perbarui juga kredensial PostgreSQL di Power BI (Data source settings).

###### ⚠️ Peringatan Keamanan

- **`.env` di mesin dev berisi kredensial asli** (Gemini, Neon, S&P, MS client secret, service account Google). File ini tidak boleh masuk git (cek `.gitignore`), tidak boleh dibagikan mentah saat handover — pihak baru harus menerima kredensial lewat jalur aman, lalu **rotasi semua kredensial setelah handover**.
- **`token.json` di root** = cache token OAuth MS Graph. Jangan di-commit; hapus aman (akan dibuat ulang saat auth berikutnya).
- `GOOGLE_CREDENTIALS`/`SPREADSHEET_ID*` di `.env` adalah sisa era Google Sheets — tidak dipakai kode aktif; kandidat dibersihkan.
- Untuk serah terima sistem: inventaris lengkap akun/kredensial + checklist rotasi ada di [bagian “Inventaris Aset & Akses”](#sec-handover-02-inventaris-aset-akses-md).

##### Manajemen Database Neon

- Console: https://console.neon.tech — monitoring storage/compute, connection string, rotasi password.
- Backup/export manual:
  ```bash
  pg_dump "$NEON_DB_URL" -Fc -f backup_$(date +%Y%m%d).dump      # full
  psql "$NEON_DB_URL" -c "\copy news_sentiment TO 'sentiment.csv' CSV HEADER"  # per tabel
  ```
- Neon punya point-in-time restore (history retention terbatas di free tier) — cek console sebelum melakukan operasi destruktif.
- Skema aman dijalankan ulang kapan pun (`CREATE TABLE IF NOT EXISTS` / `CREATE OR REPLACE VIEW`).

##### Known Issues (per Juli 2026)

| Isu | Dampak | Saran |
|---|---|---|
| `data_harga_ebt` tanpa UNIQUE constraint | Reload menduplikasi baris | `TRUNCATE` sebelum reload, atau tambah UNIQUE + daftarkan conflict key |
| `src/code_scrapping/` hanya berisi `.pyc` legacy | Membingungkan; tak terpakai | Hapus folder dari git |
| Monitoring hanya stdout GitHub Actions | Kegagalan senyap bila tak dicek | Rutin jalankan `check_workflow_schedules.py`; pertimbangkan notifikasi email GitHub (Settings → Notifications → Actions) |
| Start date hardcoded di orchestrator sentimen (`2026-04-17`) | Run lokal bisa memproses rentang salah | Sesuaikan konstanta sebelum run manual; di CI aman (`CI=true`) |
| Secrets MS/OneDrive diinject semua workflow padahal backend neon | Permukaan kredensial lebih luas dari perlu | Boleh dihapus dari YAML setelah yakin tak ada fallback OneDrive |
| Cron delay 3–5 jam | Data "pagi" masuk siang | Terima (free tier), atau geser cron lebih awal / pindah self-hosted runner |
| Step monthly tgl 12/15/28 baru diaktifkan Jul 2026 | Data petrokimia/WTE/IAEA/EBT sebelum Jul 2026 mungkin bolong | Verifikasi fire pertama 12/15/28 Jul 2026; isi gap via dispatch manual/backfill |


---

<a id="sec-09-pengembangan-md"></a>

#### 09 — Panduan Pengembangan Lanjutan

##### Setup Lokal

```bash
git clone <URL-REPO-GITHUB>
cd <NAMA-FOLDER-REPO>
python -m venv .venv
.venv\Scripts\activate                      # Windows (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt psycopg2-binary
# hanya bila mengerjakan OCR ESDM:
pip install -r requirements-ocr.txt --extra-index-url https://download.pytorch.org/whl/cpu
copy .env.example .env                       # isi kredensial (minta lewat jalur aman)
```

Python 3.11 (samakan dengan CI). Chrome terpasang lokal diperlukan untuk scraper Selenium (IAEA, beberapa berita).

###### Pilih backend saat dev

- `STORAGE_BACKEND=onedrive` (default) — aman untuk eksperimen, menulis ke Excel OneDrive, tidak menyentuh DB produksi. Butuh kredensial `MS_*`.
- `STORAGE_BACKEND=neon` — menulis ke database produksi. **Hati-hati**: tidak ada database staging. Untuk uji tulis yang aman, buat [branch database di Neon](https://neon.tech/docs/introduction/branching) dan arahkan `NEON_DB_URL` ke branch itu.

###### Menjalankan komponen secara terpisah

```bash
python src/scheduler/scheduling_day_morning.py     # pipeline penuh
# satu scraper saja:
python -c "import sys; sys.path.append('src'); from structured_data.migas_eia import main_eia; main_eia()"
```

Perhatikan: di lokal (tanpa `CI=true`) orchestrator berita memakai `START_DATE`/`END_DATE` hardcoded — sesuaikan dulu di file orchestrator.

##### Checklist: Menambah Sumber Data Terstruktur Baru

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
5. **Scheduler** — panggil `main_*()` dari scheduler yang sesuai (`scheduling_month.py` dst.) dengan pola `try/except` + banner step yang sama. Bila perlu jadwal tanggal khusus, tambah konstanta `DAY_*` dan sinkronkan cron `monthly.yml` ([bagian “04 — Pipeline & Scheduling (GitHub Actions)”](#sec-04-pipeline-scheduling-md)).
6. **Secrets** (bila sumber butuh auth) — tambah env var di `.env.example`, `.env`, GitHub Secrets, dan blok `env:` workflow terkait.
7. **Power BI** — buat query M baru dari `vw_nama_sumber` ([bagian “07 — Power BI & Power Query”](#sec-07-power-bi-md)) dan catat di `scripts/power_query_migrated.txt`.
8. **Monitoring/backfill** (opsional) — tambahkan ke `scripts/backfill.py` bila butuh pengisian historis.
9. **Dokumentasi** — daftarkan di tabel [bagian “05 — Sumber Data & Scraper”](#sec-05-sumber-data-md) dan [bagian “03 — Database Neon PostgreSQL”](#sec-03-database-md).

##### Checklist: Menambah Scraper / Topik Berita

- **Situs berita baru:** buat `src/news/nama_situs.py` meniru scraper serupa (sitemap → `kompas.py`/`cnn.py`; RSS → `tempo.py`/`oilprice.py`; search → `bisnis_indonesia.py`). Kontrak: fungsi menerima `(keyword, date_filter)` dan mengembalikan DataFrame `title, date, url, content, source, keyword`.
- **Registrasi:** tambahkan ke dict keyword → scraper di `main_news_scraping_lokal.py` atau `_internasional.py`.
- **Topik baru:** tambah nilai sheet `(News)Topik Baru` di daftar sheet aktif orchestrator + mapping keyword. Tidak perlu DDL — semua topik masuk `news_articles`.
- **Mengaktifkan topik nonaktif:** banyak topik sudah ada tapi dikomentari di dict orchestrator (lihat [bagian “05 — Sumber Data & Scraper”](#sec-05-sumber-data-md)) — cukup uncomment.
- **Sentimen untuk topik baru:** daftarkan sheet `(Summary)Topik` di orchestrator sentimen yang sesuai (harian lokal/intl atau mingguan; di mingguan banyak yang tinggal di-uncomment).

##### Mengubah Jadwal / Menambah Workflow

Lihat [bagian “04 — Pipeline & Scheduling (GitHub Actions)”](#sec-04-pipeline-scheduling-md) bagian "Mengubah Jadwal". Ingat 3 hal: cron dalam UTC, hanya jalan dari `main`, dan update `scripts/check_workflow_schedules.py` agar monitoring mengikuti.

##### Mengganti Model / Provider AI

Lihat [bagian “06 — AI & Analisis Sentimen Berita”](#sec-06-ai-sentiment-md). Ganti model Gemini = satu baris di `summary_helper.py:34`. Ganti provider = rewrite `setup_gemini()`/`summarize_all_news()` + secrets workflow.

##### Konvensi Kode Proyek Ini

- **Logging = `print`** dengan prefix `[Main]`/`[NamaScraper]` + banner `===`/`---`. Tidak ada modul `logging`. Konsisten saja dengan pola ini (log terbaca di GitHub Actions).
- **Error handling:** `try/except Exception` per step/scraper + `traceback.print_exc()`; jangan biarkan satu sumber mematikan pipeline. Exit code ≠ 0 hanya untuk kegagalan fatal seluruh pipeline.
- **Idempoten:** semua tulis harus upsert-safe. Jangan pernah `INSERT` polos ke tabel ber-UNIQUE; selalu lewat `storage.write_*` yang memakai `upsert_df`.
- **Nama kolom = kontrak dengan Power BI.** Mengubah nama/kapitalisasi kolom akan memutus Power Query dan view. Bila terpaksa, ubah serempak: scraper → DDL → view → M-code.
- **Import path:** scheduler menambah `src/` ke `sys.path`; modul saling import tanpa prefix `src.` (`from helpers.storage_backend import storage`). Jalankan script dari root repo.
- **Branch:** kerja di `dev`, merge ke `main` untuk produksi (cron hanya membaca `main`). PR ke `main`.

##### Ide Pengembangan Prioritas (backlog saran)

1. **Scraper seri makroekonomi** (BI-Rate, Kurs, Inflasi, dst.) → Neon, supaya SharePoint bisa dipensiunkan sepenuhnya ([bagian “07 — Power BI & Power Query”](#sec-07-power-bi-md)). Sebagian sumber sudah ada scraper-nya (BI, BPS) tinggal diarahkan ke tabel data.
2. **Notifikasi kegagalan** — step terakhir workflow yang mengirim alert (email/Telegram) bila ada step gagal, atau jadwalkan `check_workflow_schedules.py` sebagai workflow tersendiri.
3. **UNIQUE untuk `data_harga_ebt`** + registrasi conflict key.
4. **Bersihkan legacy:** folder `src/code_scrapping/`, env Google Sheets, secrets OneDrive di workflow (setelah dipastikan tak dipakai).
5. **Database staging** via Neon branching untuk pengujian pipeline tanpa risiko ke produksi.


---

<a id="sec-how-to-readme-md"></a>

#### How-To: Panduan Langkah-demi-Langkah

Kumpulan prosedur operasional. Tiap panduan: prasyarat → langkah bernomor → cara verifikasi hasil. Untuk konsep/referensi lihat [docs/](.) (01–09); untuk diagnosis masalah lihat [bagian “Runbook Operator Hari Pertama”](#sec-handover-03-runbook-hari-pertama-md).

| # | Panduan | Kapan dipakai |
|---|---|---|
| 1 | [Setup lokal dari nol](#sec-how-to-01-setup-lokal-dari-nol-md) | Mesin/engineer baru |
| 2 | [Menjalankan pipeline manual](#sec-how-to-02-menjalankan-pipeline-manual-md) | Run gagal, isi data hari ini, uji perubahan |
| 3 | [Cek kesehatan scheduler](#sec-how-to-03-cek-kesehatan-scheduler-md) | Rutin mingguan; curiga cron tidak jalan |
| 4 | [Backfill data bolong](#sec-how-to-04-backfill-data-bolong-md) | Ada gap data historis (berita, summary, terstruktur) |
| 5 | [Menambah topik berita](#sec-how-to-05-menambah-topik-berita-md) | Topik/keyword berita baru diminta |
| 6 | [Menambah sumber data terstruktur](#sec-how-to-06-menambah-sumber-terstruktur-md) | Dataset tabular baru untuk dashboard |
| 7 | [Menyambungkan Power BI ke Neon](#sec-how-to-07-koneksi-power-bi-neon-md) | Setup .pbix baru / pindah mesin |
| 8 | [Rotasi kredensial](#sec-how-to-08-rotasi-kredensial-md) | Handover, kebocoran, atau rutin berkala |
| 9 | [Backup & restore database](#sec-how-to-09-backup-restore-neon-md) | Sebelum operasi berisiko; pemulihan |


---

<a id="sec-how-to-01-setup-lokal-dari-nol-md"></a>

#### How-To 1: Setup Lokal dari Nol

Target: dari mesin kosong sampai bisa menjalankan pipeline di laptop. ±20 menit (tanpa OCR).

##### Prasyarat

- Windows/Linux/Mac dengan **Python 3.11** (samakan dengan CI) dan Git.
- Google Chrome terpasang (dipakai Selenium).
- Kredensial `.env` diterima lewat jalur aman (jangan lewat chat/email polos) — daftar akun di [bagian “Inventaris Aset & Akses”](#sec-handover-02-inventaris-aset-akses-md).

##### Langkah

1. Clone repo:
   ```bash
   git clone <URL-REPO-GITHUB>
   cd <NAMA-FOLDER-REPO>
   ```
2. Buat virtualenv dan aktifkan:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate          # Windows
   source .venv/bin/activate       # Linux/Mac
   ```
3. Install dependensi dasar:
   ```bash
   pip install -r requirements.txt psycopg2-binary
   ```
   **Verifikasi:** `python -c "import pandas, selenium, google.generativeai, psycopg2; print('ok')"` → cetak `ok`.
4. (Hanya bila mengerjakan OCR ESDM) install paket berat:
   ```bash
   pip install -r requirements-ocr.txt --extra-index-url https://download.pytorch.org/whl/cpu
   ```
5. Salin template env lalu isi kredensial:
   ```bash
   copy .env.example .env          # Windows (Linux/Mac: cp)
   ```
   Minimal wajib terisi untuk uji coba: `NEON_DB_URL`, `GEMINI_API_KEY`, `STORAGE_BACKEND=onedrive` (aman, tidak sentuh produksi) atau `neon` (produksi — hati-hati).
6. Tes koneksi database:
   ```bash
   python -c "import os, psycopg2; from dotenv import load_dotenv; load_dotenv('.env'); psycopg2.connect(os.environ['NEON_DB_URL']).close(); print('DB ok')"
   ```
   **Verifikasi:** cetak `DB ok`. Error SSL/timeout → cek connection string di Neon Console.
7. Jalankan satu scraper ringan sebagai smoke test (tulis ke backend sesuai `.env`):
   ```bash
   python -c "import sys; sys.path.append('src'); from structured_data.cpo_gapki import main_scraper_cpo; main_scraper_cpo()"
   ```
   **Verifikasi:** log `saved`/`upsert` tanpa traceback.
8. (Opsional) jalankan pipeline penuh:
   ```bash
   python src/scheduler/scheduling_day_morning.py
   ```
   Catatan: tanpa `CI=true`, orchestrator berita memakai `START_DATE`/`END_DATE` hardcoded di file orchestrator — sesuaikan dulu bila perlu ([bagian “09 — Panduan Pengembangan Lanjutan”](#sec-09-pengembangan-md)).

##### Kalau Gagal

| Gejala | Solusi |
|---|---|
| `ModuleNotFoundError` | venv belum aktif, atau paket belum terinstall |
| `psycopg2.OperationalError` | `NEON_DB_URL` salah/expired — ambil ulang dari Neon Console |
| Selenium `WebDriverException` | Chrome belum terpasang / versi driver — `webdriver-manager` mengunduh otomatis saat run pertama, butuh internet |
| `GEMINI_API_KEY not found` | `.env` belum terisi / `load_dotenv` tidak menemukan file — jalankan dari root repo |


---

<a id="sec-how-to-02-menjalankan-pipeline-manual-md"></a>

#### How-To 2: Menjalankan Pipeline Manual

Dua cara: lewat GitHub Actions (produksi, disarankan) atau lokal (debugging).

##### A. Lewat GitHub Actions (workflow_dispatch)

1. Buka repo GitHub proyek ini → tab **Actions**.
2. Panel kiri: pilih workflow (mis. *Daily Morning*).
3. Klik dropdown **Run workflow** (kanan atas daftar run) → branch **main** → tombol hijau **Run workflow**.
4. Refresh halaman; run baru muncul dalam ±10 detik dengan label `workflow_dispatch`.
5. Klik run → pantau log per step. Selesai: hijau ✓.

**Verifikasi data masuk** (ganti tabel sesuai pipeline):
```sql
SELECT topic, MAX(date) FROM news_articles GROUP BY topic ORDER BY 2 DESC LIMIT 5;
SELECT MAX("Upload_Dates") FROM data_cpo;
```

Catatan penting:
- **Monthly punya gating tanggal** ([bagian “04 — Pipeline & Scheduling (GitHub Actions)”](#sec-04-pipeline-scheduling-md)): dispatch tanggal 12/15/28 hanya menjalankan step tanggal itu; dispatch tanggal lain menjalankan step 1–4 (EIA, ESDM OCR, biodiesel, bioetanol).
- Aman diulang — semua tulisan upsert (tidak duplikat).
- Satu step gagal tidak menghentikan step lain; baca seluruh log.

##### B. Lokal (debugging)

1. Pastikan setup selesai ([How-To 1](#sec-how-to-01-setup-lokal-dari-nol-md)) dan tentukan target tulis:
   ```bash
   # PILIH SALAH SATU di .env / env shell:
   set STORAGE_BACKEND=onedrive   # aman, Excel dev
   set STORAGE_BACKEND=neon       # PRODUKSI - yakin dulu
   ```
2. Jalankan scheduler yang diinginkan:
   ```bash
   python src/scheduler/scheduling_day_morning.py
   python src/scheduler/scheduling_day_afternoon.py
   python src/scheduler/scheduling_week.py
   python src/scheduler/scheduling_month.py     # gating tanggal berlaku (hari ini)
   ```
3. Atau satu komponen saja (lebih cepat untuk debug):
   ```bash
   # satu scraper terstruktur
   python -c "import sys; sys.path.append('src'); from structured_data.migas_eia import main_eia; main_eia()"
   # satu orchestrator sentiment
   python -c "import sys; sys.path.append('src'); from orchestrators.main_sentiment_news_lokal_harian import main; main()"
   ```

**Verifikasi:** sama seperti bagian A (query MAX tanggal), atau perhatikan log `saved X rows` / `Summary generated successfully`.

##### Kapan Pakai yang Mana

| Situasi | Cara |
|---|---|
| Run terjadwal gagal, mau ulang | A (dispatch) |
| Data hari ini belum masuk padahal jadwal lewat >6 jam | Cek [How-To 3](#sec-how-to-03-cek-kesehatan-scheduler-md) dulu, lalu A |
| Menguji perubahan kode scraper | B, `STORAGE_BACKEND=onedrive` dulu |
| Mengisi gap beberapa hari/bulan | [How-To 4](#sec-how-to-04-backfill-data-bolong-md) |


---

<a id="sec-how-to-03-cek-kesehatan-scheduler-md"></a>

#### How-To 3: Cek Kesehatan Scheduler

Memastikan 4 cron GitHub Actions benar-benar fire sesuai jadwal. Jalankan rutin mingguan atau saat curiga data tidak masuk.

##### Langkah

1. Dari root repo (butuh kredensial git yang bisa akses repo, atau env `GITHUB_TOKEN`):
   ```bash
   python scripts/check_workflow_schedules.py
   ```
2. Baca output per workflow:
   - `OK Sen 2026-07-06 08:00 WIB — ran +220min, success` → sehat. `+menit` = keterlambatan; **3–5 jam normal** (free tier).
   - `.. pending` → jadwal baru lewat, masih dalam jendela toleransi 6 jam. Tunggu.
   - `XX ... MISSED` → cron tidak fire sama sekali → langkah 3.
   - `XX ... failure <URL>` → fire tapi gagal → buka URL, lihat step merah, lalu [How-To 2](#sec-how-to-02-menjalankan-pipeline-manual-md) untuk re-run.
   - `!! WORKFLOW STATE: disabled_inactivity` → langkah 4.
3. Bila MISSED:
   - Cek file workflow ada di branch `main` (cron hanya baca `main`).
   - Cek https://www.githubstatus.com (outage Actions).
   - Cek tanggalnya memang hari kerja (daily = Sen–Jum saja).
4. Bila `disabled_inactivity` (repo 60 hari tanpa aktivitas):
   1. GitHub → **Actions** → klik nama workflow di panel kiri.
   2. Banner kuning "This scheduled workflow is disabled" → klik **Enable workflow**.
   3. Jadwal aktif lagi mulai fire berikutnya. Untuk hari ini, jalankan manual ([How-To 2](#sec-how-to-02-menjalankan-pipeline-manual-md)).
5. Exit code script: `0` = semua sehat, `1` = ada masalah. Bisa dipakai untuk automasi/alert.

##### Verifikasi Akhir

Baris terakhir output = `ALL SCHEDULERS HEALTHY` dan data terbaru masuk:
```sql
SELECT topic, MAX(date) FROM news_articles GROUP BY topic ORDER BY 2 DESC LIMIT 5;
```

##### Opsi

```bash
python scripts/check_workflow_schedules.py --days 30   # perlebar lookback semua workflow
```

Referensi perilaku cron GitHub (delay, auto-disable, default branch): [bagian “04 — Pipeline & Scheduling (GitHub Actions)”](#sec-04-pipeline-scheduling-md).


---

<a id="sec-how-to-04-backfill-data-bolong-md"></a>

#### How-To 4: Backfill Data Bolong

Mengisi gap historis. Tiga alat, pilih sesuai jenis data. Semua tulisan upsert — aman diulang, tidak duplikat. Semua butuh `.env` lengkap; script memaksa `STORAGE_BACKEND=neon`.

##### Pilih Alat

| Jenis gap | Alat |
|---|---|
| Data terstruktur (EIA, CPO, SAF, crackspread, dst.) | `scripts/backfill.py` |
| Berita — topik aktif produksi saja | `scripts/backfill.py --sources news_lokal news_intl` |
| Berita — **semua 25+ topik** (termasuk yang nonaktif) | `scripts/backfill_news_alltopics.py` |
| Summary/sentiment harian historis | `scripts/backfill_sentiment_daily.py` |

##### A. Data Terstruktur

1. Tentukan sumber yang bolong (nama sumber = daftar di docstring `scripts/backfill.py`).
2. Jalankan:
   ```bash
   python scripts/backfill.py --sources eia spglobal_saf --start 2026-05-01 --end 2026-06-30
   ```
   Tier 1 (eia, biodiesel_esdm, bioetanol_esdm, migas_esdm, iaea, wte, cpo) bersifat self-healing — sekali jalan menutup gap sendiri, tanpa perlu rentang.
3. **Verifikasi:** `SELECT MAX(...) FROM data_...` naik sesuai rentang.

##### B. Berita Semua Topik (script alltopics)

1. Jalankan per rentang "bulan ke belakang" (bulan-1 = 30 hari terakhir):
   ```bash
   python scripts/backfill_news_alltopics.py --from-month 1 --to-month 2 --delay 0.5
   ```
2. Boleh diparalelkan per bulan (progress file terpisah otomatis per rentang):
   ```bash
   # terminal 1
   python scripts/backfill_news_alltopics.py --from-month 1 --to-month 1
   # terminal 2
   python scripts/backfill_news_alltopics.py --from-month 2 --to-month 2
   ```
3. Interrupt kapan saja (Ctrl+C); jalankan ulang perintah sama → resume dari tanggal terakhir (file `scripts/backfill_alltopics_progress_m*.json`).
4. **Verifikasi:** `SELECT COUNT(*), MIN(date), MAX(date) FROM news_articles;` bertambah.

**Ekspektasi realistis:** situs berita umumnya hanya meng-expose artikel terbaru (sitemap/RSS live). Untuk bulan >2 ke belakang, hasil terutama dari sumber berbasis pencarian (Bisnis Indonesia, Tempo). Arsip sitemap bulanan Kompas sudah **mati di sisi Kompas** (diverifikasi Jul 2026 — semua URL `sitemap-news-*-YYYY-MM.xml` mengembalikan urlset kosong); mode `--kompas` tidak akan menghasilkan apa-apa sampai Kompas memulihkannya.

##### C. Summary/Sentiment Harian Historis

Orchestrator produksi hanya bergerak maju dari summary terakhir — tanggal lampau **tidak akan pernah terisi sendiri**. Pakai script ini:

1. (Disarankan) hitung dulu tanpa memanggil Gemini:
   ```bash
   python scripts/backfill_sentiment_daily.py --dry-run
   ```
   Output akhir: `Summary akan ditulis: N`. Perhatikan N vs kuota Gemini.
2. Jalankan sungguhan (delay antar call Gemini, default 4 detik):
   ```bash
   python scripts/backfill_sentiment_daily.py --delay 4
   # atau subset:
   python scripts/backfill_sentiment_daily.py --topics IHSG Inflasi --start 2026-01-01 --end 2026-06-30
   ```
3. Hanya (topik, hari) yang **punya artikel tapi belum punya summary** yang diproses — aman diulang.
4. **Verifikasi:**
   ```sql
   SELECT topic, COUNT(*), MIN("Tanggal awal"), MAX("Tanggal awal") FROM news_sentiment GROUP BY topic;
   ```

##### Urutan yang Benar untuk Gap Besar

1. Backfill **berita** dulu (B) — summary butuh artikel.
2. Baru backfill **sentiment** (C).
3. Terakhir cek data terstruktur (A) bila perlu.


---

<a id="sec-how-to-05-menambah-topik-berita-md"></a>

#### How-To 5: Menambah / Mengaktifkan Topik Berita

Dua kasus: (A) topik sudah ada tapi nonaktif (dikomentari) — paling sering; (B) topik benar-benar baru.

##### A. Mengaktifkan Topik yang Dikomentari

Contoh: mengaktifkan kembali `(News)IHSG` di pipeline lokal.

1. Buka [src/orchestrators/main_news_scraping_lokal.py](../src/orchestrators/main_news_scraping_lokal.py) (atau `_internasional.py` untuk topik intl).
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
6. Isi data historisnya: [How-To 4](#sec-how-to-04-backfill-data-bolong-md) bagian B lalu C.

> Tidak perlu perubahan database — semua topik berita masuk tabel `news_articles` (kolom `topic`), summary masuk `news_sentiment`.

##### B. Topik Benar-Benar Baru

1. Tentukan: nama sheet `(News)Nama Topik`, keyword pencarian (akhiri spasi, konsisten dengan pola existing), scraper mana yang relevan.
2. Tambahkan entri **baru** di `SUMBER_DICT`, `SHEET_TO_KEYWORD`, `ACTIVE_SHEETS` (file orchestrator lokal dan/atau intl).
3. (Opsional summary) tambah blok di `TOPICS` orchestrator sentiment dengan `output_sheet: "(Summary)Nama Topik"` — pola blok tinggal copy dari topik lain.
4. Uji seperti langkah A.4, commit, merge ke `main`.
5. Power BI: buat query baru dari `news_articles` filter `[topic] = "(News)Nama Topik"` ([How-To 7](#sec-how-to-07-koneksi-power-bi-neon-md) pola M-code), dan dari `news_sentiment` untuk summary-nya.
6. Catat topik baru di [bagian “05 — Sumber Data & Scraper”](#sec-05-sumber-data-md).

##### Menambah Scraper Situs Baru (bila sumbernya belum ada)

1. Buat `src/news/nama_situs.py` meniru scraper serupa: sitemap → contoh `cnn.py`; RSS → `oilprice.py`; halaman pencarian → `bisnis_indonesia.py`.
2. Kontrak fungsi: terima `(keyword, tanggal_filter)`, kembalikan DataFrame kolom `title, date, url, content, source, keyword`.
3. Import + daftarkan di `SUMBER_DICT` orchestrator.
4. Uji: panggil fungsinya langsung dengan satu keyword + tanggal kemarin; pastikan kolom lengkap dan `date` sesuai filter.


---

<a id="sec-how-to-06-menambah-sumber-terstruktur-md"></a>

#### How-To 6: Menambah Sumber Data Terstruktur

Dari nol sampai tampil di Power BI. Contoh fiktif: dataset "Harga Gas" bulanan dari situs X → tabel `data_harga_gas`.

##### Langkah

1. **Scraper.** Buat `src/structured_data/harga_gas.py` (contoh paling sederhana untuk ditiru: [cpo_gapki.py](../src/structured_data/cpo_gapki.py); dengan API key: [migas_eia.py](../src/structured_data/migas_eia.py)):
   ```python
   from helpers.storage_backend import storage

   SHEET_NAME = "(Data)Harga Gas"

   def main_harga_gas():
       df = ...  # hasil scraping, kolom final persis yang mau tampil
       storage.write_structured_sheet(SHEET_NAME, df)
   ```
2. **Registrasi mapping** di [src/helpers/storage_backend.py](../src/helpers/storage_backend.py):
   ```python
   # SHEET_TO_TABLE
   "(Data)Harga Gas": "data_harga_gas",
   # SHEET_CONFLICT_COLS  (kolom yang mengidentifikasi baris unik)
   "(Data)Harga Gas": ["Tahun", "Bulan"],
   ```
3. **DDL** di [scripts/create_tables.sql](../scripts/create_tables.sql) — `UNIQUE` **harus sama persis** dengan conflict cols (upsert gagal tanpa itu):
   ```sql
   CREATE TABLE IF NOT EXISTS data_harga_gas (
       id SERIAL PRIMARY KEY,
       "Tahun" INTEGER,
       "Bulan" TEXT,
       "Harga" NUMERIC,
       UNIQUE ("Tahun", "Bulan")
   );
   ```
   Terapkan: `python scripts/run_schema.py`
4. **View** di [scripts/create_views.sql](../scripts/create_views.sql) (Power BI baca view, bukan tabel):
   ```sql
   CREATE OR REPLACE VIEW vw_harga_gas AS
   SELECT "Tahun", "Bulan", "Harga" FROM data_harga_gas;
   ```
   Terapkan: `psql $NEON_DB_URL -f scripts/create_views.sql`
5. **Uji tulis** (lokal, langsung ke Neon):
   ```bash
   set STORAGE_BACKEND=neon
   python -c "import sys; sys.path.append('src'); from structured_data.harga_gas import main_harga_gas; main_harga_gas()"
   ```
   **Verifikasi:** `psql $NEON_DB_URL -c 'SELECT * FROM vw_harga_gas LIMIT 5;'` berisi data. Jalankan **dua kali** — jumlah baris tidak boleh dobel (bukti upsert benar).
6. **Jadwalkan** — panggil `main_harga_gas()` dari scheduler yang sesuai (mis. [scheduling_month.py](../src/scheduler/scheduling_month.py)) dengan pola step existing (`try/except` + banner). Bila butuh tanggal khusus, tambah konstanta `DAY_*` **dan** tanggal di cron [monthly.yml](../.github/workflows/monthly.yml) **dan** update `scripts/check_workflow_schedules.py`.
7. **Secrets** (bila sumber butuh auth): tambah var di `.env.example` + `.env`, GitHub → Settings → Secrets → New secret, lalu inject di blok `env:` workflow terkait.
8. **Power BI**: query baru dari `vw_harga_gas` ([How-To 7](#sec-how-to-07-koneksi-power-bi-neon-md)), catat M-code di `scripts/power_query_migrated.txt`.
9. **Dokumentasi**: tambahkan baris di [bagian “05 — Sumber Data & Scraper”](#sec-05-sumber-data-md) dan [bagian “03 — Database Neon PostgreSQL”](#sec-03-database-md).

##### Checklist Verifikasi Akhir

- [ ] Run dua kali → tidak ada duplikat
- [ ] Tabel + view muncul di Neon
- [ ] Step tampil di log run workflow berikutnya (hijau)
- [ ] Kartu/visual Power BI ter-refresh dengan data baru


---

<a id="sec-how-to-07-koneksi-power-bi-neon-md"></a>

#### How-To 7: Menyambungkan Power BI ke Neon

Setup koneksi PostgreSQL di file .pbix (baru atau pindah mesin) + membuat query baru.

##### Prasyarat

- Power BI Desktop terbaru.
- Kredensial database: user + password dari `NEON_DB_URL` (format `postgresql://USER:PASSWORD@HOST/neondb?sslmode=require`; ambil dari Neon Console → Connection Details).
- Skema + view sudah terpasang di Neon ([How-To 6](#sec-how-to-06-menambah-sumber-terstruktur-md) langkah 3–4, atau `python scripts/run_schema.py`).

##### A. Koneksi Pertama Kali

1. Power BI Desktop → **Get Data** → cari **PostgreSQL database** → Connect.
2. Isi:
   - **Server:** `ep-winter-cell-aoi4t802.c-2.ap-southeast-1.aws.neon.tech`
   - **Database:** `neondb`
   - **Data Connectivity mode:** **Import** (JANGAN DirectQuery — Neon auto-suspend membuatnya lambat/gagal)
3. Dialog kredensial → tab **Database** → isi User name + Password dari `NEON_DB_URL` → Connect.
4. Bila muncul peringatan enkripsi, pilih opsi terenkripsi (Neon mewajibkan SSL).
5. Navigator menampilkan tabel/view schema `public`. **Verifikasi:** `vw_cpo`, `news_articles` dll. terlihat.

> Kredensial tersimpan per-server di Power BI (File → Options → Data source settings). Ganti password Neon = perbarui di sana.

##### B. Migrasi Query Existing (SharePoint → Neon)

1. **Transform Data** (Power Query Editor).
2. Buka [scripts/power_query_migrated.txt](../scripts/power_query_migrated.txt) — cari nama query.
3. Bertanda `[NEON]` → pilih query di panel kiri → **Advanced Editor** → ganti seluruh M-code dengan versi di file → Done.
4. Bertanda `[UNCHANGED]` → **biarkan** (masih SharePoint: seri makro, input manual).
5. Ulangi semua query `[NEON]` → **Close & Apply** → tunggu refresh penuh → simpan .pbix.

**Verifikasi:** Refresh tanpa error; jumlah baris visual ≈ `SELECT COUNT(*)` tabel terkait.

##### C. Query Baru dari Neon

Pola M-code (lihat juga contoh nyata di `power_query_migrated.txt`):

```m
// Data terstruktur - selalu lewat view vw_*
let
    Source = PostgreSQL.Database("ep-winter-cell-aoi4t802.c-2.ap-southeast-1.aws.neon.tech", "neondb"),
    data = Source{[Schema="public", Item="vw_harga_gas"]}[Data]
in
    data

// Berita per topik
let
    Source = PostgreSQL.Database("ep-winter-cell-aoi4t802.c-2.ap-southeast-1.aws.neon.tech", "neondb"),
    t = Source{[Schema="public", Item="news_articles"]}[Data],
    f = Table.SelectRows(t, each [topic] = "(News)Harga Minyak"),
    clean = Table.RemoveColumns(f, {"id", "topic"})
in
    clean
```

Konvensi: data terstruktur lewat **view** (sudah bersih dari `id`, kapitalisasi kolom benar); berita/sentimen dari tabel + filter `topic` + buang `id`,`topic`; transformasi berat taruh di view SQL, bukan di M. Setelah jadi, **catat M-code di `scripts/power_query_migrated.txt`**.

##### Troubleshooting

| Gejala | Solusi |
|---|---|
| Refresh pertama sangat lambat | Neon baru bangun dari suspend — ulangi |
| Error kredensial | Password dirotasi → Options → Data source settings → Edit Permissions → Edit |
| "column does not exist" | Skema berubah tanpa update view/M — cocokkan dengan `create_views.sql` |
| Data kosong topik tertentu | Pipeline topik itu gagal/nonaktif → [How-To 3](#sec-how-to-03-cek-kesehatan-scheduler-md) |


---

<a id="sec-how-to-08-rotasi-kredensial-md"></a>

#### How-To 8: Rotasi Kredensial

Wajib saat: handover selesai, ada indikasi bocor, atau rutin (disarankan 6-bulanan). Inventaris lengkap akun: [bagian “Inventaris Aset & Akses”](#sec-handover-02-inventaris-aset-akses-md).

##### Prinsip Umum (berlaku semua kredensial)

Untuk tiap kredensial, urutannya selalu:
1. Generate nilai baru di layanan sumber.
2. Update **GitHub Secrets**: repo → Settings → Secrets and variables → Actions → klik nama secret → Update.
3. Update `.env` lokal semua mesin dev.
4. Uji (lihat kolom uji di tabel).
5. Revoke/hapus nilai lama (bila layanannya memisahkan create/revoke).

##### Per Kredensial

| Kredensial | Cara generate baru | Uji setelah rotasi |
|---|---|---|
| `NEON_DB_URL` | Neon Console → project → Roles/Connection Details → Reset password | `python -c "...psycopg2.connect..."` ([How-To 1](#sec-how-to-01-setup-lokal-dari-nol-md) langkah 6) + **update kredensial Power BI** (Options → Data source settings) |
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey → Create API key; hapus key lama | `python -c "import sys; sys.path.append('src'); from helpers.summary_helper import setup_gemini; setup_gemini(); print('ok')"` |
| `SPGLOBAL_USERNAME/PASSWORD` | Akun S&P Global Platts (via account manager S&P bila SSO) | Dispatch workflow *Daily Afternoon*, cek step SAF hijau |
| `EIA_API_KEY` | https://www.eia.gov/opendata/register.php | Dispatch *Monthly* (step EIA) atau `main_eia()` lokal |
| `MS_CLIENT_SECRET` | Azure Portal → App registrations → app terkait → Certificates & secrets → New client secret (catat: expiry!) | `python -c "import sys; sys.path.append('src'); from helpers.onedrive_helper import get_access_token; get_access_token(); print('ok')"` |
| Kredensial Power BI/SharePoint | Ikuti kebijakan M365 organisasi | Refresh .pbix penuh |

##### Setelah Semua Dirotasi

1. Jalankan pipeline penuh sekali via dispatch (minimal *Daily Morning* + *Daily Afternoon*) — semua step hijau = rotasi bersih.
2. `python scripts/check_workflow_schedules.py` → exit 0.
3. Hapus `token.json` di root repo bila ada (cache OAuth lama; dibuat ulang otomatis).
4. Catat tanggal rotasi + expiry (khusus MS client secret punya masa berlaku!) di dokumen internal tim.

##### Bila Kredensial Bocor (urutan darurat)

1. Revoke kredensial bocor di layanan sumber **duluan** (bukan update dulu).
2. Generate baru → update GitHub Secrets → uji.
3. Khusus `NEON_DB_URL`: cek query/aktivitas asing di Neon Console → Monitoring.
4. Khusus repo: bila `.env` pernah ter-commit, anggap SEMUA isinya bocor — rotasi semuanya.


---

<a id="sec-how-to-09-backup-restore-neon-md"></a>

#### How-To 9: Backup & Restore Database Neon

Kapan backup manual: sebelum migrasi skema, sebelum operasi hapus/TRUNCATE, sebelum backfill besar, atau rutin bulanan.

##### Prasyarat

- `pg_dump`/`pg_restore`/`psql` terpasang (PostgreSQL client tools; Windows: installer EDB atau `winget install PostgreSQL.PostgreSQL`).
- `NEON_DB_URL` di env. PowerShell: `$env:NEON_DB_URL = "postgresql://..."`; Git Bash: `export NEON_DB_URL="postgresql://..."`.

##### A. Backup Penuh

```bash
pg_dump "$NEON_DB_URL" -Fc -f backup_$(date +%Y%m%d).dump
```

**Verifikasi:** file .dump ada, ukuran wajar (puluhan MB), dan bisa dibaca:
```bash
pg_restore --list backup_20260706.dump | head
```

##### B. Backup Satu Tabel (cepat, sebelum operasi berisiko)

```bash
# format dump (bisa di-restore utuh)
pg_dump "$NEON_DB_URL" -Fc -t news_sentiment -f news_sentiment_20260706.dump
# atau CSV (bisa dibuka Excel)
psql "$NEON_DB_URL" -c "\copy news_sentiment TO 'news_sentiment.csv' CSV HEADER"
```

##### C. Restore

> ⚠️ Restore menimpa data. Pastikan target benar; pertimbangkan restore ke branch Neon dulu (bagian E).

```bash
# satu tabel (drop + create + isi ulang)
pg_restore "$NEON_DB_URL" --clean --if-exists -t news_sentiment news_sentiment_20260706.dump

# seluruh database
pg_restore "$NEON_DB_URL" --clean --if-exists backup_20260706.dump
```

**Verifikasi:** `SELECT COUNT(*)` tabel terkait sama dengan sebelum insiden; spot-check beberapa baris terbaru.

##### D. Point-in-Time Restore (fitur Neon, tanpa file)

Salah hapus dan tidak punya dump? Neon menyimpan history (retensi terbatas di free tier — cek dulu di console):

1. https://console.neon.tech → project → **Branches**.
2. **Create branch** → pilih **From past state / timestamp** → pilih waktu sebelum insiden.
3. Branch baru berisi snapshot data saat itu. Ambil datanya:
   ```bash
   pg_dump "<CONNECTION_STRING_BRANCH>" -Fc -t tabel_rusak -f rescue.dump
   pg_restore "$NEON_DB_URL" --clean --if-exists -t tabel_rusak rescue.dump
   ```
4. Hapus branch penyelamat setelah selesai (hemat storage).

##### E. Branch Neon sebagai "Staging" (uji tanpa risiko)

Sebelum operasi besar (migrasi skema, TRUNCATE, backfill masif):

1. Console → Branches → **Create branch** (from current) → dapat connection string baru.
2. Jalankan operasinya ke branch itu dulu (`NEON_DB_URL` diarahkan ke branch).
3. Hasil benar → ulangi ke main branch; salah → hapus branch, tidak ada kerusakan.

##### Rutinitas Disarankan

- Bulanan: backup penuh (A), simpan di luar laptop (drive terenkripsi/cloud storage tim).
- Sebelum tiap `TRUNCATE`/`DELETE`/perubahan skema: backup tabel terkait (B) — 10 detik yang menyelamatkan hari.
- Ukuran DB mendekati 512 MB free tier? Lihat [bagian “08 — Runbook Maintenance”](#sec-08-maintenance-md).


---

<a id="sec-handover-01-bast-md"></a>

#### Berita Acara Serah Terima (BAST)
##### Sistem Dashboard SPEED Pertamina Energy Institute

> Template — semua isian `[ISI: …]` wajib dilengkapi sebelum ditandatangani.

Pada hari ini, `[ISI: hari]`, tanggal `[ISI: tanggal]`, bertempat di `[ISI: lokasi]`, telah dilakukan serah terima sistem **Dashboard SPEED Pertamina Energy Institute** dari:

**PIHAK PERTAMA (yang menyerahkan)**
- Nama: `[ISI: nama]`
- Jabatan/Peran: `[ISI: jabatan]` (developer/pengelola sistem)

kepada:

**PIHAK KEDUA (yang menerima)**
- Nama: `[ISI: nama]`
- Jabatan/Peran: `[ISI: jabatan]` (tim internal PT Pertamina Energy Institute)

---

##### 1. Ruang Lingkup yang Diserahkan

| # | Aset | Bentuk Serah Terima |
|---|---|---|
| 1 | Repositori kode dashboard (GitHub) | Transfer ownership / akses admin — lihat [bagian “Inventaris Aset & Akses”](#sec-handover-02-inventaris-aset-akses-md) |
| 2 | Database Neon PostgreSQL (`neondb`, region `ap-southeast-1`) | Transfer akun / akses admin console |
| 3 | 4 workflow GitHub Actions (daily morning, daily afternoon, weekly, monthly) | Ikut repositori; daftar secrets diserahkan terpisah |
| 4 | File Power BI (`.pbix`) | `[ISI: lokasi file / workspace Power BI Service]` |
| 5 | M-code Power Query — sumber kebenaran: `scripts/power_query_migrated.txt` | Ikut repositori |
| 6 | Dokumentasi teknis lengkap (`docs/01`–`09`) + dokumen handover (`docs/handover/`) | Ikut repositori |
| 7 | Kredensial & API key seluruh layanan | **Jalur aman terpisah** (bukan email/chat) — lalu dirotasi PIHAK KEDUA, lihat [bagian “Inventaris Aset & Akses”](#sec-handover-02-inventaris-aset-akses-md) |

##### 2. Kondisi Sistem Saat Serah Terima

- Database: **22 tabel** + **20 view** (`vw_*`) — daftar lengkap di [bagian “03 — Database Neon PostgreSQL”](#sec-03-database-md).
- Pipeline otomatis: 4 workflow terjadwal (jadwal & isi di [README](#sec-how-to-readme-md) dan [bagian “04 — Pipeline & Scheduling (GitHub Actions)”](#sec-04-pipeline-scheduling-md)).
- AI sentimen: Google Gemini `gemini-2.5-flash-lite` (free tier) — [bagian “06 — AI & Analisis Sentimen Berita”](#sec-06-ai-sentiment-md).
- Power BI: mode **Import**, sebagian query masih ke SharePoint (macro series) — [bagian “07 — Power BI & Power Query”](#sec-07-power-bi-md).
- Status run terakhir saat serah terima: `[ISI: tanggal cek + hasil, jalankan python scripts/check_workflow_schedules.py dan lampirkan output]`.

##### 3. Known Issues & Limitasi yang Disepakati

Diserahkan **apa adanya** dengan isu berikut sudah diketahui kedua pihak (detail & mitigasi di [bagian “08 — Runbook Maintenance”](#sec-08-maintenance-md) bagian Known Issues):

1. **Delay cron 3–5 jam** dari jadwal — perilaku normal GitHub Actions free tier.
2. **Limit storage Neon 512 MB** (free tier) — pertumbuhan terbesar `news_articles.content`; cek bulanan.
3. **Auto-disable workflow** setelah 60 hari repo tanpa aktivitas — perlu commit/aktivitas berkala.
4. **Anomali data WTE tahun 2018** — nilai timbulan jauh lebih kecil dari tahun lain (kemungkinan cakupan provinsi sumber lebih sedikit); perlu validasi ke sumber SIPSN bila dashboard terlihat janggal.
6. **`BPS_API_KEY`** direferensikan kode (`src/news/bps.py`) tapi tidak ada di `.env.example` maupun workflow — konfirmasi apakah scraper BPS masih aktif: `[ISI: aktif/tidak]`.
7. **Secrets MS/OneDrive masih di-inject ke semua workflow** padahal backend produksi sudah Neon — permukaan kredensial lebih luas dari yang diperlukan (legacy/fallback).
8. **Tanggal backfill hardcoded `2026-04-17`** di orchestrator sentimen — aman di CI, perlu disesuaikan bila run manual lokal.
9. **Refresh Power BI butuh dua kredensial** (Neon + SharePoint) karena macro series belum dimigrasi.
10. **Step monthly tanggal 12/15/28 baru aktif Juli 2026** — verifikasi fire pertama; gap data lama diisi via dispatch manual/backfill.

##### 4. Pekerjaan Pending / Di Luar Scope

| # | Item | Status |
|---|---|---|
| 1 | `[ISI: mis. migrasi macro series SharePoint → Neon]` | `[ISI]` |
| 2 | `[ISI]` | `[ISI]` |

Backlog ide pengembangan: [bagian “09 — Panduan Pengembangan Lanjutan”](#sec-09-pengembangan-md).

##### 5. Masa Dukungan Pasca-Serah-Terima

- PIHAK PERTAMA bersedia menjadi kontak konsultasi sampai: `[ISI: tanggal akhir masa dukungan]`.
- Periode shadow (PIHAK KEDUA operasikan, PIHAK PERTAMA standby): `[ISI: durasi, rekomendasi 2–4 minggu]`.
- Setelah masa dukungan berakhir, seluruh kredensial wajib sudah dirotasi oleh PIHAK KEDUA (checklist di [bagian “Inventaris Aset & Akses”](#sec-handover-02-inventaris-aset-akses-md)).

##### 6. Penutup

Demikian berita acara ini dibuat dalam rangkap dua, masing-masing memiliki kekuatan hukum yang sama.

| PIHAK PERTAMA | PIHAK KEDUA |
|---|---|
| <br><br><br> | <br><br><br> |
| `[ISI: nama]` | `[ISI: nama]` |
| `[ISI: jabatan]` | `[ISI: jabatan]` |


---

<a id="sec-handover-02-inventaris-aset-akses-md"></a>

#### Inventaris Aset & Akses

Daftar semua akun, kredensial, dan aset yang harus berpindah tangan saat handover, plus checklist rotasi. Pelengkap [bagian “08 — Runbook Maintenance”](#sec-08-maintenance-md) bagian "Secrets & Kredensial".

##### 1. Akun & Layanan

| Aset | Pemilik sekarang | Penerima (PEI) | Cara transfer |
|---|---|---|---|
| Repo GitHub `[NAMA-REPO-GITHUB]` | Akun personal `shelmasalsa17` | `[ISI: org/akun PEI]` | **Transfer ownership** (Settings → General → Transfer) ke org PEI, atau minimal tambah admin. Catatan: transfer mempertahankan Actions & secrets, tapi URL remote berubah — update remote di mesin dev & Power BI docs |
| Akun Neon PostgreSQL | `[ISI: email pemilik]` | `[ISI]` | Transfer project ke org Neon PEI (console.neon.tech → Project settings), atau ganti kepemilikan akun. Project: `neondb`, region `ap-southeast-1` |
| Google AI Studio (Gemini API key) | `[ISI: akun Google]` | `[ISI]` | PEI buat API key baru di akun sendiri → ganti secret `GEMINI_API_KEY`. Jangan pakai key lama |
| Aplikasi Microsoft/MS Graph (OneDrive legacy) | `[ISI: tenant/akun]` | `[ISI]` | Hanya perlu bila fallback OneDrive dipertahankan; kalau tidak, hapus secrets MS_*/ONEDRIVE_* dari workflow (lihat Known Issues docs/08) |
| Akun S&P Global Platts | `[ISI: username]` | `[ISI]` | Langganan korporat — konfirmasi kepemilikan lisensi & ganti password setelah handover |
| Akun EIA (api.eia.gov) | `[ISI: email]` | `[ISI]` | Gratis — PEI daftar sendiri, ganti `EIA_API_KEY` |
| File `.pbix` + workspace Power BI | `[ISI: akun publish]` | `[ISI]` | Serahkan file + pindahkan ownership dataset/report di Power BI Service; set ulang kredensial data source (Neon + SharePoint) |
| Akses SharePoint (macro series) | `[ISI]` | `[ISI]` | Pastikan akun refresh Power BI PEI punya akses ke file SharePoint tersebut |

##### 2. GitHub Secrets per Workflow

(Settings → Secrets and variables → Actions. Nilai TIDAK ditulis di sini — serahkan lewat jalur aman.)

| Secret | daily_morning | daily_afternoon | weekly | monthly | Fungsi |
|---|:--:|:--:|:--:|:--:|---|
| `NEON_DB_URL` | ✓ | ✓ | ✓ | ✓ | Koneksi PostgreSQL Neon |
| `GEMINI_API_KEY` | ✓ | ✓ | ✓ | — | AI sentimen (Gemini) |
| `SPGLOBAL_USERNAME` / `SPGLOBAL_PASSWORD` | — | ✓ | ✓ | ✓ | Login S&P Global Platts |
| `EIA_API_KEY` | — | — | — | ✓ | API EIA |
| `MS_CLIENT_ID` / `MS_CLIENT_SECRET` / `MS_TENANT_ID` / `MS_USER_EMAIL` | ✓ | ✓ | ✓ | ✓ | MS Graph OAuth (legacy OneDrive) |
| `ONEDRIVE_FILE_PATH` / `ONEDRIVE_SENTIMENT_PATH` / `ONEDRIVE_DATA_PATH` | ✓ | ✓ | ✓ | ✓ | Path Excel OneDrive (legacy) |

##### 3. Environment Variable Lokal (`.env`)

Template: `.env.example`. Var aktif:

| Var | Fungsi | Dipakai oleh |
|---|---|---|
| `NEON_DB_URL` | Koneksi Neon | `src/helpers/neon_helper.py`, `scripts/run_schema.py` |
| `STORAGE_BACKEND` | Switch `neon` (prod/CI) / `onedrive` (dev legacy) | `src/helpers/storage_backend.py` |
| `GEMINI_API_KEY` | Gemini API | `src/helpers/summary_helper.py` |
| `SPGLOBAL_USERNAME`, `SPGLOBAL_PASSWORD` | Login Platts | `src/news/spglobal_news.py`, `src/structured_data/spglobal_data.py` |
| `EIA_API_KEY` | API EIA | `src/structured_data/migas_eia.py` |
| `MS_CLIENT_ID`, `MS_CLIENT_SECRET`, `MS_TENANT_ID`, `MS_USER_EMAIL` | MS Graph OAuth | `src/helpers/onedrive_helper.py` |
| `ONEDRIVE_FILE_PATH`, `ONEDRIVE_SENTIMENT_PATH`, `ONEDRIVE_DATA_PATH` | Path Excel OneDrive | `src/helpers/storage_backend.py`, `src/structured_data/*` |
| `BPS_API_KEY` | API BPS — ⚠️ dipakai `src/news/bps.py` tapi **tidak ada** di `.env.example`/workflow; konfirmasi status scraper | `src/news/bps.py` |
| `GITHUB_TOKEN` / `GH_TOKEN` | Monitoring workflow (opsional, naikkan rate limit) | `scripts/check_workflow_schedules.py` |

Var **tidak terpakai** (scaffold/legacy, boleh dibersihkan): `AI_TYPE`, `OPENAI_API_KEY`, `OPENAI_MODEL_NAME`, `GOOGLE_CREDENTIALS`, `SPREADSHEET_ID`, `SPREADSHEET_ID_STRUCTURE`.

##### 4. Checklist Rotasi Kredensial Pasca-Handover

Prinsip: **semua kredensial yang pernah dipegang pihak lama dianggap bocor** — rotasi total. Detail peringatan keamanan (.env, token.json): [bagian “08 — Runbook Maintenance”](#sec-08-maintenance-md) bagian "Peringatan Keamanan".

- [ ] Reset password database Neon (console → roles) → update `NEON_DB_URL` di: GitHub Secrets, `.env` mesin operator baru, **dan Power BI Data source settings**
- [ ] Buat `GEMINI_API_KEY` baru di akun Google PEI → update GitHub Secrets + `.env`; revoke key lama
- [ ] Ganti `SPGLOBAL_PASSWORD` → update GitHub Secrets + `.env`
- [ ] Daftar `EIA_API_KEY` baru atas email PEI → update; deactivate key lama
- [ ] (Bila OneDrive dipertahankan) rotate `MS_CLIENT_SECRET` di Azure AD; hapus `token.json` lama
- [ ] (Bila OneDrive TIDAK dipertahankan) hapus secrets MS_*/ONEDRIVE_* dari 4 workflow YAML + GitHub Secrets
- [ ] Hapus akses kolaborator lama dari repo GitHub setelah masa dukungan berakhir
- [ ] Verifikasi: jalankan `workflow_dispatch` semua 4 workflow → hijau; refresh Power BI → sukses


---

<a id="sec-handover-03-runbook-hari-pertama-md"></a>

#### Runbook Operator Hari Pertama

Panduan diagnosis untuk operator baru menghadapi 3 masalah paling umum. Pelengkap [bagian “08 — Runbook Maintenance”](#sec-08-maintenance-md) (checklist rutin, tabel gejala scraper, backup) — baca itu dulu sebagai dasar.

##### Prasyarat Akses

Sebelum hari pertama, pastikan punya:
- [ ] Akses repo GitHub (minimal write, idealnya admin untuk kelola secrets)
- [ ] Akses console Neon (https://console.neon.tech) atau minimal `NEON_DB_URL` untuk query
- [ ] Akses edit + refresh file Power BI
- [ ] `.env` terisi di mesin lokal (template: `.env.example`, isi lewat jalur aman)

---

##### Skenario 1: Workflow Merah di GitHub Actions

1. Buka **Actions** → klik run yang gagal → cari step merah. Log terstruktur `>>> STEP n: ...` diikuti traceback. **Periksa seluruh log** — satu step gagal tidak membatalkan step lain, bisa jadi lebih dari satu yang gagal.
2. Cocokkan gejala dengan tabel diagnosis di [bagian “08 — Runbook Maintenance”](#sec-08-maintenance-md) (404 = situs pindah, 403/429 = diblokir, 0 baris = selector berubah, auth error = password expired, dst).
3. Kapan boleh diabaikan: kegagalan sekali karena timeout/situs down sementara — run berikutnya biasanya pulih (tulisan idempoten/upsert, tidak ada data korup).
4. Kapan harus ditindak: gagal **2+ hari berturut-turut** pada step sama → scraper rusak, perlu perbaikan kode.
5. Ulangi manual: **Actions → pilih workflow → Run workflow** (dispatch). Untuk monthly, ingat ada gating tanggal ([bagian “04 — Pipeline & Scheduling (GitHub Actions)”](#sec-04-pipeline-scheduling-md)).
6. Gap data beberapa hari: `scripts/backfill.py --sources <sumber> --start ... --end ...`

> Run "MISSED" (tidak fire sama sekali) ≠ gagal. Cek `!! WORKFLOW STATE: disabled_inactivity` via `python scripts/check_workflow_schedules.py` — GitHub mematikan cron setelah 60 hari repo tanpa aktivitas; re-enable di tab Actions.

##### Skenario 2: Data Tidak Update di Dashboard Power BI

Urutan diagnosis — dari hulu ke hilir, berhenti di titik pertama yang bermasalah:

1. **Pipeline jalan?** Tab Actions: run terakhir hijau? Ingat delay 3–5 jam dari jadwal itu normal. Kalau merah → Skenario 1.
2. **Data sampai Neon?** Query cepat (psql/console Neon):
   ```sql
   SELECT MAX("Upload_Dates") FROM data_cpo;
   SELECT topic, MAX(date) FROM news_articles GROUP BY topic;
   SELECT topic, MAX("Tanggal awal") FROM news_sentiment GROUP BY topic;
   ```
   Tanggal lama padahal Actions hijau → cek log step terkait (bisa "sukses" tapi 0 baris karena situs berubah).
3. **View mengembalikan data?** `SELECT count(*) FROM vw_<nama>;` — error di view (mis. cast numeric) berarti masalah di definisi view, perbaiki `scripts/create_views.sql` lalu jalankan ulang ke Neon.
4. **Power BI refresh?** Mode **Import** — data hanya berubah setelah refresh manual/terjadwal. Refresh butuh **dua kredensial**: PostgreSQL (Neon) dan SharePoint (macro series). Kredensial Neon berubah (mis. habis rotasi) → update di **Data source settings**.
5. Masih buntu → cek query M di `scripts/power_query_migrated.txt` (sumber kebenaran M-code); pastikan nama kolom view = nama yang di-expect Power Query (case-sensitive!).

##### Skenario 3: API Key Expired / Kena Limit

| Layanan | Gejala di log | Tindakan |
|---|---|---|
| Gemini | `401/403 API key not valid` atau `429 quota` di step sentiment | Buat key baru di Google AI Studio → update secret `GEMINI_API_KEY` + `.env`. Quota 429: tunggu reset harian atau upgrade tier |
| S&P Global | Auth error di step spglobal | Ganti `SPGLOBAL_PASSWORD` (password korporat expired berkala) |
| EIA | `403 invalid api key` di step EIA (monthly) | Regenerate di akun EIA → update `EIA_API_KEY` |
| Neon | `connection refused` / `password authentication failed` semua step | Cek console Neon (project suspended? password dirotasi?) → update `NEON_DB_URL` di Secrets + `.env` + Power BI |

Cara update secret: repo → **Settings → Secrets and variables → Actions** → edit nilai. Lalu re-run workflow yang gagal untuk verifikasi. Jangan lupa `.env` lokal ikut diganti ([checklist rotasi](#sec-handover-02-inventaris-aset-akses-md)).

---

##### Eskalasi

| Masalah | Kontak | Keterangan |
|---|---|---|
| Sistem/kode/pipeline | `[ISI: nama developer]` — `[ISI: email/telp]` | Masa dukungan s.d. `[ISI: tanggal]` |
| Infrastruktur Neon | Support Neon (console → Help) | Free tier: dokumentasi + community |
| Langganan S&P Global | `[ISI: PIC kontrak Platts di PEI]` | |
| Power BI / lisensi Microsoft | `[ISI: IT PEI]` | |

##### Rekomendasi Transisi

1. **Walkthrough terekam** 1–2 sesi: live demo buka Actions, query Neon, jalankan satu scraper lokal, refresh Power BI.
2. **Periode shadow 2–4 minggu**: operator PEI pegang checklist rutin [bagian “08 — Runbook Maintenance”](#sec-08-maintenance-md), developer lama standby.
3. Akhir shadow: jalankan [checklist rotasi kredensial](#sec-handover-02-inventaris-aset-akses-md), tutup akses lama.


---

<a id="sec-handover-04-biaya-lisensi-md"></a>

#### Biaya & Lisensi

Ringkasan tier layanan saat ini, limit yang berlaku, sinyal kapan harus upgrade, dan perkiraan biayanya. Seluruh sistem saat ini berjalan **tanpa biaya langganan** kecuali S&P Global (langganan korporat) dan lisensi Power BI.

| Layanan | Tier sekarang | Limit yang relevan | Sinyal harus upgrade | Opsi & estimasi biaya |
|---|---|---|---|---|
| **Neon PostgreSQL** | Free | Storage **512 MB**; auto-suspend compute saat idle; history/PITR retensi terbatas | `pg_database_size` mendekati 512 MB (cek bulanan, SQL di [bagian “08 — Runbook Maintenance”](#sec-08-maintenance-md)); butuh restore point lebih panjang | Launch plan (per 2026 mulai ± US$19/bln — cek harga terkini di neon.tech/pricing); alternatif: arsip/hapus artikel lama di `news_articles` |
| **GitHub Actions** | Free (repo public/personal) | Delay cron 3–5 jam; auto-disable setelah 60 hari repo inaktif; kuota menit gratis; timeout workflow diset 90/120/180 menit | Delay tidak bisa ditoleransi; workflow sering mati karena inaktivitas | GitHub Team/org berbayar tidak menghilangkan delay cron; solusi nyata = **self-hosted runner** (server internal PEI) atau scheduler eksternal yang trigger `workflow_dispatch` |
| **Google Gemini** | Free tier, model `gemini-2.5-flash-lite` | Kuota request/hari free tier; volume aktual rendah (≤ jumlah topik aktif per hari, hanya step sentimen) | Error 429 quota berulang di log | Pay-as-you-go Gemini API — biaya diperkirakan sangat kecil di volume sekarang (< US$5/bln); cek ai.google.dev/pricing |
| **Power BI** | `[ISI: lisensi PEI sekarang]` | Publish & scheduled refresh di Power BI Service butuh **Pro** per user (atau kapasitas Premium/Fabric) | Perlu share dashboard ke banyak user / refresh terjadwal otomatis | Power BI Pro ± US$14/user/bln (konfirmasi lisensi Microsoft 365 PEI — sering sudah termasuk E5) |
| **S&P Global Platts** | Langganan korporat `[ISI: pemegang kontrak]` | Sesuai kontrak | Kontrak berakhir → scraper spglobal gagal auth | `[ISI: nilai & masa kontrak]` — pastikan perpanjangan jadi tanggung jawab PEI |
| **EIA API** | Gratis (API key registrasi) | Rate limit longgar, tidak relevan di volume sekarang | — | Tetap gratis |
| **SharePoint/OneDrive** | Bagian Microsoft 365 | — | Hanya dipakai macro series Power BI + legacy dev | Sudah tercakup lisensi M365 PEI |

##### Catatan Keputusan Arsitektur Terkait Biaya

- **Power BI mode Import, bukan DirectQuery** — disengaja: compute Neon free tier auto-suspend, DirectQuery akan sering timeout dan menahan compute aktif terus (boros bila upgrade ke paid). Jangan diubah tanpa membaca [bagian “07 — Power BI & Power Query”](#sec-07-power-bi-md).
- **Model `gemini-2.5-flash-lite`** dipilih untuk biaya/kecepatan; ganti model cukup satu konstanta di `src/helpers/summary_helper.py` ([bagian “06 — AI & Analisis Sentimen Berita”](#sec-06-ai-sentiment-md)).
- Torch/EasyOCR di monthly workflow diinstal versi CPU-only untuk menghindari disk-full runner gratis — jangan "dirapikan" jadi instalasi default.

##### Skenario Total Biaya

| Skenario | Perkiraan/bulan | Kapan relevan |
|---|---|---|
| Status quo (semua free tier) | US$0 + lisensi eksisting (Platts, M365) | Berjalan baik selama data < 512 MB & delay cron diterima |
| Upgrade minimal | ± US$19–40 (Neon Launch + Gemini PAYG) | Data melewati 512 MB atau kuota Gemini habis |
| Operasional penuh internal | + biaya server runner internal / kapasitas Power BI | Butuh jadwal presisi & distribusi dashboard luas |

> Harga per Juli 2026, verifikasi ulang ke halaman pricing masing-masing sebelum pengambilan keputusan anggaran.


---

<a id="sec-handover-05-diagram-alur-data-md"></a>

#### Diagram Alur Data End-to-End

Diagram Mermaid — render otomatis di GitHub. Versi teknis detail ada di [bagian “01 — Arsitektur Sistem”](#sec-01-arsitektur-md).

##### Versi Ringkas (untuk manajemen)

Sistem mengumpulkan data energi secara otomatis dari belasan sumber publik dan berlangganan (berita, harga komoditas, statistik pemerintah), memprosesnya di cloud tanpa server sendiri (GitHub Actions), merangkum sentimen berita dengan AI (Google Gemini), menyimpan hasilnya ke database cloud (Neon PostgreSQL), dan menyajikannya sebagai dashboard Power BI yang di-refresh berkala. Seluruh rantai berjalan otomatis pada jadwal harian/mingguan/bulanan tanpa intervensi manual.

```mermaid
flowchart LR
    A["🌐 Sumber Data<br/>(situs berita, API, PDF)"] --> B["⚙️ Pipeline Otomatis<br/>(GitHub Actions, terjadwal)"]
    B --> C["🤖 AI Sentimen<br/>(Google Gemini)"]
    B --> D["🗄️ Database Cloud<br/>(Neon PostgreSQL)"]
    C --> D
    D --> E["📊 Dashboard<br/>(Power BI)"]
```

##### Versi Teknis

```mermaid
flowchart TB
    subgraph SUMBER["Sumber Data"]
        N1["Berita lokal<br/>(media Indonesia, BPS)"]
        N2["Berita internasional<br/>(CNN/CNBC, S&P Global)"]
        S1["Data terstruktur:<br/>CPO GAPKI · EIA · ESDM (OCR PDF) ·<br/>IAEA · WTE SIPSN · SP Global ·<br/>biodiesel · bioetanol · EBT"]
    end

    subgraph GHA["GitHub Actions — 4 workflow cron"]
        W1["daily_morning<br/>Sen–Jum 08:00 WIB"]
        W2["daily_afternoon<br/>Sen–Jum 14:00 WIB"]
        W3["weekly<br/>Senin 08:00 WIB"]
        W4["monthly<br/>tgl 1 / 12 / 15 / 28"]
    end

    subgraph PROSES["src/"]
        SCH["scheduler/scheduling_*.py"]
        ORC["orchestrators berita & sentimen"]
        STR["structured_data/*.py"]
        AI["helpers/summary_helper.py<br/>Gemini gemini-2.5-flash-lite"]
        SB["helpers/storage_backend.py<br/>switch STORAGE_BACKEND"]
    end

    subgraph STORAGE["Penyimpanan"]
        NEON[("Neon PostgreSQL<br/>22 tabel")]
        VW["20 view vw_*<br/>(scripts/create_views.sql)"]
        OD[("OneDrive Excel<br/>legacy / dev lokal")]
    end

    subgraph BI["Power BI"]
        PQ["Power Query (mode Import)<br/>M-code: scripts/power_query_migrated.txt"]
        SP["SharePoint<br/>(macro series, belum migrasi)"]
        DASH["Dashboard Energi Pertamina"]
    end

    N1 --> W1
    S1 --> W4
    N2 --> W2
    W1 & W2 & W3 & W4 --> SCH
    SCH --> ORC & STR
    ORC --> AI
    ORC & STR & AI --> SB
    SB -->|"STORAGE_BACKEND=neon (produksi/CI)"| NEON
    SB -.->|"STORAGE_BACKEND=onedrive (dev)"| OD
    NEON --> VW
    VW --> PQ
    SP --> PQ
    PQ --> DASH
```

##### Titik Rawan (untuk operator)

| Titik di diagram | Risiko | Rujukan |
|---|---|---|
| Sumber → Actions | Situs berubah struktur/pindah domain → scraper gagal | [bagian “08 — Runbook Maintenance”](#sec-08-maintenance-md) |
| Cron GitHub | Delay 3–5 jam; auto-disable 60 hari inaktif | [bagian “04 — Pipeline & Scheduling (GitHub Actions)”](#sec-04-pipeline-scheduling-md) |
| Gemini | Kuota free tier / key expired | [bagian “Runbook Operator Hari Pertama”](#sec-handover-03-runbook-hari-pertama-md) |
| Neon | Limit 512 MB free tier | [bagian “08 — Runbook Maintenance”](#sec-08-maintenance-md) |
| View → Power Query | Nama kolom case-sensitive; format angka teks (koma ribuan) | [bagian “07 — Power BI & Power Query”](#sec-07-power-bi-md) |
| Power BI refresh | Butuh 2 kredensial: Neon + SharePoint | [bagian “07 — Power BI & Power Query”](#sec-07-power-bi-md) |
