"""
Unit tests for all core components of the Azure Functions news scraping system.
Tests database operations, API integrations, and data processing with mock implementations.
"""

import asyncio
import pytest
import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json
import uuid
from typing import List, Dict, Any
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.models import (
    NewsArticle, SentimentAnalysis, SentimentLabel, DatabaseConfig, 
    CopilotConfig, ArticleFilters, DateRange, ExecutionResult, FunctionStatus
)
from shared.interfaces import DatabaseError, CopilotError, RateLimitError
from shared.database_handler import DatabaseHandler
from shared.copilot_integration import CopilotIntegration, CopilotRateLimiter
from shared.config import ConfigManager
from shared.utils import (
    validate_url, sanitize_text, extract_keywords, 
    calculate_text_similarity, format_date_for_api
)


class TestDatabaseHandler(unittest.TestCase):
    """Unit tests for DatabaseHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = DatabaseConfig(
            connection_string="mock://test",
            connection_pool_size=5,
            connection_timeout=30,
            command_timeout=60,
            retry_attempts=3,
            retry_delay=2
        )
        
        self.sample_article = NewsArticle(
            id=str(uuid.uuid4()),
            title="Test Article",
            content="This is test content for the article.",
            url="https://test.com/article",
            source="TestSource",
            published_date=datetime.utcnow(),
            scraped_date=datetime.utcnow(),
            keywords=["test", "article"]
        )
    
    @patch('shared.database_handler.pyodbc')
    def test_database_handler_initialization(self, mock_pyodbc):
        """Test DatabaseHandler initialization with valid config."""
        handler = DatabaseHandler(self.config)
        self.assertEqual(handler.config, self.config)
        self.assertIsNotNone(handler.logger)
    
    @patch('shared.database_handler.pyodbc')
    async def test_health_check_success(self, mock_pyodbc):
        """Test successful database health check."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.execute.return_value = None
        mock_cursor.fetchone.return_value = (1,)
        mock_pyodbc.connect.return_value = mock_connection
        
        handler = DatabaseHandler(self.config)
        result = await handler.health_check()
        
        self.assertTrue(result)
        mock_cursor.execute.assert_called_once()
    
    @patch('shared.database_handler.pyodbc')
    async def test_health_check_failure(self, mock_pyodbc):
        """Test database health check failure."""
        mock_pyodbc.connect.side_effect = Exception("Connection failed")
        
        handler = DatabaseHandler(self.config)
        result = await handler.health_check()
        
        self.assertFalse(result)
    
    @patch('shared.database_handler.pyodbc')
    async def test_save_articles_success(self, mock_pyodbc):
        """Test successful article saving."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_pyodbc.connect.return_value = mock_connection
        
        handler = DatabaseHandler(self.config)
        await handler.save_articles([self.sample_article])
        
        # Verify SQL execution was called
        mock_cursor.execute.assert_called()
        mock_connection.commit.assert_called()
    
    @patch('shared.database_handler.pyodbc')
    async def test_save_articles_duplicate_url_error(self, mock_pyodbc):
        """Test handling of duplicate URL constraint violation."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Simulate unique constraint violation
        mock_error = Exception("UNIQUE constraint failed")
        mock_cursor.execute.side_effect = mock_error
        mock_pyodbc.connect.return_value = mock_connection
        
        handler = DatabaseHandler(self.config)
        
        with self.assertRaises(DatabaseError):
            await handler.save_articles([self.sample_article])
    
    @patch('shared.database_handler.pyodbc')
    async def test_get_articles_with_filters(self, mock_pyodbc):
        """Test article retrieval with filters."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        
        # Mock database response
        mock_cursor.fetchall.return_value = [
            (str(uuid.uuid4()), "Test Title", "Test Content", "https://test.com", 
             "TestSource", datetime.utcnow(), datetime.utcnow(), "en", None, None)
        ]
        mock_pyodbc.connect.return_value = mock_connection
        
        handler = DatabaseHandler(self.config)
        filters = ArticleFilters(source="TestSource")
        articles = await handler.get_articles(filters)
        
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].source, "TestSource")
    
    @patch('shared.database_handler.pyodbc')
    async def test_deduplicate_articles(self, mock_pyodbc):
        """Test article deduplication."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 5  # 5 duplicates removed
        mock_pyodbc.connect.return_value = mock_connection
        
        handler = DatabaseHandler(self.config)
        removed_count = await handler.deduplicate_articles()
        
        self.assertEqual(removed_count, 5)
        mock_cursor.execute.assert_called()


