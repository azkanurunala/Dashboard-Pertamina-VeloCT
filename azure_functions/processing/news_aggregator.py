"""
News aggregator function for collecting and standardizing news data from multiple sources.
Implements HTTP-triggered aggregation with parallel execution and data processing.
"""

import asyncio
import logging
import re
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from dataclasses import dataclass, asdict

try:
    from ..shared.database_handler import DatabaseHandler
    from ..shared.models import NewsArticle, ArticleFilters
    from ..shared.interfaces import IDataProcessor, ProcessingError
    from ..shared.logging_config import get_logger
except ImportError:
    from shared.database_handler import DatabaseHandler
    from shared.models import NewsArticle, ArticleFilters
    from shared.interfaces import IDataProcessor, ProcessingError
    from shared.logging_config import get_logger


@dataclass
class AggregationResult:
    """Result of a news aggregation operation."""
    total_articles: int
    articles_by_source: Dict[str, int]
    processing_time_seconds: float
    errors: List[str]
    standardized_count: int
    cleaned_count: int


class NewsAggregator(IDataProcessor):
    """
    News aggregator for collecting and processing articles from multiple sources.
    
    Implements data standardization, cleaning, and keyword extraction
    following the IDataProcessor interface.
    """
    
    def __init__(self, db_handler: DatabaseHandler):
        """
        Initialize the news aggregator.
        
        Args:
            db_handler: Database handler instance
        """
        self.db_handler = db_handler
        self.logger = get_logger(__name__)
    
    async def aggregate_articles(self, articles: List[NewsArticle]) -> Dict[str, Any]:
        """
        Aggregate articles by various dimensions.
        
        Args:
            articles: List of articles to aggregate
            
        Returns:
            Aggregation results with statistics
        """
        try:
            self.logger.info(f"Aggregating {len(articles)} articles")
            
            # Aggregate by source
            by_source = {}
            for article in articles:
                source = article.source
                by_source[source] = by_source.get(source, 0) + 1
            
            # Aggregate by date
            by_date = {}
            for article in articles:
                date_key = article.published_date.strftime('%Y-%m-%d')
                by_date[date_key] = by_date.get(date_key, 0) + 1
            
            # Aggregate by keyword
            by_keyword = {}
            for article in articles:
                for keyword in article.keywords:
                    by_keyword[keyword] = by_keyword.get(keyword, 0) + 1
            
            # Aggregate by language
            by_language = {}
            for article in articles:
                lang = article.language or 'unknown'
                by_language[lang] = by_language.get(lang, 0) + 1
            
            aggregation = {
                'total_articles': len(articles),
                'by_source': by_source,
                'by_date': by_date,
                'by_keyword': by_keyword,
                'by_language': by_language,
                'date_range': {
                    'earliest': min(a.published_date for a in articles) if articles else None,
                    'latest': max(a.published_date for a in articles) if articles else None
                }
            }
            
            self.logger.info(f"Aggregation complete: {len(by_source)} sources, {len(by_date)} dates")
            return aggregation
            
        except Exception as e:
            error_msg = f"Error aggregating articles: {str(e)}"
            self.logger.error(error_msg)
            raise ProcessingError(error_msg)
    
    async def standardize_data(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """
        Standardize article data format and content.
        
        Args:
            articles: List of articles to standardize
            
        Returns:
            Standardized articles
        """
        try:
            self.logger.info(f"Standardizing {len(articles)} articles")
            
            standardized = []
            for article in articles:
                # Create a copy to avoid modifying original
                std_article = NewsArticle(
                    id=article.id,
                    title=self._standardize_title(article.title),
                    content=self._standardize_content(article.content),
                    url=self._standardize_url(article.url),
                    source=self._standardize_source(article.source),
                    published_date=article.published_date,
                    scraped_date=article.scraped_date,
                    keywords=self._standardize_keywords(article.keywords),
                    language=self._standardize_language(article.language),
                    author=self._standardize_author(article.author),
                    category=self._standardize_category(article.category)
                )
                standardized.append(std_article)
            
            self.logger.info(f"Standardization complete: {len(standardized)} articles")
            return standardized
            
        except Exception as e:
            error_msg = f"Error standardizing articles: {str(e)}"
            self.logger.error(error_msg)
            raise ProcessingError(error_msg)
    
    async def clean_content(self, content: str) -> str:
        """
        Clean and normalize article content.
        
        Args:
            content: Raw article content
            
        Returns:
            Cleaned content
        """
        if not content:
            return ""
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', content)
        
        # Remove HTML tags if any
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        
        # Remove special characters but keep punctuation
        cleaned = re.sub(r'[^\w\s\.,!?;:\-\'"()]', '', cleaned)
        
        # Trim whitespace
        cleaned = cleaned.strip()
        
        return cleaned
    
    async def extract_keywords(self, content: str) -> List[str]:
        """
        Extract keywords from article content.
        
        Args:
            content: Article content
            
        Returns:
            Extracted keywords
        """
        if not content:
            return []
        
        # Simple keyword extraction based on word frequency
        # In production, this could use NLP libraries
        
        # Convert to lowercase and split into words
        words = re.findall(r'\b\w+\b', content.lower())
        
        # Filter out common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'them', 'their'
        }
        
        # Count word frequency
        word_freq = {}
        for word in words:
            if word not in stop_words and len(word) > 3:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, freq in sorted_words[:10]]
        
        return keywords
    
    def _standardize_title(self, title: str) -> str:
        """Standardize article title."""
        if not title:
            return ""
        # Remove excessive whitespace
        title = re.sub(r'\s+', ' ', title).strip()
        # Capitalize first letter
        if title:
            title = title[0].upper() + title[1:]
        return title
    
    def _standardize_content(self, content: str) -> str:
        """Standardize article content."""
        if not content:
            return ""
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        return content
    
    def _standardize_url(self, url: str) -> str:
        """Standardize article URL."""
        if not url:
            return ""
        # Remove trailing slashes
        url = url.rstrip('/')
        # Ensure lowercase for consistency
        return url.lower()
    
    def _standardize_source(self, source: str) -> str:
        """Standardize source name."""
        if not source:
            return ""
        # Capitalize properly
        return source.strip().title()
    
    def _standardize_keywords(self, keywords: List[str]) -> List[str]:
        """Standardize keywords list."""
        if not keywords:
            return []
        # Remove duplicates, lowercase, and sort
        standardized = list(set(k.lower().strip() for k in keywords if k))
        return sorted(standardized)
    
    def _standardize_language(self, language: Optional[str]) -> str:
        """Standardize language code."""
        if not language:
            return "en"
        # Ensure lowercase 2-letter code
        lang = language.lower().strip()
        if len(lang) > 2:
            lang = lang[:2]
        return lang
    
    def _standardize_author(self, author: Optional[str]) -> Optional[str]:
        """Standardize author name."""
        if not author:
            return None
        # Remove excessive whitespace
        author = re.sub(r'\s+', ' ', author).strip()
        return author if author else None
    
    def _standardize_category(self, category: Optional[str]) -> Optional[str]:
        """Standardize category name."""
        if not category:
            return None
        # Capitalize properly
        category = category.strip().title()
        return category if category else None


