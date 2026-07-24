-- =============================================================================
-- Neon PostgreSQL Schema for Dashboard-Pertamina-VeloCT
-- Run once to initialize all tables.
-- Column names are IDENTICAL to Excel sheet column names.
-- =============================================================================

-- ── NEWS ARTICLES ─────────────────────────────────────────────────────────────
-- All (News)Scrapping.xlsx sheets → one table with `topic` discriminator.
CREATE TABLE IF NOT EXISTS news_articles (
    id      SERIAL PRIMARY KEY,
    topic   VARCHAR(100)  NOT NULL,
    title   TEXT,
    date    DATE,
    url     TEXT          NOT NULL,
    content TEXT,
    source  VARCHAR(100),
    keyword TEXT,
    matched_rule TEXT,
    UNIQUE (url, topic)
);
CREATE INDEX IF NOT EXISTS idx_news_articles_topic ON news_articles (topic);
CREATE INDEX IF NOT EXISTS idx_news_articles_date  ON news_articles (date);

-- ── NEWS SENTIMENT ────────────────────────────────────────────────────────────
-- All (News)Sentiment.xlsx sheets → one table with `topic` discriminator.
CREATE TABLE IF NOT EXISTS news_sentiment (
    id               SERIAL PRIMARY KEY,
    topic            VARCHAR(100) NOT NULL,
    "Tanggal awal"   DATE,
    "Tanggal akhir"  DATE,
    "Summary"        TEXT,
    "Summary Data"   TEXT,
    UNIQUE (topic, "Tanggal awal")
);
CREATE INDEX IF NOT EXISTS idx_sentiment_topic ON news_sentiment (topic);

-- ── STRUCTURED DATA ───────────────────────────────────────────────────────────

-- (Data)Biodesel
CREATE TABLE IF NOT EXISTS data_biodiesel (
    id                   SERIAL PRIMARY KEY,
    "Date"               DATE,
    "Bulan HIP"          TEXT NOT NULL,
    "HIP Biodiesel IDR/L" DOUBLE PRECISION,
    UNIQUE ("Bulan HIP")
);

-- (Data)Bioetanol
CREATE TABLE IF NOT EXISTS data_bioetanol (
    id                    SERIAL PRIMARY KEY,
    "Date"                DATE,
    "Bulan HIP"           TEXT NOT NULL,
    "HIP Bioetanol IDR/L" DOUBLE PRECISION,
    "Harga Tetes Tebu"    DOUBLE PRECISION,
    UNIQUE ("Bulan HIP")
);

-- (Data)Harga Minyak  — source: migas_esdm.py (OCR)
CREATE TABLE IF NOT EXISTS data_harga_minyak (
    id           SERIAL PRIMARY KEY,
    "Tahun"      TEXT NOT NULL,
    "Bulan"      TEXT NOT NULL,
    "Harga"      DOUBLE PRECISION,
    "Harga_Brent" DOUBLE PRECISION,
    "Tanggal"    TEXT,
    UNIQUE ("Tahun", "Bulan")
);

-- (Data)eia  — source: migas_eia.py
CREATE TABLE IF NOT EXISTS data_eia (
    id                       SERIAL PRIMARY KEY,
    "Bulan"                  TEXT    NOT NULL,
    "Tahun"                  INTEGER NOT NULL,
    "Next Release Date"      TEXT,
    "World Total Production" DOUBLE PRECISION,
    "OPEC"                   DOUBLE PRECISION,
    "Non-OPEC"               DOUBLE PRECISION,
    "Crude Oil"              DOUBLE PRECISION,
    "Other Liquids"          DOUBLE PRECISION,
    "World Total Consumption" DOUBLE PRECISION,
    "OECD"                   DOUBLE PRECISION,
    "Non-OECD"               DOUBLE PRECISION,
    UNIQUE ("Tahun", "Bulan")
);

-- (Data)CPO  — source: cpo_gapki.py
CREATE TABLE IF NOT EXISTS data_cpo (
    id             SERIAL PRIMARY KEY,
    "Upload_Dates" DATE,
    "Dates"        DATE NOT NULL,
    "PX_LAST"      DOUBLE PRECISION,
    UNIQUE ("Dates")
);

-- (Data)SAF  — source: spglobal_data.py (daily + weekly)
CREATE TABLE IF NOT EXISTS data_saf (
    id             SERIAL PRIMARY KEY,
    "assessDate"   DATE NOT NULL,
    "value_UCO"    DOUBLE PRECISION,
    "value_SAF"    DOUBLE PRECISION,
    "modDate_UCO"  DATE,
    "modDate_SAF"  DATE,
    UNIQUE ("assessDate")
);

