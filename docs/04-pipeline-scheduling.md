# 04 — Pipeline & Scheduling (GitHub Actions)

## Ringkasan 4 Workflow

Semua workflow: `runs-on: ubuntu-latest`, Python 3.11, Chrome via `browser-actions/setup-chrome` (untuk Selenium), `STORAGE_BACKEND: neon`, `CI: "true"`, pip cache. Semua bisa dijalankan manual via **workflow_dispatch** (tab Actions → pilih workflow → Run workflow).

| Workflow | Cron (UTC) | WIB | Entry script | Timeout |
|---|---|---|---|---|
| `daily_morning.yml` | `0 1 * * 1-5` | Sen–Jum 08:00 | `src/scheduler/scheduling_day_morning.py` | default |
| `daily_afternoon.yml` | `0 7 * * 1-5` | Sen–Jum 14:00 | `src/scheduler/scheduling_day_afternoon.py` | default |
| `weekly.yml` | `0 1 * * 1` | Senin 08:00 | `src/scheduler/scheduling_week.py` | default |
| `monthly.yml` | `0 1 1,12,15,28 * *` | tgl 1/12/15/28 08:00 | `src/scheduler/scheduling_month.py` | 180 menit |

## Urutan Step per Pipeline

Setiap step dibungkus `try/except` — kegagalan satu step tidak menghentikan step berikutnya. Ada jeda `time.sleep(60)` antar step di pipeline harian.

### Daily Morning
1. **News lokal** — `orchestrators.main_news_scraping_lokal` (Kontan, Kompas, Tempo, Bisnis Indonesia, CNBC Indonesia, Bank Indonesia, BPS, Bloomberg Technoz, S&P, CNN/CNBC via Google News) → `news_articles`
2. **CPO GAPKI** — `structured_data.cpo_gapki.main_scraper_cpo` → `data_cpo`
3. **Sentiment lokal harian** — `orchestrators.main_sentiment_news_lokal_harian` (Gemini) → `news_sentiment`

### Daily Afternoon
1. **News internasional** — `orchestrators.main_news_scraping_internasional` (BioenergyTimes, CNBC, CNN, EnergiesMedia, OilPrice, S&P, SCMP, The Guardian) → `news_articles`
2. **Sentiment internasional harian** → `news_sentiment`
3. **SAF daily** — `spglobal_data.main_saf_daily` → `data_saf` (butuh `SPGLOBAL_USERNAME/PASSWORD`)

### Weekly
1. **Sentiment mingguan** — `orchestrators.main_sentiment_news_mingguan` (jendela 6 hari, gabungan sentimen berita + tren data terstruktur) → `news_sentiment`
2. **S&P weekly** — `main_saf_weekly`, `main_crackspeed_bbm_weekly`, `main_crackspeed_non_bbm_weekly` → `data_saf`, `data_crackspeed_bbm`, `data_crackspeed_non_bbm`

### Monthly — gating per tanggal

Cron fire tanggal **1, 12, 15, 28**; [scheduling_month.py](../src/scheduler/scheduling_month.py) memilih step berdasarkan `datetime.now().day`:

| Tanggal | Step yang jalan |
|---|---|
| 1 (atau dispatch manual di tanggal selain 12/15/28) | Step 1–4: EIA (`data_eia`), ESDM OCR harga minyak (`data_harga_minyak`), biodiesel (`data_biodiesel`), bioetanol (`data_bioetanol`) |
| 12 | Step 5: petrochemical short-term + BBM price forecast → `data_crackspread_non_bbm`, `data_crackspread_bbm`, `data_crackspread_bbm_year` |
| 15 | Step 6: WTE SIPSN (`data_wte_*`) + IAEA PRIS (`data_iaea_*`, Selenium) |
| 28 | Step 7: kapasitas EBT (`data_kapasitas_ebt`) |

Pada tanggal 12/15/28, step 1–4 **dilewati** (supaya scraping berat + OCR tidak berulang 4× sebulan). Konstanta tanggal: `DAY_PETROCHEMICAL=12`, `DAY_NUCLEAR=15`, `DAY_EBT=28`.

