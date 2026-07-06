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
