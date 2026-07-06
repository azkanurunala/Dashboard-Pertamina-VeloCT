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
- Ukuran DB mendekati 512 MB free tier? Lihat [docs/08-maintenance.md](../08-maintenance.md#manajemen-database-neon).