-- (Data)Kapasitas_EBT  — source: kapasitas_esdm.py (monthly day 28)
CREATE TABLE IF NOT EXISTS data_kapasitas_ebt (
    id          SERIAL PRIMARY KEY,
    tahun       INTEGER NOT NULL,
    bulan       INTEGER NOT NULL,
    plta        DOUBLE PRECISION,
    pltm        DOUBLE PRECISION,
    pltmh       DOUBLE PRECISION,
    pltp        DOUBLE PRECISION,
    plts        DOUBLE PRECISION,
    plts_atap   DOUBLE PRECISION,
    pltb        DOUBLE PRECISION,
    pltbm       DOUBLE PRECISION,
    pltbg       DOUBLE PRECISION,
    pltsa       DOUBLE PRECISION,
    pltbn       DOUBLE PRECISION,
    plt_hybrid  DOUBLE PRECISION,
    total       DOUBLE PRECISION,
    UNIQUE (tahun, bulan)
);

-- (Data)WTE_Sumber / WTE_Komposisi / WTE_Timbulan
-- Columns beyond the 3 base cols come from SIPSN API — auto-created by neon_helper.create_table_if_needed().
-- Run scripts/sample_wte_columns.py once to see full column list, then add manually if desired.
CREATE TABLE IF NOT EXISTS data_wte_sumber (
    id                       SERIAL PRIMARY KEY,
    tahun                    INTEGER NOT NULL,
    "Nama Provinsi"          TEXT    NOT NULL,
    "Nama Kota/Kabupaten"    TEXT    NOT NULL,
    UNIQUE (tahun, "Nama Provinsi", "Nama Kota/Kabupaten")
);

CREATE TABLE IF NOT EXISTS data_wte_komposisi (
    id                       SERIAL PRIMARY KEY,
    tahun                    INTEGER NOT NULL,
    "Nama Provinsi"          TEXT    NOT NULL,
    "Nama Kota/Kabupaten"    TEXT    NOT NULL,
    UNIQUE (tahun, "Nama Provinsi", "Nama Kota/Kabupaten")
);

CREATE TABLE IF NOT EXISTS data_wte_timbulan (
    id                       SERIAL PRIMARY KEY,
    tahun                    INTEGER NOT NULL,
    "Nama Provinsi"          TEXT    NOT NULL,
    "Nama Kota/Kabupaten"    TEXT    NOT NULL,
    UNIQUE (tahun, "Nama Provinsi", "Nama Kota/Kabupaten")
);

-- (Data)IAEA_Nuclear_Capacity  — LONG format (wide Excel → long PG)
-- Excel: rows=years, cols=countries. PG: year + country + value_mw.
CREATE TABLE IF NOT EXISTS data_iaea_nuclear_capacity (
    id        SERIAL PRIMARY KEY,
    year      INTEGER NOT NULL,
    country   TEXT    NOT NULL,
    value_mw  DOUBLE PRECISION,
    UNIQUE (year, country)
);

-- (Data)IAEA_Electrical  — same pattern
CREATE TABLE IF NOT EXISTS data_iaea_electrical (
    id        SERIAL PRIMARY KEY,
    year      INTEGER NOT NULL,
    country   TEXT    NOT NULL,
    value_twh DOUBLE PRECISION,
    UNIQUE (year, country)
);

-- (Data)IAEA_Country_Stats
CREATE TABLE IF NOT EXISTS data_iaea_country_stats (
    id                              SERIAL PRIMARY KEY,
    "LastUpdate"                    DATE,
    "Country"                       TEXT,
    "CountryCode"                   TEXT NOT NULL,
    "Reactors_InOperation"          INTEGER,
    "Reactors_UnderConstruction"    INTEGER,
    "Reactors_PermanentShutdown"    INTEGER,
    "NetCapacityMW_InOperation"     DOUBLE PRECISION,
    "NetCapacityMW_UnderConstruction" DOUBLE PRECISION,
    "NetCapacityMW_PermanentShutdown" DOUBLE PRECISION,
    UNIQUE ("CountryCode")
);

