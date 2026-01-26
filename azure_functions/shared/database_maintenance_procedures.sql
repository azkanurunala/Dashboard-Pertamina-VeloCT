-- Database Maintenance Procedures for Azure Functions News Scraping System
-- Comprehensive stored procedures for database optimization and maintenance

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;

-- =====================================================
-- Performance Optimization Procedures
-- =====================================================

-- Procedure to rebuild fragmented indexes
CREATE OR ALTER PROCEDURE sp_RebuildFragmentedIndexes
    @FragmentationThreshold FLOAT = 30.0,
    @MinPageCount INT = 1000,
    @OnlineRebuild BIT = 1
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @SQL NVARCHAR(MAX);
    DECLARE @TableName NVARCHAR(128);
    DECLARE @IndexName NVARCHAR(128);
    DECLARE @Fragmentation FLOAT;
    DECLARE @PageCount INT;
    DECLARE @RebuildCount INT = 0;
    
    -- Cursor to iterate through fragmented indexes
    DECLARE index_cursor CURSOR FOR
    SELECT 
        t.name AS table_name,
        i.name AS index_name,
        ps.avg_fragmentation_in_percent,
        ps.page_count
    FROM sys.tables t
    INNER JOIN sys.indexes i ON t.object_id = i.object_id
    CROSS APPLY sys.dm_db_index_physical_stats(DB_ID(), t.object_id, i.index_id, NULL, 'LIMITED') ps
    WHERE i.index_id > 0  -- Exclude heaps
        AND ps.avg_fragmentation_in_percent >= @FragmentationThreshold
        AND ps.page_count >= @MinPageCount
        AND t.name IN ('news_articles', 'sentiment_analyses', 'execution_logs', 
                      'article_keywords', 'sentiment_analysis_articles')
    ORDER BY ps.avg_fragmentation_in_percent DESC;
    
    OPEN index_cursor;
    FETCH NEXT FROM index_cursor INTO @TableName, @IndexName, @Fragmentation, @PageCount;
    
    WHILE @@FETCH_STATUS = 0
    BEGIN
        BEGIN TRY
            -- Build rebuild command
            SET @SQL = 'ALTER INDEX [' + @IndexName + '] ON [' + @TableName + '] REBUILD';
            
            IF @OnlineRebuild = 1
                SET @SQL = @SQL + ' WITH (FILLFACTOR = 85, ONLINE = ON)';
            ELSE
                SET @SQL = @SQL + ' WITH (FILLFACTOR = 85)';
            
            -- Execute rebuild
            EXEC sp_executesql @SQL;
            SET @RebuildCount = @RebuildCount + 1;
            
            PRINT 'Rebuilt index [' + @IndexName + '] on [' + @TableName + '] - Fragmentation: ' + 
                  CAST(@Fragmentation AS VARCHAR(10)) + '%';
                  
        END TRY
        BEGIN CATCH
            PRINT 'Failed to rebuild index [' + @IndexName + '] on [' + @TableName + ']: ' + ERROR_MESSAGE();
        END CATCH
        
        FETCH NEXT FROM index_cursor INTO @TableName, @IndexName, @Fragmentation, @PageCount;
    END
    
    CLOSE index_cursor;
    DEALLOCATE index_cursor;
    
    PRINT 'Index rebuild completed. Total indexes rebuilt: ' + CAST(@RebuildCount AS VARCHAR(10));
    
    SELECT @RebuildCount AS indexes_rebuilt;
END;

