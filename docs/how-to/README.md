#### How-To: Panduan Langkah-demi-Langkah

Kumpulan prosedur operasional. Tiap panduan: prasyarat → langkah bernomor → cara verifikasi hasil. Untuk konsep/referensi lihat [docs/](../) (01–09); untuk diagnosis masalah lihat [handover/03-runbook-hari-pertama.md](../handover/03-runbook-hari-pertama.md).

| # | Panduan | Kapan dipakai |
|---|---|---|
| 1 | [Setup lokal dari nol](01-setup-lokal-dari-nol.md) | Mesin/engineer baru |
| 2 | [Menjalankan pipeline manual](02-menjalankan-pipeline-manual.md) | Run gagal, isi data hari ini, uji perubahan |
| 3 | [Cek kesehatan scheduler](03-cek-kesehatan-scheduler.md) | Rutin mingguan; curiga cron tidak jalan |
| 4 | [Backfill data bolong](04-backfill-data-bolong.md) | Ada gap data historis (berita, summary, terstruktur) |
| 5 | [Menambah topik berita](05-menambah-topik-berita.md) | Topik/keyword berita baru diminta |
| 6 | [Menambah sumber data terstruktur](06-menambah-sumber-terstruktur.md) | Dataset tabular baru untuk dashboard |
| 7 | [Menyambungkan Power BI ke Neon](07-koneksi-power-bi-neon.md) | Setup .pbix baru / pindah mesin |
| 8 | [Rotasi kredensial](08-rotasi-kredensial.md) | Handover, kebocoran, atau rutin berkala |
| 9 | [Backup & restore database](09-backup-restore-neon.md) | Sebelum operasi berisiko; pemulihan |
