"""
Azure Function for deduplicating news articles.
HTTP-triggered function that removes duplicate articles based on URL.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

import azure.functions as func

from ..shared.database_handler import DatabaseHandler, create_database_handler
from ..shared.models import DatabaseConfig, ExecutionResult, FunctionStatus
from ..shared.config import get_database_config
from ..shared.logging_config import get_logger
from ..shared.interfaces import DatabaseError


async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP-triggered Azure Function for deduplicating news articles.
    
    This function removes duplicate articles from the database based on URL uniqueness,
    maintaining the existing deduplication logic from the original system.
    
    Query Parameters:
        - dry_run (optional): If 'true', returns count of duplicates without removing them
        - source (optional): Limit deduplication to specific news source
    
    Returns:
        JSON response with deduplication results
    """
    logger = get_logger(__name__)
    start_time = datetime.utcnow()
    execution_id = f"dedup_{int(start_time.timestamp())}"
    
    # Parse request parameters
    dry_run = req.params.get('dry_run', '').lower() == 'true'
    source_filter = req.params.get('source')
    
    logger.info(f"Starting deduplication function - execution_id: {execution_id}")
    logger.info(f"Parameters: dry_run={dry_run}, source_filter={source_filter}")
    
    db_handler = None
    
    try:
        # Initialize database handler
        db_config = await get_database_config()
        db_handler = await create_database_handler(db_config)
        
        # Perform deduplication
        if dry_run:
            # Count duplicates without removing them
            duplicate_count = await count_duplicate_articles(db_handler, source_filter)
            result = {
                "success": True,
                "dry_run": True,
                "duplicate_count": duplicate_count,
                "duplicates_removed": 0,
                "message": f"Found {duplicate_count} duplicate articles (dry run - no articles removed)"
            }
        else:
            # Remove duplicates
            if source_filter:
                duplicates_removed = await deduplicate_articles_by_source(db_handler, source_filter)
            else:
                duplicates_removed = await db_handler.deduplicate_articles()
            
            result = {
                "success": True,
                "dry_run": False,
                "duplicates_removed": duplicates_removed,
                "message": f"Successfully removed {duplicates_removed} duplicate articles"
            }
        
        # Log execution result
        end_time = datetime.utcnow()
        execution_result = ExecutionResult(
            function_name="deduplication_function",
            execution_id=execution_id,
            status=FunctionStatus.SUCCESS,
            start_time=start_time,
            end_time=end_time,
            input_parameters={
                "dry_run": dry_run,
                "source_filter": source_filter
            },
            output_summary=result
        )
        
        await db_handler.save_execution_log(execution_result)
        
        logger.info(f"Deduplication completed successfully: {result}")
        
        return func.HttpResponse(
            json.dumps(result, default=str),
            status_code=200,
            mimetype="application/json"
        )
        
    except DatabaseError as e:
        error_msg = f"Database error during deduplication: {str(e)}"
        logger.error(error_msg)
        
        # Log execution error
        if db_handler:
            try:
                end_time = datetime.utcnow()
                execution_result = ExecutionResult(
                    function_name="deduplication_function",
                    execution_id=execution_id,
                    status=FunctionStatus.FAILED,
                    start_time=start_time,
                    end_time=end_time,
                    error_message=error_msg,
                    input_parameters={
                        "dry_run": dry_run,
                        "source_filter": source_filter
                    }
                )
                await db_handler.save_execution_log(execution_result)
            except Exception as log_error:
                logger.error(f"Failed to log execution error: {str(log_error)}")
        
        return func.HttpResponse(
            json.dumps({
                "success": False,
                "error": "Database operation failed",
                "message": error_msg
            }),
            status_code=500,
            mimetype="application/json"
        )
        
    except Exception as e:
        error_msg = f"Unexpected error during deduplication: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Log execution error
        if db_handler:
            try:
                end_time = datetime.utcnow()
                execution_result = ExecutionResult(
                    function_name="deduplication_function",
                    execution_id=execution_id,
                    status=FunctionStatus.FAILED,
                    start_time=start_time,
                    end_time=end_time,
                    error_message=error_msg,
                    input_parameters={
                        "dry_run": dry_run,
                        "source_filter": source_filter
                    }
                )
                await db_handler.save_execution_log(execution_result)
            except Exception as log_error:
                logger.error(f"Failed to log execution error: {str(log_error)}")
        
        return func.HttpResponse(
            json.dumps({
                "success": False,
                "error": "Internal server error",
                "message": "An unexpected error occurred during deduplication"
            }),
            status_code=500,
            mimetype="application/json"
        )
        
    finally:
        # Clean up database connection
        if db_handler:
            try:
                await db_handler.close()
            except Exception as e:
                logger.warning(f"Error closing database handler: {str(e)}")


