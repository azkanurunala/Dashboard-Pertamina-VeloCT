#### 07 — Power BI & Power Query

##### Dua File Referensi

| File | Isi |
|---|---|
| [power_query_names.txt](../power_query_names.txt) (root) | Snapshot **asli** semua M-query Power BI era SharePoint (semua query membaca `SharePoint.Files(...)` → `Excel.Workbook`). Berfungsi sebagai inventaris & arsip pra-migrasi. |
| [scripts/power_query_migrated.txt](../scripts/power_query_migrated.txt) | M-query **pengganti** pasca-migrasi. Tiap query bertanda `[NEON]` (sudah dipindah ke PostgreSQL — ganti M-code-nya) atau `[UNCHANGED]` (tetap SharePoint — **jangan diganti**). |

##### Prasyarat Koneksi (sekali per file .pbix)

1. Skema Neon sudah terpasang: `scripts/create_tables.sql` + `scripts/create_views.sql` (lihat [03-database.md](03-database.md)).
2. Tabel statis `data_ruptl` dan `data_harga_ebt` sudah diisi (one-time dari Excel).
3. Di Power BI Desktop: **Get Data → PostgreSQL database**
   - Server: `ep-winter-cell-aoi4t802.c-2.ap-southeast-1.aws.neon.tech`
   - Database: `neondb`
   - Mode: **Import** (JANGAN DirectQuery — Neon auto-suspend membuat DirectQuery lambat/gagal; Import hanya menyentuh DB saat refresh)
   - Kredensial: user/password dari `NEON_DB_URL` (Neon Console → Connection Details). Power BI menyimpan kredensial per-server, jadi cukup sekali isi.
   - Bila muncul error enkripsi, gunakan koneksi terenkripsi (Neon mewajibkan SSL).

##### Prosedur Mengganti Query (migrasi per query)

1. Power BI Desktop → **Transform Data** (Power Query Editor).
2. Pilih query yang bertanda `[NEON]` di `power_query_migrated.txt`.
3. **Advanced Editor** → hapus seluruh M-code lama → paste M-code baru dari file tersebut → Done.
4. Ulangi untuk semua query `[NEON]`; biarkan yang `[UNCHANGED]`.
5. **Close & Apply** → refresh penuh → simpan .pbix.

##### Pola M-code Neon

```m
let
    Source = PostgreSQL.Database("ep-winter-cell-aoi4t802.c-2.ap-southeast-1.aws.neon.tech", "neondb"),
    tabel = Source{[Schema="public", Item="news_articles"]}[Data],
    difilter = Table.SelectRows(tabel, each [topic] = "(News)Harga Minyak"),
    bersih = Table.RemoveColumns(difilter, {"id", "topic"})
in
    bersih
```

Pola per jenis data:
- **Berita:** baca `news_articles`, filter `[topic] = "(News)X"`, buang `id`/`topic` → hasil identik dengan sheet Excel lama.
- **Sentimen:** sama, dari `news_sentiment` dengan `[topic] = "(Summary)X"`.
- **Terstruktur:** baca view `vw_*` (bukan tabel) — view sudah membuang `id`, memulihkan kapitalisasi kolom, dan membersihkan tipe. IAEA: baca view long (`vw_iaea_*_long`) lalu `Table.Pivot` kolom `country` untuk kembali ke bentuk wide.

##### Yang Tetap di SharePoint (`[UNCHANGED]`)

- Semua seri makroekonomi dari `(Data)Makro.xlsx`: BI-Rate, Kurs, PMI, Inflasi, IHSG, PDB, Geopolitik, Volatilitas, Neraca Perdagangan, dll. **Tidak ada scraper untuk data ini** — diupdate manual di SharePoint (`<tenant>-my.sharepoint.com`).
- `(Data)Input_Fosil_Prediction` dari `(Data)Input_Manual.xlsx` (input manual).
- Tabel literal statis di M (mis. `Kategori eia`, `Kategori Harga Kilang`).

Konsekuensi: refresh dashboard tetap butuh kredensial SharePoint **dan** Neon. SharePoint baru bisa dilepas bila seri makro dipindahkan (dibuatkan scraper/loader ke Neon — kandidat pengembangan, lihat [09-pengembangan.md](09-pengembangan.md)).

##### Menambah Query Baru dari Neon

1. Pastikan tabel/view-nya ada (untuk data terstruktur baru, buat view di `create_views.sql`).
2. Power Query: **New Source → PostgreSQL** (server/db sama) atau duplikasi query Neon yang ada lalu ganti `Item="nama_view"`.
3. Ikuti konvensi: pakai view untuk data terstruktur; buang kolom `id`; jangan lakukan agregasi berat di M bila bisa di view SQL.
4. Catat query baru di `scripts/power_query_migrated.txt` supaya file itu tetap menjadi sumber kebenaran M-code.

##### Troubleshooting Refresh

| Gejala | Kemungkinan penyebab |
|---|---|
| Kolom tidak ditemukan setelah refresh | Skema tabel berubah tanpa update view/M-code ([03-database.md](03-database.md)) |
| Refresh lambat sekali di awal | Neon compute baru resume dari suspend — normal, coba lagi |
| Data kosong untuk topik tertentu | Pipeline scraping topik itu gagal/nonaktif — cek `SELECT MAX(date) FROM news_articles WHERE topic='(News)X'` dan log Actions ([08-maintenance.md](08-maintenance.md)) |
| Error kredensial PostgreSQL | Password Neon dirotasi — perbarui di Data source settings |
