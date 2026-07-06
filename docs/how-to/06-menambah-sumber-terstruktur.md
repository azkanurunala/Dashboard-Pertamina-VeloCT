#### How-To 6: Menambah Sumber Data Terstruktur

Dari nol sampai tampil di Power BI. Contoh fiktif: dataset "Harga Gas" bulanan dari situs X → tabel `data_harga_gas`.

##### Langkah

1. **Scraper.** Buat `src/structured_data/harga_gas.py` (contoh paling sederhana untuk ditiru: [cpo_gapki.py](../../src/structured_data/cpo_gapki.py); dengan API key: [migas_eia.py](../../src/structured_data/migas_eia.py)):
   ```python
   from helpers.storage_backend import storage

   SHEET_NAME = "(Data)Harga Gas"

   def main_harga_gas():
       df = ...  # hasil scraping, kolom final persis yang mau tampil
       storage.write_structured_sheet(SHEET_NAME, df)
   ```
2. **Registrasi mapping** di [src/helpers/storage_backend.py](../../src/helpers/storage_backend.py):
   ```python
   # SHEET_TO_TABLE
   "(Data)Harga Gas": "data_harga_gas",
   # SHEET_CONFLICT_COLS  (kolom yang mengidentifikasi baris unik)
   "(Data)Harga Gas": ["Tahun", "Bulan"],
   ```
3. **DDL** di [scripts/create_tables.sql](../../scripts/create_tables.sql) — `UNIQUE` **harus sama persis** dengan conflict cols (upsert gagal tanpa itu):
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
4. **View** di [scripts/create_views.sql](../../scripts/create_views.sql) (Power BI baca view, bukan tabel):
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
6. **Jadwalkan** — panggil `main_harga_gas()` dari scheduler yang sesuai (mis. [scheduling_month.py](../../src/scheduler/scheduling_month.py)) dengan pola step existing (`try/except` + banner). Bila butuh tanggal khusus, tambah konstanta `DAY_*` **dan** tanggal di cron [monthly.yml](../../.github/workflows/monthly.yml) **dan** update `scripts/check_workflow_schedules.py`.
7. **Secrets** (bila sumber butuh auth): tambah var di `.env.example` + `.env`, GitHub → Settings → Secrets → New secret, lalu inject di blok `env:` workflow terkait.
8. **Power BI**: query baru dari `vw_harga_gas` ([How-To 7](07-koneksi-power-bi-neon.md)), catat M-code di `scripts/power_query_migrated.txt`.
9. **Dokumentasi**: tambahkan baris di [docs/05-sumber-data.md](../05-sumber-data.md) dan [docs/03-database.md](../03-database.md).

##### Checklist Verifikasi Akhir

- [ ] Run dua kali → tidak ada duplikat
- [ ] Tabel + view muncul di Neon
- [ ] Step tampil di log run workflow berikutnya (hijau)
- [ ] Kartu/visual Power BI ter-refresh dengan data baru
