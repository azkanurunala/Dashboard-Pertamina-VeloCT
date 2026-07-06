#### How-To 7: Menyambungkan Power BI ke Neon

Setup koneksi PostgreSQL di file .pbix (baru atau pindah mesin) + membuat query baru.

##### Prasyarat

- Power BI Desktop terbaru.
- Kredensial database: user + password dari `NEON_DB_URL` (format `postgresql://USER:PASSWORD@HOST/neondb?sslmode=require`; ambil dari Neon Console → Connection Details).
- Skema + view sudah terpasang di Neon ([How-To 6](06-menambah-sumber-terstruktur.md) langkah 3–4, atau `python scripts/run_schema.py`).

##### A. Koneksi Pertama Kali

1. Power BI Desktop → **Get Data** → cari **PostgreSQL database** → Connect.
2. Isi:
   - **Server:** `ep-winter-cell-aoi4t802.c-2.ap-southeast-1.aws.neon.tech`
   - **Database:** `neondb`
   - **Data Connectivity mode:** **Import** (JANGAN DirectQuery — Neon auto-suspend membuatnya lambat/gagal)
3. Dialog kredensial → tab **Database** → isi User name + Password dari `NEON_DB_URL` → Connect.
4. Bila muncul peringatan enkripsi, pilih opsi terenkripsi (Neon mewajibkan SSL).
5. Navigator menampilkan tabel/view schema `public`. **Verifikasi:** `vw_cpo`, `news_articles` dll. terlihat.

> Kredensial tersimpan per-server di Power BI (File → Options → Data source settings). Ganti password Neon = perbarui di sana.

##### B. Migrasi Query Existing (SharePoint → Neon)

1. **Transform Data** (Power Query Editor).
2. Buka [scripts/power_query_migrated.txt](../../scripts/power_query_migrated.txt) — cari nama query.
3. Bertanda `[NEON]` → pilih query di panel kiri → **Advanced Editor** → ganti seluruh M-code dengan versi di file → Done.
4. Bertanda `[UNCHANGED]` → **biarkan** (masih SharePoint: seri makro, input manual).
5. Ulangi semua query `[NEON]` → **Close & Apply** → tunggu refresh penuh → simpan .pbix.

**Verifikasi:** Refresh tanpa error; jumlah baris visual ≈ `SELECT COUNT(*)` tabel terkait.

##### C. Query Baru dari Neon

Pola M-code (lihat juga contoh nyata di `power_query_migrated.txt`):

```m
// Data terstruktur - selalu lewat view vw_*
let
    Source = PostgreSQL.Database("ep-winter-cell-aoi4t802.c-2.ap-southeast-1.aws.neon.tech", "neondb"),
    data = Source{[Schema="public", Item="vw_harga_gas"]}[Data]
in
    data

// Berita per topik
let
    Source = PostgreSQL.Database("ep-winter-cell-aoi4t802.c-2.ap-southeast-1.aws.neon.tech", "neondb"),
    t = Source{[Schema="public", Item="news_articles"]}[Data],
    f = Table.SelectRows(t, each [topic] = "(News)Harga Minyak"),
    clean = Table.RemoveColumns(f, {"id", "topic"})
in
    clean
```

Konvensi: data terstruktur lewat **view** (sudah bersih dari `id`, kapitalisasi kolom benar); berita/sentimen dari tabel + filter `topic` + buang `id`,`topic`; transformasi berat taruh di view SQL, bukan di M. Setelah jadi, **catat M-code di `scripts/power_query_migrated.txt`**.

##### Troubleshooting

| Gejala | Solusi |
|---|---|
| Refresh pertama sangat lambat | Neon baru bangun dari suspend — ulangi |
| Error kredensial | Password dirotasi → Options → Data source settings → Edit Permissions → Edit |
| "column does not exist" | Skema berubah tanpa update view/M — cocokkan dengan `create_views.sql` |
| Data kosong topik tertentu | Pipeline topik itu gagal/nonaktif → [How-To 3](03-cek-kesehatan-scheduler.md) |
