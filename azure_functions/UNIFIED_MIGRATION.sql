-- =====================================================
-- UNIFIED DATABASE MIGRATION SCRIPT
-- Based on pei-dashboard.bacpac Schema
-- Generated: 2026-02-16
-- =====================================================
-- This script creates all 30 tables from the bacpac schema
-- Run this script to initialize or update the database
-- =====================================================

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

PRINT '========================================';
PRINT 'Starting Unified Database Migration';
PRINT 'Based on pei-dashboard.bacpac';
PRINT '========================================';
GO

-- =====================================================
-- SECTION 1: NEWS & SENTIMENT TABLES (6 tables)
-- =====================================================

PRINT '';
PRINT 'Creating News & Sentiment Tables...';
GO

-- Table: news_sources
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[news_sources]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[news_sources] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [name] NVARCHAR(100) NOT NULL UNIQUE,
        [base_url] NVARCHAR(500) NOT NULL,
        [country] VARCHAR(10) NULL,
        [language] VARCHAR(10) NULL DEFAULT 'en',
        [category] NVARCHAR(50) NULL,
        [is_active] BIT NOT NULL DEFAULT 1,
        [created_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        [updated_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: news_sources';
END
ELSE
    PRINT '  Table news_sources already exists';
GO

-- Table: keywords
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[keywords]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[keywords] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [keyword] NVARCHAR(100) NOT NULL UNIQUE,
        [category] NVARCHAR(50) NULL,
        [is_active] BIT NOT NULL DEFAULT 1,
        [created_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: keywords';
END
ELSE
    PRINT '  Table keywords already exists';
GO

-- Table: news_articles
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[news_articles]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[news_articles] (
        [id] UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        [title] NVARCHAR(500) NOT NULL,
        [content] NTEXT NOT NULL,
        [url] NVARCHAR(1000) NOT NULL UNIQUE,
        [source_id] INT NOT NULL,
        [published_date] DATETIME2 NOT NULL,
        [scraped_date] DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        [language] VARCHAR(10) NOT NULL DEFAULT 'en',
        [author] NVARCHAR(200) NULL,
        [category] NVARCHAR(100) NULL,
        [created_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        [updated_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        CONSTRAINT [FK_news_articles_source] FOREIGN KEY ([source_id]) 
            REFERENCES [dbo].[news_sources]([id])
    );
    PRINT '✓ Created table: news_articles';
END
ELSE
    PRINT '  Table news_articles already exists';
GO

-- Table: article_keywords
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[article_keywords]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[article_keywords] (
        [article_id] UNIQUEIDENTIFIER NOT NULL,
        [keyword_id] INT NOT NULL,
        [relevance_score] FLOAT NOT NULL DEFAULT 1.0,
        [created_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        CONSTRAINT [PK_article_keywords] PRIMARY KEY ([article_id], [keyword_id]),
        CONSTRAINT [FK_article_keywords_article] FOREIGN KEY ([article_id]) 
            REFERENCES [dbo].[news_articles]([id]) ON DELETE CASCADE,
        CONSTRAINT [FK_article_keywords_keyword] FOREIGN KEY ([keyword_id]) 
            REFERENCES [dbo].[keywords]([id]),
        CONSTRAINT [CHK_relevance_score] CHECK ([relevance_score] >= 0.0 AND [relevance_score] <= 1.0)
    );
    PRINT '✓ Created table: article_keywords';
END
ELSE
    PRINT '  Table article_keywords already exists';
GO

-- Table: sentiment_analyses
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[sentiment_analyses]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[sentiment_analyses] (
        [id] UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        [analysis_date] DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        [date_range_start] DATETIME2 NOT NULL,
        [date_range_end] DATETIME2 NOT NULL,
        [sentiment_score] FLOAT NOT NULL,
        [sentiment_label] VARCHAR(20) NOT NULL,
        [confidence] FLOAT NOT NULL,
        [summary] NTEXT NOT NULL,
        [model_version] VARCHAR(50) NOT NULL DEFAULT 'copilot-1.0',
        [role_context] NVARCHAR(200) NULL,
        [article_count] INT NOT NULL DEFAULT 0,
        [created_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        [updated_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        CONSTRAINT [CHK_sentiment_score] CHECK ([sentiment_score] >= -1.0 AND [sentiment_score] <= 1.0),
        CONSTRAINT [CHK_confidence] CHECK ([confidence] >= 0.0 AND [confidence] <= 1.0),
        CONSTRAINT [CHK_sentiment_label] CHECK ([sentiment_label] IN ('positive', 'negative', 'neutral')),
        CONSTRAINT [CHK_date_range] CHECK ([date_range_start] <= [date_range_end]),
        CONSTRAINT [CHK_article_count] CHECK ([article_count] >= 0)
    );
    PRINT '✓ Created table: sentiment_analyses';
END
ELSE
    PRINT '  Table sentiment_analyses already exists';
GO

-- Table: sentiment_analysis_articles
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[sentiment_analysis_articles]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[sentiment_analysis_articles] (
        [sentiment_analysis_id] UNIQUEIDENTIFIER NOT NULL,
        [article_id] UNIQUEIDENTIFIER NOT NULL,
        [created_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        CONSTRAINT [PK_sentiment_analysis_articles] PRIMARY KEY ([sentiment_analysis_id], [article_id]),
        CONSTRAINT [FK_sentiment_analysis_articles_analysis] FOREIGN KEY ([sentiment_analysis_id]) 
            REFERENCES [dbo].[sentiment_analyses]([id]) ON DELETE CASCADE,
        CONSTRAINT [FK_sentiment_analysis_articles_article] FOREIGN KEY ([article_id]) 
            REFERENCES [dbo].[news_articles]([id]) ON DELETE CASCADE
    );
    PRINT '✓ Created table: sentiment_analysis_articles';
END
ELSE
    PRINT '  Table sentiment_analysis_articles already exists';
GO

-- =====================================================
-- SECTION 2: SYSTEM TABLES (2 tables)
-- =====================================================

PRINT '';
PRINT 'Creating System Tables...';
GO

-- Table: configuration
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[configuration]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[configuration] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [config_key] NVARCHAR(100) NOT NULL UNIQUE,
        [config_value] NVARCHAR(MAX) NOT NULL,
        [category] NVARCHAR(50) NULL,
        [description] NVARCHAR(500) NULL,
        [is_active] BIT NOT NULL DEFAULT 1,
        [created_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        [updated_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: configuration';
END
ELSE
    PRINT '  Table configuration already exists';
GO

-- Table: execution_logs
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[execution_logs]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[execution_logs] (
        [id] UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        [function_name] NVARCHAR(100) NOT NULL,
        [status] VARCHAR(20) NOT NULL,
        [start_time] DATETIME2 NOT NULL,
        [end_time] DATETIME2 NULL,
        [duration_seconds] FLOAT NULL,
        [articles_scraped] INT NULL DEFAULT 0,
        [error_message] NVARCHAR(MAX) NULL,
        [metadata] NVARCHAR(MAX) NULL,
        [created_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        CONSTRAINT [CHK_execution_status] CHECK ([status] IN ('success', 'failed', 'running', 'queued'))
    );
    PRINT '✓ Created table: execution_logs';
END
ELSE
    PRINT '  Table execution_logs already exists';
GO

-- =====================================================
-- SECTION 3: BIOFUEL & RENEWABLE ENERGY TABLES (7 tables)
-- =====================================================

PRINT '';
PRINT 'Creating Biofuel & Renewable Energy Tables...';
GO

-- Table: data_biodiesel_hip
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_biodiesel_hip]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_biodiesel_hip] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [published_date] DATE NOT NULL,
        [hip_month] NVARCHAR(50) NULL,
        [price_idr_liter] FLOAT NULL,
        [scraped_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_biodiesel_hip';
END
ELSE
    PRINT '  Table data_biodiesel_hip already exists';
GO

-- Table: data_bioetanol_hip
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_bioetanol_hip]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_bioetanol_hip] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [published_date] DATE NOT NULL,
        [hip_month] NVARCHAR(50) NULL,
        [price_idr_liter] FLOAT NULL,
        [scraped_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_bioetanol_hip';
END
ELSE
    PRINT '  Table data_bioetanol_hip already exists';
GO

-- Table: data_cpo_prices
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_cpo_prices]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_cpo_prices] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [date] DATE NOT NULL,
        [price_usd_ton] FLOAT NULL,
        [price_idr_kg] FLOAT NULL,
        [source] NVARCHAR(100) NULL,
        [scraped_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_cpo_prices';
END
ELSE
    PRINT '  Table data_cpo_prices already exists';
GO

-- Table: data_saf_uco_prices
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_saf_uco_prices]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_saf_uco_prices] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [date] DATE NOT NULL,
        [saf_price_usd_liter] FLOAT NULL,
        [uco_price_usd_liter] FLOAT NULL,
        [source] NVARCHAR(100) NULL,
        [scraped_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_saf_uco_prices';
END
ELSE
    PRINT '  Table data_saf_uco_prices already exists';
GO

-- Table: data_ebt_capacity
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_ebt_capacity]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_ebt_capacity] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [year] INT NOT NULL,
        [energy_type] NVARCHAR(100) NOT NULL,
        [capacity_mw] FLOAT NULL,
        [region] NVARCHAR(100) NULL,
        [source] NVARCHAR(100) NULL,
        [scraped_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_ebt_capacity';
END
ELSE
    PRINT '  Table data_ebt_capacity already exists';
GO

-- Table: data_ebt_prices
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_ebt_prices]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_ebt_prices] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [date] DATE NOT NULL,
        [energy_type] NVARCHAR(100) NOT NULL,
        [price_idr_kwh] FLOAT NULL,
        [region] NVARCHAR(100) NULL,
        [source] NVARCHAR(100) NULL,
        [scraped_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_ebt_prices';
END
ELSE
    PRINT '  Table data_ebt_prices already exists';
GO

-- Table: data_renewable_energy
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_renewable_energy]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_renewable_energy] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [year] INT NOT NULL,
        [energy_type] NVARCHAR(100) NOT NULL,
        [production_gwh] FLOAT NULL,
        [capacity_mw] FLOAT NULL,
        [region] NVARCHAR(100) NULL,
        [source] NVARCHAR(100) NULL,
        [scraped_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_renewable_energy';
END
ELSE
    PRINT '  Table data_renewable_energy already exists';
GO

-- =====================================================
-- SECTION 4: FOSSIL FUEL & OIL TABLES (5 tables)
-- =====================================================

PRINT '';
PRINT 'Creating Fossil Fuel & Oil Tables...';
GO

-- Table: data_fossil
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_fossil]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_fossil] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [date] DATE NOT NULL,
        [product_type] NVARCHAR(100) NOT NULL,
        [volume_kl] FLOAT NULL,
        [price_idr_liter] FLOAT NULL,
        [region] NVARCHAR(100) NULL,
        [source] NVARCHAR(100) NULL,
        [scraped_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_fossil';
END
ELSE
    PRINT '  Table data_fossil already exists';
GO

-- Table: data_fossil_prediction
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_fossil_prediction]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_fossil_prediction] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [prediction_date] DATE NOT NULL,
        [product_type] NVARCHAR(100) NOT NULL,
        [predicted_volume_kl] FLOAT NULL,
        [predicted_price_idr_liter] FLOAT NULL,
        [confidence_level] FLOAT NULL,
        [model_version] NVARCHAR(50) NULL,
        [created_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_fossil_prediction';
END
ELSE
    PRINT '  Table data_fossil_prediction already exists';
GO

-- Table: data_oil_prices
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_oil_prices]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_oil_prices] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [date] DATE NOT NULL,
        [oil_type] NVARCHAR(50) NOT NULL,
        [price_usd_barrel] FLOAT NULL,
        [source] NVARCHAR(100) NULL,
        [scraped_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_oil_prices';
END
ELSE
    PRINT '  Table data_oil_prices already exists';
GO

-- Table: data_oil_crackspreads
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_oil_crackspreads]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_oil_crackspreads] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [date] DATE NOT NULL,
        [product_type] NVARCHAR(100) NOT NULL,
        [crackspread_usd_barrel] FLOAT NULL,
        [region] NVARCHAR(100) NULL,
        [source] NVARCHAR(100) NULL,
        [scraped_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_oil_crackspreads';
END
ELSE
    PRINT '  Table data_oil_crackspreads already exists';
GO

-- Table: data_petrochemical_prices
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_petrochemical_prices]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_petrochemical_prices] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [date] DATE NOT NULL,
        [product_name] NVARCHAR(100) NOT NULL,
        [price_usd_ton] FLOAT NULL,
        [region] NVARCHAR(100) NULL,
        [source] NVARCHAR(100) NULL,
        [scraped_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_petrochemical_prices';
END
ELSE
    PRINT '  Table data_petrochemical_prices already exists';
GO

-- =====================================================
-- SECTION 5: NUCLEAR & POWER TABLES (3 tables)
-- =====================================================

PRINT '';
PRINT 'Creating Nuclear & Power Tables...';
GO

-- Table: data_iaea_electrical
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_iaea_electrical]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_iaea_electrical] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [year] INT NOT NULL,
        [country] NVARCHAR(100) NOT NULL,
        [reactor_name] NVARCHAR(200) NULL,
        [electrical_output_gwh] FLOAT NULL,
        [load_factor_percent] FLOAT NULL,
        [source] NVARCHAR(100) NULL,
        [scraped_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_iaea_electrical';
END
ELSE
    PRINT '  Table data_iaea_electrical already exists';
GO

-- Table: data_iaea_nuclear_capacity
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_iaea_nuclear_capacity]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_iaea_nuclear_capacity] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [year] INT NOT NULL,
        [country] NVARCHAR(100) NOT NULL,
        [reactor_name] NVARCHAR(200) NULL,
        [capacity_mw] FLOAT NULL,
        [status] NVARCHAR(50) NULL,
        [source] NVARCHAR(100) NULL,
        [scraped_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_iaea_nuclear_capacity';
END
ELSE
    PRINT '  Table data_iaea_nuclear_capacity already exists';
GO

-- Table: data_ruptl_projects
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_ruptl_projects]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_ruptl_projects] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [project_name] NVARCHAR(200) NOT NULL,
        [project_type] NVARCHAR(100) NULL,
        [capacity_mw] FLOAT NULL,
        [location] NVARCHAR(200) NULL,
        [planned_year] INT NULL,
        [status] NVARCHAR(50) NULL,
        [source] NVARCHAR(100) NULL,
        [scraped_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_ruptl_projects';
END
ELSE
    PRINT '  Table data_ruptl_projects already exists';
GO

-- =====================================================
-- SECTION 6: MARKET & ECONOMIC TABLES (4 tables)
-- =====================================================

PRINT '';
PRINT 'Creating Market & Economic Tables...';
GO

-- Table: data_eia_market
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_eia_market]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_eia_market] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [date] DATE NOT NULL,
        [indicator_name] NVARCHAR(200) NOT NULL,
        [value] FLOAT NULL,
        [unit] NVARCHAR(50) NULL,
        [region] NVARCHAR(100) NULL,
        [source] NVARCHAR(100) NULL,
        [scraped_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_eia_market';
END
ELSE
    PRINT '  Table data_eia_market already exists';
GO

-- Table: data_market_indicators
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_market_indicators]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_market_indicators] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [date] DATE NOT NULL,
        [indicator_type] NVARCHAR(100) NOT NULL,
        [indicator_name] NVARCHAR(200) NOT NULL,
        [value] FLOAT NULL,
        [unit] NVARCHAR(50) NULL,
        [source] NVARCHAR(100) NULL,
        [scraped_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_market_indicators';
END
ELSE
    PRINT '  Table data_market_indicators already exists';
GO

-- Table: data_volatility_index
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_volatility_index]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_volatility_index] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [date] DATE NOT NULL,
        [index_value] FLOAT NULL,
        [market] NVARCHAR(100) NULL,
        [source] NVARCHAR(100) NULL,
        [scraped_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_volatility_index';
END
ELSE
    PRINT '  Table data_volatility_index already exists';
GO

-- Table: data_geopolitical_risk_index
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_geopolitical_risk_index]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_geopolitical_risk_index] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [date] DATE NOT NULL,
        [index_value] FLOAT NULL,
        [region] NVARCHAR(100) NULL,
        [source] NVARCHAR(100) NULL,
        [scraped_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_geopolitical_risk_index';
END
ELSE
    PRINT '  Table data_geopolitical_risk_index already exists';
GO

-- =====================================================
-- SECTION 7: WASTE TO ENERGY TABLES (3 tables)
-- =====================================================

PRINT '';
PRINT 'Creating Waste to Energy Tables...';
GO

-- Table: data_wte_komposisi
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_wte_komposisi]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_wte_komposisi] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [year] INT NOT NULL,
        [region] NVARCHAR(100) NOT NULL,
        [waste_type] NVARCHAR(100) NOT NULL,
        [percentage] FLOAT NULL,
        [source] NVARCHAR(100) NULL,
        [scraped_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_wte_komposisi';
END
ELSE
    PRINT '  Table data_wte_komposisi already exists';
GO

-- Table: data_wte_sumber
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_wte_sumber]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_wte_sumber] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [year] INT NOT NULL,
        [region] NVARCHAR(100) NOT NULL,
        [source_type] NVARCHAR(100) NOT NULL,
        [volume_ton] FLOAT NULL,
        [source] NVARCHAR(100) NULL,
        [scraped_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_wte_sumber';
END
ELSE
    PRINT '  Table data_wte_sumber already exists';
GO

-- Table: data_wte_timbulan
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[data_wte_timbulan]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[data_wte_timbulan] (
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [year] INT NOT NULL,
        [region] NVARCHAR(100) NOT NULL,
        [total_waste_ton] FLOAT NULL,
        [population] INT NULL,
        [waste_per_capita_kg] FLOAT NULL,
        [source] NVARCHAR(100) NULL,
        [scraped_at] DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT '✓ Created table: data_wte_timbulan';
END
ELSE
    PRINT '  Table data_wte_timbulan already exists';
GO

-- =====================================================
-- SECTION 8: INDEXES FOR PERFORMANCE
-- =====================================================

PRINT '';
PRINT 'Creating Performance Indexes...';
GO

-- Indexes for news_articles
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_news_articles_published_date' AND object_id = OBJECT_ID('news_articles'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_news_articles_published_date] 
    ON [dbo].[news_articles] ([published_date] DESC);
    PRINT '✓ Created index: IX_news_articles_published_date';
END

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_news_articles_source_id' AND object_id = OBJECT_ID('news_articles'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_news_articles_source_id] 
    ON [dbo].[news_articles] ([source_id]);
    PRINT '✓ Created index: IX_news_articles_source_id';
END

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_news_articles_scraped_date' AND object_id = OBJECT_ID('news_articles'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_news_articles_scraped_date] 
    ON [dbo].[news_articles] ([scraped_date] DESC);
    PRINT '✓ Created index: IX_news_articles_scraped_date';
END

-- Indexes for sentiment_analyses
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_sentiment_analyses_date_range' AND object_id = OBJECT_ID('sentiment_analyses'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_sentiment_analyses_date_range] 
    ON [dbo].[sentiment_analyses] ([date_range_start], [date_range_end]);
    PRINT '✓ Created index: IX_sentiment_analyses_date_range';
END

-- Indexes for execution_logs
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_execution_logs_function_name' AND object_id = OBJECT_ID('execution_logs'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_execution_logs_function_name] 
    ON [dbo].[execution_logs] ([function_name], [start_time] DESC);
    PRINT '✓ Created index: IX_execution_logs_function_name';
END

-- Indexes for data tables (date-based queries)
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_data_biodiesel_hip_date' AND object_id = OBJECT_ID('data_biodiesel_hip'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_data_biodiesel_hip_date] 
    ON [dbo].[data_biodiesel_hip] ([published_date] DESC);
    PRINT '✓ Created index: IX_data_biodiesel_hip_date';
END

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_data_bioetanol_hip_date' AND object_id = OBJECT_ID('data_bioetanol_hip'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_data_bioetanol_hip_date] 
    ON [dbo].[data_bioetanol_hip] ([published_date] DESC);
    PRINT '✓ Created index: IX_data_bioetanol_hip_date';
END

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_data_oil_prices_date' AND object_id = OBJECT_ID('data_oil_prices'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_data_oil_prices_date] 
    ON [dbo].[data_oil_prices] ([date] DESC);
    PRINT '✓ Created index: IX_data_oil_prices_date';
END

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_data_fossil_date' AND object_id = OBJECT_ID('data_fossil'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_data_fossil_date] 
    ON [dbo].[data_fossil] ([date] DESC);
    PRINT '✓ Created index: IX_data_fossil_date';
END

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_data_market_indicators_date' AND object_id = OBJECT_ID('data_market_indicators'))
BEGIN
    CREATE NONCLUSTERED INDEX [IX_data_market_indicators_date] 
    ON [dbo].[data_market_indicators] ([date] DESC);
    PRINT '✓ Created index: IX_data_market_indicators_date';
END

GO

PRINT '';
PRINT '========================================';
PRINT 'Migration Completed Successfully!';
PRINT '========================================';
PRINT '';
PRINT 'Summary:';
PRINT '  - News & Sentiment Tables: 6';
PRINT '  - System Tables: 2';
PRINT '  - Biofuel & Renewable Tables: 7';
PRINT '  - Fossil Fuel & Oil Tables: 5';
PRINT '  - Nuclear & Power Tables: 3';
PRINT '  - Market & Economic Tables: 4';
PRINT '  - Waste to Energy Tables: 3';
PRINT '  - Total Tables: 30';
PRINT '  - Performance Indexes: Created';
PRINT '';
PRINT 'All tables match pei-dashboard.bacpac schema';
PRINT '========================================';
GO
