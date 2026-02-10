-- Migration Script for PEI Dashboard Structured Data Tables
-- Date: 2026-02-10
-- Naming Convention: Prefix data_, Remove _data suffix.

-- Renaming existing tables if they exist without prefix
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'biodiesel_hip') EXEC sp_rename 'biodiesel_hip', 'data_biodiesel_hip';
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'bioetanol_hip') EXEC sp_rename 'bioetanol_hip', 'data_bioetanol_hip';
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'cpo_prices') EXEC sp_rename 'cpo_prices', 'data_cpo_prices';
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'saf_uco_prices') EXEC sp_rename 'saf_uco_prices', 'data_saf_uco_prices';
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'oil_crackspreads') EXEC sp_rename 'oil_crackspreads', 'data_oil_crackspreads';
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'market_indicators') EXEC sp_rename 'market_indicators', 'data_market_indicators';
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'ruptl_projects') EXEC sp_rename 'ruptl_projects', 'data_ruptl_projects';
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'petrochemical_prices') EXEC sp_rename 'petrochemical_prices', 'data_petrochemical_prices';
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'fossil_predictions') EXEC sp_rename 'fossil_predictions', 'data_fossil_prediction';
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'oil_prices') EXEC sp_rename 'oil_prices', 'data_oil_prices';
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'volatility_index') EXEC sp_rename 'volatility_index', 'data_volatility_index';
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'geopolitical_risk_index') EXEC sp_rename 'geopolitical_risk_index', 'data_geopolitical_risk_index';

-- Renaming and removing _data suffix
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'wte_waste_data') EXEC sp_rename 'wte_waste_data', 'data_wte_waste';
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'eia_market_data') EXEC sp_rename 'eia_market_data', 'data_eia_market';
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'renewable_energy_data') EXEC sp_rename 'renewable_energy_data', 'data_renewable_energy';
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'nuclear_data') EXEC sp_rename 'nuclear_data', 'data_nuclear';
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'manual_input_data') EXEC sp_rename 'manual_input_data', 'data_fossil';

-------------------------------------------------------------------------------
-- CREATION BLOCKS (IDEMPOTENT)
-------------------------------------------------------------------------------

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'data_biodiesel_hip')
BEGIN
    CREATE TABLE data_biodiesel_hip (
        id INT IDENTITY(1,1) PRIMARY KEY,
        published_date DATE,
        hip_month NVARCHAR(50),
        price_idr_liter FLOAT,
        scraped_at DATETIME2 DEFAULT GETUTCDATE()
    );
END

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'data_bioetanol_hip')
BEGIN
    CREATE TABLE data_bioetanol_hip (
        id INT IDENTITY(1,1) PRIMARY KEY,
        published_date DATE,
        hip_month NVARCHAR(50),
        price_idr_liter FLOAT,
        scraped_at DATETIME2 DEFAULT GETUTCDATE()
    );
END

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'data_cpo_prices')
BEGIN
    CREATE TABLE data_cpo_prices (
        id INT IDENTITY(1,1) PRIMARY KEY,
        upload_date DATE,
        price_date DATE,
        px_last FLOAT,
        scraped_at DATETIME2 DEFAULT GETUTCDATE()
    );
END

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'data_saf_uco_prices')
BEGIN
    CREATE TABLE data_saf_uco_prices (
        id INT IDENTITY(1,1) PRIMARY KEY,
        assess_date DATE UNIQUE,
        value_uco FLOAT,
        value_saf FLOAT,
        mod_date_uco DATETIME2,
        mod_date_saf DATETIME2,
        scraped_at DATETIME2 DEFAULT GETUTCDATE()
    );
END

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'data_oil_crackspreads')
BEGIN
    CREATE TABLE data_oil_crackspreads (
        id INT IDENTITY(1,1) PRIMARY KEY,
        assess_date DATE UNIQUE,
        val_ron92 FLOAT, val_ron95 FLOAT, val_ron97 FLOAT,
        val_fo05 FLOAT, val_jetkero FLOAT, val_go50 FLOAT,
        val_go2500 FLOAT, val_brent FLOAT,
        val_ron92_mt FLOAT, val_ron95_mt FLOAT,
        cs_ron92 FLOAT, cs_ron95 FLOAT, cs_ron97 FLOAT,
        scraped_at DATETIME2 DEFAULT GETUTCDATE()
    );
END

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'data_wte_waste')
BEGIN
    CREATE TABLE data_wte_waste (
        id INT IDENTITY(1,1) PRIMARY KEY,
        tahun INT,
        provinsi NVARCHAR(100),
        kab_kota NVARCHAR(100),
        jenis_data NVARCHAR(50), -- 'timbulan', 'sumber', 'komposisi'
        metric_name NVARCHAR(100),
        metric_value FLOAT,
        scraped_at DATETIME2 DEFAULT GETUTCDATE()
    );
END

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'data_market_indicators')
BEGIN
    CREATE TABLE data_market_indicators (
        id INT IDENTITY(1,1) PRIMARY KEY,
        indicator_date DATE,
        category NVARCHAR(50), -- 'Kurs', 'Inflation', 'BI Rate'
        indicator_name NVARCHAR(100),
        value FLOAT,
        scraped_at DATETIME2 DEFAULT GETUTCDATE()
    );