class NewsAggregatorFunction:
    """
    HTTP-triggered Azure Function for news aggregation.
    
    Coordinates parallel scraping from multiple sources and processes results.
    """
    
    def __init__(self, db_handler: DatabaseHandler):
        """
        Initialize the news aggregator function.
        
        Args:
            db_handler: Database handler instance
        """
        self.db_handler = db_handler
        self.aggregator = NewsAggregator(db_handler)
        self.logger = get_logger(__name__)
    
    async def aggregate_from_sources(
        self,
        sources: List[str],
        keywords: List[str],
        start_date: datetime,
        end_date: datetime,
        parallel: bool = True
    ) -> AggregationResult:
        """
        Aggregate news from multiple sources with parallel execution.
        
        Args:
            sources: List of source names to aggregate from
            keywords: Keywords to filter articles
            start_date: Start date for article retrieval
            end_date: End date for article retrieval
            parallel: Whether to execute in parallel (default: True)
            
        Returns:
            AggregationResult with statistics
        """
        start_time = datetime.utcnow()
        errors = []
        
        try:
            self.logger.info(f"Starting aggregation from {len(sources)} sources")
            
            # Retrieve articles from database for each source
            all_articles = []
            articles_by_source = {}
            
            if parallel:
                # Execute in parallel
                tasks = []
                for source in sources:
                    task = self._fetch_articles_for_source(
                        source, keywords, start_date, end_date
                    )
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for source, result in zip(sources, results):
                    if isinstance(result, Exception):
                        error_msg = f"Error fetching from {source}: {str(result)}"
                        self.logger.error(error_msg)
                        errors.append(error_msg)
                        articles_by_source[source] = 0
                    else:
                        articles = result
                        all_articles.extend(articles)
                        articles_by_source[source] = len(articles)
            else:
                # Execute sequentially
                for source in sources:
                    try:
                        articles = await self._fetch_articles_for_source(
                            source, keywords, start_date, end_date
                        )
                        all_articles.extend(articles)
                        articles_by_source[source] = len(articles)
                    except Exception as e:
                        error_msg = f"Error fetching from {source}: {str(e)}"
                        self.logger.error(error_msg)
                        errors.append(error_msg)
                        articles_by_source[source] = 0
            
            # Standardize and clean data
            standardized_articles = await self.aggregator.standardize_data(all_articles)
            
            # Clean content for each article
            cleaned_count = 0
            for article in standardized_articles:
                article.content = await self.aggregator.clean_content(article.content)
                cleaned_count += 1
            
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            result = AggregationResult(
                total_articles=len(all_articles),
                articles_by_source=articles_by_source,
                processing_time_seconds=processing_time,
                errors=errors,
                standardized_count=len(standardized_articles),
                cleaned_count=cleaned_count
            )
            
            self.logger.info(
                f"Aggregation complete: {len(all_articles)} articles from "
                f"{len(sources)} sources in {processing_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Error during aggregation: {str(e)}"
            self.logger.error(error_msg)
            errors.append(error_msg)
            
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            return AggregationResult(
                total_articles=0,
                articles_by_source={},
                processing_time_seconds=processing_time,
                errors=errors,
                standardized_count=0,
                cleaned_count=0
            )
    
    async def _fetch_articles_for_source(
        self,
        source: str,
        keywords: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> List[NewsArticle]:
        """
        Fetch articles for a specific source from the database.
        
        Args:
            source: Source name
            keywords: Keywords to filter
            start_date: Start date
            end_date: End date
            
        Returns:
            List of articles
        """
        try:
            filters = ArticleFilters(
                source=source,
                keywords=keywords,
                start_date=start_date,
                end_date=end_date
            )
            
            articles = await self.db_handler.get_articles(filters)
            self.logger.info(f"Fetched {len(articles)} articles from {source}")
            return articles
            
        except Exception as e:
            self.logger.error(f"Error fetching articles from {source}: {str(e)}")
            raise