async def count_duplicate_articles(db_handler: DatabaseHandler, source_filter: Optional[str] = None) -> int:
    """
    Count duplicate articles without removing them.
    
    Args:
        db_handler: Database handler instance
        source_filter: Optional source name to filter by
        
    Returns:
        Number of duplicate articles found
    """
    logger = get_logger(__name__)
    
    try:
        # Build query to count duplicates
        if source_filter:
            query = """
            SELECT COUNT(*) - COUNT(DISTINCT a.url) as duplicate_count
            FROM news_articles a
            INNER JOIN news_sources s ON a.source_id = s.id
            WHERE s.name = ?
            """
            params = [source_filter]
        else:
            query = """
            SELECT COUNT(*) - COUNT(DISTINCT url) as duplicate_count
            FROM news_articles
            """
            params = None
        
        result = await db_handler.execute_query(query, params)
        duplicate_count = result[0]['duplicate_count'] if result else 0
        
        logger.info(f"Found {duplicate_count} duplicate articles")
        return duplicate_count
        
    except Exception as e:
        logger.error(f"Error counting duplicate articles: {str(e)}")
        raise DatabaseError(f"Failed to count duplicates: {str(e)}")


async def deduplicate_articles_by_source(db_handler: DatabaseHandler, source_name: str) -> int:
    """
    Remove duplicate articles for a specific news source.
    
    Args:
        db_handler: Database handler instance
        source_name: Name of the news source to deduplicate
        
    Returns:
        Number of duplicate articles removed
    """
    logger = get_logger(__name__)
    
    try:
        # Custom deduplication query for specific source
        query = """
        WITH DuplicateArticles AS (
            SELECT a.id, a.url, a.scraped_date,
                   ROW_NUMBER() OVER (PARTITION BY a.url ORDER BY a.scraped_date ASC) as rn
            FROM news_articles a
            INNER JOIN news_sources s ON a.source_id = s.id
            WHERE s.name = ?
        )
        DELETE FROM news_articles 
        WHERE id IN (
            SELECT id FROM DuplicateArticles WHERE rn > 1
        )
        """
        
        deleted_count = await db_handler.execute_query(query, [source_name])
        
        logger.info(f"Removed {deleted_count} duplicate articles for source: {source_name}")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error deduplicating articles for source {source_name}: {str(e)}")
        raise DatabaseError(f"Failed to deduplicate articles for source: {str(e)}")


async def get_duplicate_statistics(db_handler: DatabaseHandler) -> Dict[str, Any]:
    """
    Get detailed statistics about duplicate articles.
    
    Args:
        db_handler: Database handler instance
        
    Returns:
        Dictionary with duplicate statistics
    """
    logger = get_logger(__name__)
    
    try:
        # Query for duplicate statistics by source
        query = """
        SELECT 
            s.name as source_name,
            COUNT(a.id) as total_articles,
            COUNT(DISTINCT a.url) as unique_urls,
            COUNT(a.id) - COUNT(DISTINCT a.url) as duplicates
        FROM news_articles a
        INNER JOIN news_sources s ON a.source_id = s.id
        GROUP BY s.name
        HAVING COUNT(a.id) > COUNT(DISTINCT a.url)
        ORDER BY duplicates DESC
        """
        
        results = await db_handler.execute_query(query)
        
        # Calculate totals
        total_articles = sum(row['total_articles'] for row in results)
        total_unique = sum(row['unique_urls'] for row in results)
        total_duplicates = sum(row['duplicates'] for row in results)
        
        statistics = {
            "total_articles": total_articles,
            "unique_articles": total_unique,
            "total_duplicates": total_duplicates,
            "duplicate_percentage": round((total_duplicates / total_articles * 100), 2) if total_articles > 0 else 0,
            "sources_with_duplicates": len(results),
            "by_source": results
        }
        
        logger.info(f"Duplicate statistics: {statistics}")
        return statistics
        
    except Exception as e:
        logger.error(f"Error getting duplicate statistics: {str(e)}")
        raise DatabaseError(f"Failed to get duplicate statistics: {str(e)}")