-- Procedure to update statistics for all tables
CREATE OR ALTER PROCEDURE sp_UpdateAllStatistics
    @FullScan BIT = 1
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @SQL NVARCHAR(MAX);
    DECLARE @TableName NVARCHAR(128);
    DECLARE @UpdateCount INT = 0;
    
    -- Cursor to iterate through tables
    DECLARE table_cursor CURSOR FOR
    SELECT name 
    FROM sys.tables 
    WHERE name IN ('news_articles', 'sentiment_analyses', 'execution_logs', 
                  'article_keywords', 'news_sources', 'keywords', 'configuration',
                  'sentiment_analysis_articles');
    
    OPEN table_cursor;
    FETCH NEXT FROM table_cursor INTO @TableName;
    
    WHILE @@FETCH_STATUS = 0
    BEGIN
        BEGIN TRY
            -- Build update statistics command
            IF @FullScan = 1
                SET @SQL = 'UPDATE STATISTICS [' + @TableName + '] WITH FULLSCAN';
            ELSE
                SET @SQL = 'UPDATE STATISTICS [' + @TableName + ']';
            
            -- Execute update
            EXEC sp_executesql @SQL;
            SET @UpdateCount = @UpdateCount + 1;
            
            PRINT 'Updated statistics for table [' + @TableName + ']';
                  
        END TRY
        BEGIN CATCH
            PRINT 'Failed to update statistics for table [' + @TableName + ']: ' + ERROR_MESSAGE();
        END CATCH
        
        FETCH NEXT FROM table_cursor INTO @TableName;
    END
    
    CLOSE table_cursor;
    DEALLOCATE table_cursor;
    
    PRINT 'Statistics update completed. Total tables updated: ' + CAST(@UpdateCount AS VARCHAR(10));
    
    SELECT @UpdateCount AS tables_updated;
END;

-- Procedure to clean up old execution logs
CREATE OR ALTER PROCEDURE sp_CleanupOldLogs
    @RetentionDays INT = 30,
    @BatchSize INT = 1000
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @CutoffDate DATETIME2 = DATEADD(DAY, -@RetentionDays, GETUTCDATE());
    DECLARE @DeletedCount INT = 0;
    DECLARE @BatchDeletedCount INT;
    
    PRINT 'Starting cleanup of execution logs older than ' + CAST(@RetentionDays AS VARCHAR(10)) + ' days';
    PRINT 'Cutoff date: ' + CAST(@CutoffDate AS VARCHAR(30));
    
    -- Delete in batches to avoid blocking
    WHILE 1 = 1
    BEGIN
        DELETE TOP (@BatchSize) FROM execution_logs 
        WHERE created_at < @CutoffDate 
            AND status IN ('success', 'failed');  -- Keep running/queued logs
        
        SET @BatchDeletedCount = @@ROWCOUNT;
        SET @DeletedCount = @DeletedCount + @BatchDeletedCount;
        
        IF @BatchDeletedCount = 0
            BREAK;
        
        -- Small delay between batches
        WAITFOR DELAY '00:00:01';
    END
    
    PRINT 'Cleanup completed. Total records deleted: ' + CAST(@DeletedCount AS VARCHAR(10));
    
    SELECT @DeletedCount AS records_deleted;
END;

