-- Azure Functions News Scraping System Database Schema
-- SQL Server Database Schema for news articles, sentiment analysis, and system metadata

-- Enable ANSI_NULLS and QUOTED_IDENTIFIER for best practices
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;

-- Create database if it doesn't exist (for initial setup)
-- Note: This should be run by a database administrator
-- IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'NewsScrapingDB')
-- BEGIN
--     CREATE DATABASE NewsScrapingDB;
-- END;

-- Use the news scraping database
-- USE NewsScrapingDB;

-- =====================================================
-- Core Tables
-- =====================================================

-- News sources table
CREATE TABLE news_sources (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL UNIQUE,
    base_url NVARCHAR(500) NOT NULL,
    country VARCHAR(10) NULL,
    language VARCHAR(10) NULL DEFAULT 'en',
    category NVARCHAR(50) NULL,
    is_active BIT NOT NULL DEFAULT 1,
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE()
);

-- Keywords table
CREATE TABLE keywords (
    id INT IDENTITY(1,1) PRIMARY KEY,
    keyword NVARCHAR(100) NOT NULL UNIQUE,
    category NVARCHAR(50) NULL,
    is_active BIT NOT NULL DEFAULT 1,
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE()
);

-- News articles table
CREATE TABLE news_articles (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    title NVARCHAR(500) NOT NULL,
    content NTEXT NOT NULL,
    url NVARCHAR(1000) NOT NULL UNIQUE,
    source_id INT NOT NULL,
    published_date DATETIME2 NOT NULL,
    scraped_date DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    author NVARCHAR(200) NULL,
    category NVARCHAR(100) NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    
    CONSTRAINT FK_news_articles_source FOREIGN KEY (source_id) REFERENCES news_sources(id)
);

-- Article keywords junction table
CREATE TABLE article_keywords (
    article_id UNIQUEIDENTIFIER NOT NULL,
    keyword_id INT NOT NULL,
    relevance_score FLOAT NOT NULL DEFAULT 1.0,
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    
    CONSTRAINT PK_article_keywords PRIMARY KEY (article_id, keyword_id),
    CONSTRAINT FK_article_keywords_article FOREIGN KEY (article_id) REFERENCES news_articles(id) ON DELETE CASCADE,
    CONSTRAINT FK_article_keywords_keyword FOREIGN KEY (keyword_id) REFERENCES keywords(id),
    CONSTRAINT CHK_relevance_score CHECK (relevance_score >= 0.0 AND relevance_score <= 1.0)
);

-- Sentiment analyses table
CREATE TABLE sentiment_analyses (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    analysis_date DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    date_range_start DATETIME2 NOT NULL,
    date_range_end DATETIME2 NOT NULL,
    sentiment_score FLOAT NOT NULL,
    sentiment_label VARCHAR(20) NOT NULL,
    confidence FLOAT NOT NULL,
    summary NTEXT NOT NULL,
    model_version VARCHAR(50) NOT NULL DEFAULT 'copilot-1.0',
    role_context NVARCHAR(200) NULL,
    article_count INT NOT NULL DEFAULT 0,
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    
    CONSTRAINT CHK_sentiment_score CHECK (sentiment_score >= -1.0 AND sentiment_score <= 1.0),
    CONSTRAINT CHK_confidence CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CONSTRAINT CHK_sentiment_label CHECK (sentiment_label IN ('positive', 'negative', 'neutral')),
    CONSTRAINT CHK_date_range CHECK (date_range_start <= date_range_end),
    CONSTRAINT CHK_article_count CHECK (article_count >= 0)
);

-- Sentiment analysis articles junction table
CREATE TABLE sentiment_analysis_articles (
    sentiment_analysis_id UNIQUEIDENTIFIER NOT NULL,
    article_id UNIQUEIDENTIFIER NOT NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    
    CONSTRAINT PK_sentiment_analysis_articles PRIMARY KEY (sentiment_analysis_id, article_id),
    CONSTRAINT FK_sentiment_analysis_articles_analysis FOREIGN KEY (sentiment_analysis_id) REFERENCES sentiment_analyses(id) ON DELETE CASCADE,
    CONSTRAINT FK_sentiment_analysis_articles_article FOREIGN KEY (article_id) REFERENCES news_articles(id)
);

-- =====================================================
-- System and Utility Tables
-- =====================================================

-- Execution logs table
CREATE TABLE execution_logs (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    function_name NVARCHAR(100) NOT NULL,
    execution_id NVARCHAR(100) NOT NULL,
    start_time DATETIME2 NOT NULL,
    end_time DATETIME2 NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    error_message NTEXT NULL,
    input_parameters NTEXT NULL,
    output_summary NTEXT NULL,
    duration_ms INT NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    
    CONSTRAINT CHK_execution_status CHECK (status IN ('success', 'failed', 'running', 'queued')),
    CONSTRAINT CHK_duration_ms CHECK (duration_ms >= 0)
);

