#### Biaya & Lisensi

Ringkasan tier layanan saat ini, limit yang berlaku, sinyal kapan harus upgrade, dan perkiraan biayanya. Seluruh sistem saat ini berjalan **tanpa biaya langganan** kecuali S&P Global (langganan korporat) dan lisensi Power BI.

| Layanan | Tier sekarang | Limit yang relevan | Sinyal harus upgrade | Opsi & estimasi biaya |
|---|---|---|---|---|
| **Neon PostgreSQL** | Free | Storage **512 MB**; auto-suspend compute saat idle; history/PITR retensi terbatas | `pg_database_size` mendekati 512 MB (cek bulanan, SQL di [docs/08](../08-maintenance.md#bulanan)); butuh restore point lebih panjang | Launch plan (per 2026 mulai ± US$19/bln — cek harga terkini di neon.tech/pricing); alternatif: arsip/hapus artikel lama di `news_articles` |
| **GitHub Actions** | Free (repo public/personal) | Delay cron 3–5 jam; auto-disable setelah 60 hari repo inaktif; kuota menit gratis; timeout workflow diset 90/120/180 menit | Delay tidak bisa ditoleransi; workflow sering mati karena inaktivitas | GitHub Team/org berbayar tidak menghilangkan delay cron; solusi nyata = **self-hosted runner** (server internal PEI) atau scheduler eksternal yang trigger `workflow_dispatch` |
| **Google Gemini** | Free tier, model `gemini-2.5-flash-lite` | Kuota request/hari free tier; volume aktual rendah (≤ jumlah topik aktif per hari, hanya step sentimen) | Error 429 quota berulang di log | Pay-as-you-go Gemini API — biaya diperkirakan sangat kecil di volume sekarang (< US$5/bln); cek ai.google.dev/pricing |
| **Power BI** | `[ISI: lisensi PEI sekarang]` | Publish & scheduled refresh di Power BI Service butuh **Pro** per user (atau kapasitas Premium/Fabric) | Perlu share dashboard ke banyak user / refresh terjadwal otomatis | Power BI Pro ± US$14/user/bln (konfirmasi lisensi Microsoft 365 PEI — sering sudah termasuk E5) |
| **S&P Global Platts** | Langganan korporat `[ISI: pemegang kontrak]` | Sesuai kontrak | Kontrak berakhir → scraper spglobal gagal auth | `[ISI: nilai & masa kontrak]` — pastikan perpanjangan jadi tanggung jawab PEI |
| **EIA API** | Gratis (API key registrasi) | Rate limit longgar, tidak relevan di volume sekarang | — | Tetap gratis |
| **SharePoint/OneDrive** | Bagian Microsoft 365 | — | Hanya dipakai macro series Power BI + legacy dev | Sudah tercakup lisensi M365 PEI |

##### Catatan Keputusan Arsitektur Terkait Biaya

- **Power BI mode Import, bukan DirectQuery** — disengaja: compute Neon free tier auto-suspend, DirectQuery akan sering timeout dan menahan compute aktif terus (boros bila upgrade ke paid). Jangan diubah tanpa membaca [docs/07-power-bi.md](../07-power-bi.md).
- **Model `gemini-2.5-flash-lite`** dipilih untuk biaya/kecepatan; ganti model cukup satu konstanta di `src/helpers/summary_helper.py` ([docs/06](../06-ai-sentiment.md)).
- Torch/EasyOCR di monthly workflow diinstal versi CPU-only untuk menghindari disk-full runner gratis — jangan "dirapikan" jadi instalasi default.

##### Skenario Total Biaya

| Skenario | Perkiraan/bulan | Kapan relevan |
|---|---|---|
| Status quo (semua free tier) | US$0 + lisensi eksisting (Platts, M365) | Berjalan baik selama data < 512 MB & delay cron diterima |
| Upgrade minimal | ± US$19–40 (Neon Launch + Gemini PAYG) | Data melewati 512 MB atau kuota Gemini habis |
| Operasional penuh internal | + biaya server runner internal / kapasitas Power BI | Butuh jadwal presisi & distribusi dashboard luas |

> Harga per Juli 2026, verifikasi ulang ke halaman pricing masing-masing sebelum pengambilan keputusan anggaran.