-- Procedure to analyze database performance
CREATE OR ALTER PROCEDURE sp_AnalyzeDatabasePerformance
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Database size information
    SELECT 
        'Database Size Analysis' AS analysis_type,
        DB_NAME() AS database_name,
        SUM(CASE WHEN type = 0 THEN size END) * 8 / 1024 AS data_size_mb,
        SUM(CASE WHEN type = 1 THEN size END) * 8 / 1024 AS log_size_mb,
        SUM(size) * 8 / 1024 AS total_size_mb
    FROM sys.master_files
    WHERE database_id = DB_ID();
    
    -- Table size analysis
    SELECT 
        'Table Size Analysis' AS analysis_type,
        t.name AS table_name,
        p.rows AS row_count,
        SUM(a.total_pages) * 8 / 1024 AS total_size_mb,
        SUM(a.used_pages) * 8 / 1024 AS used_size_mb,
        SUM(a.data_pages) * 8 / 1024 AS data_size_mb
    FROM sys.tables t
    INNER JOIN sys.indexes i ON t.object_id = i.object_id
    INNER JOIN sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
    INNER JOIN sys.allocation_units a ON p.partition_id = a.container_id
    WHERE t.name IN ('news_articles', 'sentiment_analyses', 'execution_logs', 
                    'article_keywords', 'news_sources', 'keywords')
    GROUP BY t.name, p.rows
    ORDER BY SUM(a.total_pages) DESC;
    
    -- Index fragmentation analysis
    SELECT 
        'Index Fragmentation Analysis' AS analysis_type,
        t.name AS table_name,
        i.name AS index_name,
        ps.avg_fragmentation_in_percent,
        ps.page_count,
        ps.page_count * 8.0 / 1024 AS size_mb,
        CASE 
            WHEN ps.avg_fragmentation_in_percent > 30 THEN 'REBUILD'
            WHEN ps.avg_fragmentation_in_percent > 10 THEN 'REORGANIZE'
            ELSE 'OK'
        END AS recommendation
    FROM sys.tables t
    INNER JOIN sys.indexes i ON t.object_id = i.object_id
    CROSS APPLY sys.dm_db_index_physical_stats(DB_ID(), t.object_id, i.index_id, NULL, 'LIMITED') ps
    WHERE i.index_id > 0
        AND ps.page_count > 100  -- Only analyze indexes with significant size
    ORDER BY ps.avg_fragmentation_in_percent DESC;
    
    -- Top slow queries
    SELECT TOP 10
        'Slow Query Analysis' AS analysis_type,
        qs.execution_count,
        qs.total_elapsed_time / 1000 AS total_duration_ms,
        (qs.total_elapsed_time / qs.execution_count) / 1000 AS avg_duration_ms,
        qs.total_worker_time / 1000 AS total_cpu_time_ms,
        (qs.total_worker_time / qs.execution_count) / 1000 AS avg_cpu_time_ms,
        qs.total_logical_reads,
        qs.total_logical_reads / qs.execution_count AS avg_logical_reads,
        SUBSTRING(st.text, (qs.statement_start_offset/2)+1,
            ((CASE qs.statement_end_offset
                WHEN -1 THEN DATALENGTH(st.text)
                ELSE qs.statement_end_offset
            END - qs.statement_start_offset)/2) + 1) AS query_text
    FROM sys.dm_exec_query_stats qs
    CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
    WHERE st.text NOT LIKE '%sys.%'
    ORDER BY qs.total_elapsed_time DESC;
END;

-- Procedure for comprehensive database maintenance
CREATE OR ALTER PROCEDURE sp_ComprehensiveMaintenance
    @RebuildIndexes BIT = 1,
    @UpdateStatistics BIT = 1,
    @CleanupLogs BIT = 1,
    @FragmentationThreshold FLOAT = 30.0,
    @LogRetentionDays INT = 30
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @StartTime DATETIME2 = GETUTCDATE();
    DECLARE @StepStartTime DATETIME2;
    DECLARE @Duration INT;
    
    PRINT '=== Starting Comprehensive Database Maintenance ===';
    PRINT 'Start time: ' + CAST(@StartTime AS VARCHAR(30));
    PRINT '';
    
    -- Step 1: Update Statistics
    IF @UpdateStatistics = 1
    BEGIN
        SET @StepStartTime = GETUTCDATE();
        PRINT '1. Updating table statistics...';
        
        EXEC sp_UpdateAllStatistics @FullScan = 1;
        
        SET @Duration = DATEDIFF(SECOND, @StepStartTime, GETUTCDATE());
        PRINT 'Statistics update completed in ' + CAST(@Duration AS VARCHAR(10)) + ' seconds';
        PRINT '';
    END
    
    -- Step 2: Rebuild Fragmented Indexes
    IF @RebuildIndexes = 1
    BEGIN
        SET @StepStartTime = GETUTCDATE();
        PRINT '2. Rebuilding fragmented indexes...';
        
        EXEC sp_RebuildFragmentedIndexes 
            @FragmentationThreshold = @FragmentationThreshold,
            @MinPageCount = 1000,
            @OnlineRebuild = 1;
        
        SET @Duration = DATEDIFF(SECOND, @StepStartTime, GETUTCDATE());
        PRINT 'Index rebuild completed in ' + CAST(@Duration AS VARCHAR(10)) + ' seconds';
        PRINT '';
    END
    
    -- Step 3: Clean Up Old Logs
    IF @CleanupLogs = 1
    BEGIN
        SET @StepStartTime = GETUTCDATE();
        PRINT '3. Cleaning up old execution logs...';
        
        EXEC sp_CleanupOldLogs 
            @RetentionDays = @LogRetentionDays,
            @BatchSize = 1000;
        
        SET @Duration = DATEDIFF(SECOND, @StepStartTime, GETUTCDATE());
        PRINT 'Log cleanup completed in ' + CAST(@Duration AS VARCHAR(10)) + ' seconds';
        PRINT '';
    END
    
    -- Final summary
    SET @Duration = DATEDIFF(SECOND, @StartTime, GETUTCDATE());
    PRINT '=== Comprehensive Maintenance Completed ===';
    PRINT 'Total duration: ' + CAST(@Duration AS VARCHAR(10)) + ' seconds';
    PRINT 'End time: ' + CAST(GETUTCDATE() AS VARCHAR(30));
    
    -- Return summary
    SELECT 
        @StartTime AS start_time,
        GETUTCDATE() AS end_time,
        @Duration AS total_duration_seconds,
        @RebuildIndexes AS rebuilt_indexes,
        @UpdateStatistics AS updated_statistics,
        @CleanupLogs AS cleaned_logs;