-- Configuration table
CREATE TABLE configuration (
    id INT IDENTITY(1,1) PRIMARY KEY,
    config_key NVARCHAR(100) NOT NULL UNIQUE,
    config_value NTEXT NOT NULL,
    config_type VARCHAR(20) NOT NULL DEFAULT 'string',
    description NVARCHAR(500) NULL,
    is_sensitive BIT NOT NULL DEFAULT 0,
    created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    
    CONSTRAINT CHK_config_type CHECK (config_type IN ('string', 'json', 'int', 'bool', 'float'))
);

-- =====================================================
-- Indexes for Performance Optimization
-- =====================================================

-- News articles indexes
CREATE INDEX IX_news_articles_published_date ON news_articles(published_date DESC);
CREATE INDEX IX_news_articles_source_date ON news_articles(source_id, published_date DESC);
CREATE INDEX IX_news_articles_scraped_date ON news_articles(scraped_date DESC);
CREATE INDEX IX_news_articles_language ON news_articles(language);
CREATE INDEX IX_news_articles_category ON news_articles(category);
CREATE INDEX IX_news_articles_author ON news_articles(author);

-- Sentiment analyses indexes
CREATE INDEX IX_sentiment_analyses_analysis_date ON sentiment_analyses(analysis_date DESC);
CREATE INDEX IX_sentiment_analyses_date_range ON sentiment_analyses(date_range_start, date_range_end);
CREATE INDEX IX_sentiment_analyses_sentiment_label ON sentiment_analyses(sentiment_label);
CREATE INDEX IX_sentiment_analyses_model_version ON sentiment_analyses(model_version);

-- Execution logs indexes
CREATE INDEX IX_execution_logs_function_time ON execution_logs(function_name, start_time DESC);
CREATE INDEX IX_execution_logs_status ON execution_logs(status, start_time DESC);
CREATE INDEX IX_execution_logs_execution_id ON execution_logs(execution_id);

-- Keywords indexes
CREATE INDEX IX_keywords_category ON keywords(category);
CREATE INDEX IX_keywords_active ON keywords(is_active);

-- News sources indexes
CREATE INDEX IX_news_sources_active ON news_sources(is_active);
CREATE INDEX IX_news_sources_country ON news_sources(country);
CREATE INDEX IX_news_sources_language ON news_sources(language);

-- =====================================================
-- Views for Common Queries
-- =====================================================

-- View for articles with source information
CREATE VIEW vw_articles_with_source AS
SELECT 
    a.id,
    a.title,
    a.content,
    a.url,
    a.published_date,
    a.scraped_date,
    a.language,
    a.author,
    a.category,
    s.name AS source_name,
    s.base_url AS source_base_url,
    s.country AS source_country
FROM news_articles a
INNER JOIN news_sources s ON a.source_id = s.id
WHERE s.is_active = 1;

-- View for sentiment analyses with article count
CREATE VIEW vw_sentiment_analyses_summary AS
SELECT 
    sa.id,
    sa.analysis_date,
    sa.date_range_start,
    sa.date_range_end,
    sa.sentiment_score,
    sa.sentiment_label,
    sa.confidence,
    sa.summary,
    sa.model_version,
    sa.role_context,
    COUNT(saa.article_id) AS actual_article_count,
    sa.article_count AS recorded_article_count
FROM sentiment_analyses sa
LEFT JOIN sentiment_analysis_articles saa ON sa.id = saa.sentiment_analysis_id
GROUP BY sa.id, sa.analysis_date, sa.date_range_start, sa.date_range_end, 
         sa.sentiment_score, sa.sentiment_label, sa.confidence, sa.summary,
         sa.model_version, sa.role_context, sa.article_count;

-- =====================================================
-- Stored Procedures for Common Operations
-- =====================================================

-- Procedure to get or create a news source
CREATE PROCEDURE sp_GetOrCreateNewsSource
    @name NVARCHAR(100),
    @base_url NVARCHAR(500),
    @country VARCHAR(10) = NULL,
    @language VARCHAR(10) = 'en',
    @category NVARCHAR(50) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @source_id INT;
    
    -- Try to get existing source
    SELECT @source_id = id 
    FROM news_sources 
    WHERE name = @name;
    
    -- Create if doesn't exist
    IF @source_id IS NULL
    BEGIN
        INSERT INTO news_sources (name, base_url, country, language, category)
        VALUES (@name, @base_url, @country, @language, @category);
        
        SET @source_id = SCOPE_IDENTITY();
    END
    
    SELECT @source_id AS source_id;
END;