-- (Data)Crackspread_BBM  — SHORT-TERM FORECAST, year+month indexed
-- BBM_PRODUCTS = ["RON92","RON95","RON97","FO05","JetKero","GO50","GO2500"]
CREATE TABLE IF NOT EXISTS data_crackspread_bbm (
    id                        SERIAL PRIMARY KEY,
    year                      INTEGER NOT NULL,
    month                     INTEGER NOT NULL,
    price_RON92               DOUBLE PRECISION,
    price_RON95               DOUBLE PRECISION,
    price_RON97               DOUBLE PRECISION,
    price_FO05                DOUBLE PRECISION,
    price_JetKero             DOUBLE PRECISION,
    price_GO50                DOUBLE PRECISION,
    price_GO2500              DOUBLE PRECISION,
    price_Brent               DOUBLE PRECISION,
    price_RON92_crackspread   DOUBLE PRECISION,
    price_RON95_crackspread   DOUBLE PRECISION,
    price_RON97_crackspread   DOUBLE PRECISION,
    price_FO05_crackspread    DOUBLE PRECISION,
    price_JetKero_crackspread DOUBLE PRECISION,
    price_GO50_crackspread    DOUBLE PRECISION,
    price_GO2500_crackspread  DOUBLE PRECISION,
    UNIQUE (year, month)
);

-- (Data)Crackspread_NON_BBM  — monthly petrochemical prices
CREATE TABLE IF NOT EXISTS data_crackspread_non_bbm (
    id                          SERIAL PRIMARY KEY,
    "Year"                      INTEGER NOT NULL,
    "Month"                     INTEGER NOT NULL,
    "Price_Paraxylene"          DOUBLE PRECISION,
    "Price_Propylene"           DOUBLE PRECISION,
    "Price_Benzene"             DOUBLE PRECISION,
    "Price_Butane"              DOUBLE PRECISION,
    "Price_Propane"             DOUBLE PRECISION,
    "Price_LPG"                 DOUBLE PRECISION,
    "Price_Brent"               DOUBLE PRECISION,
    "Price_Paraxylene_crackspread" DOUBLE PRECISION,
    "Price_Propylene_crackspread"  DOUBLE PRECISION,
    "Price_Benzene_crackspread"    DOUBLE PRECISION,
    "Price_LPG_crackspread"        DOUBLE PRECISION,
    UNIQUE ("Year", "Month")
);

-- (Data)Crackspread_BBM_YEAR  — LONG-TERM FORECAST, year indexed
CREATE TABLE IF NOT EXISTS data_crackspread_bbm_year (
    id                        SERIAL PRIMARY KEY,
    year                      INTEGER NOT NULL,
    price_RON92               DOUBLE PRECISION,
    price_RON95               DOUBLE PRECISION,
    price_RON97               DOUBLE PRECISION,
    price_FO05                DOUBLE PRECISION,
    price_JetKero             DOUBLE PRECISION,
    price_GO50                DOUBLE PRECISION,
    price_GO2500              DOUBLE PRECISION,
    price_Brent               DOUBLE PRECISION,
    price_RON92_crackspread   DOUBLE PRECISION,
    price_RON95_crackspread   DOUBLE PRECISION,
    price_RON97_crackspread   DOUBLE PRECISION,
    price_FO05_crackspread    DOUBLE PRECISION,
    price_JetKero_crackspread DOUBLE PRECISION,
    price_GO50_crackspread    DOUBLE PRECISION,
    price_GO2500_crackspread  DOUBLE PRECISION,
    UNIQUE (year)
);