END;

-- =====================================================
-- Query Optimization Procedures
-- =====================================================

-- Procedure to create missing performance indexes
CREATE OR ALTER PROCEDURE sp_CreatePerformanceIndexes
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @SQL NVARCHAR(MAX);
    DECLARE @IndexCount INT = 0;
    
    PRINT 'Creating additional performance indexes...';
    
    -- Index for source-based date range queries
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('news_articles') AND name = 'IX_news_articles_source_published_scraped')
    BEGIN
        SET @SQL = 'CREATE NONCLUSTERED INDEX [IX_news_articles_source_published_scraped] 
                   ON [news_articles] ([source_id], [published_date] DESC, [scraped_date] DESC)
                   WITH (FILLFACTOR = 85, ONLINE = ON)';
        EXEC sp_executesql @SQL;
        SET @IndexCount = @IndexCount + 1;
        PRINT 'Created index: IX_news_articles_source_published_scraped';
    END
    
    -- Index for language and category filtering
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('news_articles') AND name = 'IX_news_articles_language_category')
    BEGIN
        SET @SQL = 'CREATE NONCLUSTERED INDEX [IX_news_articles_language_category] 
                   ON [news_articles] ([language], [category])
                   WITH (FILLFACTOR = 85, ONLINE = ON)';
        EXEC sp_executesql @SQL;
        SET @IndexCount = @IndexCount + 1;
        PRINT 'Created index: IX_news_articles_language_category';
    END
    
    -- Index for sentiment analysis filtering
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('sentiment_analyses') AND name = 'IX_sentiment_analyses_label_confidence')
    BEGIN
        SET @SQL = 'CREATE NONCLUSTERED INDEX [IX_sentiment_analyses_label_confidence] 
                   ON [sentiment_analyses] ([sentiment_label], [confidence] DESC)
                   WITH (FILLFACTOR = 85, ONLINE = ON)';
        EXEC sp_executesql @SQL;
        SET @IndexCount = @IndexCount + 1;
        PRINT 'Created index: IX_sentiment_analyses_label_confidence';
    END
    
    -- Index for execution log monitoring
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('execution_logs') AND name = 'IX_execution_logs_function_status_time')
    BEGIN
        SET @SQL = 'CREATE NONCLUSTERED INDEX [IX_execution_logs_function_status_time] 
                   ON [execution_logs] ([function_name], [status], [start_time] DESC)
                   WITH (FILLFACTOR = 85, ONLINE = ON)';
        EXEC sp_executesql @SQL;
        SET @IndexCount = @IndexCount + 1;
        PRINT 'Created index: IX_execution_logs_function_status_time';
    END
    
    -- Index for keyword-based searches with relevance
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('article_keywords') AND name = 'IX_article_keywords_keyword_relevance')
    BEGIN
        SET @SQL = 'CREATE NONCLUSTERED INDEX [IX_article_keywords_keyword_relevance] 
                   ON [article_keywords] ([keyword_id], [relevance_score] DESC)
                   WITH (FILLFACTOR = 85, ONLINE = ON)';
        EXEC sp_executesql @SQL;
        SET @IndexCount = @IndexCount + 1;
        PRINT 'Created index: IX_article_keywords_keyword_relevance';
    END
    
    -- Index for URL-based deduplication (covering index)
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('news_articles') AND name = 'IX_news_articles_url_covering')
    BEGIN
        SET @SQL = 'CREATE NONCLUSTERED INDEX [IX_news_articles_url_covering] 
                   ON [news_articles] ([url]) 
                   INCLUDE ([id], [scraped_date], [source_id])
                   WITH (FILLFACTOR = 90, ONLINE = ON)';
        EXEC sp_executesql @SQL;
        SET @IndexCount = @IndexCount + 1;
        PRINT 'Created index: IX_news_articles_url_covering';
    END
    
    -- Index for date range sentiment analysis queries
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('sentiment_analyses') AND name = 'IX_sentiment_analyses_daterange_covering')
    BEGIN
        SET @SQL = 'CREATE NONCLUSTERED INDEX [IX_sentiment_analyses_daterange_covering] 
                   ON [sentiment_analyses] ([date_range_start], [date_range_end]) 
                   INCLUDE ([sentiment_score], [sentiment_label], [confidence], [model_version])
                   WITH (FILLFACTOR = 85, ONLINE = ON)';
        EXEC sp_executesql @SQL;
        SET @IndexCount = @IndexCount + 1;
        PRINT 'Created index: IX_sentiment_analyses_daterange_covering';
    END
    
    PRINT 'Performance index creation completed. Total indexes created: ' + CAST(@IndexCount AS VARCHAR(10));
    
    SELECT @IndexCount AS indexes_created;
