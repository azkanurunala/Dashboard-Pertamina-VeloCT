#### 06 — AI & Analisis Sentimen Berita

##### Provider Aktif: Google Gemini

Satu-satunya titik pemanggilan AI di seluruh repo: [src/helpers/summary_helper.py](../src/helpers/summary_helper.py).

- `setup_gemini()` — baca `GEMINI_API_KEY` dari env, konfigurasi `google.generativeai`, kembalikan `GenerativeModel("gemini-2.5-flash-lite")` (model di-hardcode di `summary_helper.py:34`; varian `gemini-2.5-flash` tersedia sebagai komentar).
- `summarize_all_news(model, ...)` — bangun prompt analis berbahasa Indonesia (ringkasan 3 poin per topik), panggil `model.generate_content()`, kembalikan teks ringkasan.

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

1. **`src/helpers/summary_helper.py`** — ganti `setup_gemini()` dan pemanggilan `generate_content()` dengan SDK provider baru. Pertahankan signature `summarize_all_news(...)` agar 3 orchestrator tidak perlu berubah (mereka hanya `from helpers.summary_helper import setup_gemini, summarize_all_news`).
2. **`requirements.txt`** — tambah SDK baru (mis. `openai`).
3. **`.env` / `.env.example`** — isi `AI_TYPE`, `OPENAI_API_KEY`, `OPENAI_MODEL_NAME` (var-nya sudah disiapkan).
4. **GitHub Secrets + workflow YAML** — tambahkan secret baru dan inject di blok `env:` `daily_morning.yml`, `daily_afternoon.yml`, `weekly.yml` (monthly tidak memanggil AI).
5. Uji lokal: jalankan salah satu orchestrator sentimen dengan `STORAGE_BACKEND=onedrive` (atau neon dev) dan periksa baris baru di `news_sentiment`.

Gotcha umum bila memakai model GPT-5.x/o-series: parameter `temperature`/`max_tokens` klasik ditolak (pakai `max_completion_tokens`), dan Azure OpenAI memakai header `api-key:` bukan `Authorization: Bearer`.