END

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'data_eia_market')
BEGIN
    CREATE TABLE data_eia_market (
        id INT IDENTITY(1,1) PRIMARY KEY,
        report_date DATE,
        series_id NVARCHAR(100),
        value FLOAT,
        uom NVARCHAR(20),
        scraped_at DATETIME2 DEFAULT GETUTCDATE()
    );
END

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'data_ruptl_projects')
BEGIN
    CREATE TABLE data_ruptl_projects (
        id INT IDENTITY(1,1) PRIMARY KEY,
        year_period NVARCHAR(20),
        region NVARCHAR(100),
        project_name NVARCHAR(255),
        capacity_mw FLOAT,
        fuel_type NVARCHAR(50),
        cod_year INT
    );
END

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'data_petrochemical_prices')
BEGIN
    CREATE TABLE data_petrochemical_prices (
        id INT IDENTITY(1,1) PRIMARY KEY,
        year INT,
        month INT,
        price_paraxylene FLOAT,
        price_propylene FLOAT,
        price_benzene FLOAT,
        price_butane FLOAT,
        price_propane FLOAT,
        price_lpg FLOAT,
        price_brent FLOAT,
        cs_paraxylene FLOAT,
        cs_propylene FLOAT,
        cs_benzene FLOAT,
        cs_lpg FLOAT,
        scraped_at DATETIME2 DEFAULT GETUTCDATE()
    );
END

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'data_fossil_prediction')
BEGIN
    CREATE TABLE data_fossil_prediction (
        id INT IDENTITY(1,1) PRIMARY KEY,
        prediction_year INT,
        brent FLOAT,
        gasoline FLOAT,
        diesel FLOAT,
        avtur FLOAT,
        fo05_price FLOAT,
        go2500_price FLOAT,
        go50_price FLOAT,
        jetkero_price FLOAT,
        ron92_price FLOAT,
        ron95_price FLOAT,
        ron97_price FLOAT,
        fo05_cs FLOAT,
        go2500_cs FLOAT,
        go50_cs FLOAT,
        jetkero_cs FLOAT,
        ron92_cs FLOAT,
        ron95_cs FLOAT,
        ron97_cs FLOAT,
        scraped_at DATETIME2 DEFAULT GETUTCDATE()
    );
END

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'data_nuclear')
BEGIN
    CREATE TABLE data_nuclear (
        id INT IDENTITY(1,1) PRIMARY KEY,
        year INT,
        electrical_capacity_gwe FLOAT,
        operated_reactors INT,
        electricity_supplied_twh FLOAT,
        scraped_at DATETIME2 DEFAULT GETUTCDATE()
    );
END

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'data_volatility_index')
BEGIN
    CREATE TABLE data_volatility_index (
        id INT IDENTITY(1,1) PRIMARY KEY,
        indicator_date DATE,
        index_name NVARCHAR(50),
        index_value FLOAT,
        scraped_at DATETIME2 DEFAULT GETUTCDATE()
    );
END

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'data_geopolitical_risk_index')
BEGIN
    CREATE TABLE data_geopolitical_risk_index (
        id INT IDENTITY(1,1) PRIMARY KEY,
        index_date DATE,
        region NVARCHAR(50),
        gpr_value FLOAT,
        scraped_at DATETIME2 DEFAULT GETUTCDATE()
    );
END

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'data_oil_prices')
BEGIN
    CREATE TABLE data_oil_prices (
        id INT IDENTITY(1,1) PRIMARY KEY,
        price_date DATE,
        brent FLOAT,
        gasoline FLOAT,
        diesel FLOAT,
        avtur FLOAT,
        scraped_at DATETIME2 DEFAULT GETUTCDATE()
    );
END

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'data_renewable_energy')
BEGIN
    CREATE TABLE data_renewable_energy (
        id INT IDENTITY(1,1) PRIMARY KEY,
        indicator_date DATE,
        energy_type NVARCHAR(50), -- 'Solar', 'Wind', 'Hydro', etc.
        metric_name NVARCHAR(50), -- 'Price', 'Capacity'
        region NVARCHAR(100),
        value FLOAT,
        uom NVARCHAR(20),
        scraped_at DATETIME2 DEFAULT GETUTCDATE()
    );
END

IF EXISTS (SELECT * FROM sys.tables WHERE name = 'data_fossil') DROP TABLE data_fossil;
CREATE TABLE data_fossil (
    id INT IDENTITY(1,1) PRIMARY KEY,
    [Time] NVARCHAR(100),
    Brent FLOAT,
    Gasoline FLOAT,
    Diesel FLOAT,
    Avtur FLOAT,
    created_at DATETIME2 DEFAULT GETUTCDATE()
);

-- Ensure reference_topic exists in news/sentiment tracking
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('news_articles') AND name = 'reference_topic')
    ALTER TABLE news_articles ADD reference_topic NVARCHAR(100) NULL;

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('sentiment_analyses') AND name = 'reference_topic')
    ALTER TABLE sentiment_analyses ADD reference_topic NVARCHAR(100) NULL;