class TestCopilotIntegration(unittest.TestCase):
    """Unit tests for CopilotIntegration class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = CopilotConfig(
            api_endpoint="https://api.copilot.test.com",
            api_key="test_key",
            model_name="gpt-4",
            max_tokens=1000,
            temperature=0.7,
            requests_per_minute=60,
            max_retries=3,
            retry_delay=1
        )
        
        self.sample_articles = [
            NewsArticle(
                id=str(uuid.uuid4()),
                title="Positive News",
                content="This is great news about economic growth.",
                url="https://test.com/positive",
                source="TestSource",
                published_date=datetime.utcnow(),
                scraped_date=datetime.utcnow()
            ),
            NewsArticle(
                id=str(uuid.uuid4()),
                title="Negative News",
                content="This is concerning news about market decline.",
                url="https://test.com/negative",
                source="TestSource",
                published_date=datetime.utcnow(),
                scraped_date=datetime.utcnow()
            )
        ]
    
    def test_copilot_integration_initialization(self):
        """Test CopilotIntegration initialization."""
        integration = CopilotIntegration(self.config)
        self.assertEqual(integration.config, self.config)
        self.assertIsNotNone(integration.rate_limiter)
    
    @patch('aiohttp.ClientSession.post')
    async def test_analyze_sentiment_success(self, mock_post):
        """Test successful sentiment analysis."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "sentiment_score": 0.8,
                        "sentiment_label": "positive",
                        "confidence": 0.9,
                        "summary": "Overall positive sentiment about economic growth."
                    })
                }
            }]
        })
        mock_post.return_value.__aenter__.return_value = mock_response
        
        integration = CopilotIntegration(self.config)
        result = await integration.analyze_sentiment(self.sample_articles)
        
        self.assertIsInstance(result, SentimentAnalysis)
        self.assertEqual(result.sentiment_label, SentimentLabel.POSITIVE)
        self.assertEqual(result.sentiment_score, 0.8)
        self.assertEqual(result.confidence, 0.9)
    
    @patch('aiohttp.ClientSession.post')
    async def test_analyze_sentiment_rate_limit(self, mock_post):
        """Test handling of rate limit errors."""
        # Mock rate limit response
        mock_response = Mock()
        mock_response.status = 429
        mock_response.text = AsyncMock(return_value="Rate limit exceeded")
        mock_post.return_value.__aenter__.return_value = mock_response
        
        integration = CopilotIntegration(self.config)
        
        with self.assertRaises(RateLimitError):
            await integration.analyze_sentiment(self.sample_articles)
    
    @patch('aiohttp.ClientSession.post')
    async def test_generate_summary_success(self, mock_post):
        """Test successful summary generation."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "choices": [{
                "message": {
                    "content": "This is a comprehensive summary of the news articles."
                }
            }]
        })
        mock_post.return_value.__aenter__.return_value = mock_response
        
        integration = CopilotIntegration(self.config)
        summary = await integration.generate_summary(
            self.sample_articles, 
            "financial_analyst"
        )
        
        self.assertIsInstance(summary, str)
        self.assertIn("comprehensive summary", summary)
    
    async def test_batch_process_articles(self):
        """Test batch processing of articles."""
        integration = CopilotIntegration(self.config)
        
        # Create a large list of articles
        large_article_list = []
        for i in range(25):  # More than batch size
            article = NewsArticle(
                id=str(uuid.uuid4()),
                title=f"Article {i}",
                content=f"Content for article {i}",
                url=f"https://test.com/article-{i}",
                source="TestSource",
                published_date=datetime.utcnow(),
                scraped_date=datetime.utcnow()
            )
            large_article_list.append(article)
        
        # Test batch creation
        batches = integration._create_batches(large_article_list, batch_size=10)
        batch_list = list(batches)
        
        self.assertEqual(len(batch_list), 3)  # 25 articles / 10 per batch = 3 batches
        self.assertEqual(len(batch_list[0]), 10)
        self.assertEqual(len(batch_list[1]), 10)
        self.assertEqual(len(batch_list[2]), 5)


class TestCopilotRateLimiter(unittest.TestCase):
    """Unit tests for CopilotRateLimiter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.rate_limiter = CopilotRateLimiter(requests_per_minute=60)
    
    async def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        self.assertEqual(self.rate_limiter.requests_per_minute, 60)
        self.assertEqual(self.rate_limiter.tokens, 60)
    
    async def test_acquire_token_success(self):
        """Test successful token acquisition."""
        # Should not raise any exception
        await self.rate_limiter.acquire()
        self.assertLess(self.rate_limiter.tokens, 60)
    
    async def test_token_refill(self):
        """Test token refill over time."""
        # Consume all tokens
        for _ in range(60):
            await self.rate_limiter.acquire()
        
        self.assertEqual(self.rate_limiter.tokens, 0)
        
        # Simulate time passage
        import time
        original_time = time.time
        time.time = lambda: original_time() + 60  # Add 1 minute
        
        try:
            await self.rate_limiter.acquire()
            # Should have refilled tokens
            self.assertGreater(self.rate_limiter.tokens, 0)
        finally:
            time.time = original_time


