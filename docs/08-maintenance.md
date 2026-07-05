# 08 — Runbook Maintenance

## Checklist Rutin

### Harian (opsional, 2 menit)
- Lihat tab **Actions** di GitHub: run terakhir daily morning/afternoon hijau?
- Ingat: delay 3–5 jam dari jadwal itu normal (free tier).

### Mingguan
- `python scripts/check_workflow_schedules.py` — exit 0 & "ALL SCHEDULERS HEALTHY" = beres.
- Spot-check data terbaru:
  ```sql
  SELECT MAX("Upload_Dates") FROM data_cpo;
  SELECT topic, MAX(date) FROM news_articles GROUP BY topic;
  SELECT topic, MAX("Tanggal awal") FROM news_sentiment GROUP BY topic;
  ```

### Bulanan
- Cek run monthly tanggal 1/12/15/28 sukses (Actions atau script monitoring).
- Cek ukuran database vs limit 512 MB free tier:
  ```sql
  SELECT pg_size_pretty(pg_database_size('neondb'));
  SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
  FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 10;
  ```
  (Pertumbuhan terbesar biasanya `news_articles` karena kolom `content`. Bila mendekati limit: arsip/hapus artikel lama, atau upgrade plan.)
- **Pastikan ada aktivitas repo dalam 60 hari terakhir** — GitHub menonaktifkan scheduled workflow setelah 60 hari tanpa aktivitas. Commit apa pun mereset timer; script monitoring mendeteksi state `disabled_inactivity`.

## Monitoring Scheduler

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

## Menangani Run Gagal

1. Buka log run di Actions. Struktur log jelas per step: `>>> STEP n: ...` diikuti error + traceback. Satu step gagal **tidak** membatalkan step lain — periksa seluruh log, jangan cuma step pertama yang merah.
2. Identifikasi step gagal → lihat tabel scraper di [05-sumber-data.md](05-sumber-data.md) untuk tahu file & sumber datanya.
3. Re-run: **Actions → workflow → Run workflow** (dispatch). Aman diulang — semua tulisan idempoten (upsert). Untuk monthly perhatikan gating tanggal ([04-pipeline-scheduling.md](04-pipeline-scheduling.md)).
4. Bila gap data beberapa hari: gunakan `scripts/backfill.py --sources <sumber> --start ... --end ...` ([02-migrasi-storage.md](02-migrasi-storage.md)).

## Diagnosis Scraper Rusak (situs berubah)

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

## Secrets & Kredensial

### Daftar GitHub Secrets (Settings → Secrets and variables → Actions)

| Secret | Dipakai oleh | Workflow |
|---|---|---|
| `NEON_DB_URL` | `neon_helper.py` | semua |
| `GEMINI_API_KEY` | `summary_helper.py` | morning, afternoon, weekly |
| `SPGLOBAL_USERNAME`, `SPGLOBAL_PASSWORD` | `spglobal_data.py`, `spglobal_news.py` | afternoon, weekly, monthly |
| `EIA_API_KEY` | `migas_eia.py` | monthly |
| `MS_CLIENT_ID`, `MS_CLIENT_SECRET`, `MS_TENANT_ID`, `MS_USER_EMAIL` | `onedrive_helper.py` | semua (legacy/fallback) |
| `ONEDRIVE_FILE_PATH`, `ONEDRIVE_SENTIMENT_PATH`, `ONEDRIVE_DATA_PATH` | `storage_backend.py` | semua (legacy/fallback) |

Rotasi: perbarui nilai di GitHub Secrets **dan** `.env` lokal. Khusus `NEON_DB_URL`, perbarui juga kredensial PostgreSQL di Power BI (Data source settings).

### ⚠️ Peringatan Keamanan

- **`.env` di mesin dev berisi kredensial asli** (Gemini, Neon, S&P, MS client secret, service account Google). File ini tidak boleh masuk git (cek `.gitignore`), tidak boleh dibagikan mentah saat handover — pihak baru harus menerima kredensial lewat jalur aman, lalu **rotasi semua kredensial setelah handover**.
- **`token.json` di root** = cache token OAuth MS Graph. Jangan di-commit; hapus aman (akan dibuat ulang saat auth berikutnya).
- `GOOGLE_CREDENTIALS`/`SPREADSHEET_ID*` di `.env` adalah sisa era Google Sheets — tidak dipakai kode aktif; kandidat dibersihkan.

## Manajemen Database Neon

- Console: https://console.neon.tech — monitoring storage/compute, connection string, rotasi password.
- Backup/export manual:
  ```bash
  pg_dump "$NEON_DB_URL" -Fc -f backup_$(date +%Y%m%d).dump      # full
  psql "$NEON_DB_URL" -c "\copy news_sentiment TO 'sentiment.csv' CSV HEADER"  # per tabel
  ```
- Neon punya point-in-time restore (history retention terbatas di free tier) — cek console sebelum melakukan operasi destruktif.
- Skema aman dijalankan ulang kapan pun (`CREATE TABLE IF NOT EXISTS` / `CREATE OR REPLACE VIEW`).

## Known Issues (per Juli 2026)

| Isu | Dampak | Saran |
|---|---|---|
| `data_harga_ebt` tanpa UNIQUE constraint | Reload menduplikasi baris | `TRUNCATE` sebelum reload, atau tambah UNIQUE + daftarkan conflict key |
| `src/code_scrapping/` hanya berisi `.pyc` legacy | Membingungkan; tak terpakai | Hapus folder dari git |
| Monitoring hanya stdout GitHub Actions | Kegagalan senyap bila tak dicek | Rutin jalankan `check_workflow_schedules.py`; pertimbangkan notifikasi email GitHub (Settings → Notifications → Actions) |
| Start date hardcoded di orchestrator sentimen (`2026-04-17`) | Run lokal bisa memproses rentang salah | Sesuaikan konstanta sebelum run manual; di CI aman (`CI=true`) |
| Secrets MS/OneDrive diinject semua workflow padahal backend neon | Permukaan kredensial lebih luas dari perlu | Boleh dihapus dari YAML setelah yakin tak ada fallback OneDrive |
| Cron delay 3–5 jam | Data "pagi" masuk siang | Terima (free tier), atau geser cron lebih awal / pindah self-hosted runner |
| Step monthly tgl 12/15/28 baru diaktifkan Jul 2026 | Data petrokimia/WTE/IAEA/EBT sebelum Jul 2026 mungkin bolong | Verifikasi fire pertama 12/15/28 Jul 2026; isi gap via dispatch manual/backfill |
