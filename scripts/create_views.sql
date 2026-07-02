-- =============================================================================
-- Neon PostgreSQL Views for Power BI compatibility.
-- Each view excludes `id` and preserves Excel column order exactly.
--
-- Prerequisites: run create_tables.sql first, then populate data.
-- Run: psql $NEON_DB_URL -f scripts/create_views.sql
-- =============================================================================

-- ── SIMPLE STRUCTURED VIEWS ───────────────────────────────────────────────────

CREATE OR REPLACE VIEW vw_biodiesel AS
SELECT "Date", "Bulan HIP", "HIP Biodiesel IDR/L"
FROM data_biodiesel;

CREATE OR REPLACE VIEW vw_bioetanol AS
SELECT "Date", "Bulan HIP", "HIP Bioetanol IDR/L", "Harga Tetes Tebu"
FROM data_bioetanol;

CREATE OR REPLACE VIEW vw_harga_minyak AS
SELECT "Tahun", "Bulan", "Harga", "Harga_Brent", "Tanggal"
FROM data_harga_minyak;

CREATE OR REPLACE VIEW vw_eia AS
SELECT "Bulan", "Tahun", "Next Release Date",
       "World Total Production", "OPEC", "Non-OPEC",
       "Crude Oil", "Other Liquids",
       "World Total Consumption", "OECD", "Non-OECD"
FROM data_eia;

CREATE OR REPLACE VIEW vw_cpo AS
SELECT "Upload_Dates", "Dates", "PX_LAST"
FROM data_cpo;

CREATE OR REPLACE VIEW vw_saf AS
SELECT "assessDate", "value_UCO", "value_SAF", "modDate_UCO", "modDate_SAF"
FROM data_saf;

CREATE OR REPLACE VIEW vw_kapasitas_ebt AS
SELECT tahun, bulan, plta, pltm, pltmh, pltp, plts, plts_atap,
       pltb, pltbm, pltbg, pltsa, pltbn, plt_hybrid, total
FROM data_kapasitas_ebt;

-- ── IAEA VIEWS ────────────────────────────────────────────────────────────────

-- Country stats: simple flat view
CREATE OR REPLACE VIEW vw_iaea_country_stats AS
SELECT "LastUpdate", "Country", "CountryCode",
       "Reactors_InOperation", "Reactors_UnderConstruction", "Reactors_PermanentShutdown",
       "NetCapacityMW_InOperation", "NetCapacityMW_UnderConstruction",
       "NetCapacityMW_PermanentShutdown"
FROM data_iaea_country_stats;

-- Nuclear capacity and Electrical: stored long in Neon (year, country, value).
-- Power Query pivots these back to wide format using Table.Pivot.
-- The "country" column stores metric names (e.g. "Total Net Electrical Capacity[GW]").
CREATE OR REPLACE VIEW vw_iaea_nuclear_capacity_long AS
SELECT year, country, value_mw
FROM data_iaea_nuclear_capacity;

CREATE OR REPLACE VIEW vw_iaea_electrical_long AS
SELECT year, country, value_twh
FROM data_iaea_electrical;

-- ── CRACKSPREAD / CRACKSPEED VIEWS ───────────────────────────────────────────

CREATE OR REPLACE VIEW vw_crackspread_bbm AS
SELECT year, month,
       price_RON92, price_RON95, price_RON97, price_FO05,
       price_JetKero, price_GO50, price_GO2500, price_Brent,
       price_RON92_crackspread, price_RON95_crackspread,
       price_RON97_crackspread, price_FO05_crackspread,
       price_JetKero_crackspread, price_GO50_crackspread,
       price_GO2500_crackspread
FROM data_crackspread_bbm;

CREATE OR REPLACE VIEW vw_crackspread_non_bbm AS
SELECT "Year", "Month",
       "Price_Paraxylene", "Price_Propylene", "Price_Benzene",
       "Price_Butane", "Price_Propane", "Price_LPG", "Price_Brent",
       "Price_Paraxylene_crackspread", "Price_Propylene_crackspread",
       "Price_Benzene_crackspread", "Price_LPG_crackspread"
FROM data_crackspread_non_bbm;

CREATE OR REPLACE VIEW vw_crackspread_bbm_year AS
SELECT year,
       price_RON92, price_RON95, price_RON97, price_FO05,
       price_JetKero, price_GO50, price_GO2500, price_Brent,
       price_RON92_crackspread, price_RON95_crackspread,
       price_RON97_crackspread, price_FO05_crackspread,
       price_JetKero_crackspread, price_GO50_crackspread,
       price_GO2500_crackspread
FROM data_crackspread_bbm_year;

