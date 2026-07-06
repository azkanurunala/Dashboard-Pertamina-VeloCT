#### How-To 8: Rotasi Kredensial

Wajib saat: handover selesai, ada indikasi bocor, atau rutin (disarankan 6-bulanan). Inventaris lengkap akun: [handover/02-inventaris-aset-akses.md](../handover/02-inventaris-aset-akses.md).

##### Prinsip Umum (berlaku semua kredensial)

Untuk tiap kredensial, urutannya selalu:
1. Generate nilai baru di layanan sumber.
2. Update **GitHub Secrets**: repo → Settings → Secrets and variables → Actions → klik nama secret → Update.
3. Update `.env` lokal semua mesin dev.
4. Uji (lihat kolom uji di tabel).
5. Revoke/hapus nilai lama (bila layanannya memisahkan create/revoke).

##### Per Kredensial

| Kredensial | Cara generate baru | Uji setelah rotasi |
|---|---|---|
| `NEON_DB_URL` | Neon Console → project → Roles/Connection Details → Reset password | `python -c "...psycopg2.connect..."` ([How-To 1](01-setup-lokal-dari-nol.md) langkah 6) + **update kredensial Power BI** (Options → Data source settings) |
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey → Create API key; hapus key lama | `python -c "import sys; sys.path.append('src'); from helpers.summary_helper import setup_gemini; setup_gemini(); print('ok')"` |
| `SPGLOBAL_USERNAME/PASSWORD` | Akun S&P Global Platts (via account manager S&P bila SSO) | Dispatch workflow *Daily Afternoon*, cek step SAF hijau |
| `EIA_API_KEY` | https://www.eia.gov/opendata/register.php | Dispatch *Monthly* (step EIA) atau `main_eia()` lokal |
| `MS_CLIENT_SECRET` | Azure Portal → App registrations → app terkait → Certificates & secrets → New client secret (catat: expiry!) | `python -c "import sys; sys.path.append('src'); from helpers.onedrive_helper import get_access_token; get_access_token(); print('ok')"` |
| Kredensial Power BI/SharePoint | Ikuti kebijakan M365 organisasi | Refresh .pbix penuh |

##### Setelah Semua Dirotasi

1. Jalankan pipeline penuh sekali via dispatch (minimal *Daily Morning* + *Daily Afternoon*) — semua step hijau = rotasi bersih.
2. `python scripts/check_workflow_schedules.py` → exit 0.
3. Hapus `token.json` di root repo bila ada (cache OAuth lama; dibuat ulang otomatis).
4. Catat tanggal rotasi + expiry (khusus MS client secret punya masa berlaku!) di dokumen internal tim.

##### Bila Kredensial Bocor (urutan darurat)

1. Revoke kredensial bocor di layanan sumber **duluan** (bukan update dulu).
2. Generate baru → update GitHub Secrets → uji.
3. Khusus `NEON_DB_URL`: cek query/aktivitas asing di Neon Console → Monitoring.
4. Khusus repo: bila `.env` pernah ter-commit, anggap SEMUA isinya bocor — rotasi semuanya.
