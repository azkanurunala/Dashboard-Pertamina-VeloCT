"""
Unit tests for data processing functions.
Tests news aggregator and data caching functionality.
"""

import unittest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

import sys
import os

# Add the workspace root to path so we can import azure_functions as a package
workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from azure_functions.processing.news_aggregator import NewsAggregator, NewsAggregatorFunction, AggregationResult
from azure_functions.processing.data_cache import DataCache, CachedDatabaseHandler, CacheStats
from azure_functions.shared.models import NewsArticle, ArticleFilters


class TestNewsAggregator(unittest.TestCase):
    """Test cases for NewsAggregator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_db_handler = Mock()
        self.aggregator = NewsAggregator(self.mock_db_handler)
    
    def test_aggregate_articles_by_source(self):
        """Test aggregating articles by source."""
        articles = [
            NewsArticle(
                id="1",
                title="Test Article 1",
                content="Content 1",
                url="https://example.com/1",
                source="CNBC",
                published_date=datetime.utcnow(),
                scraped_date=datetime.utcnow(),
                keywords=["test"],
                language="en"
            ),
            NewsArticle(
                id="2",
                title="Test Article 2",
                content="Content 2",
                url="https://example.com/2",
                source="CNN",
                published_date=datetime.utcnow(),
                scraped_date=datetime.utcnow(),
                keywords=["test"],
                language="en"
            ),
            NewsArticle(
                id="3",
                title="Test Article 3",
                content="Content 3",
                url="https://example.com/3",
                source="CNBC",
                published_date=datetime.utcnow(),
                scraped_date=datetime.utcnow(),
                keywords=["test"],
                language="en"
            )
        ]
        
        result = asyncio.run(self.aggregator.aggregate_articles(articles))
        
        self.assertEqual(result['total_articles'], 3)
        self.assertEqual(result['by_source']['CNBC'], 2)
        self.assertEqual(result['by_source']['CNN'], 1)
    
    def test_standardize_data(self):
        """Test data standardization."""
        articles = [
            NewsArticle(
                id="1",
                title="  test   article  ",
                content="  content   with   spaces  ",
                url="HTTPS://EXAMPLE.COM/TEST/",
                source="cnbc",
                published_date=datetime.utcnow(),
                scraped_date=datetime.utcnow(),
                keywords=["TEST", "test", "Test"],
                language="EN"
            )
        ]
        
        result = asyncio.run(self.aggregator.standardize_data(articles))
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "Test article")
        self.assertEqual(result[0].url, "https://example.com/test")
        self.assertEqual(result[0].source, "Cnbc")
        self.assertEqual(result[0].language, "en")
        self.assertEqual(result[0].keywords, ["test"])
    
    def test_clean_content(self):
        """Test content cleaning."""
        content = "  This   is   <b>test</b>   content   with   HTML  "
        
        result = asyncio.run(self.aggregator.clean_content(content))
        
        self.assertNotIn("<b>", result)
        self.assertNotIn("</b>", result)
        self.assertNotIn("  ", result)
    
    def test_extract_keywords(self):
        """Test keyword extraction."""
        content = "This is a test article about energy and oil prices. Energy markets are volatile."
        
        result = asyncio.run(self.aggregator.extract_keywords(content))
        
        self.assertIsInstance(result, list)
        self.assertIn("energy", result)
        # Stop words should be filtered out
        self.assertNotIn("this", result)
        self.assertNotIn("is", result)


class TestDataCache(unittest.TestCase):
    """Test cases for DataCache class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cache = DataCache(default_ttl_seconds=60, max_size=100)
    
    def test_set_and_get(self):
        """Test basic set and get operations."""
        asyncio.run(self.cache.set("test_key", "test_value"))
        result = asyncio.run(self.cache.get("test_key"))
        
        self.assertEqual(result, "test_value")
    
    def test_get_nonexistent_key(self):
        """Test getting a non-existent key."""
        result = asyncio.run(self.cache.get("nonexistent"))
        
        self.assertIsNone(result)
    
    def test_expiration(self):
        """Test cache entry expiration."""
        asyncio.run(self.cache.set("test_key", "test_value", ttl_seconds=1))
        
        # Should exist immediately
        result1 = asyncio.run(self.cache.get("test_key"))
        self.assertEqual(result1, "test_value")
        
        # Wait for expiration
        import time
        time.sleep(2)
        
        # Should be expired
        result2 = asyncio.run(self.cache.get("test_key"))
        self.assertIsNone(result2)
    
    def test_delete(self):
        """Test deleting a cache entry."""
        asyncio.run(self.cache.set("test_key", "test_value"))
        deleted = asyncio.run(self.cache.delete("test_key"))
        
        self.assertTrue(deleted)
        
        result = asyncio.run(self.cache.get("test_key"))
        self.assertIsNone(result)
    
    def test_invalidate_pattern(self):
        """Test pattern-based invalidation."""
        asyncio.run(self.cache.set("articles:1", "value1"))
        asyncio.run(self.cache.set("articles:2", "value2"))
        asyncio.run(self.cache.set("sentiment:1", "value3"))
        
        count = asyncio.run(self.cache.invalidate_pattern("articles"))
        
        self.assertEqual(count, 2)
        
        # Articles should be gone
        self.assertIsNone(asyncio.run(self.cache.get("articles:1")))
        self.assertIsNone(asyncio.run(self.cache.get("articles:2")))
        
        # Sentiment should still exist
        self.assertEqual(asyncio.run(self.cache.get("sentiment:1")), "value3")
    
    def test_clear(self):
        """Test clearing all cache entries."""
        asyncio.run(self.cache.set("key1", "value1"))
        asyncio.run(self.cache.set("key2", "value2"))
        
        asyncio.run(self.cache.clear())
        
        stats = asyncio.run(self.cache.get_stats())
        self.assertEqual(stats.total_entries, 0)
    
    def test_cache_stats(self):
        """Test cache statistics."""
        asyncio.run(self.cache.set("key1", "value1"))
        asyncio.run(self.cache.set("key2", "value2"))
        
        # Generate some hits and misses
        asyncio.run(self.cache.get("key1"))
        asyncio.run(self.cache.get("key1"))
        asyncio.run(self.cache.get("nonexistent"))
        
        stats = asyncio.run(self.cache.get_stats())
        
        self.assertEqual(stats.total_entries, 2)
        self.assertEqual(stats.total_hits, 2)
        self.assertEqual(stats.total_misses, 1)
        self.assertGreater(stats.hit_rate, 0)
    
    def test_generate_key(self):
        """Test cache key generation."""
        key1 = self.cache.generate_key("articles", source="CNBC", date="2024-01-01")
        key2 = self.cache.generate_key("articles", source="CNBC", date="2024-01-01")
        key3 = self.cache.generate_key("articles", source="CNN", date="2024-01-01")
        
        # Same arguments should generate same key
        self.assertEqual(key1, key2)
        
        # Different arguments should generate different key
        self.assertNotEqual(key1, key3)