END;

-- =====================================================
-- Monitoring and Health Check Procedures
-- =====================================================

-- Procedure to check database health
CREATE OR ALTER PROCEDURE sp_DatabaseHealthCheck
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @HealthScore INT = 100;
    DECLARE @Issues TABLE (issue_type VARCHAR(50), description VARCHAR(500), severity VARCHAR(20));
    
    -- Check database connectivity
    INSERT INTO @Issues (issue_type, description, severity)
    SELECT 'Connectivity', 'Database connection test', 'INFO';
    
    -- Check for highly fragmented indexes
    INSERT INTO @Issues (issue_type, description, severity)
    SELECT 
        'Index Fragmentation',
        'Index ' + i.name + ' on table ' + t.name + ' is ' + 
        CAST(ROUND(ps.avg_fragmentation_in_percent, 1) AS VARCHAR(10)) + '% fragmented',
        CASE 
            WHEN ps.avg_fragmentation_in_percent > 50 THEN 'CRITICAL'
            WHEN ps.avg_fragmentation_in_percent > 30 THEN 'WARNING'
            ELSE 'INFO'
        END
    FROM sys.tables t
    INNER JOIN sys.indexes i ON t.object_id = i.object_id
    CROSS APPLY sys.dm_db_index_physical_stats(DB_ID(), t.object_id, i.index_id, NULL, 'LIMITED') ps
    WHERE i.index_id > 0 
        AND ps.avg_fragmentation_in_percent > 30
        AND ps.page_count > 1000;
    
    -- Check for old execution logs
    DECLARE @OldLogCount INT;
    SELECT @OldLogCount = COUNT(*) 
    FROM execution_logs 
    WHERE created_at < DATEADD(DAY, -30, GETUTCDATE());
    
    IF @OldLogCount > 10000
    BEGIN
        INSERT INTO @Issues (issue_type, description, severity)
        VALUES ('Log Cleanup', 'Found ' + CAST(@OldLogCount AS VARCHAR(10)) + ' old execution logs (>30 days)', 'WARNING');
        SET @HealthScore = @HealthScore - 10;
    END
    
    -- Check for failed executions in last 24 hours
    DECLARE @FailedExecutions INT;
    SELECT @FailedExecutions = COUNT(*) 
    FROM execution_logs 
    WHERE status = 'failed' 
        AND created_at > DATEADD(HOUR, -24, GETUTCDATE());
    
    IF @FailedExecutions > 10
    BEGIN
        INSERT INTO @Issues (issue_type, description, severity)
        VALUES ('Execution Failures', 'Found ' + CAST(@FailedExecutions AS VARCHAR(10)) + ' failed executions in last 24 hours', 'CRITICAL');
        SET @HealthScore = @HealthScore - 20;
    END
    
    -- Check database size growth
    DECLARE @DatabaseSizeMB INT;
    SELECT @DatabaseSizeMB = SUM(size) * 8 / 1024
    FROM sys.master_files
    WHERE database_id = DB_ID();
    
    IF @DatabaseSizeMB > 10240  -- 10GB
    BEGIN
        INSERT INTO @Issues (issue_type, description, severity)
        VALUES ('Database Size', 'Database size is ' + CAST(@DatabaseSizeMB AS VARCHAR(10)) + 'MB - consider archiving', 'INFO');
    END
    
    -- Calculate final health score
    DECLARE @CriticalIssues INT, @WarningIssues INT;
    SELECT @CriticalIssues = COUNT(*) FROM @Issues WHERE severity = 'CRITICAL';
    SELECT @WarningIssues = COUNT(*) FROM @Issues WHERE severity = 'WARNING';
    
    SET @HealthScore = @HealthScore - (@CriticalIssues * 20) - (@WarningIssues * 10);
    SET @HealthScore = CASE WHEN @HealthScore < 0 THEN 0 ELSE @HealthScore END;
    
    -- Return results
    SELECT 
        GETUTCDATE() AS check_timestamp,
        @HealthScore AS health_score,
        CASE 
            WHEN @HealthScore >= 90 THEN 'EXCELLENT'
            WHEN @HealthScore >= 70 THEN 'GOOD'
            WHEN @HealthScore >= 50 THEN 'FAIR'
            WHEN @HealthScore >= 30 THEN 'POOR'
            ELSE 'CRITICAL'
        END AS health_status,
        @CriticalIssues AS critical_issues,
        @WarningIssues AS warning_issues;
    
    -- Return detailed issues
    SELECT * FROM @Issues ORDER BY 
        CASE severity 
            WHEN 'CRITICAL' THEN 1 
            WHEN 'WARNING' THEN 2 
            ELSE 3 
        END;
