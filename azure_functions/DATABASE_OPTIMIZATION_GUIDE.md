# Database Optimization and Maintenance Guide

## Overview

This guide covers the comprehensive database optimization and maintenance features implemented for the Azure Functions News Scraping System. The system includes automated performance monitoring, index management, query optimization, and scheduled maintenance operations.

## Table of Contents

1. [Architecture](#architecture)
2. [Performance Indexes](#performance-indexes)
3. [Maintenance Operations](#maintenance-operations)
4. [Stored Procedures](#stored-procedures)
5. [Automated Scheduling](#automated-scheduling)
6. [Azure Function API](#azure-function-api)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Architecture

The database optimization system consists of three main components:

### 1. Database Optimizer (`database_optimization.py`)
- Index analysis and management
- Query performance monitoring
- Maintenance operation execution
- Performance report generation

### 2. Maintenance Scheduler (`database_maintenance_scheduler.py`)
- Automated task scheduling (daily, weekly, monthly)
- Health check monitoring
- Task configuration and management
- Stored procedure execution

### 3. Maintenance Function (`database_maintenance_function/`)
- HTTP API for manual operations
- Integration with Azure Functions
- Real-time maintenance execution
- Status reporting

## Performance Indexes

### Core Indexes (Existing)

The database schema includes essential indexes for common query patterns:

```sql
-- News articles indexes
IX_news_articles_published_date
IX_news_articles_source_date
IX_news_articles_scraped_date
IX_news_articles_language
IX_news_articles_category
IX_news_articles_author

-- Sentiment analyses indexes
IX_sentiment_analyses_analysis_date
IX_sentiment_analyses_date_range
IX_sentiment_analyses_sentiment_label
IX_sentiment_analyses_model_version

-- Execution logs indexes
IX_execution_logs_function_time
IX_execution_logs_status
IX_execution_logs_execution_id
```

### Additional Performance Indexes

The optimization system can create additional composite indexes for complex queries:

```sql
-- Composite index for source-based date range queries
IX_news_articles_source_published_scraped
  ON news_articles (source_id, published_date DESC, scraped_date DESC)

-- Language and category filtering
IX_news_articles_language_category
  ON news_articles (language, category)

-- Sentiment filtering and ranking
IX_sentiment_analyses_label_confidence
  ON sentiment_analyses (sentiment_label, confidence DESC)

-- Function performance monitoring
IX_execution_logs_function_status_time
  ON execution_logs (function_name, status, start_time DESC)

-- Keyword-based searches with relevance
IX_article_keywords_keyword_relevance
  ON article_keywords (keyword_id, relevance_score DESC)

-- URL-based deduplication (covering index)
IX_news_articles_url_covering
  ON news_articles (url) INCLUDE (id, scraped_date, source_id)

-- Date range sentiment analysis (covering index)
IX_sentiment_analyses_daterange_covering
  ON sentiment_analyses (date_range_start, date_range_end)
  INCLUDE (sentiment_score, sentiment_label, confidence, model_version)
```

### Index Design Principles

1. **Composite Indexes**: Combine frequently queried columns
2. **Covering Indexes**: Include additional columns to avoid lookups
3. **Descending Order**: Use DESC for date columns in range queries
4. **Fill Factor**: Set to 85% for write-heavy tables, 90% for read-heavy
5. **Online Operations**: Use ONLINE = ON for production rebuilds

## Maintenance Operations

### 1. Index Rebuild

Rebuilds fragmented indexes to improve query performance.

**When to Run**: Weekly or when fragmentation > 30%

**Python API**:
```python
from shared.database_optimization import DatabaseOptimizer

optimizer = DatabaseOptimizer(db_handler)
result = await optimizer.rebuild_fragmented_indexes(
    fragmentation_threshold=30.0
)
```

**SQL Procedure**:
```sql
EXEC sp_RebuildFragmentedIndexes 
    @FragmentationThreshold = 30.0,
    @MinPageCount = 1000,
    @OnlineRebuild = 1
```

### 2. Statistics Update

Updates table statistics for optimal query plan generation.

**When to Run**: Weekly or after large data changes

**Python API**:
```python
result = await optimizer.update_table_statistics(
    table_names=['news_articles', 'sentiment_analyses']
)
```

**SQL Procedure**:
```sql
EXEC sp_UpdateAllStatistics @FullScan = 1
```

### 3. Log Cleanup

Removes old execution logs to free up space.

**When to Run**: Daily

**Python API**:
```python
result = await optimizer.cleanup_old_logs(retention_days=30)
```

**SQL Procedure**:
```sql
EXEC sp_CleanupOldLogs 
    @RetentionDays = 30,
    @BatchSize = 1000
```

### 4. Create Missing Indexes

Creates additional performance indexes based on query patterns.

**When to Run**: Monthly or after schema changes

**Python API**:
```python
result = await optimizer.create_missing_indexes()
```

**SQL Procedure**:
```sql
EXEC sp_CreatePerformanceIndexes
```

### 5. Comprehensive Maintenance

Runs all maintenance operations in sequence.

**When to Run**: Weekly during off-peak hours

**Python API**:
```python
results = await optimizer.run_comprehensive_maintenance(
    rebuild_indexes=True,
    update_statistics=True,
    cleanup_logs=True,
    create_indexes=True,
    retention_days=30
)
```

**SQL Procedure**:
```sql
EXEC sp_ComprehensiveMaintenance
    @RebuildIndexes = 1,
    @UpdateStatistics = 1,
    @CleanupLogs = 1,
    @FragmentationThreshold = 30.0,
    @LogRetentionDays = 30
```

## Stored Procedures

### Performance Optimization Procedures

#### sp_RebuildFragmentedIndexes
Rebuilds indexes exceeding fragmentation threshold.

**Parameters**:
- `@FragmentationThreshold` (FLOAT): Minimum fragmentation % (default: 30.0)
- `@MinPageCount` (INT): Minimum pages to consider (default: 1000)
- `@OnlineRebuild` (BIT): Use online rebuild (default: 1)

**Returns**: Number of indexes rebuilt

#### sp_UpdateAllStatistics
Updates statistics for all core tables.

**Parameters**:
- `@FullScan` (BIT): Use full scan (default: 1)

**Returns**: Number of tables updated

#### sp_CleanupOldLogs
Removes old execution logs in batches.

**Parameters**:
- `@RetentionDays` (INT): Days to retain (default: 30)
- `@BatchSize` (INT): Records per batch (default: 1000)

**Returns**: Number of records deleted

#### sp_CreatePerformanceIndexes
Creates additional performance indexes.

**Parameters**: None

**Returns**: Number of indexes created

#### sp_ComprehensiveMaintenance
Runs all maintenance operations.

**Parameters**:
- `@RebuildIndexes` (BIT): Rebuild indexes (default: 1)
- `@UpdateStatistics` (BIT): Update statistics (default: 1)
- `@CleanupLogs` (BIT): Clean logs (default: 1)
- `@FragmentationThreshold` (FLOAT): Fragmentation threshold (default: 30.0)
- `@LogRetentionDays` (INT): Log retention (default: 30)

**Returns**: Summary of operations

### Monitoring Procedures

#### sp_AnalyzeDatabasePerformance
Generates comprehensive performance analysis.

**Returns**:
- Database size information
- Table size analysis
- Index fragmentation analysis
- Top slow queries

#### sp_DatabaseHealthCheck
Performs health check and returns status.

**Returns**:
- Health score (0-100)
- Health status (EXCELLENT, GOOD, FAIR, POOR, CRITICAL)
- Critical and warning issue counts
- Detailed issue list

#### sp_GetTableStatistics
Returns table size and row count statistics.

**Returns**: Table statistics with size breakdown

## Automated Scheduling

### Default Schedule

The maintenance scheduler includes default tasks:

| Task | Schedule | Operation | Parameters |
|------|----------|-----------|------------|
| daily_log_cleanup | Daily 2:00 AM | Cleanup logs | retention_days: 30 |
| weekly_statistics_update | Sunday 2:00 AM | Update statistics | All tables |
| weekly_index_rebuild | Sunday 3:00 AM | Rebuild indexes | threshold: 30% |
| monthly_optimization | 1st of month 2:00 AM | Create indexes | - |

### Configuration

```python
from shared.database_maintenance_scheduler import create_maintenance_scheduler

scheduler = create_maintenance_scheduler(
    db_handler=db_handler,
    daily_time="02:00",      # HH:MM format
    weekly_day=6,            # 0=Monday, 6=Sunday
    monthly_day=1,           # Day of month (1-28)
    timezone="UTC",
    max_duration_minutes=60,
    enable_online_operations=True
)
```

### Custom Tasks

Add custom maintenance tasks:

```python
from shared.database_maintenance_scheduler import MaintenanceTask, MaintenanceSchedule, MaintenanceType

custom_task = MaintenanceTask(
    name="custom_cleanup",
    operation_type=MaintenanceType.CLEANUP_LOGS,
    schedule=MaintenanceSchedule.DAILY,
    enabled=True,
    parameters={"retention_days": 7},
    last_run=None,
    next_run=None
)

scheduler.add_custom_task(custom_task)
```

### Task Management

```python
# Enable/disable tasks
scheduler.enable_task("daily_log_cleanup")
scheduler.disable_task("monthly_optimization")

# Remove tasks
scheduler.remove_task("custom_cleanup")

# Get task status
status = scheduler.get_task_status()
```

## Azure Function API

### Endpoint

```
POST https://<function-app>.azurewebsites.net/api/maintenance
```

### Authentication

Requires function key in header or query parameter:
```
x-functions-key: <your-function-key>
```

### Operations

#### 1. Health Check

**Request**:
```json
{
  "operation": "health_check"
}
```

**Response**:
```json
{
  "operation": "health_check",
  "timestamp": "2026-01-26T10:00:00Z",
  "result": {
    "status": "GOOD",
    "score": 85,
    "critical_issues": 0,
    "warning_issues": 2,
    "performance_report": {...},
    "next_maintenance": {...}
  }
}
```

#### 2. Run Comprehensive Maintenance

**Request**:
```json
{
  "operation": "run_maintenance",
  "rebuild_indexes": true,
  "update_statistics": true,
  "cleanup_logs": true,
  "create_indexes": true,
  "retention_days": 30
}
```

**Response**:
```json
{
  "operation": "run_maintenance",
  "timestamp": "2026-01-26T10:00:00Z",
  "parameters": {...},
  "results": [
    {
      "operation_type": "create_indexes",
      "success": true,
      "duration_seconds": 45.2,
      "message": "Successfully created 3 new indexes",
      "affected_objects": [...],
      "performance_improvement": {"indexes_created": 3}
    }
  ]
}
```

#### 3. Analyze Indexes

**Request**:
```json
{
  "operation": "analyze_indexes"
}
```

**Response**:
```json
{
  "operation": "analyze_indexes",
  "timestamp": "2026-01-26T10:00:00Z",
  "total_indexes": 25,
  "indexes": [
    {
      "table_name": "news_articles",
      "index_name": "IX_news_articles_published_date",
      "columns": ["published_date"],
      "index_type": "nonclustered",
      "fragmentation_percent": 15.3,
      "size_mb": 245.6,
      "page_count": 31436
    }
  ]
}
```

#### 4. Performance Report

**Request**:
```json
{
  "operation": "performance_report"
}
```

**Response**:
```json
{
  "operation": "performance_report",
  "timestamp": "2026-01-26T10:00:00Z",
  "report": {
    "database_size": {...},
    "index_analysis": {...},
    "query_performance": {...},
    "recommendations": [...]
  }
}
```

### cURL Examples

```bash
# Health check
curl -X POST "https://<function-app>.azurewebsites.net/api/maintenance?code=<key>" \
  -H "Content-Type: application/json" \
  -d '{"operation": "health_check"}'

# Run maintenance
curl -X POST "https://<function-app>.azurewebsites.net/api/maintenance?code=<key>" \
  -H "Content-Type: application/json" \
  -d '{"operation": "run_maintenance", "retention_days": 30}'

# Analyze indexes
curl -X POST "https://<function-app>.azurewebsites.net/api/maintenance?code=<key>" \
  -H "Content-Type: application/json" \
  -d '{"operation": "analyze_indexes"}'
```

## Best Practices

### 1. Scheduling

- **Daily**: Log cleanup (off-peak hours)
- **Weekly**: Statistics update and index rebuild (weekends)
- **Monthly**: Create missing indexes and comprehensive analysis
- **On-Demand**: Performance reports and troubleshooting

### 2. Index Management

- Monitor fragmentation weekly
- Rebuild indexes when fragmentation > 30%
- Use online rebuilds in production
- Set appropriate fill factors (85% for write-heavy, 90% for read-heavy)

### 3. Statistics

- Update statistics after large data imports
- Use FULLSCAN for accurate statistics
- Update weekly for optimal query plans

### 4. Log Retention

- Keep 30 days for operational analysis
- Archive older logs if needed for compliance
- Clean up daily to prevent growth

### 5. Performance Monitoring

- Generate weekly performance reports
- Track slow queries and optimize
- Monitor database size growth
- Set up alerts for critical issues

### 6. Maintenance Windows

- Schedule intensive operations during off-peak hours
- Use online operations when possible
- Set maximum duration limits
- Monitor operation progress

## Troubleshooting

### High Fragmentation

**Symptom**: Queries slowing down, high fragmentation percentage

**Solution**:
```python
# Rebuild fragmented indexes
result = await optimizer.rebuild_fragmented_indexes(
    fragmentation_threshold=20.0  # Lower threshold
)
```

### Slow Queries

**Symptom**: Queries taking longer than expected

**Solution**:
```python
# Analyze slow queries
slow_queries = await optimizer.get_slow_queries(top_n=20)

# Check for missing indexes
result = await optimizer.create_missing_indexes()

# Update statistics
result = await optimizer.update_table_statistics()
```

### Database Size Growth

**Symptom**: Database growing rapidly

**Solution**:
```python
# Get size information
size_info = await optimizer.get_database_size_info()

# Clean up old logs more aggressively
result = await optimizer.cleanup_old_logs(retention_days=7)

# Check table sizes
# EXEC sp_GetTableStatistics
```

### Failed Maintenance Operations

**Symptom**: Maintenance tasks failing

**Solution**:
1. Check database connectivity
2. Verify permissions (ALTER INDEX, UPDATE STATISTICS)
3. Check disk space
4. Review error logs
5. Run health check

```python
# Run health check
health_status = await scheduler.run_health_check()

# Check specific operation
result = await optimizer.rebuild_fragmented_indexes()
if not result.success:
    print(f"Error: {result.message}")
```

### Performance Degradation

**Symptom**: Overall system performance declining

**Solution**:
```python
# Generate comprehensive report
report = await optimizer.generate_performance_report()

# Run comprehensive maintenance
results = await optimizer.run_comprehensive_maintenance()

# Review recommendations
for recommendation in report['recommendations']:
    print(recommendation)
```

## Monitoring and Alerts

### Key Metrics to Monitor

1. **Index Fragmentation**: Alert if > 50%
2. **Query Duration**: Alert if avg > 1000ms
3. **Database Size**: Alert if > 80% capacity
4. **Failed Executions**: Alert if > 10 in 24 hours
5. **Health Score**: Alert if < 50

### Setting Up Alerts

Use Azure Monitor to create alerts based on:
- Custom metrics from Application Insights
- Database performance counters
- Function execution failures
- Health check results

### Example Alert Configuration

```json
{
  "alert_name": "High Index Fragmentation",
  "condition": "fragmentation_percent > 50",
  "severity": "Warning",
  "action": "Run index rebuild maintenance"
}
```

## Conclusion

The database optimization and maintenance system provides comprehensive tools for maintaining optimal database performance. Regular use of these features ensures:

- Fast query performance
- Efficient storage utilization
- Proactive issue detection
- Automated maintenance operations
- Detailed performance insights

For additional support or questions, refer to the main project documentation or contact the development team.
