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
   - `XX ... failure <URL>` → fire tapi gagal → buka URL, lihat step merah, lalu [How-To 2](02-menjalankan-pipeline-manual.md) untuk re-run.
   - `!! WORKFLOW STATE: disabled_inactivity` → langkah 4.
3. Bila MISSED:
   - Cek file workflow ada di branch `main` (cron hanya baca `main`).
   - Cek https://www.githubstatus.com (outage Actions).
   - Cek tanggalnya memang hari kerja (daily = Sen–Jum saja).
4. Bila `disabled_inactivity` (repo 60 hari tanpa aktivitas):
   1. GitHub → **Actions** → klik nama workflow di panel kiri.
   2. Banner kuning "This scheduled workflow is disabled" → klik **Enable workflow**.
   3. Jadwal aktif lagi mulai fire berikutnya. Untuk hari ini, jalankan manual ([How-To 2](02-menjalankan-pipeline-manual.md)).
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

Referensi perilaku cron GitHub (delay, auto-disable, default branch): [04-pipeline-scheduling.md](../04-pipeline-scheduling.md).
