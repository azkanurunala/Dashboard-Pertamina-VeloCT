"""
Database handler for Azure Functions news scraping system.
Provides database operations with connection pooling, retry logic, and error handling.
"""

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False

from .models import NewsArticle, SentimentAnalysis, DatabaseConfig, ArticleFilters
from .interfaces import IDatabaseHandler, DatabaseError


class DatabaseHandler(IDatabaseHandler):
    """
    SQL Server database handler with connection pooling and retry logic.
    """
    
    def __init__(self, config: DatabaseConfig):
        """Initialize database handler with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._connection_pool = []
        self._pool_lock = asyncio.Lock()
        
        if not PYODBC_AVAILABLE:
            raise DatabaseError("pyodbc library is required for SQL Server operations")
    
    @asynccontextmanager
    async def _get_connection(self):
        """Get a database connection from the pool."""
        connection = None
        try:
            # Try to get connection from pool
            async with self._pool_lock:
                if self._connection_pool:
                    connection = self._connection_pool.pop()
            
            # Create new connection if pool is empty
            if connection is None:
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
            # Return connection to pool
            if connection:
                try:
                    async with self._pool_lock:
                        if len(self._connection_pool) < self.config.connection_pool_size:
                            self._connection_pool.append(connection)
                        else:
                            connection.close()
                except Exception as e:
                    self.logger.warning(f"Error returning connection to pool: {str(e)}")
                    try:
                        connection.close()
                    except Exception:
                        pass
    
    async def health_check(self) -> bool:
        """Check database connectivity and health."""
        try:
            async with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result is not None and result[0] == 1
        except Exception as e:
            self.logger.error(f"Database health check failed: {str(e)}")
            return False
    
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
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
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
                    for article in articles:
                        # Get or create source
                        source_id = self._get_or_create_source(cursor, article.source)
                        
                        # Insert article
                        insert_query = """
                        INSERT INTO news_articles 
                        (id, title, content, url, source_id, published_date, scraped_date, 
                         language, author, category)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """
                        
                        article_id = article.id or str(uuid.uuid4())
                        
                        cursor.execute(insert_query, (
                            article_id,
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
                            self._save_article_keywords(cursor, article_id, article.keywords)
                    
                    conn.commit()
                    self.logger.info(f"Successfully saved {len(articles)} articles")
                    
                except Exception as e:
                    conn.rollback()
                    raise DatabaseError(f"Failed to save articles: {str(e)}")
        
        await self._execute_with_retry(_save_operation)
    
    def _get_or_create_source(self, cursor, source_name: str) -> int:
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
    
    def _save_article_keywords(self, cursor, article_id: str, keywords: List[str]) -> None:
        """Save keywords for an article."""
        for keyword in keywords:
            # Get or create keyword
            keyword_id = self._get_or_create_keyword(cursor, keyword)
            
            # Insert article-keyword relationship
            cursor.execute(
                "INSERT INTO article_keywords (article_id, keyword_id) VALUES (?, ?)",
                (article_id, keyword_id)
            )
    
    def _get_or_create_keyword(self, cursor, keyword: str) -> int:
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
                
                if filters.language:
                    query += " AND a.language = ?"
                    params.append(filters.language)
                
                if filters.category:
                    query += " AND a.category = ?"
                    params.append(filters.category)
                
                if filters.start_date:
                    query += " AND a.published_date >= ?"
                    params.append(filters.start_date)
                
                if filters.end_date:
                    query += " AND a.published_date <= ?"
                    params.append(filters.end_date)
                
                if filters.keywords:
                    # Join with keywords table
                    query = query.replace("WHERE 1=1", """
                    INNER JOIN article_keywords ak ON a.id = ak.article_id
                    INNER JOIN keywords k ON ak.keyword_id = k.id
                    WHERE k.keyword IN ({})
                    """.format(','.join(['?' for _ in filters.keywords])))
                    params.extend(filters.keywords)
                
                # Add ordering and pagination
                query += " ORDER BY a.published_date DESC"
                
                if filters.offset:
                    query += f" OFFSET {filters.offset} ROWS"
                
                if filters.limit:
                    query += f" FETCH NEXT {filters.limit} ROWS ONLY"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                articles = []
                for row in rows:
                    # Get keywords for this article
                    cursor.execute("""
                        SELECT k.keyword 
                        FROM article_keywords ak
                        INNER JOIN keywords k ON ak.keyword_id = k.id
                        WHERE ak.article_id = ?
                    """, (row[0],))
                    
                    keywords = [kw[0] for kw in cursor.fetchall()]
                    
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
                
                return articles
        
        return await self._execute_with_retry(_get_operation)
    
    async def save_sentiment_analysis(self, analysis: SentimentAnalysis) -> None:
        """Save sentiment analysis to the database."""
        async def _save_operation():
            async with self._get_connection() as conn:
                cursor = conn.cursor()
                
                try:
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
                        analysis.date_range_start,
                        analysis.date_range_end,
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
                    self.logger.info(f"Successfully saved sentiment analysis: {analysis.id}")
                    
                except Exception as e:
                    conn.rollback()
                    raise DatabaseError(f"Failed to save sentiment analysis: {str(e)}")
        
        await self._execute_with_retry(_save_operation)
    
    async def deduplicate_articles(self) -> int:
        """Remove duplicate articles based on URL and return count of removed duplicates."""
        async def _deduplicate_operation():
            async with self._get_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    # Find duplicates (keep the most recent one)
                    cursor.execute("""
                        WITH DuplicateArticles AS (
                            SELECT id, url, scraped_date,
                                   ROW_NUMBER() OVER (PARTITION BY url ORDER BY scraped_date DESC) as rn
                            FROM news_articles
                        )
                        DELETE FROM news_articles 
                        WHERE id IN (
                            SELECT id FROM DuplicateArticles WHERE rn > 1
                        )
                    """)
                    
                    deleted_count = cursor.rowcount
                    conn.commit()
                    
                    self.logger.info(f"Removed {deleted_count} duplicate articles")
                    return deleted_count
                    
                except Exception as e:
                    conn.rollback()
                    raise DatabaseError(f"Failed to deduplicate articles: {str(e)}")
        
        return await self._execute_with_retry(_deduplicate_operation)
    
    async def execute_query(self, query: str, params: Optional[List] = None) -> List[Dict[str, Any]]:
        """Execute a custom query and return results."""
        async def _query_operation():
            async with self._get_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    
                    # Get column names
                    columns = [column[0] for column in cursor.description] if cursor.description else []
                    
                    # Fetch results
                    rows = cursor.fetchall()
                    
                    # Convert to list of dictionaries
                    results = []
                    for row in rows:
                        result_dict = {}
                        for i, value in enumerate(row):
                            if i < len(columns):
                                result_dict[columns[i]] = value
                        results.append(result_dict)
                    
                    return results
                    
                except Exception as e:
                    raise DatabaseError(f"Failed to execute query: {str(e)}")
        
        return await self._execute_with_retry(_query_operation)
    
    async def close(self) -> None:
        """Close all database connections."""
        async with self._pool_lock:
            for connection in self._connection_pool:
                try:
                    connection.close()
                except Exception as e:
                    self.logger.warning(f"Error closing connection: {str(e)}")
            self._connection_pool.clear()