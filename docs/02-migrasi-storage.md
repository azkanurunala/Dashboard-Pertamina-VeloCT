#### 02 — Migrasi Storage: OneDrive Excel → Neon PostgreSQL

##### Latar Belakang

Sampai pertengahan 2026, seluruh hasil scraping disimpan sebagai 3 file Excel di OneDrive/SharePoint (via MS Graph API):

| File Excel (OneDrive) | Isi | Env path |
|---|---|---|
| `(News)Scrapping.xlsx` | Artikel berita, 1 sheet per topik `(News)...` | `ONEDRIVE_FILE_PATH` |
| `(News)Sentiment.xlsx` | Ringkasan sentimen, 1 sheet per topik `(Summary)...` | `ONEDRIVE_SENTIMENT_PATH` |
| `(Terstruktur)Data Scrapping.xlsx` | Data tabular, 1 sheet per dataset `(Data)...` | `ONEDRIVE_DATA_PATH` |

Masalahnya: file Excel sebagai "database" rapuh (lock, corrupt, race antar pipeline), lambat, dan menyulitkan query. Pada awal Juli 2026 (commit `508e3cda`, 2026-07-02) storage produksi dipindah ke **Neon PostgreSQL**.

**Kenapa Neon:** free tier 512 MB cukup, compute auto-suspend dan resume <1 detik (dibanding Supabase yang mem-pause seluruh project setelah 1 minggu tidak aktif — fatal untuk pipeline harian).

##### Mekanisme Switch: `STORAGE_BACKEND`

Semua baca/tulis lewat satu modul: [src/helpers/storage_backend.py](../src/helpers/storage_backend.py).

```
STORAGE_BACKEND=onedrive  → _OneDriveBackend (default; dev lokal / legacy)
STORAGE_BACKEND=neon      → _NeonBackend     (produksi; semua GitHub Actions)
```

Modul mengekspor singleton `storage` yang dipakai semua orchestrator dan scraper terstruktur:

```python
from helpers.storage_backend import storage

# Berita
all_sheets = storage.read_all_news_sheets(ACTIVE_SHEETS)  # dict[str, DataFrame]
df = storage.read_news_sheet(sheet_name)
storage.write_news_file(all_sheets)                       # upsert (neon) / upload (onedrive)

# Sentimen
all_sheets = storage.read_all_sentiment_sheets(sheet_names)
df = storage.read_sentiment_sheet(sheet_name)
storage.write_sentiment_file(all_sheets)

# Data terstruktur
df = storage.read_structured_sheet("(Data)Biodesel")
storage.write_structured_sheet("(Data)Biodesel", df)
```

Kedua backend mengimplementasikan interface yang sama, jadi scraper tidak perlu tahu backend aktif.

###### Pemetaan sheet → tabel

Di backend Neon, nama sheet Excel dipetakan ke tabel PostgreSQL lewat dict `SHEET_TO_TABLE` dan kunci upsert `SHEET_CONFLICT_COLS` (keduanya di `storage_backend.py`). Daftar lengkap ada di [03-database.md](03-database.md). Ringkas:

- Semua sheet `(News)*` → **satu** tabel `news_articles`, dibedakan kolom `topic`.
- Semua sheet `(Summary)*` → **satu** tabel `news_sentiment`, dibedakan kolom `topic`.
- Tiap sheet `(Data)*` → tabel `data_*` masing-masing.

###### Transformasi khusus di backend Neon

- **IAEA wide↔long:** sheet `(Data)IAEA_Nuclear_Capacity` dan `(Data)IAEA_Electrical` di Excel berbentuk wide (baris = tahun, kolom = negara). Di PostgreSQL disimpan long (`year, country, value_mw/value_twh`). Fungsi `_melt_iaea` (saat tulis) dan `_pivot_iaea` (saat baca) di `storage_backend.py` membuat transformasi ini transparan — scraper tetap bekerja dengan format wide.
- **WTE dynamic schema:** kolom data SIPSN berubah-ubah, jadi tabel `data_wte_*` dibuat/di-ALTER otomatis dari dtype DataFrame via `create_table_if_needed()` di [src/helpers/neon_helper.py](../src/helpers/neon_helper.py).

