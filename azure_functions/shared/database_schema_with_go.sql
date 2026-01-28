-- Azure Functions News Scraping System Database Schema
-- SQL Server Database Schema with GO statements for proper batch execution

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

-- =====================================================
-- Core Tables
-- =====================================================

-- News sources table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[news_sources]') AND type in (N'U'))
BEGIN
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
    PRINT 'Created table: news_sources';
END
ELSE
    PRINT 'Table news_sources already exists';
GO

-- Keywords table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[keywords]') AND type in (N'U'))
BEGIN
    CREATE TABLE keywords (
        id INT IDENTITY(1,1) PRIMARY KEY,
        keyword NVARCHAR(100) NOT NULL UNIQUE,
        category NVARCHAR(50) NULL,
        is_active BIT NOT NULL DEFAULT 1,
        created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE()
    );
    PRINT 'Created table: keywords';
END
ELSE
    PRINT 'Table keywords already exists';
GO

-- News articles table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[news_articles]') AND type in (N'U'))
BEGIN
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
    PRINT 'Created table: news_articles';
END
ELSE
    PRINT 'Table news_articles already exists';
GO

-- Article keywords junction table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[article_keywords]') AND type in (N'U'))
BEGIN
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
    PRINT 'Created table: article_keywords';
END
ELSE
    PRINT 'Table article_keywords already exists';
GO

-- Sentiment analyses table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[sentiment_analyses]') AND type in (N'U'))
BEGIN
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
    PRINT 'Created table: sentiment_analyses';
END
ELSE
    PRINT 'Table sentiment_analyses already exists';
GO

-- Sentiment analysis articles junction table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[sentiment_analysis_articles]') AND type in (N'U'))
BEGIN
    CREATE TABLE sentiment_analysis_articles (
        sentiment_analysis_id UNIQUEIDENTIFIER NOT NULL,
        article_id UNIQUEIDENTIFIER NOT NULL,
        created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
        
        CONSTRAINT PK_sentiment_analysis_articles PRIMARY KEY (sentiment_analysis_id, article_id),
        CONSTRAINT FK_sentiment_analysis_articles_analysis FOREIGN KEY (sentiment_analysis_id) REFERENCES sentiment_analyses(id) ON DELETE CASCADE,
        CONSTRAINT FK_sentiment_analysis_articles_article FOREIGN KEY (article_id) REFERENCES news_articles(id)
    );
    PRINT 'Created table: sentiment_analysis_articles';
END
ELSE
    PRINT 'Table sentiment_analysis_articles already exists';
GO

-- =====================================================
-- System and Utility Tables
-- =====================================================

-- Execution logs table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[execution_logs]') AND type in (N'U'))
BEGIN
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
    PRINT 'Created table: execution_logs';
END
ELSE
    PRINT 'Table execution_logs already exists';
GO

-- Configuration table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[configuration]') AND type in (N'U'))
BEGIN
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
    PRINT 'Created table: configuration';
END
ELSE
    PRINT 'Table configuration already exists';
GO

-- =====================================================
-- Indexes for Performance Optimization
-- =====================================================

-- News articles indexes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_news_articles_published_date' AND object_id = OBJECT_ID('news_articles'))
    CREATE INDEX IX_news_articles_published_date ON news_articles(published_date DESC);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_news_articles_source_date' AND object_id = OBJECT_ID('news_articles'))
    CREATE INDEX IX_news_articles_source_date ON news_articles(source_id, published_date DESC);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_news_articles_scraped_date' AND object_id = OBJECT_ID('news_articles'))
    CREATE INDEX IX_news_articles_scraped_date ON news_articles(scraped_date DESC);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_news_articles_language' AND object_id = OBJECT_ID('news_articles'))
    CREATE INDEX IX_news_articles_language ON news_articles(language);
GO

-- Sentiment analyses indexes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_sentiment_analyses_analysis_date' AND object_id = OBJECT_ID('sentiment_analyses'))
    CREATE INDEX IX_sentiment_analyses_analysis_date ON sentiment_analyses(analysis_date DESC);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_sentiment_analyses_date_range' AND object_id = OBJECT_ID('sentiment_analyses'))
    CREATE INDEX IX_sentiment_analyses_date_range ON sentiment_analyses(date_range_start, date_range_end);
GO

-- Execution logs indexes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_execution_logs_function_time' AND object_id = OBJECT_ID('execution_logs'))
    CREATE INDEX IX_execution_logs_function_time ON execution_logs(function_name, start_time DESC);
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_execution_logs_status' AND object_id = OBJECT_ID('execution_logs'))
    CREATE INDEX IX_execution_logs_status ON execution_logs(status, start_time DESC);
GO

PRINT 'All indexes created successfully';
GO

-- =====================================================
-- Initial Data Setup
-- =====================================================

-- Insert default news sources (only if table is empty)
IF NOT EXISTS (SELECT * FROM news_sources)
BEGIN
    INSERT INTO news_sources (name, base_url, country, language, category) VALUES
    ('CNBC', 'https://www.cnbc.com', 'US', 'en', 'business'),
    ('CNN', 'https://www.cnn.com', 'US', 'en', 'news'),
    ('Reuters', 'https://www.reuters.com', 'UK', 'en', 'news'),
    ('Kompas', 'https://www.kompas.com', 'ID', 'id', 'news'),
    ('Bisnis Indonesia', 'https://www.bisnis.com', 'ID', 'id', 'business'),
    ('Kontan', 'https://www.kontan.co.id', 'ID', 'id', 'business'),
    ('Tempo', 'https://www.tempo.co', 'ID', 'id', 'news'),
    ('The Guardian', 'https://www.theguardian.com', 'UK', 'en', 'news'),
    ('OilPrice', 'https://oilprice.com', 'US', 'en', 'energy'),
    ('BPS', 'https://www.bps.go.id', 'ID', 'id', 'statistics'),
    ('CNBC Indonesia', 'https://www.cnbcindonesia.com', 'ID', 'id', 'business');
    
    PRINT 'Inserted default news sources';
END
ELSE
    PRINT 'News sources already populated';
GO

-- Insert default keywords (only if table is empty)
IF NOT EXISTS (SELECT * FROM keywords)
BEGIN
    INSERT INTO keywords (keyword, category) VALUES
    ('energy', 'sector'),
    ('oil', 'commodity'),
    ('gas', 'commodity'),
    ('renewable', 'energy_type'),
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
    ('carbon', 'environment'),
    ('climate', 'environment'),
    ('sustainability', 'environment');
    
    PRINT 'Inserted default keywords';
END
ELSE
    PRINT 'Keywords already populated';
GO

PRINT '========================================';
PRINT 'Database schema setup completed!';
PRINT '========================================';
GO
