#### How-To 1: Setup Lokal dari Nol

Target: dari mesin kosong sampai bisa menjalankan pipeline di laptop. ±20 menit (tanpa OCR).

##### Prasyarat

- Windows/Linux/Mac dengan **Python 3.11** (samakan dengan CI) dan Git.
- Google Chrome terpasang (dipakai Selenium).
- Kredensial `.env` diterima lewat jalur aman (jangan lewat chat/email polos) — daftar akun di [handover/02-inventaris-aset-akses.md](../handover/02-inventaris-aset-akses.md).

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
   Catatan: tanpa `CI=true`, orchestrator berita memakai `START_DATE`/`END_DATE` hardcoded di file orchestrator — sesuaikan dulu bila perlu ([09-pengembangan.md](../09-pengembangan.md)).

##### Kalau Gagal

| Gejala | Solusi |
|---|---|
| `ModuleNotFoundError` | venv belum aktif, atau paket belum terinstall |
| `psycopg2.OperationalError` | `NEON_DB_URL` salah/expired — ambil ulang dari Neon Console |
| Selenium `WebDriverException` | Chrome belum terpasang / versi driver — `webdriver-manager` mengunduh otomatis saat run pertama, butuh internet |
| `GEMINI_API_KEY not found` | `.env` belum terisi / `load_dotenv` tidak menemukan file — jalankan dari root repo |