-- Procedure to get or create a keyword
CREATE PROCEDURE sp_GetOrCreateKeyword
    @keyword NVARCHAR(100),
    @category NVARCHAR(50) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @keyword_id INT;
    
    -- Try to get existing keyword
    SELECT @keyword_id = id 
    FROM keywords 
    WHERE keyword = @keyword;
    
    -- Create if doesn't exist
    IF @keyword_id IS NULL
    BEGIN
        INSERT INTO keywords (keyword, category)
        VALUES (@keyword, @category);
        
        SET @keyword_id = SCOPE_IDENTITY();
    END
    
    SELECT @keyword_id AS keyword_id;
END;

-- Procedure to deduplicate articles by URL
CREATE PROCEDURE sp_DeduplicateArticles
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @deleted_count INT = 0;
    
    -- Delete duplicate articles, keeping the earliest scraped_date
    WITH DuplicateArticles AS (
        SELECT id, url,
               ROW_NUMBER() OVER (PARTITION BY url ORDER BY scraped_date ASC) as rn
        FROM news_articles
    )
    DELETE FROM news_articles 
    WHERE id IN (
        SELECT id FROM DuplicateArticles WHERE rn > 1
    );
    
    SET @deleted_count = @@ROWCOUNT;
    
    SELECT @deleted_count AS deleted_count;
END;

-- =====================================================
-- Initial Data Setup
-- =====================================================

-- Insert default news sources
INSERT INTO news_sources (name, base_url, country, language, category) VALUES
('CNBC', 'https://www.cnbc.com', 'US', 'en', 'business'),
('CNN', 'https://www.cnn.com', 'US', 'en', 'news'),
('Reuters', 'https://www.reuters.com', 'UK', 'en', 'news'),
('Kompas', 'https://www.kompas.com', 'ID', 'id', 'news'),
('Bisnis Indonesia', 'https://www.bisnis.com', 'ID', 'id', 'business'),
('Kontan', 'https://www.kontan.co.id', 'ID', 'id', 'business'),
('Tempo', 'https://www.tempo.co', 'ID', 'id', 'news'),
('Bloomberg', 'https://www.bloomberg.com', 'US', 'en', 'business'),
('The Guardian', 'https://www.theguardian.com', 'UK', 'en', 'news'),
('SCMP', 'https://www.scmp.com', 'HK', 'en', 'news'),
('OilPrice', 'https://oilprice.com', 'US', 'en', 'energy'),
('Energies Media', 'https://www.energiesmedia.com', 'FR', 'en', 'energy'),
('Bioenergy Times', 'https://www.bioenergytimes.com', 'US', 'en', 'energy'),
('Bank Indonesia', 'https://www.bi.go.id', 'ID', 'id', 'finance'),
('BPS', 'https://www.bps.go.id', 'ID', 'id', 'statistics'),
('ESDM', 'https://www.esdm.go.id', 'ID', 'id', 'energy'),
('EIA', 'https://www.eia.gov', 'US', 'en', 'energy'),
('Google News', 'https://news.google.com', 'US', 'en', 'aggregator'),
('CNBC Indonesia', 'https://www.cnbcindonesia.com', 'ID', 'id', 'business');

-- Insert default keywords
INSERT INTO keywords (keyword, category) VALUES
('energy', 'sector'),
('oil', 'commodity'),
('gas', 'commodity'),
('renewable', 'energy_type'),
('solar', 'energy_type'),
('wind', 'energy_type'),
('biodiesel', 'biofuel'),
('bioethanol', 'biofuel'),
('palm oil', 'commodity'),
('CPO', 'commodity'),
('coal', 'commodity'),
('electricity', 'utility'),
('power', 'utility'),
('fuel', 'commodity'),
('petroleum', 'commodity'),
('LNG', 'commodity'),
('pipeline', 'infrastructure'),
('refinery', 'infrastructure'),
('carbon', 'environment'),
('climate', 'environment'),
('sustainability', 'environment'),
('ESG', 'investment'),
('investment', 'finance'),
('market', 'finance'),
('price', 'finance'),
('trading', 'finance'),
('policy', 'government'),
('regulation', 'government'),
('subsidy', 'government'),
('tax', 'government');

-- Insert default configuration values
INSERT INTO configuration (config_key, config_value, config_type, description) VALUES
('scraper.default_rate_limit_delay', '1', 'int', 'Default delay between scraper requests in seconds'),
('scraper.default_max_retries', '3', 'int', 'Default maximum retry attempts for failed requests'),
('scraper.default_timeout', '30', 'int', 'Default request timeout in seconds'),
('copilot.default_batch_size', '10', 'int', 'Default batch size for Copilot API requests'),
('copilot.default_max_tokens', '4000', 'int', 'Default maximum tokens for Copilot responses'),
('copilot.default_temperature', '0.3', 'float', 'Default temperature for Copilot API calls'),
('database.connection_pool_size', '10', 'int', 'Database connection pool size'),
('database.command_timeout', '60', 'int', 'Database command timeout in seconds'),
('system.version', '1.0.0', 'string', 'Current system version'),
('system.environment', 'development', 'string', 'Current deployment environment');