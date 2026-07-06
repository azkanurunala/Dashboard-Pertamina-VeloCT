#### 05 — Sumber Data & Scraper

Dua kelompok: **data terstruktur** (`src/structured_data/`, output tabel `data_*`) dan **berita** (`src/news/`, output `news_articles`).

##### Data Terstruktur

| Sumber | File | Endpoint / situs | Auth (env) | Output tabel | Jadwal |
|---|---|---|---|---|---|
| CPO (GAPKI) | `cpo_gapki.py` | `gapki.id/posisi-harga-komoditas/` (HTML) | — | `data_cpo` | daily morning |
| SAF + crackspeed + forecast (S&P Global Platts) | `spglobal_data.py` | `api.ci.spglobal.com` (auth `/auth/api`, market-data v3, odata petchem, energy-price-forecast) | `SPGLOBAL_USERNAME`, `SPGLOBAL_PASSWORD` | `data_saf`, `data_crackspeed_bbm`, `data_crackspeed_non_bbm`, `data_crackspread_bbm`, `data_crackspread_non_bbm`, `data_crackspread_bbm_year` | daily PM / weekly / monthly tgl 12 |
| EIA STEO | `migas_eia.py` | `api.eia.gov/v2/steo/data/` + scrape release date | `EIA_API_KEY` (gratis dari eia.gov/opendata) | `data_eia` | monthly tgl 1 |
| Harga minyak mentah ESDM (OCR) | `migas_esdm.py` | `migas.esdm.go.id/post/read/harga-minyak-mentah` → PDF → easyocr + PyMuPDF | — | `data_harga_minyak` | monthly tgl 1 |
| Biodiesel HIP (EBTKE ESDM) | `biodiesel_esdm.py` | `ebtke.esdm.go.id/api/api/artikel` + pdfplumber | — | `data_biodiesel` | monthly tgl 1 |
| Bioetanol HIP (EBTKE ESDM) | `bioetanol_esdm.py` | `ebtke.esdm.go.id/api/api/artikel` + pdfplumber | — | `data_bioetanol` | monthly tgl 1 |
| Kapasitas EBT (EBTKE ESDM) | `kapasitas_esdm.py` | `ebtke.esdm.go.id/api/api/konten/data-angka` (JSON) | — | `data_kapasitas_ebt` | monthly tgl 28 |
| Nuklir (IAEA PRIS) | `nuclear_iaea_pris.py` | `pris.iaea.org/PRIS/...` (Selenium/Chrome, 4 halaman) | — | `data_iaea_nuclear_capacity`, `data_iaea_electrical`, `data_iaea_country_stats` | monthly tgl 15 |
| Sampah / WTE (SIPSN KemenLH) | `wte_sipsn.py` | `sampahnasional.kemenlh.go.id/indikatif/public/home/ajax_list` (JSON) | — | `data_wte_sumber/komposisi/timbulan` (kolom dinamis) | monthly tgl 15 |

Catatan:
- **SIPSN:** domain lama `sipsn.kemenlh.go.id` mati sejak Okt 2024 — sudah dipindah ke `sampahnasional.kemenlh.go.id`. Bila mati lagi, cari domain penerus dan update konstanta URL di `wte_sipsn.py`.
- **S&P Global** satu-satunya sumber terstruktur berbayar/berkredensial; kegagalan auth mematikan SAF + semua crackspeed/crackspread sekaligus.
- **ESDM OCR** paling rapuh: bergantung format PDF pengumuman + akurasi OCR. Perubahan layout PDF = perlu penyesuaian parsing di `migas_esdm.py`.

##### Berita

Semua scraper berita ada di `src/news/`, dipanggil orchestrator dengan `(keyword, date_filter)`, hasil digabung → dedup per `(url, topic)` → `news_articles`.

###### Scraper lokal (dipakai `main_news_scraping_lokal.py`)

| File | Situs / endpoint |
|---|---|
| `kompas.py` | `kompas.com/sitemap*.xml` |
| `kontan.py`, `kontan_bbm.py`, `kontan_biodiesel.py` | `kontan.co.id/sitemap.xml` |
| `tempo.py` | `rss.tempo.co` + pencarian |
| `bisnis_indonesia.py` | `search.bisnis.com` |
| `cnbc_id.py` | `cnbcindonesia.com` |
| `bloomberg_technoz.py` | `bloombergtechnoz.com` |
| `bank_indonesia.py` | `bi.go.id` news release |
| `bps.py` | `webapi.bps.go.id/v1/api/` |
| `google_news.py` | `news.google.com/rss/search` + sitemap CNN/CNBC (pre-filter keyword sebelum fetch konten — lihat commit `301cf6e2`) |
| `spglobal_news.py` | `api.ci.spglobal.com/news-insights/v1/` (butuh `SPGLOBAL_*`) |

###### Scraper internasional (dipakai `main_news_scraping_internasional.py`)

| File | Situs / endpoint |
|---|---|
| `cnn.py` | `cnn.com/sitemap/news.xml` |
| `cnbc.py` | `cnbc.com/sitemap_news.xml` |
| `oilprice.py` | `oilprice.com/googlenews.xml` |
| `the_guardian.py` | `theguardian.com/sitemaps/news.xml` |
| `scmp.py` | `scmp.com/search` |
| `bioenergytimes.py` | `bioenergytimes.com` |
| `energiesmedia.py` | `energiesmedia.com` |
| `spglobal_news.py` | (sama dengan lokal) |

###### Topik berita (nilai `topic` di `news_articles`)

25 topik lokal, format `(News)<Topik>`:

```
Indeks Risiko Geopolitik, Indeks Volatilitas, Kurs, IHSG, Inflasi, BI Rate,
Indonia, Indeks Penjualan Ritel, Indeks Kepercayaan Knsmn, Indeks Kinerja
Manufaktur, Indeks Kinerja Jasa, Neraca Perdagangan, PDB, Harga Minyak,
Volume Minyak, Harga Produk Kilang, Volume Produk Kilang, Crackspread BBM,
Biodiesel, SAF, Bioetanol, RUPTL, EBT, WTE, Nuklir
```

Scraper internasional menulis ke tabel yang sama dengan nilai topic versi internasionalnya.

###### Routing keyword → scraper

Peta keyword → daftar scraper dan keyword → sheet/topik ada di dict besar dalam `main_news_scraping_lokal.py` dan `main_news_scraping_internasional.py`. **Sebagian besar topik sedang dinonaktifkan (dikomentari)** — periksa dict aktif di file tersebut untuk tahu topik apa yang benar-benar jalan sekarang. Mengaktifkan topik = uncomment entri di dict + pastikan sheet/topik terdaftar di daftar sheet aktif orchestrator.

###### Perilaku tanggal

- Di CI (`CI=true`): scrape berita "kemarin" (H-1).
- Di lokal: rentang `START_DATE`/`END_DATE` hardcoded di masing-masing orchestrator — sesuaikan sebelum run manual.
- Backfill historis berita: `scripts/backfill.py --sources news_lokal news_intl` (loop harian) atau `kompas_monthly` (sitemap bulanan Kompas).

##### Menambah Sumber Baru

Checklist lengkap di [09-pengembangan.md](09-pengembangan.md).
