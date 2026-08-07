#### 03 — Database Neon PostgreSQL

##### Koneksi

- Provider: [Neon](https://neon.tech) (serverless PostgreSQL), region `ap-southeast-1`.
- Server: `ep-winter-cell-aoi4t802.c-2.ap-southeast-1.aws.neon.tech`, database `neondb`.
- Env var: `NEON_DB_URL` — connection string format `postgresql://user:password@ep-xxx.region.aws.neon.tech/dbname?sslmode=require` (ambil dari Neon Console → Connection Details).
- Batasan free tier: **512 MB storage**; compute auto-suspend saat idle (resume otomatis <1 detik, tidak perlu penanganan khusus di kode).
- Akses dari kode hanya lewat [src/helpers/neon_helper.py](../src/helpers/neon_helper.py) (psycopg2): `read_table()`, `upsert_df()` (`INSERT ... ON CONFLICT ... DO UPDATE SET`), `create_table_if_needed()` (khusus WTE), dengan commit/rollback otomatis.

Query manual cepat:

```bash
psql $NEON_DB_URL -c "SELECT topic, COUNT(*) FROM news_articles GROUP BY topic ORDER BY 2 DESC;"
```

##### Setup Skema

```bash
python scripts/run_schema.py                      # scripts/create_tables.sql (CREATE TABLE IF NOT EXISTS — aman diulang)
psql $NEON_DB_URL -f scripts/create_views.sql     # 20 view vw_* untuk Power BI
```

##### Daftar Tabel (22 tabel)

Sumber kebenaran: [scripts/create_tables.sql](../scripts/create_tables.sql) dan `SHEET_TO_TABLE`/`SHEET_CONFLICT_COLS` di [src/helpers/storage_backend.py](../src/helpers/storage_backend.py). Kolom ber-huruf-besar/spasi di-quote (`"Bulan HIP"`) — dipertahankan persis dari Excel agar Power Query tidak berubah.

###### Berita & sentimen (topic-discriminated)

| Tabel | Sumber sheet Excel | Conflict key (UNIQUE) |
|---|---|---|
| `news_articles` | semua sheet `(News)*` | `(url, topic)` |
| `news_sentiment` | semua sheet `(Summary)*` | `(topic, "Tanggal awal")` |

Kolom `news_articles`: `title, date, url, content, source, keyword` + `topic` (nama sheet asal). Kolom `news_sentiment`: `"Tanggal awal", "Tanggal akhir", "Summary", "Summary Data"` + `topic`.

###### Data terstruktur

| Sheet Excel | Tabel | Conflict key | Penulis | Jadwal |
|---|---|---|---|---|
| (Data)Biodesel | `data_biodiesel` | `"Bulan HIP"` | `biodiesel_esdm.py` | monthly tgl 1 |
| (Data)Bioetanol | `data_bioetanol` | `"Bulan HIP"` | `bioetanol_esdm.py` | monthly tgl 1 |
| (Data)Harga Minyak | `data_harga_minyak` | `"Tahun","Bulan"` | `migas_esdm.py` (OCR) | monthly tgl 1 |
| (Data)EIA | `data_eia` | `"Tahun","Bulan"` | `migas_eia.py` | monthly tgl 1 |
| (Data)CPO | `data_cpo` | `"Dates"` | `cpo_gapki.py` | daily morning |
| (Data)SAF | `data_saf` | `"assessDate"` | `spglobal_data.py` | daily afternoon + weekly |
| (Data)Kapasitas_EBT | `data_kapasitas_ebt` | `tahun, bulan` | `kapasitas_esdm.py` | monthly tgl 28 |
| (Data)WTE_Sumber | `data_wte_sumber` | `tahun,"Nama Provinsi","Nama Kota/Kabupaten"` | `wte_sipsn.py` | monthly tgl 15 |
| (Data)WTE_Komposisi | `data_wte_komposisi` | sama | `wte_sipsn.py` | monthly tgl 15 |
| (Data)WTE_Timbulan | `data_wte_timbulan` | sama | `wte_sipsn.py` | monthly tgl 15 |
| (Data)IAEA_Nuclear_Capacity | `data_iaea_nuclear_capacity` | `year, country` | `nuclear_iaea_pris.py` | monthly tgl 15 |
| (Data)IAEA_Electrical | `data_iaea_electrical` | `year, country` | `nuclear_iaea_pris.py` | monthly tgl 15 |
| (Data)IAEA_Country_Stats | `data_iaea_country_stats` | `"CountryCode"` | `nuclear_iaea_pris.py` | monthly tgl 15 |
| (Data)Crackspread_BBM | `data_crackspread_bbm` | `year, month` | `spglobal_data.py` | monthly tgl 12 |
| (Data)Crackspread_NON_BBM | `data_crackspread_non_bbm` | `"Year","Month"` | `spglobal_data.py` | monthly tgl 12 |
| (Data)Crackspread_BBM_YEAR | `data_crackspread_bbm_year` | `year` | `spglobal_data.py` | monthly tgl 12 |

###### Tabel statis (diisi sekali dari Excel, tanpa scraper)

| Tabel | Conflict key | Catatan |
|---|---|---|
| `data_ruptl` | `"ID"` | Data RUPTL |
| `data_harga_ebt` | **tidak ada UNIQUE** | ⚠️ Tidak bisa di-upsert — load ulang akan menduplikasi baris. Bila perlu reload: `TRUNCATE data_harga_ebt;` dulu, atau tambahkan UNIQUE constraint. |

##### Kasus Khusus

###### IAEA wide↔long

Excel/Power BI memakai format wide (baris = tahun, kolom = negara); PostgreSQL menyimpan long: `year INTEGER, country TEXT, value_mw/value_twh NUMERIC`, UNIQUE `(year, country)`. Transformasi otomatis di `storage_backend.py` (`_melt_iaea`/`_pivot_iaea`). View `vw_iaea_nuclear_capacity_long` dan `vw_iaea_electrical_long` mengekspos format long ke Power BI, yang kemudian melakukan `Table.Pivot` sendiri.

###### WTE dynamic schema

Kolom data SIPSN berubah antar tahun. `neon_helper.create_table_if_needed()` membuat tabel dari dtype DataFrame dan menambah kolom baru via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` saat kolom baru muncul. Nilai numerik tersimpan sebagai teks dengan pemisah ribuan koma — view `vw_wte_*` yang membersihkannya (`REPLACE(...,',','')::numeric`).

Untuk melihat kolom aktual dari API: `python scripts/sample_wte_columns.py`.

##### Views (20, untuk Power BI)

Didefinisikan di [scripts/create_views.sql](../scripts/create_views.sql). Konvensi: view mengecualikan kolom `id`, mempertahankan urutan dan kapitalisasi kolom Excel (alias `price_ron92 AS "price_RON92"` dsb.), dan menangani pembersihan tipe (WTE).

`vw_biodiesel, vw_bioetanol, vw_harga_minyak, vw_eia, vw_cpo, vw_saf, vw_kapasitas_ebt, vw_iaea_country_stats, vw_iaea_nuclear_capacity_long, vw_iaea_electrical_long, vw_crackspread_bbm, vw_crackspread_non_bbm, vw_crackspread_bbm_year, vw_wte_komposisi, vw_wte_sumber, vw_wte_timbulan, vw_ruptl, vw_harga_ebt`

`news_articles` dan `news_sentiment` dibaca Power BI langsung dari tabel (filter per `topic`), bukan lewat view.

##### Menambah Tabel Baru

Checklist lengkap ada di [09-pengembangan.md](09-pengembangan.md). Ringkas: tambah DDL di `create_tables.sql` (dengan UNIQUE constraint = conflict key) → daftarkan di `SHEET_TO_TABLE` + `SHEET_CONFLICT_COLS` → tambah view di `create_views.sql` → jalankan `run_schema.py`.