class TestUtilityFunctions(unittest.TestCase):
    """Unit tests for utility functions."""
    
    def test_validate_url_valid(self):
        """Test URL validation with valid URLs."""
        valid_urls = [
            "https://example.com",
            "http://test.org/path",
            "https://news.site.com/article/123"
        ]
        
        for url in valid_urls:
            self.assertTrue(validate_url(url))
    
    def test_validate_url_invalid(self):
        """Test URL validation with invalid URLs."""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",
            "",
            None,
            "javascript:alert('xss')"
        ]
        
        for url in invalid_urls:
            self.assertFalse(validate_url(url))
    
    def test_sanitize_text(self):
        """Test text sanitization."""
        test_cases = [
            ("Normal text", "Normal text"),
            ("Text with\nnewlines\r\n", "Text with newlines"),
            ("Text with\ttabs", "Text with tabs"),
            ("Text with  multiple   spaces", "Text with multiple spaces"),
            ("<script>alert('xss')</script>", "alert('xss')"),
            ("", "")
        ]
        
        for input_text, expected in test_cases:
            result = sanitize_text(input_text)
            self.assertEqual(result, expected)
    
    def test_extract_keywords(self):
        """Test keyword extraction from text."""
        text = "This is a test article about machine learning and artificial intelligence."
        keywords = extract_keywords(text, max_keywords=5)
        
        self.assertIsInstance(keywords, list)
        self.assertLessEqual(len(keywords), 5)
        self.assertTrue(all(isinstance(keyword, str) for keyword in keywords))
    
    def test_calculate_text_similarity(self):
        """Test text similarity calculation."""
        text1 = "This is a test article"
        text2 = "This is a test article"
        text3 = "Completely different content"
        
        # Identical texts should have high similarity
        similarity_identical = calculate_text_similarity(text1, text2)
        self.assertGreaterEqual(similarity_identical, 0.9)
        
        # Different texts should have low similarity
        similarity_different = calculate_text_similarity(text1, text3)
        self.assertLess(similarity_different, 0.5)
    
    def test_format_date_for_api(self):
        """Test date formatting for API calls."""
        test_date = datetime(2024, 1, 15, 10, 30, 45)
        formatted = format_date_for_api(test_date)
        
        self.assertIsInstance(formatted, str)
        self.assertIn("2024", formatted)
        self.assertIn("01", formatted)
        self.assertIn("15", formatted)


class TestConfigManager(unittest.TestCase):
    """Unit tests for ConfigManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config_manager = ConfigManager()
    
    @patch.dict(os.environ, {'TEST_CONFIG_VALUE': 'test_value'})
    def test_get_config_from_environment(self):
        """Test configuration retrieval from environment variables."""
        value = self.config_manager.get_config('TEST_CONFIG_VALUE')
        self.assertEqual(value, 'test_value')
    
    def test_get_config_with_default(self):
        """Test configuration retrieval with default value."""
        value = self.config_manager.get_config('NON_EXISTENT_CONFIG', 'default_value')
        self.assertEqual(value, 'default_value')
    
    def test_get_config_missing_required(self):
        """Test error handling for missing required configuration."""
        with self.assertRaises(ValueError):
            self.config_manager.get_config('NON_EXISTENT_REQUIRED_CONFIG')


# Test fixtures and data generators
class TestDataGenerators:
    """Utility class for generating test data."""
    
    @staticmethod
    def create_sample_article(
        title: str = "Sample Article",
        source: str = "TestSource",
        days_ago: int = 0
    ) -> NewsArticle:
        """Create a sample NewsArticle for testing."""
        return NewsArticle(
            id=str(uuid.uuid4()),
            title=title,
            content=f"Sample content for {title}. This is a longer text to simulate real article content.",
            url=f"https://test.com/{title.lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}",
            source=source,
            published_date=datetime.utcnow() - timedelta(days=days_ago),
            scraped_date=datetime.utcnow(),
            keywords=["test", "sample", title.lower()]
        )
    
    @staticmethod
    def create_sample_sentiment(
        article_ids: List[str],
        sentiment_label: SentimentLabel = SentimentLabel.NEUTRAL
    ) -> SentimentAnalysis:
        """Create a sample SentimentAnalysis for testing."""
        return SentimentAnalysis(
            id=str(uuid.uuid4()),
            sentiment_score=0.5 if sentiment_label == SentimentLabel.NEUTRAL else (0.8 if sentiment_label == SentimentLabel.POSITIVE else 0.2),
            sentiment_label=sentiment_label,
            confidence=0.85,
            summary=f"Sample sentiment analysis with {sentiment_label.value} sentiment.",
            analysis_date=datetime.utcnow(),
            model_version="test-1.0",
            role_context="test_analyst",
            article_ids=article_ids
        )


if __name__ == '__main__':
    # Run unit tests
    unittest.main(verbosity=2)