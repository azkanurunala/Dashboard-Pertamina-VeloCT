"""
Database handler implementation for SQL Server operations.
Provides connection pooling, retry logic, and comprehensive database operations.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import json
import uuid
from contextlib import asynccontextmanager

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False
    pyodbc = None

try:
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    DefaultAzureCredential = None
    SecretClient = None

from .models import (
    NewsArticle, SentimentAnalysis, DatabaseConfig, ArticleFilters, 
    DateRange, ExecutionResult, FunctionStatus
)
from .interfaces import IDatabaseHandler, DatabaseError
from .logging_config import get_logger


class DatabaseHandler(IDatabaseHandler):
    """
    SQL Server database handler with connection pooling and retry logic.
    Implements the IDatabaseHandler interface for all database operations.
    """
    
    def __init__(self, config: DatabaseConfig):
        """
        Initialize the database handler.
        
        Args:
            config: Database configuration
        """
        if not PYODBC_AVAILABLE:
            raise DatabaseError("pyodbc library is required for SQL Server operations")
            
        self.config = config
        self.logger = get_logger(__name__)
        self._connection_pool: Optional[Any] = None
        self._pool_lock = asyncio.Lock()
        
    async def _get_connection_pool(self):
        """Get or create the connection pool."""
        if self._connection_pool is None:
            async with self._pool_lock:
                if self._connection_pool is None:
                    try:
                        # For SQL Server, we'll use a simple connection approach
                        # In production, consider using aioodbc or similar async library
                        self._connection_pool = {
                            'connection_string': self.config.connection_string,
                            'pool_size': self.config.connection_pool_size,
                            'timeout': self.config.connection_timeout
                        }
                        self.logger.info("Database connection pool initialized")
                    except Exception as e:
                        self.logger.error(f"Failed to initialize connection pool: {str(e)}")
                        raise DatabaseError(f"Connection pool initialization failed: {str(e)}")
        
        return self._connection_pool
    
    @asynccontextmanager
    async def _get_connection(self):
        """Get a database connection with automatic cleanup."""
        connection = None
        try:
            await self._get_connection_pool()
            
            # Create connection using pyodbc
            connection = pyodbc.connect(
                self.config.connection_string,
                timeout=self.config.connection_timeout
            )
            connection.timeout = self.config.command_timeout
            
            yield connection
            
        except Exception as e:
            self.logger.error(f"Database connection error: {str(e)}")
            raise DatabaseError(f"Database connection failed: {str(e)}")
        finally:
            if connection:
                try:
                    connection.close()
                except Exception as e:
                    self.logger.warning(f"Error closing connection: {str(e)}")
    
    async def _execute_with_retry(self, operation_func, *args, **kwargs):
        """Execute database operation with retry logic."""
        last_exception = None
        
        for attempt in range(self.config.retry_attempts + 1):
            try:
                return await operation_func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                self.logger.warning(
                    f"Database operation failed (attempt {attempt + 1}/{self.config.retry_attempts + 1}): {str(e)}"
                )
                
                if attempt < self.config.retry_attempts:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    break
        
        raise DatabaseError(f"Database operation failed after {self.config.retry_attempts + 1} attempts: {str(last_exception)}")
    
    async def save_articles(self, articles: List[NewsArticle]) -> None:
        """Save news articles to the database."""
        if not articles:
            return
        
        async def _save_operation():
            async with self._get_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    # Filter out articles that already exist in the database (based on URL)
                    # unique constraint is generally on URL
                    
                    if not articles:
                        return 0

                    # 1. Get List of URLs from input
                    input_urls = [a.url for a in articles]
                    
                    # 2. Check which ones exist
                    # Handle large lists by chunking if necessary, but for now simple IN clause
                    # SQL Server parameter limit is around 2100, so we should be careful if batch is huge
                    
                    existing_urls = set()
                    
                    # Process in chunks of 1000 to be safe with parameters
                    chunk_size = 1000
                    for i in range(0, len(input_urls), chunk_size):
                        chunk_urls = input_urls[i:i + chunk_size]
                        placeholders = ','.join(['?' for _ in chunk_urls])
                        
                        check_query = f"SELECT url FROM news_articles WHERE url IN ({placeholders})"
                        cursor.execute(check_query, chunk_urls)
                        
                        for row in cursor.fetchall():
                            existing_urls.add(row[0])
                    
                    # 3. Filter articles
                    new_articles = [a for a in articles if a.url not in existing_urls]
                    
                    if not new_articles:
                        self.logger.info("No new articles to save (all duplicates)")
                        return 0

                    saved_count = 0
                    for article in new_articles:
                        try:
                            # Get or create source
                            source_id = self._get_or_create_source_sync(cursor, article.source)
                            
                            # Insert article
                            insert_query = """
                            INSERT INTO news_articles 
                            (id, title, content, url, source_id, published_date, scraped_date, 
                             language, author, category)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """
                            
                            cursor.execute(insert_query, (
                                article.id or str(uuid.uuid4()),
                                article.title,
                                article.content,
                                article.url,
                                source_id,
                                article.published_date,
                                article.scraped_date,
                                article.language,
                                article.author,
                                article.category
                            ))
                            
                            # Insert keywords
                            if article.keywords:
                                self._save_article_keywords_sync(cursor, article.id or str(uuid.uuid4()), article.keywords)
                            
                            saved_count += 1
                        except Exception as inner_e:
                            self.logger.warning(f"Failed to save individual article {article.url}: {inner_e}")
                            # Continue to next article
                            pass
                    
                    conn.commit()
                    self.logger.info(f"Successfully saved {saved_count} new articles (skipped {len(articles) - len(new_articles)} duplicates)")
                    return saved_count
                    
                except Exception as e:
                    conn.rollback()
                    raise DatabaseError(f"Failed to save articles batch: {str(e)}")
        
        return await self._execute_with_retry(_save_operation)
    
    async def _get_or_create_source(self, cursor, source_name: str) -> int:
        """Get or create a news source and return its ID."""
        # Check if source exists
        cursor.execute("SELECT id FROM news_sources WHERE name = ?", (source_name,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        # Create new source
        cursor.execute(
            "INSERT INTO news_sources (name, base_url) VALUES (?, ?)",
            (source_name, f"https://www.{source_name.lower().replace(' ', '')}.com")
        )
        
        # Get the inserted ID
        cursor.execute("SELECT SCOPE_IDENTITY()")
        return int(cursor.fetchone()[0])
    
    async def _save_article_keywords(self, cursor, article_id: str, keywords: List[str]) -> None:
        """Save keywords for an article."""
        for keyword in keywords:
            # Get or create keyword
            keyword_id = await self._get_or_create_keyword(cursor, keyword)
            
            # Insert article-keyword relationship
            cursor.execute(
                "INSERT INTO article_keywords (article_id, keyword_id) VALUES (?, ?)",
                (article_id, keyword_id)
            )
    
    async def _get_or_create_keyword(self, cursor, keyword: str) -> int:
        """Get or create a keyword and return its ID."""
        # Check if keyword exists
        cursor.execute("SELECT id FROM keywords WHERE keyword = ?", (keyword,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        # Create new keyword
        cursor.execute(
            "INSERT INTO keywords (keyword) VALUES (?)",
            (keyword,)
        )
        
        # Get the inserted ID
        cursor.execute("SELECT SCOPE_IDENTITY()")
        return int(cursor.fetchone()[0])
        
        if result:
            return result[0]
        
        # Create new keyword
        cursor.execute("INSERT INTO keywords (keyword) VALUES (?)", (keyword,))
        
        # Get the inserted ID
        cursor.execute("SELECT SCOPE_IDENTITY()")
        return cursor.fetchone()[0]
    
    async def get_articles(self, filters: ArticleFilters) -> List[NewsArticle]:
        """Retrieve articles from the database based on filters."""
        async def _get_operation():
            async with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Build query based on filters
                query = """
                SELECT a.id, a.title, a.content, a.url, s.name as source, 
                       a.published_date, a.scraped_date, a.language, a.author, a.category
                FROM news_articles a
                INNER JOIN news_sources s ON a.source_id = s.id
                WHERE 1=1
                """
                params = []
                
                if filters.source:
                    query += " AND s.name = ?"
                    params.append(filters.source)
                
                if filters.start_date:
                    query += " AND a.published_date >= ?"
                    params.append(filters.start_date)
                
                if filters.end_date:
                    query += " AND a.published_date <= ?"
                    params.append(filters.end_date)
                
                if filters.language:
                    query += " AND a.language = ?"
                    params.append(filters.language)
                
                if filters.category:
                    query += " AND a.category = ?"
                    params.append(filters.category)
                
                if filters.keywords:
                    # Join with keywords
                    query += """
                    AND a.id IN (
                        SELECT ak.article_id 
                        FROM article_keywords ak
                        INNER JOIN keywords k ON ak.keyword_id = k.id
                        WHERE k.keyword IN ({})
                    )
                    """.format(','.join(['?' for _ in filters.keywords]))
                    params.extend(filters.keywords)
                
                query += " ORDER BY a.published_date DESC"
                
                if filters.limit:
                    query += f" OFFSET {filters.offset or 0} ROWS FETCH NEXT {filters.limit} ROWS ONLY"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                articles = []
                for row in rows:
                    # Get keywords for this article
                    keywords = await self._get_article_keywords(cursor, row[0])
                    
                    article = NewsArticle(
                        id=row[0],
                        title=row[1],
                        content=row[2],
                        url=row[3],
                        source=row[4],
                        published_date=row[5],
                        scraped_date=row[6],
                        language=row[7],
                        author=row[8],
                        category=row[9],
                        keywords=keywords
                    )
                    articles.append(article)
                
                self.logger.info(f"Retrieved {len(articles)} articles")
                return articles
        
        return await self._execute_with_retry(_get_operation)
    
    async def _get_article_keywords(self, cursor, article_id: str) -> List[str]:
        """Get keywords for a specific article."""
        cursor.execute("""
            SELECT k.keyword 
            FROM article_keywords ak
            INNER JOIN keywords k ON ak.keyword_id = k.id
            WHERE ak.article_id = ?
        """, (article_id,))
        
        return [row[0] for row in cursor.fetchall()]
    
    async def save_sentiment_analysis(self, analysis: SentimentAnalysis) -> None:
        """Save sentiment analysis results to the database."""
        async def _save_operation():
            async with self._get_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    # Calculate date range from article IDs if not provided
                    date_range_start, date_range_end = await self._calculate_date_range(cursor, analysis.article_ids)
                    
                    # Insert sentiment analysis
                    insert_query = """
                    INSERT INTO sentiment_analyses 
                    (id, analysis_date, date_range_start, date_range_end, sentiment_score, 
                     sentiment_label, confidence, summary, model_version, role_context, article_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    
                    cursor.execute(insert_query, (
                        analysis.id or str(uuid.uuid4()),
                        analysis.analysis_date,
                        date_range_start,
                        date_range_end,
                        analysis.sentiment_score,
                        analysis.sentiment_label.value,
                        analysis.confidence,
                        analysis.summary,
                        analysis.model_version,
                        analysis.role_context,
                        len(analysis.article_ids)
                    ))
                    
                    # Insert article relationships
                    for article_id in analysis.article_ids:
                        cursor.execute(
                            "INSERT INTO sentiment_analysis_articles (sentiment_analysis_id, article_id) VALUES (?, ?)",
                            (analysis.id, article_id)
                        )
                    
                    conn.commit()
                    self.logger.info(f"Successfully saved sentiment analysis for {len(analysis.article_ids)} articles")
                    
                except Exception as e:
                    conn.rollback()
                    raise DatabaseError(f"Failed to save sentiment analysis: {str(e)}")
        
        await self._execute_with_retry(_save_operation)
    
    async def _calculate_date_range(self, cursor, article_ids: List[str]) -> tuple[datetime, datetime]:
        """Calculate date range from article IDs."""
        if not article_ids:
            now = datetime.utcnow()
            return now, now
        
        placeholders = ','.join(['?' for _ in article_ids])
        cursor.execute(f"""
            SELECT MIN(published_date), MAX(published_date)
            FROM news_articles
            WHERE id IN ({placeholders})
        """, article_ids)
        
        result = cursor.fetchone()
        return result[0] or datetime.utcnow(), result[1] or datetime.utcnow()
    
    async def get_sentiment_analyses(self, date_range: Optional[DateRange] = None) -> List[SentimentAnalysis]:
        """Retrieve sentiment analyses from the database."""
        async def _get_operation():
            async with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                SELECT id, analysis_date, date_range_start, date_range_end, sentiment_score,
                       sentiment_label, confidence, summary, model_version, role_context
                FROM sentiment_analyses
                WHERE 1=1
                """
                params = []
                
                if date_range:
                    query += " AND date_range_start >= ? AND date_range_end <= ?"
                    params.extend([date_range.start_date, date_range.end_date])
                
                query += " ORDER BY analysis_date DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                analyses = []
                for row in rows:
                    # Get article IDs for this analysis
                    article_ids = await self._get_analysis_article_ids(cursor, row[0])
                    
                    from .models import SentimentLabel
                    analysis = SentimentAnalysis(
                        id=row[0],
                        sentiment_score=row[4],
                        sentiment_label=SentimentLabel(row[5]),
                        confidence=row[6],
                        summary=row[7],
                        analysis_date=row[1],
                        model_version=row[8],
                        role_context=row[9],
                        article_ids=article_ids
                    )
                    analyses.append(analysis)
                
                self.logger.info(f"Retrieved {len(analyses)} sentiment analyses")
                return analyses
        
        return await self._execute_with_retry(_get_operation)
    
    async def _get_analysis_article_ids(self, cursor, analysis_id: str) -> List[str]:
        """Get article IDs for a specific sentiment analysis."""
        cursor.execute("""
            SELECT article_id 
            FROM sentiment_analysis_articles
            WHERE sentiment_analysis_id = ?
        """, (analysis_id,))
        
        return [row[0] for row in cursor.fetchall()]
    
    async def deduplicate_articles(self) -> int:
        """Remove duplicate articles based on URL."""
        async def _deduplicate_operation():
            async with self._get_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    # Call the stored procedure
                    cursor.execute("EXEC sp_DeduplicateArticles")
                    result = cursor.fetchone()
                    deleted_count = result[0] if result else 0
                    
                    conn.commit()
                    self.logger.info(f"Deduplicated {deleted_count} articles")
                    return deleted_count
                    
                except Exception as e:
                    conn.rollback()
                    raise DatabaseError(f"Failed to deduplicate articles: {str(e)}")
        
        return await self._execute_with_retry(_deduplicate_operation)
    
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a raw SQL query."""
        async def _execute_operation():
            async with self._get_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    if params:
                        # Convert dict params to list for pyodbc
                        param_list = list(params.values()) if isinstance(params, dict) else params
                        cursor.execute(query, param_list)
                    else:
                        cursor.execute(query)
                    
                    # Determine if this is a SELECT query
                    if query.strip().upper().startswith('SELECT'):
                        results = cursor.fetchall()
                        columns = [desc[0] for desc in cursor.description]
                        return [dict(zip(columns, row)) for row in results]
                    else:
                        conn.commit()
                        return cursor.rowcount
                        
                except Exception as e:
                    conn.rollback()
                    raise DatabaseError(f"Failed to execute query: {str(e)}")
        
        return await self._execute_with_retry(_execute_operation)
    
    async def health_check(self) -> bool:
        """Check database connectivity and health."""
        try:
            result = await self.execute_query("SELECT 1 as health_check")
            return len(result) > 0 and result[0]['health_check'] == 1
        except Exception as e:
            self.logger.error(f"Database health check failed: {str(e)}")
            return False
    
    async def save_execution_log(self, execution_result: ExecutionResult) -> None:
        """Save function execution log to the database."""
        async def _save_log_operation():
            async with self._get_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    insert_query = """
                    INSERT INTO execution_logs 
                    (id, function_name, execution_id, start_time, end_time, status, 
                     error_message, input_parameters, output_summary, duration_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    
                    cursor.execute(insert_query, (
                        str(uuid.uuid4()),
                        execution_result.function_name,
                        execution_result.execution_id,
                        execution_result.start_time,
                        execution_result.end_time,
                        execution_result.status.value,
                        execution_result.error_message,
                        json.dumps(execution_result.input_parameters) if execution_result.input_parameters else None,
                        json.dumps(execution_result.output_summary) if execution_result.output_summary else None,
                        execution_result.duration_ms
                    ))
                    
                    conn.commit()
                    
                except Exception as e:
                    conn.rollback()
                    raise DatabaseError(f"Failed to save execution log: {str(e)}")
        
        await self._execute_with_retry(_save_log_operation)
    
    async def get_configuration(self, config_key: str) -> Optional[str]:
        """Get a configuration value from the database."""
        try:
            result = await self.execute_query(
                "SELECT config_value FROM configuration WHERE config_key = ?",
                [config_key]
            )
            return result[0]['config_value'] if result else None
        except Exception as e:
            self.logger.error(f"Failed to get configuration '{config_key}': {str(e)}")
            return None
    
    async def set_configuration(self, config_key: str, config_value: str, config_type: str = 'string') -> None:
        """Set a configuration value in the database."""
        try:
            # Check if configuration exists
            existing = await self.get_configuration(config_key)
            
            if existing is not None:
                # Update existing
                await self.execute_query(
                    "UPDATE configuration SET config_value = ?, updated_at = GETUTCDATE() WHERE config_key = ?",
                    [config_value, config_key]
                )
            else:
                # Insert new
                await self.execute_query(
                    "INSERT INTO configuration (config_key, config_value, config_type) VALUES (?, ?, ?)",
                    [config_key, config_value, config_type]
                )
                
            self.logger.info(f"Configuration '{config_key}' updated successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to set configuration '{config_key}': {str(e)}")
            raise DatabaseError(f"Failed to set configuration: {str(e)}")
    
    async def close(self) -> None:
        """Close database connections and cleanup resources."""
        try:
            # In a full implementation, this would close the connection pool
            self._connection_pool = None
            self.logger.info("Database handler closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing database handler: {str(e)}")
    
    def _get_or_create_source_sync(self, cursor, source_name: str) -> int:
        """Get or create a news source and return its ID (synchronous)."""
        # Check if source exists
        cursor.execute("SELECT id FROM news_sources WHERE name = ?", (source_name,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        # Create new source
        cursor.execute(
            "INSERT INTO news_sources (name, base_url) VALUES (?, ?)",
            (source_name, f"https://www.{source_name.lower().replace(' ', '')}.com")
        )
        
        # Get the inserted ID with proper error handling
        cursor.execute("SELECT SCOPE_IDENTITY()")
        identity_result = cursor.fetchone()
        
        if identity_result and identity_result[0] is not None:
            return int(identity_result[0])
        else:
            # Fallback: try to get the ID by name again
            cursor.execute("SELECT id FROM news_sources WHERE name = ?", (source_name,))
            fallback_result = cursor.fetchone()
            if fallback_result and fallback_result[0] is not None:
                return int(fallback_result[0])
            else:
                raise DatabaseError(f"Failed to get or create source ID for: {source_name}")
    
    def _save_article_keywords_sync(self, cursor, article_id: str, keywords: List[str]) -> None:
        """Save keywords for an article (synchronous)."""
        for keyword in keywords:
            # Get or create keyword
            keyword_id = self._get_or_create_keyword_sync(cursor, keyword)
            
            # Insert article-keyword relationship
            cursor.execute(
                "INSERT INTO article_keywords (article_id, keyword_id) VALUES (?, ?)",
                (article_id, keyword_id)
            )
    
    def _get_or_create_keyword_sync(self, cursor, keyword: str) -> int:
        """Get or create a keyword and return its ID (synchronous)."""
        # Check if keyword exists
        cursor.execute("SELECT id FROM keywords WHERE keyword = ?", (keyword,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        # Create new keyword
        cursor.execute(
            "INSERT INTO keywords (keyword) VALUES (?)",
            (keyword,)
        )
        
        # Get the inserted ID with proper error handling
        cursor.execute("SELECT SCOPE_IDENTITY()")
        identity_result = cursor.fetchone()
        
        if identity_result and identity_result[0] is not None:
            return int(identity_result[0])
        else:
            # Fallback: try to get the ID by keyword again
            cursor.execute("SELECT id FROM keywords WHERE keyword = ?", (keyword,))
            fallback_result = cursor.fetchone()
            if fallback_result and fallback_result[0] is not None:
                return int(fallback_result[0])
            else:
                raise DatabaseError(f"Failed to get or create keyword ID for: {keyword}")


# Factory function for creating database handler instances
async def create_database_handler(config: DatabaseConfig) -> DatabaseHandler:
    """
    Factory function to create and initialize a database handler.
    
    Args:
        config: Database configuration
        
    Returns:
        Initialized database handler
    """
    handler = DatabaseHandler(config)
    
    # Verify connection on creation
    if not await handler.health_check():
        raise DatabaseError("Failed to establish database connection")
    
    return handler