END;

-- =====================================================
-- Utility Procedures
-- =====================================================

-- Procedure to get table row counts and sizes
CREATE OR ALTER PROCEDURE sp_GetTableStatistics
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT 
        t.name AS table_name,
        p.rows AS row_count,
        SUM(a.total_pages) * 8 / 1024 AS total_size_mb,
        SUM(a.used_pages) * 8 / 1024 AS used_size_mb,
        SUM(a.data_pages) * 8 / 1024 AS data_size_mb,
        (SUM(a.total_pages) - SUM(a.used_pages)) * 8 / 1024 AS unused_size_mb,
        CAST(ROUND(((SUM(a.used_pages) * 1.0) / SUM(a.total_pages)) * 100, 2) AS DECIMAL(5,2)) AS used_percent
    FROM sys.tables t
    INNER JOIN sys.indexes i ON t.object_id = i.object_id
    INNER JOIN sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
    INNER JOIN sys.allocation_units a ON p.partition_id = a.container_id
    WHERE t.name IN ('news_articles', 'sentiment_analyses', 'execution_logs', 
                    'article_keywords', 'news_sources', 'keywords', 'configuration',
                    'sentiment_analysis_articles')
        AND i.index_id <= 1  -- Only clustered index or heap
    GROUP BY t.name, p.rows
    ORDER BY SUM(a.total_pages) DESC;
END;

PRINT 'Database maintenance procedures created successfully.';