-- (Data)Crackspeed_BBM  — WEEKLY HISTORICAL, assessDate indexed
-- BBM_PRODUCTS = ["RON92","RON95","RON97","FO05","JetKero","GO50","GO2500"]
CREATE TABLE IF NOT EXISTS data_crackspeed_bbm (
    id                        SERIAL PRIMARY KEY,
    "assessDate"              TEXT NOT NULL,
    "value_RON92"             DOUBLE PRECISION,
    "value_RON95"             DOUBLE PRECISION,
    "value_RON97"             DOUBLE PRECISION,
    "value_FO05"              DOUBLE PRECISION,
    "value_JetKero"           DOUBLE PRECISION,
    "value_GO50"              DOUBLE PRECISION,
    "value_GO2500"            DOUBLE PRECISION,
    "value_Brent"             DOUBLE PRECISION,
    "value_RON92_MT"          DOUBLE PRECISION,
    "value_RON95_MT"          DOUBLE PRECISION,
    "value_RON97_MT"          DOUBLE PRECISION,
    "value_FO05_MT"           DOUBLE PRECISION,
    "value_JetKero_MT"        DOUBLE PRECISION,
    "value_GO50_MT"           DOUBLE PRECISION,
    "value_GO2500_MT"         DOUBLE PRECISION,
    "value_Brent_MT"          DOUBLE PRECISION,
    "value_RON92_final"       DOUBLE PRECISION,
    "value_RON95_final"       DOUBLE PRECISION,
    "value_RON97_final"       DOUBLE PRECISION,
    "value_FO05_final"        DOUBLE PRECISION,
    "value_JetKero_final"     DOUBLE PRECISION,
    "value_GO50_final"        DOUBLE PRECISION,
    "value_GO2500_final"      DOUBLE PRECISION,
    "value_RON92_MT_final"    DOUBLE PRECISION,
    "value_RON95_MT_final"    DOUBLE PRECISION,
    "value_RON97_MT_final"    DOUBLE PRECISION,
    "value_FO05_MT_final"     DOUBLE PRECISION,
    "value_JetKero_MT_final"  DOUBLE PRECISION,
    "value_GO50_MT_final"     DOUBLE PRECISION,
    "value_GO2500_MT_final"   DOUBLE PRECISION,
    "modDate_RON92"           TEXT,
    "modDate_RON95"           TEXT,
    "modDate_RON97"           TEXT,
    "modDate_FO05"            TEXT,
    "modDate_JetKero"         TEXT,
    "modDate_GO50"            TEXT,
    "modDate_GO2500"          TEXT,
    "modDate_Brent"           TEXT,
    UNIQUE ("assessDate")
);

-- (Data)Crackspeed_NonBBM  — WEEKLY HISTORICAL, assessDate indexed
CREATE TABLE IF NOT EXISTS data_crackspeed_non_bbm (
    id                         SERIAL PRIMARY KEY,
    "assessDate"               TEXT NOT NULL,
    "value_Butane"             DOUBLE PRECISION,
    "value_Propane"            DOUBLE PRECISION,
    "value_LPG"                DOUBLE PRECISION,
    "value_Paraxylene"         DOUBLE PRECISION,
    "value_Propylene"          DOUBLE PRECISION,
    "value_Benzene"            DOUBLE PRECISION,
    "value_Brent"              DOUBLE PRECISION,
    "value_LPG_final"          DOUBLE PRECISION,
    "value_Paraxylene_final"   DOUBLE PRECISION,
    "value_Propylene_final"    DOUBLE PRECISION,
    "value_Benzene_final"      DOUBLE PRECISION,
    "modDate_Butane"           TEXT,
    "modDate_Propane"          TEXT,
    "modDate_Paraxylene"       TEXT,
    "modDate_Propylene"        TEXT,
    "modDate_Benzene"          TEXT,
    UNIQUE ("assessDate")
);

-- ── STATIC LOOKUP TABLES ──────────────────────────────────────────────────────
-- Populated once from Excel. No scraper. Update only if source data changes.

-- (Data)RUPTL — RUPTL power plant reference data
CREATE TABLE IF NOT EXISTS data_ruptl (
    id                                SERIAL PRIMARY KEY,
    "ID"                              INTEGER,
    "Provinsi"                        TEXT,
    "No"                              INTEGER,
    "Nama Sistem Tenaga Listrik"      TEXT,
    "Jenis Pembangkit"                TEXT,
    "Lokasi / Nama Pembangkit"        TEXT,
    "Kapasitas (MW)"                  DOUBLE PRECISION,
    "Target COD Skenario RE Base"     INTEGER,
    "Target COD Skenario ARED"        INTEGER,
    "Status"                          TEXT,
    "Pengembang"                      TEXT,
    "Keterangan"                      TEXT,
    UNIQUE ("ID")
);

-- (Data)HargaEBT — renewable energy pricing reference data
CREATE TABLE IF NOT EXISTS data_harga_ebt (
    id               SERIAL PRIMARY KEY,
    "No"             TEXT,
    "Lokasi"         TEXT,
    "Provinsi"       TEXT,
    "Jenis EBT"      TEXT,
    "Faktor Lokasi"  DOUBLE PRECISION,
    "Kelompok HPT"   TEXT,
    "Stage"          INTEGER,
    "cent $/kWh"     DOUBLE PRECISION,
    "LCOE cent$/kWh" DOUBLE PRECISION,
    "Battery"        DOUBLE PRECISION
);