CREATE OR REPLACE VIEW vw_crackspeed_bbm AS
SELECT "assessDate",
       "value_RON92", "value_RON95", "value_RON97", "value_FO05",
       "value_JetKero", "value_GO50", "value_GO2500", "value_Brent",
       "value_RON92_MT", "value_RON95_MT", "value_RON97_MT", "value_FO05_MT",
       "value_JetKero_MT", "value_GO50_MT", "value_GO2500_MT", "value_Brent_MT",
       "value_RON92_final", "value_RON95_final", "value_RON97_final",
       "value_FO05_final", "value_JetKero_final", "value_GO50_final",
       "value_GO2500_final",
       "value_RON92_MT_final", "value_RON95_MT_final", "value_RON97_MT_final",
       "value_FO05_MT_final", "value_JetKero_MT_final",
       "value_GO50_MT_final", "value_GO2500_MT_final",
       "modDate_RON92", "modDate_RON95", "modDate_RON97", "modDate_FO05",
       "modDate_JetKero", "modDate_GO50", "modDate_GO2500", "modDate_Brent"
FROM data_crackspeed_bbm;

CREATE OR REPLACE VIEW vw_crackspeed_non_bbm AS
SELECT "assessDate",
       "value_Butane", "value_Propane", "value_LPG",
       "value_Paraxylene", "value_Propylene", "value_Benzene", "value_Brent",
       "value_LPG_final", "value_Paraxylene_final",
       "value_Propylene_final", "value_Benzene_final",
       "modDate_Butane", "modDate_Propane", "modDate_Paraxylene",
       "modDate_Propylene", "modDate_Benzene"
FROM data_crackspeed_non_bbm;

-- ── WTE VIEWS (aggregate by tahun — Power Query has no province columns) ──────
-- NOTE: The extra columns (sisa_makanan, ss_*, timbulan_*) are created at
-- runtime by neon_helper.create_table_if_needed() when the WTE scraper runs.
-- If these views fail, run the WTE scraper first, then re-run this file.

CREATE OR REPLACE VIEW vw_wte_komposisi AS
SELECT
    tahun,
    SUM(sisa_makanan::numeric)   AS sisa_makanan,
    SUM(kayu_ranting::numeric)   AS kayu_ranting,
    SUM(kertas_karton::numeric)  AS kertas_karton,
    SUM(plastik::numeric)        AS plastik,
    SUM(logam::numeric)          AS logam,
    SUM(kain::numeric)           AS kain,
    SUM(karet_kulit::numeric)    AS karet_kulit,
    SUM(kaca::numeric)           AS kaca,
    SUM(lainnya::numeric)        AS lainnya
FROM data_wte_komposisi
GROUP BY tahun
ORDER BY tahun;

CREATE OR REPLACE VIEW vw_wte_sumber AS
SELECT
    tahun,
    SUM(ss_rumah_tangga::numeric)     AS ss_rumah_tangga,
    SUM(ss_perkantoran::numeric)      AS ss_perkantoran,
    SUM(ss_pasar::numeric)            AS ss_pasar,
    SUM(ss_perniagaan::numeric)       AS ss_perniagaan,
    SUM(ss_fasilitas_publik::numeric) AS ss_fasilitas_publik,
    SUM(ss_kawasan::numeric)          AS ss_kawasan,
    SUM(ss_lain::numeric)             AS ss_lain
FROM data_wte_sumber
GROUP BY tahun
ORDER BY tahun;

CREATE OR REPLACE VIEW vw_wte_timbulan AS
SELECT
    tahun,
    SUM(timbulan_harian::numeric)  AS timbulan_harian,
    SUM(timbulan_tahunan::numeric) AS timbulan_tahunan
FROM data_wte_timbulan
GROUP BY tahun
ORDER BY tahun;

-- ── STATIC LOOKUP TABLE VIEWS (populated once from Excel) ─────────────────────

CREATE OR REPLACE VIEW vw_ruptl AS
SELECT "ID", "Provinsi", "No", "Nama Sistem Tenaga Listrik", "Jenis Pembangkit",
       "Lokasi / Nama Pembangkit", "Kapasitas (MW)",
       "Target COD Skenario RE Base", "Target COD Skenario ARED",
       "Status", "Pengembang", "Keterangan"
FROM data_ruptl;

CREATE OR REPLACE VIEW vw_harga_ebt AS
SELECT "No", "Lokasi", "Jenis EBT", "Faktor Lokasi", "Kelompok HPT",
       "Stage", "cent $/kWh", "LCOE cent$/kWh", "Battery"
FROM data_harga_ebt;
