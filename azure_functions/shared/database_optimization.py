"""
Database optimization utilities for performance monitoring and maintenance.
Provides query optimization, index management, and performance analysis tools.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from .database_handler import DatabaseHandler
from .interfaces import DatabaseError
from .logging_config import get_logger


class IndexType(Enum):
    """Types of database indexes."""
    CLUSTERED = "clustered"
    NONCLUSTERED = "nonclustered"
    UNIQUE = "unique"
    FILTERED = "filtered"
    COLUMNSTORE = "columnstore"


class MaintenanceType(Enum):
    """Types of database maintenance operations."""
    REBUILD_INDEXES = "rebuild_indexes"
    UPDATE_STATISTICS = "update_statistics"
    CLEANUP_LOGS = "cleanup_logs"
    OPTIMIZE_QUERIES = "optimize_queries"
    DEFRAGMENT = "defragment"


@dataclass
class IndexInfo:
    """Information about a database index."""
    table_name: str
    index_name: str
    column_names: List[str]
    index_type: IndexType
    is_unique: bool
    fill_factor: int
    fragmentation_percent: float
    page_count: int
    size_mb: float


@dataclass
class QueryPerformance:
    """Query performance metrics."""
    query_hash: str
    query_text: str
    execution_count: int
    total_duration_ms: int
    avg_duration_ms: float
    total_cpu_time_ms: int
    avg_cpu_time_ms: float
    total_logical_reads: int
    avg_logical_reads: float
    last_execution_time: datetime


@dataclass
class MaintenanceResult:
    """Result of a maintenance operation."""
    operation_type: MaintenanceType
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    success: bool
    message: str
    affected_objects: List[str]
    performance_improvement: Optional[Dict[str, float]]


class DatabaseOptimizer:
    """
    Database optimization and maintenance utilities.
    Provides performance monitoring, index management, and query optimization.
    """
    
    def __init__(self, db_handler: DatabaseHandler):
        """
        Initialize the database optimizer.
        
        Args:
            db_handler: Database handler instance
        """
        self.db_handler = db_handler
        self.logger = get_logger(__name__)
    
    async def analyze_index_usage(self) -> List[IndexInfo]:
        """
        Analyze index usage and fragmentation across all tables.
        
        Returns:
            List of index information with usage statistics
        """
        try:
            query = """
            SELECT 
                t.name AS table_name,
                i.name AS index_name,
                STRING_AGG(c.name, ', ') AS column_names,
                i.type_desc AS index_type,
                i.is_unique,
                i.fill_factor,
                ps.avg_fragmentation_in_percent,
                ps.page_count,
                ps.page_count * 8.0 / 1024 AS size_mb
            FROM sys.tables t
            INNER JOIN sys.indexes i ON t.object_id = i.object_id
            INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
            INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
            CROSS APPLY sys.dm_db_index_physical_stats(DB_ID(), t.object_id, i.index_id, NULL, 'LIMITED') ps
            WHERE i.index_id > 0  -- Exclude heaps
            GROUP BY t.name, i.name, i.type_desc, i.is_unique, i.fill_factor, 
                     ps.avg_fragmentation_in_percent, ps.page_count
            ORDER BY ps.avg_fragmentation_in_percent DESC, ps.page_count DESC
            """
            
            results = await self.db_handler.execute_query(query)
            
            indexes = []
            for row in results:
                index_type_map = {
                    'CLUSTERED': IndexType.CLUSTERED,
                    'NONCLUSTERED': IndexType.NONCLUSTERED,
                    'UNIQUE NONCLUSTERED': IndexType.UNIQUE,
                    'CLUSTERED COLUMNSTORE': IndexType.COLUMNSTORE,
                    'NONCLUSTERED COLUMNSTORE': IndexType.COLUMNSTORE
                }
                
                index_info = IndexInfo(
                    table_name=row['table_name'],
                    index_name=row['index_name'],
                    column_names=row['column_names'].split(', '),
                    index_type=index_type_map.get(row['index_type'], IndexType.NONCLUSTERED),
                    is_unique=row['is_unique'],
                    fill_factor=row['fill_factor'] or 100,
                    fragmentation_percent=row['avg_fragmentation_in_percent'] or 0.0,
                    page_count=row['page_count'] or 0,
                    size_mb=row['size_mb'] or 0.0
                )
                indexes.append(index_info)
            
            self.logger.info(f"Analyzed {len(indexes)} indexes")
            return indexes
            
        except Exception as e:
            self.logger.error(f"Failed to analyze index usage: {str(e)}")
            raise DatabaseError(f"Index analysis failed: {str(e)}")
    
    async def get_slow_queries(self, top_n: int = 20) -> List[QueryPerformance]:
        """
        Get the slowest performing queries.
        
        Args:
            top_n: Number of top slow queries to return
            
        Returns:
            List of query performance metrics
        """
        try:
            query = """
            SELECT TOP (?)
                qs.query_hash,
                SUBSTRING(st.text, (qs.statement_start_offset/2)+1,
                    ((CASE qs.statement_end_offset
                        WHEN -1 THEN DATALENGTH(st.text)
                        ELSE qs.statement_end_offset
                    END - qs.statement_start_offset)/2) + 1) AS query_text,
                qs.execution_count,
                qs.total_elapsed_time / 1000 AS total_duration_ms,
                (qs.total_elapsed_time / qs.execution_count) / 1000 AS avg_duration_ms,
                qs.total_worker_time / 1000 AS total_cpu_time_ms,
                (qs.total_worker_time / qs.execution_count) / 1000 AS avg_cpu_time_ms,
                qs.total_logical_reads,
                qs.total_logical_reads / qs.execution_count AS avg_logical_reads,
                qs.last_execution_time
            FROM sys.dm_exec_query_stats qs
            CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
            WHERE st.text NOT LIKE '%sys.%'  -- Exclude system queries
            ORDER BY qs.total_elapsed_time DESC
            """
            
            results = await self.db_handler.execute_query(query, [top_n])
            
            queries = []
            for row in results:
                query_perf = QueryPerformance(
                    query_hash=str(row['query_hash']),
                    query_text=row['query_text'].strip(),
                    execution_count=row['execution_count'],
                    total_duration_ms=row['total_duration_ms'],
                    avg_duration_ms=row['avg_duration_ms'],
                    total_cpu_time_ms=row['total_cpu_time_ms'],
                    avg_cpu_time_ms=row['avg_cpu_time_ms'],
                    total_logical_reads=row['total_logical_reads'],
                    avg_logical_reads=row['avg_logical_reads'],
                    last_execution_time=row['last_execution_time']
                )
                queries.append(query_perf)
            
            self.logger.info(f"Retrieved {len(queries)} slow queries")
            return queries
            
        except Exception as e:
            self.logger.error(f"Failed to get slow queries: {str(e)}")
            raise DatabaseError(f"Slow query analysis failed: {str(e)}")
    
    async def rebuild_fragmented_indexes(self, fragmentation_threshold: float = 30.0) -> MaintenanceResult:
        """
        Rebuild indexes that exceed the fragmentation threshold.
        
        Args:
            fragmentation_threshold: Minimum fragmentation percentage to trigger rebuild
            
        Returns:
            Maintenance operation result
        """
        start_time = datetime.utcnow()
        affected_objects = []
        
        try:
            # Get fragmented indexes
            indexes = await self.analyze_index_usage()
            fragmented_indexes = [
                idx for idx in indexes 
                if idx.fragmentation_percent >= fragmentation_threshold and idx.page_count > 1000
            ]
            
            if not fragmented_indexes:
                return MaintenanceResult(
                    operation_type=MaintenanceType.REBUILD_INDEXES,
                    start_time=start_time,
                    end_time=datetime.utcnow(),
                    duration_seconds=0.0,
                    success=True,
                    message="No indexes require rebuilding",
                    affected_objects=[],
                    performance_improvement=None
                )
            
            # Rebuild each fragmented index
            for index in fragmented_indexes:
                try:
                    rebuild_query = f"""
                    ALTER INDEX [{index.index_name}] ON [{index.table_name}] 
                    REBUILD WITH (FILLFACTOR = {max(index.fill_factor, 80)}, ONLINE = ON)
                    """
                    
                    await self.db_handler.execute_query(rebuild_query)
                    affected_objects.append(f"{index.table_name}.{index.index_name}")
                    
                    self.logger.info(
                        f"Rebuilt index {index.index_name} on {index.table_name} "
                        f"(was {index.fragmentation_percent:.1f}% fragmented)"
                    )
                    
                except Exception as e:
                    self.logger.warning(f"Failed to rebuild index {index.index_name}: {str(e)}")
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            return MaintenanceResult(
                operation_type=MaintenanceType.REBUILD_INDEXES,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                success=True,
                message=f"Successfully rebuilt {len(affected_objects)} indexes",
                affected_objects=affected_objects,
                performance_improvement={"indexes_rebuilt": len(affected_objects)}
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.error(f"Index rebuild operation failed: {str(e)}")
            return MaintenanceResult(
                operation_type=MaintenanceType.REBUILD_INDEXES,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                success=False,
                message=f"Index rebuild failed: {str(e)}",
                affected_objects=affected_objects,
                performance_improvement=None
            )
    
    async def update_table_statistics(self, table_names: Optional[List[str]] = None) -> MaintenanceResult:
        """
        Update statistics for specified tables or all tables.
        
        Args:
            table_names: List of table names to update, or None for all tables
            
        Returns:
            Maintenance operation result
        """
        start_time = datetime.utcnow()
        affected_objects = []
        
        try:
            # Get table names if not specified
            if table_names is None:
                table_query = """
                SELECT name FROM sys.tables 
                WHERE name IN ('news_articles', 'sentiment_analyses', 'execution_logs', 
                              'article_keywords', 'news_sources', 'keywords')
                """
                results = await self.db_handler.execute_query(table_query)
                table_names = [row['name'] for row in results]
            
            # Update statistics for each table
            for table_name in table_names:
                try:
                    update_query = f"UPDATE STATISTICS [{table_name}] WITH FULLSCAN"
                    await self.db_handler.execute_query(update_query)
                    affected_objects.append(table_name)
                    
                    self.logger.info(f"Updated statistics for table {table_name}")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to update statistics for {table_name}: {str(e)}")
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            return MaintenanceResult(
                operation_type=MaintenanceType.UPDATE_STATISTICS,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                success=True,
                message=f"Successfully updated statistics for {len(affected_objects)} tables",
                affected_objects=affected_objects,
                performance_improvement={"tables_updated": len(affected_objects)}
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.error(f"Statistics update operation failed: {str(e)}")
            return MaintenanceResult(
                operation_type=MaintenanceType.UPDATE_STATISTICS,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                success=False,
                message=f"Statistics update failed: {str(e)}",
                affected_objects=affected_objects,
                performance_improvement=None
            )
    
    async def cleanup_old_logs(self, retention_days: int = 30) -> MaintenanceResult:
        """
        Clean up old execution logs and temporary data.
        
        Args:
            retention_days: Number of days to retain logs
            
        Returns:
            Maintenance operation result
        """
        start_time = datetime.utcnow()
        affected_objects = []
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            # Clean up execution logs
            cleanup_query = """
            DELETE FROM execution_logs 
            WHERE created_at < ? AND status IN ('success', 'failed')
            """
            
            deleted_count = await self.db_handler.execute_query(cleanup_query, [cutoff_date])
            affected_objects.append(f"execution_logs ({deleted_count} records)")
            
            # Clean up old sentiment analyses (optional - keep for historical analysis)
            # This could be made configurable based on business requirements
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            return MaintenanceResult(
                operation_type=MaintenanceType.CLEANUP_LOGS,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                success=True,
                message=f"Successfully cleaned up {deleted_count} old log records",
                affected_objects=affected_objects,
                performance_improvement={"records_deleted": deleted_count}
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.error(f"Log cleanup operation failed: {str(e)}")
            return MaintenanceResult(
                operation_type=MaintenanceType.CLEANUP_LOGS,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                success=False,
                message=f"Log cleanup failed: {str(e)}",
                affected_objects=affected_objects,
                performance_improvement=None
            )
    
    async def get_database_size_info(self) -> Dict[str, Any]:
        """
        Get database size and space usage information.
        
        Returns:
            Dictionary with database size metrics
        """
        try:
            size_query = """
            SELECT 
                DB_NAME() AS database_name,
                SUM(CASE WHEN type = 0 THEN size END) * 8 / 1024 AS data_size_mb,
                SUM(CASE WHEN type = 1 THEN size END) * 8 / 1024 AS log_size_mb,
                SUM(size) * 8 / 1024 AS total_size_mb
            FROM sys.master_files
            WHERE database_id = DB_ID()
            """
            
            size_result = await self.db_handler.execute_query(size_query)
            
            # Get table sizes
            table_size_query = """
            SELECT 
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
            ORDER BY SUM(a.total_pages) DESC
            """
            
            table_results = await self.db_handler.execute_query(table_size_query)
            
            return {
                "database_info": size_result[0] if size_result else {},
                "table_sizes": table_results,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get database size info: {str(e)}")
            raise DatabaseError(f"Database size analysis failed: {str(e)}")
    
    async def create_missing_indexes(self) -> MaintenanceResult:
        """
        Create additional performance indexes based on query patterns.
        
        Returns:
            Maintenance operation result
        """
        start_time = datetime.utcnow()
        affected_objects = []
        
        try:
            # Define additional indexes for performance optimization
            additional_indexes = [
                # Composite indexes for common query patterns
                {
                    "table": "news_articles",
                    "name": "IX_news_articles_source_published_scraped",
                    "columns": ["source_id", "published_date DESC", "scraped_date DESC"],
                    "description": "Optimize source-based date range queries"
                },
                {
                    "table": "news_articles", 
                    "name": "IX_news_articles_language_category",
                    "columns": ["language", "category"],
                    "description": "Optimize filtering by language and category"
                },
                {
                    "table": "sentiment_analyses",
                    "name": "IX_sentiment_analyses_label_confidence",
                    "columns": ["sentiment_label", "confidence DESC"],
                    "description": "Optimize sentiment filtering and ranking"
                },
                {
                    "table": "execution_logs",
                    "name": "IX_execution_logs_function_status_time",
                    "columns": ["function_name", "status", "start_time DESC"],
                    "description": "Optimize function performance monitoring"
                },
                {
                    "table": "article_keywords",
                    "name": "IX_article_keywords_keyword_relevance",
                    "columns": ["keyword_id", "relevance_score DESC"],
                    "description": "Optimize keyword-based article searches"
                }
            ]
            
            for index_def in additional_indexes:
                try:
                    # Check if index already exists
                    check_query = """
                    SELECT COUNT(*) as count FROM sys.indexes 
                    WHERE object_id = OBJECT_ID(?) AND name = ?
                    """
                    
                    exists_result = await self.db_handler.execute_query(
                        check_query, [index_def["table"], index_def["name"]]
                    )
                    
                    if exists_result[0]["count"] == 0:
                        # Create the index
                        columns_str = ", ".join(index_def["columns"])
                        create_query = f"""
                        CREATE NONCLUSTERED INDEX [{index_def["name"]}] 
                        ON [{index_def["table"]}] ({columns_str})
                        WITH (FILLFACTOR = 85, ONLINE = ON)
                        """
                        
                        await self.db_handler.execute_query(create_query)
                        affected_objects.append(f"{index_def['table']}.{index_def['name']}")
                        
                        self.logger.info(
                            f"Created index {index_def['name']} on {index_def['table']}: "
                            f"{index_def['description']}"
                        )
                    else:
                        self.logger.info(f"Index {index_def['name']} already exists")
                        
                except Exception as e:
                    self.logger.warning(f"Failed to create index {index_def['name']}: {str(e)}")
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            return MaintenanceResult(
                operation_type=MaintenanceType.OPTIMIZE_QUERIES,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                success=True,
                message=f"Successfully created {len(affected_objects)} new indexes",
                affected_objects=affected_objects,
                performance_improvement={"indexes_created": len(affected_objects)}
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.error(f"Index creation operation failed: {str(e)}")
            return MaintenanceResult(
                operation_type=MaintenanceType.OPTIMIZE_QUERIES,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                success=False,
                message=f"Index creation failed: {str(e)}",
                affected_objects=affected_objects,
                performance_improvement=None
            )
    
    async def run_comprehensive_maintenance(
        self, 
        rebuild_indexes: bool = True,
        update_statistics: bool = True,
        cleanup_logs: bool = True,
        create_indexes: bool = True,
        retention_days: int = 30
    ) -> List[MaintenanceResult]:
        """
        Run comprehensive database maintenance operations.
        
        Args:
            rebuild_indexes: Whether to rebuild fragmented indexes
            update_statistics: Whether to update table statistics
            cleanup_logs: Whether to clean up old logs
            create_indexes: Whether to create missing indexes
            retention_days: Log retention period in days
            
        Returns:
            List of maintenance operation results
        """
        results = []
        
        self.logger.info("Starting comprehensive database maintenance")
        
        try:
            # Create missing indexes first
            if create_indexes:
                result = await self.create_missing_indexes()
                results.append(result)
            
            # Update statistics
            if update_statistics:
                result = await self.update_table_statistics()
                results.append(result)
            
            # Rebuild fragmented indexes
            if rebuild_indexes:
                result = await self.rebuild_fragmented_indexes()
                results.append(result)
            
            # Clean up old logs
            if cleanup_logs:
                result = await self.cleanup_old_logs(retention_days)
                results.append(result)
            
            successful_operations = sum(1 for r in results if r.success)
            self.logger.info(
                f"Comprehensive maintenance completed: {successful_operations}/{len(results)} operations successful"
            )
            
        except Exception as e:
            self.logger.error(f"Comprehensive maintenance failed: {str(e)}")
            raise DatabaseError(f"Maintenance operation failed: {str(e)}")
        
        return results
    
    async def generate_performance_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive database performance report.
        
        Returns:
            Dictionary containing performance analysis results
        """
        try:
            self.logger.info("Generating database performance report")
            
            # Get index analysis
            indexes = await self.analyze_index_usage()
            
            # Get slow queries
            slow_queries = await self.get_slow_queries(10)
            
            # Get database size info
            size_info = await self.get_database_size_info()
            
            # Calculate summary statistics
            fragmented_indexes = [idx for idx in indexes if idx.fragmentation_percent > 30]
            large_indexes = [idx for idx in indexes if idx.size_mb > 100]
            
            report = {
                "report_timestamp": datetime.utcnow().isoformat(),
                "database_size": size_info,
                "index_analysis": {
                    "total_indexes": len(indexes),
                    "fragmented_indexes": len(fragmented_indexes),
                    "large_indexes": len(large_indexes),
                    "avg_fragmentation": sum(idx.fragmentation_percent for idx in indexes) / len(indexes) if indexes else 0,
                    "most_fragmented": [
                        {
                            "table": idx.table_name,
                            "index": idx.index_name,
                            "fragmentation": idx.fragmentation_percent,
                            "size_mb": idx.size_mb
                        }
                        for idx in sorted(indexes, key=lambda x: x.fragmentation_percent, reverse=True)[:5]
                    ]
                },
                "query_performance": {
                    "slow_queries_analyzed": len(slow_queries),
                    "slowest_queries": [
                        {
                            "query_text": q.query_text[:200] + "..." if len(q.query_text) > 200 else q.query_text,
                            "execution_count": q.execution_count,
                            "avg_duration_ms": q.avg_duration_ms,
                            "avg_cpu_time_ms": q.avg_cpu_time_ms,
                            "avg_logical_reads": q.avg_logical_reads
                        }
                        for q in slow_queries[:5]
                    ]
                },
                "recommendations": self._generate_recommendations(indexes, slow_queries)
            }
            
            self.logger.info("Performance report generated successfully")
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate performance report: {str(e)}")
            raise DatabaseError(f"Performance report generation failed: {str(e)}")
    
    def _generate_recommendations(self, indexes: List[IndexInfo], slow_queries: List[QueryPerformance]) -> List[str]:
        """Generate performance recommendations based on analysis."""
        recommendations = []
        
        # Index recommendations
        fragmented_indexes = [idx for idx in indexes if idx.fragmentation_percent > 30]
        if fragmented_indexes:
            recommendations.append(
                f"Rebuild {len(fragmented_indexes)} fragmented indexes (>30% fragmentation)"
            )
        
        # Query recommendations
        if slow_queries:
            avg_duration = sum(q.avg_duration_ms for q in slow_queries) / len(slow_queries)
            if avg_duration > 1000:  # 1 second
                recommendations.append(
                    f"Optimize slow queries - average duration is {avg_duration:.0f}ms"
                )
        
        # Size recommendations
        large_indexes = [idx for idx in indexes if idx.size_mb > 500]
        if large_indexes:
            recommendations.append(
                f"Consider partitioning or archiving for {len(large_indexes)} large indexes (>500MB)"
            )
        
        # General recommendations
        recommendations.extend([
            "Update statistics weekly for optimal query performance",
            "Monitor index fragmentation monthly",
            "Clean up old execution logs regularly",
            "Consider implementing query result caching for frequently accessed data"
        ])
        
        return recommendations