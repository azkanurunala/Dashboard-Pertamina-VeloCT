# Diagram Alur Data End-to-End

Diagram Mermaid — render otomatis di GitHub. Versi teknis detail ada di [docs/01-arsitektur.md](../01-arsitektur.md).

## Versi Ringkas (untuk manajemen)

Sistem mengumpulkan data energi secara otomatis dari belasan sumber publik dan berlangganan (berita, harga komoditas, statistik pemerintah), memprosesnya di cloud tanpa server sendiri (GitHub Actions), merangkum sentimen berita dengan AI (Google Gemini), menyimpan hasilnya ke database cloud (Neon PostgreSQL), dan menyajikannya sebagai dashboard Power BI yang di-refresh berkala. Seluruh rantai berjalan otomatis pada jadwal harian/mingguan/bulanan tanpa intervensi manual.

```mermaid
flowchart LR
    A["🌐 Sumber Data<br/>(situs berita, API, PDF)"] --> B["⚙️ Pipeline Otomatis<br/>(GitHub Actions, terjadwal)"]
    B --> C["🤖 AI Sentimen<br/>(Google Gemini)"]
    B --> D["🗄️ Database Cloud<br/>(Neon PostgreSQL)"]
    C --> D
    D --> E["📊 Dashboard<br/>(Power BI)"]
```

## Versi Teknis

```mermaid
flowchart TB
    subgraph SUMBER["Sumber Data"]
        N1["Berita lokal<br/>(media Indonesia, BPS)"]
        N2["Berita internasional<br/>(CNN/CNBC, S&P Global)"]
        S1["Data terstruktur:<br/>CPO GAPKI · EIA · ESDM (OCR PDF) ·<br/>IAEA · WTE SIPSN · SP Global ·<br/>biodiesel · bioetanol · EBT"]
    end

    subgraph GHA["GitHub Actions — 4 workflow cron"]
        W1["daily_morning<br/>Sen–Jum 08:00 WIB"]
        W2["daily_afternoon<br/>Sen–Jum 14:00 WIB"]
        W3["weekly<br/>Senin 08:00 WIB"]
        W4["monthly<br/>tgl 1 / 12 / 15 / 28"]
    end

    subgraph PROSES["src/"]
        SCH["scheduler/scheduling_*.py"]
        ORC["orchestrators berita & sentimen"]
        STR["structured_data/*.py"]
        AI["helpers/summary_helper.py<br/>Gemini gemini-2.5-flash-lite"]
        SB["helpers/storage_backend.py<br/>switch STORAGE_BACKEND"]
    end

    subgraph STORAGE["Penyimpanan"]
        NEON[("Neon PostgreSQL<br/>22 tabel")]
        VW["20 view vw_*<br/>(scripts/create_views.sql)"]
        OD[("OneDrive Excel<br/>legacy / dev lokal")]
    end

    subgraph BI["Power BI"]
        PQ["Power Query (mode Import)<br/>M-code: scripts/power_query_migrated.txt"]
        SP["SharePoint<br/>(macro series, belum migrasi)"]
        DASH["Dashboard Energi Pertamina"]
    end

    N1 --> W1
    S1 --> W4
    N2 --> W2
    W1 & W2 & W3 & W4 --> SCH
    SCH --> ORC & STR
    ORC --> AI
    ORC & STR & AI --> SB
    SB -->|"STORAGE_BACKEND=neon (produksi/CI)"| NEON
    SB -.->|"STORAGE_BACKEND=onedrive (dev)"| OD
    NEON --> VW
    VW --> PQ
    SP --> PQ
    PQ --> DASH
```

## Titik Rawan (untuk operator)

| Titik di diagram | Risiko | Rujukan |
|---|---|---|
| Sumber → Actions | Situs berubah struktur/pindah domain → scraper gagal | [docs/08](../08-maintenance.md#diagnosis-scraper-rusak-situs-berubah) |
| Cron GitHub | Delay 3–5 jam; auto-disable 60 hari inaktif | [docs/04](../04-pipeline-scheduling.md) |
| Gemini | Kuota free tier / key expired | [03-runbook-hari-pertama.md](03-runbook-hari-pertama.md#skenario-3-api-key-expired--kena-limit) |
| Neon | Limit 512 MB free tier | [docs/08](../08-maintenance.md#bulanan) |
| View → Power Query | Nama kolom case-sensitive; format angka teks (koma ribuan) | [docs/07](../07-power-bi.md) |
| Power BI refresh | Butuh 2 kredensial: Neon + SharePoint | [docs/07](../07-power-bi.md) |
