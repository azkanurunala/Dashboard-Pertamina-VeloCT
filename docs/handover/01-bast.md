#### Berita Acara Serah Terima (BAST)
##### Sistem Dashboard SPEED Pertamina Energy Institute

> Template — semua isian `[ISI: …]` wajib dilengkapi sebelum ditandatangani.

Pada hari ini, `[ISI: hari]`, tanggal `[ISI: tanggal]`, bertempat di `[ISI: lokasi]`, telah dilakukan serah terima sistem **Dashboard SPEED Pertamina Energy Institute** dari:

**PIHAK PERTAMA (yang menyerahkan)**
- Nama: `[ISI: nama]`
- Jabatan/Peran: `[ISI: jabatan]` (developer/pengelola sistem)

kepada:

**PIHAK KEDUA (yang menerima)**
- Nama: `[ISI: nama]`
- Jabatan/Peran: `[ISI: jabatan]` (tim internal PT Pertamina Energy Institute)

---

##### 1. Ruang Lingkup yang Diserahkan

| # | Aset | Bentuk Serah Terima |
|---|---|---|
| 1 | Repositori kode dashboard (GitHub) | Transfer ownership / akses admin — lihat [02-inventaris-aset-akses.md](02-inventaris-aset-akses.md) |
| 2 | Database Neon PostgreSQL (`neondb`, region `ap-southeast-1`) | Transfer akun / akses admin console |
| 3 | 4 workflow GitHub Actions (daily morning, daily afternoon, weekly, monthly) | Ikut repositori; daftar secrets diserahkan terpisah |
| 4 | File Power BI (`.pbix`) | `[ISI: lokasi file / workspace Power BI Service]` |
| 5 | M-code Power Query — sumber kebenaran: `scripts/power_query_migrated.txt` | Ikut repositori |
| 6 | Dokumentasi teknis lengkap (`docs/01`–`09`) + dokumen handover (`docs/handover/`) | Ikut repositori |
| 7 | Kredensial & API key seluruh layanan | **Jalur aman terpisah** (bukan email/chat) — lalu dirotasi PIHAK KEDUA, lihat [02-inventaris-aset-akses.md](02-inventaris-aset-akses.md) |

##### 2. Kondisi Sistem Saat Serah Terima

- Database: **22 tabel** + **20 view** (`vw_*`) — daftar lengkap di [docs/03-database.md](../03-database.md).
- Pipeline otomatis: 4 workflow terjadwal (jadwal & isi di [README](../../README.md) dan [docs/04-pipeline-scheduling.md](../04-pipeline-scheduling.md)).
- AI sentimen: Google Gemini `gemini-2.5-flash-lite` (free tier) — [docs/06-ai-sentiment.md](../06-ai-sentiment.md).
- Power BI: mode **Import**, sebagian query masih ke SharePoint (macro series) — [docs/07-power-bi.md](../07-power-bi.md).
- Status run terakhir saat serah terima: `[ISI: tanggal cek + hasil, jalankan python scripts/check_workflow_schedules.py dan lampirkan output]`.

##### 3. Known Issues & Limitasi yang Disepakati

Diserahkan **apa adanya** dengan isu berikut sudah diketahui kedua pihak (detail & mitigasi di [docs/08-maintenance.md](../08-maintenance.md) bagian Known Issues):

1. **Delay cron 3–5 jam** dari jadwal — perilaku normal GitHub Actions free tier.
2. **Limit storage Neon 512 MB** (free tier) — pertumbuhan terbesar `news_articles.content`; cek bulanan.
3. **Auto-disable workflow** setelah 60 hari repo tanpa aktivitas — perlu commit/aktivitas berkala.
4. **Anomali data WTE tahun 2018** — nilai timbulan jauh lebih kecil dari tahun lain (kemungkinan cakupan provinsi sumber lebih sedikit); perlu validasi ke sumber SIPSN bila dashboard terlihat janggal.
5. **Secrets MS/OneDrive masih di-inject ke semua workflow** padahal backend produksi sudah Neon — permukaan kredensial lebih luas dari yang diperlukan (legacy/fallback).
6. **Tanggal backfill hardcoded `2026-04-17`** di orchestrator sentimen — aman di CI, perlu disesuaikan bila run manual lokal.
7. **Refresh Power BI butuh dua kredensial** (Neon + SharePoint) karena macro series belum dimigrasi.
8. **Step monthly tanggal 12/15/28 baru aktif Juli 2026** — verifikasi fire pertama; gap data lama diisi via dispatch manual/backfill.

##### 4. Pekerjaan Pending / Di Luar Scope

| # | Item | Status |
|---|---|---|
| 1 | `[ISI: mis. migrasi macro series SharePoint → Neon]` | `[ISI]` |
| 2 | `[ISI]` | `[ISI]` |

Backlog ide pengembangan: [docs/09-pengembangan.md](../09-pengembangan.md).

##### 5. Masa Dukungan Pasca-Serah-Terima

- PIHAK PERTAMA bersedia menjadi kontak konsultasi sampai: `[ISI: tanggal akhir masa dukungan]`.
- Periode shadow (PIHAK KEDUA operasikan, PIHAK PERTAMA standby): `[ISI: durasi, rekomendasi 2–4 minggu]`.
- Setelah masa dukungan berakhir, seluruh kredensial wajib sudah dirotasi oleh PIHAK KEDUA (checklist di [02-inventaris-aset-akses.md](02-inventaris-aset-akses.md)).

##### 6. Penutup

Demikian berita acara ini dibuat dalam rangkap dua, masing-masing memiliki kekuatan hukum yang sama.

| PIHAK PERTAMA | PIHAK KEDUA |
|---|---|
| <br><br><br> | <br><br><br> |
| `[ISI: nama]` | `[ISI: nama]` |
| `[ISI: jabatan]` | `[ISI: jabatan]` |
