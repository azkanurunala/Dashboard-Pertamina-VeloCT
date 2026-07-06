#### Runbook Operator Hari Pertama

Panduan diagnosis untuk operator baru menghadapi 3 masalah paling umum. Pelengkap [docs/08-maintenance.md](../08-maintenance.md) (checklist rutin, tabel gejala scraper, backup) — baca itu dulu sebagai dasar.

##### Prasyarat Akses

Sebelum hari pertama, pastikan punya:
- [ ] Akses repo GitHub (minimal write, idealnya admin untuk kelola secrets)
- [ ] Akses console Neon (https://console.neon.tech) atau minimal `NEON_DB_URL` untuk query
- [ ] Akses edit + refresh file Power BI
- [ ] `.env` terisi di mesin lokal (template: `.env.example`, isi lewat jalur aman)

---

##### Skenario 1: Workflow Merah di GitHub Actions

1. Buka **Actions** → klik run yang gagal → cari step merah. Log terstruktur `>>> STEP n: ...` diikuti traceback. **Periksa seluruh log** — satu step gagal tidak membatalkan step lain, bisa jadi lebih dari satu yang gagal.
2. Cocokkan gejala dengan tabel diagnosis di [docs/08-maintenance.md](../08-maintenance.md#diagnosis-scraper-rusak-situs-berubah) (404 = situs pindah, 403/429 = diblokir, 0 baris = selector berubah, auth error = password expired, dst).
3. Kapan boleh diabaikan: kegagalan sekali karena timeout/situs down sementara — run berikutnya biasanya pulih (tulisan idempoten/upsert, tidak ada data korup).
4. Kapan harus ditindak: gagal **2+ hari berturut-turut** pada step sama → scraper rusak, perlu perbaikan kode.
5. Ulangi manual: **Actions → pilih workflow → Run workflow** (dispatch). Untuk monthly, ingat ada gating tanggal ([docs/04-pipeline-scheduling.md](../04-pipeline-scheduling.md)).
6. Gap data beberapa hari: `scripts/backfill.py --sources <sumber> --start ... --end ...`

> Run "MISSED" (tidak fire sama sekali) ≠ gagal. Cek `!! WORKFLOW STATE: disabled_inactivity` via `python scripts/check_workflow_schedules.py` — GitHub mematikan cron setelah 60 hari repo tanpa aktivitas; re-enable di tab Actions.

##### Skenario 2: Data Tidak Update di Dashboard Power BI

Urutan diagnosis — dari hulu ke hilir, berhenti di titik pertama yang bermasalah:

1. **Pipeline jalan?** Tab Actions: run terakhir hijau? Ingat delay 3–5 jam dari jadwal itu normal. Kalau merah → Skenario 1.
2. **Data sampai Neon?** Query cepat (psql/console Neon):
   ```sql
   SELECT MAX("Upload_Dates") FROM data_cpo;
   SELECT topic, MAX(date) FROM news_articles GROUP BY topic;
   SELECT topic, MAX("Tanggal awal") FROM news_sentiment GROUP BY topic;
   ```
   Tanggal lama padahal Actions hijau → cek log step terkait (bisa "sukses" tapi 0 baris karena situs berubah).
3. **View mengembalikan data?** `SELECT count(*) FROM vw_<nama>;` — error di view (mis. cast numeric) berarti masalah di definisi view, perbaiki `scripts/create_views.sql` lalu jalankan ulang ke Neon.
4. **Power BI refresh?** Mode **Import** — data hanya berubah setelah refresh manual/terjadwal. Refresh butuh **dua kredensial**: PostgreSQL (Neon) dan SharePoint (macro series). Kredensial Neon berubah (mis. habis rotasi) → update di **Data source settings**.
5. Masih buntu → cek query M di `scripts/power_query_migrated.txt` (sumber kebenaran M-code); pastikan nama kolom view = nama yang di-expect Power Query (case-sensitive!).

##### Skenario 3: API Key Expired / Kena Limit

| Layanan | Gejala di log | Tindakan |
|---|---|---|
| Gemini | `401/403 API key not valid` atau `429 quota` di step sentiment | Buat key baru di Google AI Studio → update secret `GEMINI_API_KEY` + `.env`. Quota 429: tunggu reset harian atau upgrade tier |
| S&P Global | Auth error di step spglobal | Ganti `SPGLOBAL_PASSWORD` (password korporat expired berkala) |
| EIA | `403 invalid api key` di step EIA (monthly) | Regenerate di akun EIA → update `EIA_API_KEY` |
| Neon | `connection refused` / `password authentication failed` semua step | Cek console Neon (project suspended? password dirotasi?) → update `NEON_DB_URL` di Secrets + `.env` + Power BI |

Cara update secret: repo → **Settings → Secrets and variables → Actions** → edit nilai. Lalu re-run workflow yang gagal untuk verifikasi. Jangan lupa `.env` lokal ikut diganti ([checklist rotasi](02-inventaris-aset-akses.md#4-checklist-rotasi-kredensial-pasca-handover)).

---

##### Eskalasi

| Masalah | Kontak | Keterangan |
|---|---|---|
| Sistem/kode/pipeline | `[ISI: nama developer]` — `[ISI: email/telp]` | Masa dukungan s.d. `[ISI: tanggal]` |
| Infrastruktur Neon | Support Neon (console → Help) | Free tier: dokumentasi + community |
| Langganan S&P Global | `[ISI: PIC kontrak Platts di PEI]` | |
| Power BI / lisensi Microsoft | `[ISI: IT PEI]` | |

##### Rekomendasi Transisi

1. **Walkthrough terekam** 1–2 sesi: live demo buka Actions, query Neon, jalankan satu scraper lokal, refresh Power BI.
2. **Periode shadow 2–4 minggu**: operator PEI pegang checklist rutin [docs/08](../08-maintenance.md), developer lama standby.
3. Akhir shadow: jalankan [checklist rotasi kredensial](02-inventaris-aset-akses.md#4-checklist-rotasi-kredensial-pasca-handover), tutup akses lama.
