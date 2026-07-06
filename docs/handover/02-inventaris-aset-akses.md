#### Inventaris Aset & Akses

Daftar semua akun, kredensial, dan aset yang harus berpindah tangan saat handover, plus checklist rotasi. Pelengkap [docs/08-maintenance.md](../08-maintenance.md) bagian "Secrets & Kredensial".

##### 1. Akun & Layanan

| Aset | Pemilik sekarang | Penerima (PEI) | Cara transfer |
|---|---|---|---|
| Repo GitHub `[NAMA-REPO-GITHUB]` | Akun personal `shelmasalsa17` | `[ISI: org/akun PEI]` | **Transfer ownership** (Settings → General → Transfer) ke org PEI, atau minimal tambah admin. Catatan: transfer mempertahankan Actions & secrets, tapi URL remote berubah — update remote di mesin dev & Power BI docs |
| Akun Neon PostgreSQL | `[ISI: email pemilik]` | `[ISI]` | Transfer project ke org Neon PEI (console.neon.tech → Project settings), atau ganti kepemilikan akun. Project: `neondb`, region `ap-southeast-1` |
| Google AI Studio (Gemini API key) | `[ISI: akun Google]` | `[ISI]` | PEI buat API key baru di akun sendiri → ganti secret `GEMINI_API_KEY`. Jangan pakai key lama |
| Aplikasi Microsoft/MS Graph (OneDrive legacy) | `[ISI: tenant/akun]` | `[ISI]` | Hanya perlu bila fallback OneDrive dipertahankan; kalau tidak, hapus secrets MS_*/ONEDRIVE_* dari workflow (lihat Known Issues docs/08) |
| Akun S&P Global Platts | `[ISI: username]` | `[ISI]` | Langganan korporat — konfirmasi kepemilikan lisensi & ganti password setelah handover |
| Akun EIA (api.eia.gov) | `[ISI: email]` | `[ISI]` | Gratis — PEI daftar sendiri, ganti `EIA_API_KEY` |
| File `.pbix` + workspace Power BI | `[ISI: akun publish]` | `[ISI]` | Serahkan file + pindahkan ownership dataset/report di Power BI Service; set ulang kredensial data source (Neon + SharePoint) |
| Akses SharePoint (macro series) | `[ISI]` | `[ISI]` | Pastikan akun refresh Power BI PEI punya akses ke file SharePoint tersebut |

##### 2. GitHub Secrets per Workflow

(Settings → Secrets and variables → Actions. Nilai TIDAK ditulis di sini — serahkan lewat jalur aman.)

| Secret | daily_morning | daily_afternoon | weekly | monthly | Fungsi |
|---|:--:|:--:|:--:|:--:|---|
| `NEON_DB_URL` | ✓ | ✓ | ✓ | ✓ | Koneksi PostgreSQL Neon |
| `GEMINI_API_KEY` | ✓ | ✓ | ✓ | — | AI sentimen (Gemini) |
| `SPGLOBAL_USERNAME` / `SPGLOBAL_PASSWORD` | — | ✓ | ✓ | ✓ | Login S&P Global Platts |
| `EIA_API_KEY` | — | — | — | ✓ | API EIA |
| `MS_CLIENT_ID` / `MS_CLIENT_SECRET` / `MS_TENANT_ID` / `MS_USER_EMAIL` | ✓ | ✓ | ✓ | ✓ | MS Graph OAuth (legacy OneDrive) |
| `ONEDRIVE_FILE_PATH` / `ONEDRIVE_SENTIMENT_PATH` / `ONEDRIVE_DATA_PATH` | ✓ | ✓ | ✓ | ✓ | Path Excel OneDrive (legacy) |

##### 3. Environment Variable Lokal (`.env`)

Template: `.env.example`. Var aktif:

| Var | Fungsi | Dipakai oleh |
|---|---|---|
| `NEON_DB_URL` | Koneksi Neon | `src/helpers/neon_helper.py`, `scripts/run_schema.py` |
| `STORAGE_BACKEND` | Switch `neon` (prod/CI) / `onedrive` (dev legacy) | `src/helpers/storage_backend.py` |
| `GEMINI_API_KEY` | Gemini API | `src/helpers/summary_helper.py` |
| `SPGLOBAL_USERNAME`, `SPGLOBAL_PASSWORD` | Login Platts | `src/news/spglobal_news.py`, `src/structured_data/spglobal_data.py` |
| `EIA_API_KEY` | API EIA | `src/structured_data/migas_eia.py` |
| `MS_CLIENT_ID`, `MS_CLIENT_SECRET`, `MS_TENANT_ID`, `MS_USER_EMAIL` | MS Graph OAuth | `src/helpers/onedrive_helper.py` |
| `ONEDRIVE_FILE_PATH`, `ONEDRIVE_SENTIMENT_PATH`, `ONEDRIVE_DATA_PATH` | Path Excel OneDrive | `src/helpers/storage_backend.py`, `src/structured_data/*` |
| `BPS_API_KEY` | API BPS — ⚠️ dipakai `src/news/bps.py` tapi **tidak ada** di `.env.example`/workflow; konfirmasi status scraper | `src/news/bps.py` |
| `GITHUB_TOKEN` / `GH_TOKEN` | Monitoring workflow (opsional, naikkan rate limit) | `scripts/check_workflow_schedules.py` |

Var **tidak terpakai** (scaffold/legacy, boleh dibersihkan): `AI_TYPE`, `OPENAI_API_KEY`, `OPENAI_MODEL_NAME`, `GOOGLE_CREDENTIALS`, `SPREADSHEET_ID`, `SPREADSHEET_ID_STRUCTURE`.

##### 4. Checklist Rotasi Kredensial Pasca-Handover

Prinsip: **semua kredensial yang pernah dipegang pihak lama dianggap bocor** — rotasi total. Detail peringatan keamanan (.env, token.json): [docs/08-maintenance.md](../08-maintenance.md) bagian "Peringatan Keamanan".

- [ ] Reset password database Neon (console → roles) → update `NEON_DB_URL` di: GitHub Secrets, `.env` mesin operator baru, **dan Power BI Data source settings**
- [ ] Buat `GEMINI_API_KEY` baru di akun Google PEI → update GitHub Secrets + `.env`; revoke key lama
- [ ] Ganti `SPGLOBAL_PASSWORD` → update GitHub Secrets + `.env`
- [ ] Daftar `EIA_API_KEY` baru atas email PEI → update; deactivate key lama
- [ ] (Bila OneDrive dipertahankan) rotate `MS_CLIENT_SECRET` di Azure AD; hapus `token.json` lama
- [ ] (Bila OneDrive TIDAK dipertahankan) hapus secrets MS_*/ONEDRIVE_* dari 4 workflow YAML + GitHub Secrets
- [ ] Hapus akses kolaborator lama dari repo GitHub setelah masa dukungan berakhir
- [ ] Verifikasi: jalankan `workflow_dispatch` semua 4 workflow → hijau; refresh Power BI → sukses
