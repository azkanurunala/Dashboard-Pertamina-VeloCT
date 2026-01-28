"""
Deduplication service for news articles.
Provides comprehensive deduplication functionality maintaining existing logic from the original system.
"""

import logging
import sys
import os
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

# Add parent directory to Python path for absolute imports in Azure Functions
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from shared.database_handler import DatabaseHandler
from shared.models import NewsArticle, ArticleFilters
from shared.interfaces import DatabaseError
from shared.logging_config import get_logger


@dataclass
class DeduplicationResult:
    """Result of a deduplication operation."""
    duplicates_removed: int
    unique_articles_remaining: int
    processing_time_seconds: float
    source_breakdown: Dict[str, int]
    errors: List[str]


@dataclass
class DeduplicationStats:
    """Statistics about duplicate articles."""
    total_articles: int
    unique_articles: int
    duplicate_count: int
    duplicate_percentage: float
    sources_with_duplicates: int
    by_source: List[Dict[str, Any]]


class DeduplicationService:
    """
    Service class for handling news article deduplication.
    
    Maintains the existing deduplication logic from the original system:
    - URL-based deduplication (primary method)
    - Keeps earliest scraped article when duplicates found
    - Supports source-specific deduplication
    - Provides detailed statistics and reporting
    """
    
    def __init__(self, db_handler: DatabaseHandler):
        """
        Initialize the deduplication service.
        
        Args:
            db_handler: Database handler instance
        """
        self.db_handler = db_handler
        self.logger = get_logger(__name__)
    
    async def deduplicate_all_articles(self) -> DeduplicationResult:
        """
        Remove all duplicate articles from the database.
        
        Uses the existing stored procedure for optimal performance.
        
        Returns:
            DeduplicationResult with operation details
        """
        start_time = datetime.utcnow()
        
        try:
            self.logger.info("Starting full article deduplication")
            
            # Get statistics before deduplication
            stats_before = await self.get_duplicate_statistics()
            
            # Perform deduplication using stored procedure
            duplicates_removed = await self.db_handler.deduplicate_articles()
            
            # Get statistics after deduplication
            stats_after = await self.get_duplicate_statistics()
            
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            result = DeduplicationResult(
                duplicates_removed=duplicates_removed,
                unique_articles_remaining=stats_after.unique_articles,
                processing_time_seconds=processing_time,
                source_breakdown=self._calculate_source_breakdown(stats_before, stats_after),
                errors=[]
            )
            
            self.logger.info(f"Deduplication completed: {duplicates_removed} duplicates removed in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            error_msg = f"Error during full deduplication: {str(e)}"
            self.logger.error(error_msg)
            
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            return DeduplicationResult(
                duplicates_removed=0,
                unique_articles_remaining=0,
                processing_time_seconds=processing_time,
                source_breakdown={},
                errors=[error_msg]
            )
    
    async def deduplicate_by_source(self, source_name: str) -> DeduplicationResult:
        """
        Remove duplicate articles for a specific news source.
        
        Args:
            source_name: Name of the news source to deduplicate
            
        Returns:
            DeduplicationResult with operation details
        """
        start_time = datetime.utcnow()
        
        try:
            self.logger.info(f"Starting deduplication for source: {source_name}")
            
            # Get source-specific statistics before deduplication
            stats_before = await self._get_source_duplicate_count(source_name)
            
            # Perform source-specific deduplication
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
            
            duplicates_removed = await self.db_handler.execute_query(query, [source_name])
            
            # Get statistics after deduplication
            stats_after = await self._get_source_duplicate_count(source_name)
            
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            result = DeduplicationResult(
                duplicates_removed=duplicates_removed,
                unique_articles_remaining=stats_after,
                processing_time_seconds=processing_time,
                source_breakdown={source_name: duplicates_removed},
                errors=[]
            )
            
            self.logger.info(f"Source deduplication completed: {duplicates_removed} duplicates removed for {source_name}")
            return result
            
        except Exception as e:
            error_msg = f"Error during source deduplication for {source_name}: {str(e)}"
            self.logger.error(error_msg)
            
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            return DeduplicationResult(
                duplicates_removed=0,
                unique_articles_remaining=0,
                processing_time_seconds=processing_time,
                source_breakdown={},
                errors=[error_msg]
            )
    
    async def deduplicate_by_date_range(self, start_date: datetime, end_date: datetime) -> DeduplicationResult:
        """
        Remove duplicate articles within a specific date range.
        
        Args:
            start_date: Start of date range for deduplication
            end_date: End of date range for deduplication
            
        Returns:
            DeduplicationResult with operation details
        """
        start_time = datetime.utcnow()
        
        try:
            self.logger.info(f"Starting deduplication for date range: {start_date} to {end_date}")
            
            # Perform date-range specific deduplication
            query = """
            WITH DuplicateArticles AS (
                SELECT id, url, scraped_date,
                       ROW_NUMBER() OVER (PARTITION BY url ORDER BY scraped_date ASC) as rn
                FROM news_articles
                WHERE scraped_date >= ? AND scraped_date <= ?
            )
            DELETE FROM news_articles 
            WHERE id IN (
                SELECT id FROM DuplicateArticles WHERE rn > 1
            )
            """
            
            duplicates_removed = await self.db_handler.execute_query(query, [start_date, end_date])
            
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            result = DeduplicationResult(
                duplicates_removed=duplicates_removed,
                unique_articles_remaining=0,  # Would need additional query to calculate
                processing_time_seconds=processing_time,
                source_breakdown={},
                errors=[]
            )
            
            self.logger.info(f"Date range deduplication completed: {duplicates_removed} duplicates removed")
            return result
            
        except Exception as e:
            error_msg = f"Error during date range deduplication: {str(e)}"
            self.logger.error(error_msg)
            
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            return DeduplicationResult(
                duplicates_removed=0,
                unique_articles_remaining=0,
                processing_time_seconds=processing_time,
                source_breakdown={},
                errors=[error_msg]
            )
    
    async def get_duplicate_statistics(self) -> DeduplicationStats:
        """
        Get comprehensive statistics about duplicate articles.
        
        Returns:
            DeduplicationStats with detailed information
        """
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
            ORDER BY duplicates DESC
            """
            
            results = await self.db_handler.execute_query(query)
            
            # Calculate totals
            total_articles = sum(row['total_articles'] for row in results)
            total_unique = sum(row['unique_urls'] for row in results)
            total_duplicates = sum(row['duplicates'] for row in results)
            sources_with_duplicates = len([row for row in results if row['duplicates'] > 0])
            
            stats = DeduplicationStats(
                total_articles=total_articles,
                unique_articles=total_unique,
                duplicate_count=total_duplicates,
                duplicate_percentage=round((total_duplicates / total_articles * 100), 2) if total_articles > 0 else 0,
                sources_with_duplicates=sources_with_duplicates,
                by_source=results
            )
            
            self.logger.info(f"Duplicate statistics calculated: {total_duplicates} duplicates out of {total_articles} articles")
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting duplicate statistics: {str(e)}")
            raise DatabaseError(f"Failed to get duplicate statistics: {str(e)}")
    
    async def find_duplicate_urls(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find URLs that have duplicate articles.
        
        Args:
            limit: Maximum number of duplicate URLs to return
            
        Returns:
            List of dictionaries with URL and duplicate count information
        """
        try:
            query = """
            SELECT 
                url,
                COUNT(*) as duplicate_count,
                MIN(scraped_date) as first_scraped,
                MAX(scraped_date) as last_scraped,
                STRING_AGG(s.name, ', ') as sources
            FROM news_articles a
            INNER JOIN news_sources s ON a.source_id = s.id
            GROUP BY url
            HAVING COUNT(*) > 1
            ORDER BY duplicate_count DESC, first_scraped DESC
            OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
            """
            
            results = await self.db_handler.execute_query(query, [limit])
            
            self.logger.info(f"Found {len(results)} URLs with duplicates")
            return results
            
        except Exception as e:
            self.logger.error(f"Error finding duplicate URLs: {str(e)}")
            raise DatabaseError(f"Failed to find duplicate URLs: {str(e)}")
    
    async def preview_deduplication(self, source_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Preview what would be removed in a deduplication operation without actually removing anything.
        
        Args:
            source_name: Optional source name to filter by
            
        Returns:
            Dictionary with preview information
        """
        try:
            if source_name:
                query = """
                WITH DuplicateArticles AS (
                    SELECT a.id, a.url, a.title, a.scraped_date, s.name as source,
                           ROW_NUMBER() OVER (PARTITION BY a.url ORDER BY a.scraped_date ASC) as rn
                    FROM news_articles a
                    INNER JOIN news_sources s ON a.source_id = s.id
                    WHERE s.name = ?
                )
                SELECT id, url, title, scraped_date, source
                FROM DuplicateArticles 
                WHERE rn > 1
                ORDER BY url, scraped_date
                """
                params = [source_name]
            else:
                query = """
                WITH DuplicateArticles AS (
                    SELECT a.id, a.url, a.title, a.scraped_date, s.name as source,
                           ROW_NUMBER() OVER (PARTITION BY a.url ORDER BY a.scraped_date ASC) as rn
                    FROM news_articles a
                    INNER JOIN news_sources s ON a.source_id = s.id
                )
                SELECT id, url, title, scraped_date, source
                FROM DuplicateArticles 
                WHERE rn > 1
                ORDER BY url, scraped_date
                """
                params = None
            
            results = await self.db_handler.execute_query(query, params)
            
            # Group by URL for better presentation
            grouped_results = {}
            for row in results:
                url = row['url']
                if url not in grouped_results:
                    grouped_results[url] = []
                grouped_results[url].append({
                    'id': row['id'],
                    'title': row['title'],
                    'scraped_date': row['scraped_date'],
                    'source': row['source']
                })
            
            preview = {
                'total_duplicates_to_remove': len(results),
                'unique_urls_with_duplicates': len(grouped_results),
                'duplicates_by_url': grouped_results,
                'source_filter': source_name
            }
            
            self.logger.info(f"Deduplication preview: {len(results)} articles would be removed")
            return preview
            
        except Exception as e:
            self.logger.error(f"Error creating deduplication preview: {str(e)}")
            raise DatabaseError(f"Failed to create deduplication preview: {str(e)}")
    
    async def _get_source_duplicate_count(self, source_name: str) -> int:
        """Get the count of unique articles for a specific source."""
        try:
            query = """
            SELECT COUNT(DISTINCT url) as unique_count
            FROM news_articles a
            INNER JOIN news_sources s ON a.source_id = s.id
            WHERE s.name = ?
            """
            
            result = await self.db_handler.execute_query(query, [source_name])
            return result[0]['unique_count'] if result else 0
            
        except Exception as e:
            self.logger.error(f"Error getting source duplicate count: {str(e)}")
            return 0
    
    def _calculate_source_breakdown(self, stats_before: DeduplicationStats, stats_after: DeduplicationStats) -> Dict[str, int]:
        """Calculate the breakdown of duplicates removed by source."""
        breakdown = {}
        
        # Create lookup for before stats
        before_lookup = {row['source_name']: row['duplicates'] for row in stats_before.by_source}
        after_lookup = {row['source_name']: row['duplicates'] for row in stats_after.by_source}
        
        # Calculate difference for each source
        for source_name in before_lookup:
            before_count = before_lookup.get(source_name, 0)
            after_count = after_lookup.get(source_name, 0)
            removed = before_count - after_count
            if removed > 0:
                breakdown[source_name] = removed
        
        return breakdown