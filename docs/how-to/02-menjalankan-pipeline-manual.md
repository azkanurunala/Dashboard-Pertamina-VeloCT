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
- **Monthly punya gating tanggal** ([04-pipeline-scheduling.md](../04-pipeline-scheduling.md)): dispatch tanggal 12/15/28 hanya menjalankan step tanggal itu; dispatch tanggal lain menjalankan step 1–4 (EIA, ESDM OCR, biodiesel, bioetanol).
- Aman diulang — semua tulisan upsert (tidak duplikat).
- Satu step gagal tidak menghentikan step lain; baca seluruh log.

##### B. Lokal (debugging)

1. Pastikan setup selesai ([How-To 1](01-setup-lokal-dari-nol.md)) dan tentukan target tulis:
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
| Data hari ini belum masuk padahal jadwal lewat >6 jam | Cek [How-To 3](03-cek-kesehatan-scheduler.md) dulu, lalu A |
| Menguji perubahan kode scraper | B, `STORAGE_BACKEND=onedrive` dulu |
| Mengisi gap beberapa hari/bulan | [How-To 4](04-backfill-data-bolong.md) |
