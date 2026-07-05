# Dashboard-Pertamina-VeloCT

Pipeline pengumpulan data otomatis untuk dashboard energi Pertamina (Power BI). Sistem ini melakukan scraping berita energi (lokal & internasional), data terstruktur komoditas (minyak mentah, biodiesel, bioetanol, CPO, SAF, petrokimia, nuklir, EBT, waste-to-energy), lalu merangkum sentimen berita dengan AI (Google Gemini) dan menyimpan semuanya ke **Neon PostgreSQL** yang dikonsumsi dashboard Power BI.

> Sistem baru saja menyelesaikan migrasi storage dari OneDrive/SharePoint Excel ke Neon PostgreSQL (Juli 2026). Dokumentasi lengkap ada di folder [docs/](docs/).

## Arsitektur Ringkas

```
                 GitHub Actions (cron, 4 workflow)
                              │
                              ▼
              src/scheduler/scheduling_*.py
                              │
        ┌─────────────────────┼──────────────────────┐
        ▼                     ▼                      ▼
 orchestrators/          structured_data/       helpers/summary_helper.py
 (berita lokal/intl,     (CPO, SAF, EIA,        (ringkasan sentimen
  sentiment harian/       ESDM OCR, IAEA,        via Gemini)
  mingguan)               WTE, crackspread, …)
        │                     │                      │
        └─────────────────────┴──────────────────────┘
                              │
                              ▼
              src/helpers/storage_backend.py
              (switch: STORAGE_BACKEND=neon|onedrive)
                    │                   │
                    ▼                   ▼
          Neon PostgreSQL        OneDrive Excel
          (produksi/CI)          (dev lokal/legacy)
                    │
                    ▼
             Power BI (mode Import, tabel + view vw_*)
```

## Jadwal Pipeline

| Workflow | Cron (UTC) | WIB | Isi |
|---|---|---|---|
| [daily_morning.yml](.github/workflows/daily_morning.yml) | `0 1 * * 1-5` | Sen–Jum 08:00 | Berita lokal → CPO GAPKI → sentiment lokal harian |
| [daily_afternoon.yml](.github/workflows/daily_afternoon.yml) | `0 7 * * 1-5` | Sen–Jum 14:00 | Berita internasional → sentiment intl → SAF daily |
| [weekly.yml](.github/workflows/weekly.yml) | `0 1 * * 1` | Senin 08:00 | Sentiment mingguan → SAF/crackspeed weekly |
| [monthly.yml](.github/workflows/monthly.yml) | `0 1 1,12,15,28 * *` | Tgl 1/12/15/28 08:00 | EIA, ESDM OCR, biodiesel, bioetanol (tgl 1); petrokimia (tgl 12); WTE+IAEA (tgl 15); kapasitas EBT (tgl 28) |

Catatan: cron GitHub Actions free tier biasa terlambat 3–5 jam dari jadwal. Cek kesehatan scheduler dengan `python scripts/check_workflow_schedules.py`.

## Quickstart (Dev Lokal)

```bash
git clone https://github.com/shelmasalsa17/Dashboard-Pertamina-VeloCT.git
cd Dashboard-Pertamina-VeloCT
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt psycopg2-binary
copy .env.example .env                               # lalu isi kredensial
python src/scheduler/scheduling_day_morning.py       # contoh menjalankan pipeline
```

Detail setup lengkap: [docs/09-pengembangan.md](docs/09-pengembangan.md).

## Indeks Dokumentasi

| Dokumen | Isi |
|---|---|
| [docs/01-arsitektur.md](docs/01-arsitektur.md) | Arsitektur sistem, struktur folder, alur data end-to-end |
| [docs/02-migrasi-storage.md](docs/02-migrasi-storage.md) | Migrasi OneDrive Excel → Neon PostgreSQL: mekanisme, status, backfill |
| [docs/03-database.md](docs/03-database.md) | Skema database Neon: tabel, conflict key, views, kasus khusus |
| [docs/04-pipeline-scheduling.md](docs/04-pipeline-scheduling.md) | 4 pipeline GitHub Actions: cron, step, monitoring |
| [docs/05-sumber-data.md](docs/05-sumber-data.md) | Semua sumber data: scraper, endpoint, auth, output |
| [docs/06-ai-sentiment.md](docs/06-ai-sentiment.md) | Analisis sentimen berita dengan Gemini |
| [docs/07-power-bi.md](docs/07-power-bi.md) | Koneksi Power BI ke Neon, Power Query migrasi |
| [docs/08-maintenance.md](docs/08-maintenance.md) | Runbook maintenance: monitoring, troubleshooting, secrets, known issues |
| [docs/09-pengembangan.md](docs/09-pengembangan.md) | Panduan pengembangan: setup lokal, menambah sumber data/fitur baru |