> **Riwayat bug (diperbaiki Jul 2026):** sebelumnya cron monthly hanya fire tanggal 1, sehingga step tanggal 12/15/28 tidak pernah jalan otomatis — hanya via dispatch manual. Bila data petrokimia/WTE/IAEA/EBT bolong di periode sebelum Jul 2026, ini penyebabnya; isi dengan dispatch manual pada tanggal yang sesuai atau `scripts/backfill.py`.

## Dependensi & Instalasi di CI

- **`requirements.txt`** (~137 paket): dipasang semua workflow (`pip install -r requirements.txt psycopg2-binary`). Scraping (selenium, undetected-chromedriver, beautifulsoup4, feedparser), data (pandas, openpyxl), Gemini, MSAL, PDF ringan.
- **`requirements-ocr.txt`**: torch CPU (`--extra-index-url https://download.pytorch.org/whl/cpu`), easyocr, opencv — **hanya monthly** (OCR PDF harga minyak ESDM). Dipisah karena ~GB; pernah menyebabkan disk-full di runner (commit `56e3e652`, `4ef9009e`).
- Pip cache per workflow; monthly punya key cache sendiri yang mencakup kedua file requirements.

## Perilaku Cron GitHub — Penting

1. **Delay 3–5 jam adalah normal.** Cron GitHub Actions free tier best-effort; run tercatat mulai pukul ~11:40–13:00 WIB untuk jadwal 08:00 WIB. Jangan dianggap gagal. (Mitigasi parsial: geser menit cron dari `:00`, mis. `23 0 * * 1-5`.)
2. **Auto-disable setelah 60 hari repo tidak aktif.** GitHub menonaktifkan scheduled workflow bila tidak ada commit 60 hari. Re-enable manual di tab Actions. Script monitoring (di bawah) mendeteksi kondisi ini.
3. **Cron hanya jalan dari default branch (`main`).** Perubahan workflow di branch `dev` tidak mempengaruhi jadwal sampai di-merge ke `main`. Workflow terdaftar di GitHub sejak 2026-07-02 — tidak ada scheduled run sebelum tanggal itu.

## Monitoring: `scripts/check_workflow_schedules.py`

Membandingkan waktu fire cron yang diharapkan vs run `event=schedule` aktual dari GitHub API.

```bash
python scripts/check_workflow_schedules.py            # lookback default per workflow (14/35/120 hari)
python scripts/check_workflow_schedules.py --days 30  # override lookback
```

- Token: env `GITHUB_TOKEN`/`GH_TOKEN`, fallback otomatis ke git credential helper (kredensial `git push`). Tanpa dependensi eksternal (stdlib).
- Output per workflow: `OK` (jalan, dengan delay menit + conclusion), `XX MISSED` (tidak ada run), `XX failed` (+ URL run), `!!` bila workflow di-disable GitHub, `pending` bila masih dalam jendela toleransi 6 jam.
- **Exit code 0** = semua sehat; **1** = ada masalah — cocok dipakai di automasi.
- Jendela pencocokan 6 jam (menampung delay GitHub). Lookback dipotong otomatis ke tanggal registrasi workflow.

Jalankan minimal **sebulan sekali** (sekaligus menangkal auto-disable-60-hari lewat aktivitas repo). Runbook lengkap: [08-maintenance.md](08-maintenance.md).

## Menjalankan Ulang Manual

- **Via GitHub:** Actions → pilih workflow → Run workflow (branch `main`). Untuk monthly, ingat gating tanggal: dispatch pada tanggal 12/15/28 hanya menjalankan step tanggal itu; dispatch tanggal lain menjalankan step 1–4.
- **Via lokal:** `python src/scheduler/scheduling_month.py` dengan `.env` lengkap dan `STORAGE_BACKEND=neon`. Gating tanggal tetap berlaku (pakai tanggal hari ini).

## Mengubah Jadwal

1. Edit `cron` di `.github/workflows/*.yml` (UTC; WIB = UTC+7).
2. Bila menyentuh gating monthly, sinkronkan konstanta `DAY_*` di `scheduling_month.py`.
3. Update tabel `WORKFLOWS` di `scripts/check_workflow_schedules.py` (cron + lookback) agar monitoring tetap akurat.
4. Merge ke `main` — cron baru aktif setelah itu.