class TestCachedDatabaseHandler(unittest.TestCase):
    """Test cases for CachedDatabaseHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_db_handler = Mock()
        self.cache = DataCache(default_ttl_seconds=60)
        self.cached_handler = CachedDatabaseHandler(self.mock_db_handler, self.cache)
    
    def test_get_articles_cached_miss(self):
        """Test getting articles with cache miss."""
        # Mock database response
        mock_articles = [
            NewsArticle(
                id="1",
                title="Test",
                content="Content",
                url="https://example.com/1",
                source="CNBC",
                published_date=datetime.utcnow(),
                scraped_date=datetime.utcnow(),
                keywords=["test"],
                language="en"
            )
        ]
        self.mock_db_handler.get_articles = AsyncMock(return_value=mock_articles)
        
        filters = ArticleFilters(
            source="CNBC",
            keywords=["test"],
            start_date=datetime.utcnow() - timedelta(days=1),
            end_date=datetime.utcnow()
        )
        
        result = asyncio.run(self.cached_handler.get_articles_cached(filters))
        
        self.assertEqual(len(result), 1)
        self.mock_db_handler.get_articles.assert_called_once()
    
    def test_get_articles_cached_hit(self):
        """Test getting articles with cache hit."""
        # Mock database response
        mock_articles = [
            NewsArticle(
                id="1",
                title="Test",
                content="Content",
                url="https://example.com/1",
                source="CNBC",
                published_date=datetime.utcnow(),
                scraped_date=datetime.utcnow(),
                keywords=["test"],
                language="en"
            )
        ]
        self.mock_db_handler.get_articles = AsyncMock(return_value=mock_articles)
        
        filters = ArticleFilters(
            source="CNBC",
            keywords=["test"],
            start_date=datetime.utcnow() - timedelta(days=1),
            end_date=datetime.utcnow()
        )
        
        # First call - cache miss
        result1 = asyncio.run(self.cached_handler.get_articles_cached(filters))
        
        # Second call - cache hit
        result2 = asyncio.run(self.cached_handler.get_articles_cached(filters))
        
        self.assertEqual(len(result1), 1)
        self.assertEqual(len(result2), 1)
        # Database should only be called once
        self.assertEqual(self.mock_db_handler.get_articles.call_count, 1)


if __name__ == '__main__':
    unittest.main()