##### Apa yang Sudah Migrasi vs Belum

| Kategori | Status |
|---|---|
| Berita (`news_articles`) | ✅ Neon |
| Sentimen (`news_sentiment`) | ✅ Neon |
| Semua data terstruktur hasil scraping (`data_*`) | ✅ Neon |
| Tabel statis `data_ruptl`, `data_harga_ebt` | ✅ Neon (diisi sekali dari Excel) |
| **Seri makroekonomi** (BI-Rate, Kurs, PMI, Inflasi, IHSG, PDB, Neraca Perdagangan, Geopolitik, Volatilitas, dst. dari `(Data)Makro.xlsx`) | ❌ **Masih SharePoint** — tidak ada scraper-nya, diupdate manual. Power Query-nya bertanda `[UNCHANGED]`. |
| `(Data)Input_Fosil_Prediction` dari `(Data)Input_Manual.xlsx` | ❌ Masih SharePoint (input manual) |

Konsekuensi: **OneDrive/SharePoint belum bisa dimatikan total.** Secrets `MS_*` dan `ONEDRIVE_*` masih diinject ke semua workflow (dipakai bila fallback ke backend onedrive dan oleh script migrasi).

##### Script Migrasi & Backfill

###### Setup skema (sekali per database)

```bash
python scripts/run_schema.py            # menjalankan scripts/create_tables.sql
psql $NEON_DB_URL -f scripts/create_views.sql
```

###### Migrasi data Excel → Neon (one-time)

[scripts/migrate_excel_to_neon.py](../scripts/migrate_excel_to_neon.py) membaca semua sheet dari OneDrive lalu upsert ke Neon. Tabel WTE dikecualikan (kolom dinamis) — jalankan `wte_sipsn.py` dengan `STORAGE_BACKEND=neon` sebagai gantinya.

```bash
# butuh .env lengkap (kredensial MS Graph + NEON_DB_URL)
python scripts/migrate_excel_to_neon.py
```

###### Backfill historis (gap Okt 2025 – Jun 2026)

[scripts/backfill.py](../scripts/backfill.py) mengisi kekosongan data historis. Dapat di-interrupt dan di-resume — progres disimpan ke `scripts/backfill_progress.json` setelah tiap unit kerja.

```bash
python scripts/backfill.py                                        # semua sumber
python scripts/backfill.py --sources eia spglobal_saf news_lokal  # sumber tertentu
python scripts/backfill.py --start 2025-10-01 --end 2025-12-31    # rentang custom
python scripts/backfill.py --sources news_lokal --resume-from 2026-01-15
python scripts/backfill.py --delay 5.0                            # rate-limit lebih pelan
```

Tier sumber (lihat docstring file untuk daftar penuh):
- **Tier 1** (self-healing, cukup sekali): `eia`, `biodiesel_esdm`, `bioetanol_esdm`, `migas_esdm`, `iaea`, `wte`, `cpo`
- **Tier 2** (S&P dengan rentang tanggal): `spglobal_saf`
- **Tier 3** (berita, loop harian): `news_lokal`, `news_intl`
- **Tier 4** (sitemap historis Kompas, loop bulanan): `kompas_monthly`

Format `backfill_progress.json`: `completed_sources[]`, `last_completed_date_lokal`, `last_completed_date_intl`, `completed_kompas_months[]`. Hapus entri untuk memaksa jalan ulang sumber tertentu.

##### Status OneDrive Legacy

- [src/helpers/onedrive_helper.py](../src/helpers/onedrive_helper.py) **dipertahankan** — dipakai internal `_OneDriveBackend` dan `migrate_excel_to_neon.py`. Token MS Graph di-refresh otomatis pada tiap operasi tulis.
- Backend onedrive masih berfungsi penuh; berguna untuk dev lokal tanpa akses Neon, atau rollback darurat (set `STORAGE_BACKEND=onedrive` di workflow — data akan menyimpang dari Neon sejak saat itu, perlu migrasi ulang saat kembali).
- File `token.json` di root adalah cache OAuth lokal — **jangan di-commit**, lihat peringatan di [08-maintenance.md](08-maintenance.md).
