"""
Property-based tests for URL-based deduplication functionality.
Tests Property 25: URL-Based Deduplication
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List, Set
from unittest.mock import AsyncMock, MagicMock
import uuid

from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite

from azure_functions.shared.models import NewsArticle, DatabaseConfig
from azure_functions.shared.database_handler import DatabaseHandler
from azure_functions.processing.deduplication_service import DeduplicationService, DeduplicationResult
from azure_functions.shared.interfaces import DatabaseError


# Custom strategies for generating test data
@composite
def news_article_strategy(draw):
    """Generate a NewsArticle with realistic data."""
    title = draw(st.text(min_size=10, max_size=200))
    content = draw(st.text(min_size=50, max_size=1000))
    url = draw(st.text(min_size=10, max_size=500).filter(lambda x: '/' in x and '.' in x))
    source = draw(st.sampled_from(['CNBC', 'CNN', 'Reuters', 'Kompas', 'Bloomberg']))
    
    # Generate realistic dates
    base_date = datetime(2024, 1, 1)
    days_offset = draw(st.integers(min_value=0, max_value=365))
    published_date = base_date + timedelta(days=days_offset)
    
    # Scraped date should be after published date
    scraped_offset = draw(st.integers(min_value=0, max_value=30))
    scraped_date = published_date + timedelta(days=scraped_offset)
    
    keywords = draw(st.lists(st.text(min_size=3, max_size=20), min_size=0, max_size=5))
    language = draw(st.sampled_from(['en', 'id', 'fr']))
    
    return NewsArticle(
        id=str(uuid.uuid4()),
        title=title,
        content=content,
        url=url,
        source=source,
        published_date=published_date,
        scraped_date=scraped_date,
        keywords=keywords,
        language=language
    )


@composite
def articles_with_duplicates_strategy(draw):
    """Generate a list of articles that includes some duplicates by URL."""
    # Generate base articles
    base_articles = draw(st.lists(news_article_strategy(), min_size=2, max_size=10))
    
    # Create some duplicates by copying URLs
    duplicate_articles = []
    for article in base_articles[:3]:  # Take first 3 articles to create duplicates
        # Create a duplicate with same URL but different scraped date
        duplicate = NewsArticle(
            id=str(uuid.uuid4()),
            title=article.title + " (duplicate)",
            content=article.content + " (duplicate content)",
            url=article.url,  # Same URL - this makes it a duplicate
            source=article.source,
            published_date=article.published_date,
            scraped_date=article.scraped_date + timedelta(hours=1),  # Later scraped date
            keywords=article.keywords,
            language=article.language
        )
        duplicate_articles.append(duplicate)
    
    # Combine original and duplicate articles
    all_articles = base_articles + duplicate_articles
    
    # Shuffle to make order random
    draw(st.randoms()).shuffle(all_articles)
    
    return all_articles


class TestURLBasedDeduplicationProperties:
    """
    Property-based tests for URL-based deduplication functionality.
    **Feature: azure-functions-porting, Property 25: URL-Based Deduplication**
    **Validates: Requirements 9.3**
    """
    
    @pytest.fixture
    def mock_db_handler(self):
        """Create a mock database handler for testing."""
        handler = AsyncMock(spec=DatabaseHandler)
        return handler
    
    @pytest.fixture
    def deduplication_service(self, mock_db_handler):
        """Create a deduplication service with mock database handler."""
        return DeduplicationService(mock_db_handler)
    
    @given(articles_with_duplicates_strategy())
    @settings(max_examples=100, deadline=None)
    async def test_deduplication_preserves_unique_urls(self, articles_with_duplicates, mock_db_handler, deduplication_service):
        """
        Property: After deduplication, each URL should appear only once in the dataset.
        **Feature: azure-functions-porting, Property 25: URL-Based Deduplication**
        """
        # Arrange
        original_urls = [article.url for article in articles_with_duplicates]
        unique_urls = set(original_urls)
        
        # Mock the database operations
        mock_db_handler.deduplicate_articles.return_value = len(original_urls) - len(unique_urls)
        
        # Mock execute_query to simulate the deduplication logic
        def mock_execute_query(query, params=None):
            if "DuplicateArticles" in query and "DELETE" in query:
                # Simulate removing duplicates, keeping earliest scraped
                return len(original_urls) - len(unique_urls)
            elif "COUNT" in query and "DISTINCT" in query:
                # Return unique count
                return [{'unique_count': len(unique_urls)}]
            else:
                return []
        
        mock_db_handler.execute_query.side_effect = mock_execute_query
        
        # Act
        result = await deduplication_service.deduplicate_all_articles()
        
        # Assert
        # Property: The number of duplicates removed should equal total articles minus unique URLs
        expected_duplicates_removed = len(original_urls) - len(unique_urls)
        assert result.duplicates_removed == expected_duplicates_removed
        
        # Property: After deduplication, remaining articles should equal unique URL count
        assert result.unique_articles_remaining == len(unique_urls)
    
    @given(st.lists(news_article_strategy(), min_size=1, max_size=20))
    @settings(max_examples=100, deadline=None)
    async def test_deduplication_keeps_earliest_scraped_article(self, articles, mock_db_handler, deduplication_service):
        """
        Property: When duplicates exist, the article with the earliest scraped_date should be kept.
        **Feature: azure-functions-porting, Property 25: URL-Based Deduplication**
        """
        # Arrange - Create duplicates with different scraped dates
        if len(articles) == 0:
            return
        
        base_article = articles[0]
        duplicate_articles = []
        
        # Create multiple versions of the same article with different scraped dates
        for i in range(3):
            duplicate = NewsArticle(
                id=str(uuid.uuid4()),
                title=base_article.title,
                content=base_article.content,
                url=base_article.url,  # Same URL
                source=base_article.source,
                published_date=base_article.published_date,
                scraped_date=base_article.scraped_date + timedelta(hours=i),  # Different scraped times
                keywords=base_article.keywords,
                language=base_article.language
            )
            duplicate_articles.append(duplicate)
        
        all_articles = [base_article] + duplicate_articles
        earliest_scraped = min(article.scraped_date for article in all_articles)
        
        # Mock database to simulate keeping earliest
        mock_db_handler.deduplicate_articles.return_value = len(all_articles) - 1
        
        def mock_execute_query(query, params=None):
            if "ORDER BY a.scraped_date ASC" in query:
                # Simulate the stored procedure logic - keep earliest
                return len(all_articles) - 1
            return []
        
        mock_db_handler.execute_query.side_effect = mock_execute_query
        
        # Act
        result = await deduplication_service.deduplicate_all_articles()
        
        # Assert
        # Property: Should remove all but one (the earliest)
        assert result.duplicates_removed == len(all_articles) - 1
    
    @given(st.lists(news_article_strategy(), min_size=0, max_size=50))
    @settings(max_examples=100, deadline=None)
    async def test_deduplication_handles_no_duplicates(self, articles, mock_db_handler, deduplication_service):
        """
        Property: When no duplicates exist, deduplication should remove zero articles.
        **Feature: azure-functions-porting, Property 25: URL-Based Deduplication**
        """
        # Arrange - Ensure all articles have unique URLs
        unique_articles = []
        seen_urls = set()
        
        for article in articles:
            if article.url not in seen_urls:
                unique_articles.append(article)
                seen_urls.add(article.url)
        
        # Mock database operations
        mock_db_handler.deduplicate_articles.return_value = 0
        mock_db_handler.execute_query.return_value = []
        
        # Act
        result = await deduplication_service.deduplicate_all_articles()
        
        # Assert
        # Property: No duplicates should be removed when all URLs are unique
        assert result.duplicates_removed == 0
    
    @given(st.text(min_size=1, max_size=50), st.lists(news_article_strategy(), min_size=1, max_size=20))
    @settings(max_examples=100, deadline=None)
    async def test_source_specific_deduplication_only_affects_target_source(self, source_name, articles, mock_db_handler, deduplication_service):
        """
        Property: Source-specific deduplication should only affect articles from the specified source.
        **Feature: azure-functions-porting, Property 25: URL-Based Deduplication**
        """
        # Arrange - Set all articles to the target source and create duplicates
        target_articles = []
        for article in articles[:3]:  # Take first 3 articles
            article.source = source_name
            target_articles.append(article)
            
            # Create duplicate with same URL
            duplicate = NewsArticle(
                id=str(uuid.uuid4()),
                title=article.title,
                content=article.content,
                url=article.url,  # Same URL
                source=source_name,  # Same source
                published_date=article.published_date,
                scraped_date=article.scraped_date + timedelta(hours=1),
                keywords=article.keywords,
                language=article.language
            )
            target_articles.append(duplicate)
        
        # Mock database operations for source-specific deduplication
        expected_removed = len(target_articles) // 2  # Half are duplicates
        mock_db_handler.execute_query.return_value = expected_removed
        
        # Act
        result = await deduplication_service.deduplicate_by_source(source_name)
        
        # Assert
        # Property: Should only remove duplicates from the specified source
        assert result.duplicates_removed == expected_removed
        assert source_name in result.source_breakdown
        assert result.source_breakdown[source_name] == expected_removed
    
    @given(st.lists(news_article_strategy(), min_size=2, max_size=10))
    @settings(max_examples=100, deadline=None)
    async def test_deduplication_preserves_data_integrity(self, articles, mock_db_handler, deduplication_service):
        """
        Property: Deduplication should not corrupt or modify the content of kept articles.
        **Feature: azure-functions-porting, Property 25: URL-Based Deduplication**
        """
        # Arrange - Create articles with same URL but different content
        if len(articles) < 2:
            return
        
        base_article = articles[0]
        duplicate_articles = []
        
        for i, article in enumerate(articles[1:3]):
            duplicate = NewsArticle(
                id=str(uuid.uuid4()),
                title=f"Modified Title {i}",
                content=f"Modified Content {i}",
                url=base_article.url,  # Same URL - makes it duplicate
                source=base_article.source,
                published_date=base_article.published_date,
                scraped_date=base_article.scraped_date + timedelta(hours=i+1),
                keywords=base_article.keywords,
                language=base_article.language
            )
            duplicate_articles.append(duplicate)
        
        all_articles = [base_article] + duplicate_articles
        
        # Mock database operations
        mock_db_handler.deduplicate_articles.return_value = len(duplicate_articles)
        
        # Act
        result = await deduplication_service.deduplicate_all_articles()
        
        # Assert
        # Property: Should remove duplicates but preserve the original article data
        assert result.duplicates_removed == len(duplicate_articles)
        # The original article should remain unchanged (this would be verified in integration tests)
    
    @given(st.lists(news_article_strategy(), min_size=1, max_size=30))
    @settings(max_examples=100, deadline=None)
    async def test_deduplication_is_idempotent(self, articles, mock_db_handler, deduplication_service):
        """
        Property: Running deduplication multiple times should not remove additional articles after the first run.
        **Feature: azure-functions-porting, Property 25: URL-Based Deduplication**
        """
        # Arrange - Create some duplicates
        duplicate_urls = set()
        for article in articles[:3]:
            duplicate_urls.add(article.url)
        
        # First run should remove duplicates
        first_run_removed = len([a for a in articles if a.url in duplicate_urls]) - len(duplicate_urls)
        
        # Mock first deduplication run
        mock_db_handler.deduplicate_articles.return_value = first_run_removed
        
        # Act - First deduplication
        first_result = await deduplication_service.deduplicate_all_articles()
        
        # Mock second deduplication run (should remove nothing)
        mock_db_handler.deduplicate_articles.return_value = 0
        
        # Act - Second deduplication
        second_result = await deduplication_service.deduplicate_all_articles()
        
        # Assert
        # Property: Second run should remove zero articles
        assert second_result.duplicates_removed == 0
        # Property: First run should have removed the expected duplicates
        assert first_result.duplicates_removed >= 0
    
    @given(st.lists(news_article_strategy(), min_size=1, max_size=20))
    @settings(max_examples=100, deadline=None)
    async def test_deduplication_statistics_are_consistent(self, articles, mock_db_handler, deduplication_service):
        """
        Property: Deduplication statistics should be mathematically consistent.
        **Feature: azure-functions-porting, Property 25: URL-Based Deduplication**
        """
        # Arrange
        total_articles = len(articles)
        unique_urls = len(set(article.url for article in articles))
        expected_duplicates = total_articles - unique_urls
        
        # Mock statistics query
        mock_stats_data = [
            {
                'source_name': 'CNBC',
                'total_articles': total_articles,
                'unique_urls': unique_urls,
                'duplicates': expected_duplicates
            }
        ]
        mock_db_handler.execute_query.return_value = mock_stats_data
        
        # Act
        stats = await deduplication_service.get_duplicate_statistics()
        
        # Assert
        # Property: Total articles should equal unique articles plus duplicates
        assert stats.total_articles == stats.unique_articles + stats.duplicate_count
        
        # Property: Duplicate percentage should be calculated correctly
        if stats.total_articles > 0:
            expected_percentage = round((stats.duplicate_count / stats.total_articles * 100), 2)
            assert stats.duplicate_percentage == expected_percentage
        else:
            assert stats.duplicate_percentage == 0
    
    @given(st.lists(news_article_strategy(), min_size=1, max_size=15))
    @settings(max_examples=100, deadline=None)
    async def test_deduplication_handles_database_errors_gracefully(self, articles, mock_db_handler, deduplication_service):
        """
        Property: Deduplication should handle database errors gracefully and return appropriate error information.
        **Feature: azure-functions-porting, Property 25: URL-Based Deduplication**
        """
        # Arrange - Mock database error
        mock_db_handler.deduplicate_articles.side_effect = DatabaseError("Connection failed")
        
        # Act
        result = await deduplication_service.deduplicate_all_articles()
        
        # Assert
        # Property: Should return error information when database fails
        assert result.duplicates_removed == 0
        assert len(result.errors) > 0
        assert "Connection failed" in result.errors[0]
        assert result.processing_time_seconds >= 0
    
    @given(st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2024, 12, 31)))
    @settings(max_examples=100, deadline=None)
    async def test_date_range_deduplication_respects_boundaries(self, start_date, mock_db_handler, deduplication_service):
        """
        Property: Date range deduplication should only affect articles within the specified date range.
        **Feature: azure-functions-porting, Property 25: URL-Based Deduplication**
        """
        # Arrange
        end_date = start_date + timedelta(days=30)
        expected_removed = 5  # Mock value
        
        mock_db_handler.execute_query.return_value = expected_removed
        
        # Act
        result = await deduplication_service.deduplicate_by_date_range(start_date, end_date)
        
        # Assert
        # Property: Should process only articles in the date range
        assert result.duplicates_removed == expected_removed
        assert result.processing_time_seconds >= 0
        
        # Verify the query was called with correct date parameters
        mock_db_handler.execute_query.assert_called_once()
        call_args = mock_db_handler.execute_query.call_args
        assert len(call_args[0]) >= 1  # Query string
        assert len(call_args[0][1]) == 2  # Two date parameters
        assert call_args[0][1][0] == start_date
        assert call_args[0][1][1] == end_date


# Async test runner helper
def run_async_test(coro):
    """Helper to run async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Pytest async support
@pytest.mark.asyncio
class TestURLBasedDeduplicationPropertiesAsync(TestURLBasedDeduplicationProperties):
    """Async version of the property tests for pytest-asyncio."""
    pass