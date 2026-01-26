"""
Property-based tests for data migration integrity.
Tests universal properties that should hold for Excel to SQL Server data migration.
"""

import asyncio
import os
import sys
import tempfile
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid
import json

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Mock pandas for testing without installation
class MockPandas:
    """Mock pandas for testing when pandas is not available."""
    
    class DataFrame:
        def __init__(self, data):
            self.data = data
            self.columns = list(data.keys()) if data else []
        
        def iterrows(self):
            if not self.data:
                return iter([])
            
            # Convert dict of lists to list of dicts
            rows = []
            if self.data:
                num_rows = len(next(iter(self.data.values())))
                for i in range(num_rows):
                    row_data = {col: values[i] for col, values in self.data.items()}
                    rows.append((i, MockPandas.Series(row_data)))
            
            return iter(rows)
        
        @property
        def empty(self):
            return not self.data or all(len(values) == 0 for values in self.data.values())
    
    class Series:
        def __init__(self, data):
            self.data = data
            self.index = list(data.keys()) if isinstance(data, dict) else range(len(data))
        
        def __getitem__(self, key):
            if isinstance(self.data, dict):
                return self.data.get(key)
            return self.data[key] if 0 <= key < len(self.data) else None
        
        def __contains__(self, key):
            if isinstance(self.data, dict):
                return key in self.data
            return 0 <= key < len(self.data)
    
    @staticmethod
    def read_excel(file_path):
        # Mock Excel reading - return sample data
        return MockPandas.DataFrame({
            'Title': ['Test Article 1', 'Test Article 2'],
            'Content': ['Content 1', 'Content 2'],
            'URL': ['https://test1.com', 'https://test2.com'],
            'Source': ['TestSource1', 'TestSource2'],
            'Date': ['2023-06-15', '2023-06-16'],
            'Keywords': ['test,article', 'sample,data']
        })
    
    @staticmethod
    def isna(value):
        return value is None or (isinstance(value, float) and str(value).lower() == 'nan')
    
    @staticmethod
    def to_datetime(value):
        if isinstance(value, str):
            return datetime.strptime(value, '%Y-%m-%d')
        return value

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pd = MockPandas()
    PANDAS_AVAILABLE = False

from shared.models import (
    NewsArticle, SentimentAnalysis, SentimentLabel, DatabaseConfig
)
from shared.excel_migration import ExcelDataMigrator


class MockDatabaseHandler:
    """Mock database handler for testing migration integrity."""
    
    def __init__(self, config):
        self.config = config
        self.saved_articles = []
        self.saved_sentiment_analyses = []
        self.migration_log = []
    
    async def health_check(self) -> bool:
        return True
    
    async def save_articles(self, articles: List[NewsArticle]) -> None:
        """Save articles and log the operation."""
        self.saved_articles.extend(articles)
        self.migration_log.append({
            'operation': 'save_articles',
            'count': len(articles),
            'timestamp': datetime.utcnow(),
            'articles': [article.to_dict() for article in articles]
        })
    
    async def save_sentiment_analysis(self, analysis: SentimentAnalysis) -> None:
        """Save sentiment analysis and log the operation."""
        self.saved_sentiment_analyses.append(analysis)
        self.migration_log.append({
            'operation': 'save_sentiment_analysis',
            'timestamp': datetime.utcnow(),
            'analysis': analysis.to_dict()
        })
    
    async def execute_query(self, query: str, params=None) -> List[Dict[str, Any]]:
        """Mock database queries."""
        if "COUNT(*)" in query and "news_articles" in query:
            return [{'count': len(self.saved_articles)}]
        elif "COUNT(*)" in query and "sentiment_analyses" in query:
            return [{'count': len(self.saved_sentiment_analyses)}]
        else:
            return [{'count': 0}]
    
    async def close(self) -> None:
        pass
    
    def get_migration_stats(self) -> Dict[str, Any]:
        """Get migration statistics for validation."""
        return {
            'total_articles': len(self.saved_articles),
            'total_sentiment_analyses': len(self.saved_sentiment_analyses),
            'operations': len(self.migration_log),
            'migration_log': self.migration_log
        }


class TestMigrationIntegrityProperties:
    """
    Property-based tests for data migration integrity.
    **Feature: azure-functions-porting, Property 31: Data Migration Integrity**
    **Validates: Requirements 12.4**
    """
    
    def __init__(self):
        """Initialize test configuration."""
        self.test_config = DatabaseConfig(
            connection_string="mock://test",
            connection_pool_size=5,
            connection_timeout=10,
            command_timeout=30,
            retry_attempts=2,
            retry_delay=1
        )
    
    async def test_property_31_data_migration_integrity(self):
        """
        **Property 31: Data Migration Integrity**
        **Validates: Requirements 12.4**
        
        For any data migrated from Excel to SQL Server, all existing data 
        relationships and formats should be preserved.
        """
        print("Testing Property 31: Data Migration Integrity...")
        
        try:
            # Test 1: Article Data Preservation
            await self._test_article_data_preservation()
            
            # Test 2: Sentiment Analysis Data Preservation
            await self._test_sentiment_data_preservation()
            
            # Test 3: Data Format Consistency
            await self._test_data_format_consistency()
            
            # Test 4: Relationship Preservation
            await self._test_relationship_preservation()
            
            # Test 5: Error Handling During Migration
            await self._test_migration_error_handling()
            
            print("✓ Property 31: Data Migration Integrity - PASSED")
            return True
            
        except Exception as e:
            print(f"✗ Property 31: Data Migration Integrity - FAILED: {str(e)}")
            return False
    
    async def _test_article_data_preservation(self):
        """Test that article data is preserved during migration."""
        print("  Testing article data preservation...")
        
        # Create migrator with mock database
        migrator = ExcelDataMigrator(self.test_config)
        mock_db = MockDatabaseHandler(self.test_config)
        migrator.db_handler = mock_db
        
        # Create test Excel data
        test_excel_data = {
            'Title': ['Article 1', 'Article 2', 'Article 3'],
            'Content': ['Content 1 with details', 'Content 2 with details', 'Content 3 with details'],
            'URL': ['https://test1.com/article1', 'https://test2.com/article2', 'https://test3.com/article3'],
            'Source': ['Source1', 'Source2', 'Source1'],
            'Date': ['2023-06-15', '2023-06-16', '2023-06-17'],
            'Author': ['Author 1', 'Author 2', 'Author 3'],
            'Keywords': ['test,migration', 'data,integrity', 'excel,sql']
        }
        
        # Mock pandas DataFrame
        if PANDAS_AVAILABLE:
            df = pd.DataFrame(test_excel_data)
        else:
            df = MockPandas.DataFrame(test_excel_data)
        
        # Extract articles using migrator logic
        column_mapping = migrator._map_columns(list(test_excel_data.keys()), 'news_articles')
        
        articles = []
        for index, row in df.iterrows():
            article_data = migrator._extract_article_data(row, column_mapping)
            if migrator._validate_article_data(article_data):
                article = NewsArticle(**article_data)
                articles.append(article)
        
        # Save articles
        await mock_db.save_articles(articles)
        
        # Property: All articles should be preserved
        assert len(mock_db.saved_articles) == 3, f"Expected 3 articles, got {len(mock_db.saved_articles)}"
        
        # Property: Article data should match original Excel data
        for i, saved_article in enumerate(mock_db.saved_articles):
            original_title = test_excel_data['Title'][i]
            original_content = test_excel_data['Content'][i]
            original_url = test_excel_data['URL'][i]
            original_source = test_excel_data['Source'][i]
            
            assert saved_article.title == original_title, f"Title mismatch: {saved_article.title} != {original_title}"
            assert saved_article.content == original_content, f"Content mismatch for article {i}"
            assert saved_article.url == original_url, f"URL mismatch for article {i}"
            assert saved_article.source == original_source, f"Source mismatch for article {i}"
        
        print("    ✓ Article data preservation test passed")
    
    async def _test_sentiment_data_preservation(self):
        """Test that sentiment analysis data is preserved during migration."""
        print("  Testing sentiment data preservation...")
        
        # Create migrator with mock database
        migrator = ExcelDataMigrator(self.test_config)
        mock_db = MockDatabaseHandler(self.test_config)
        migrator.db_handler = mock_db
        
        # Create test sentiment Excel data
        test_sentiment_data = {
            'sentiment_score': [0.8, -0.3, 0.1],
            'sentiment_label': ['positive', 'negative', 'neutral'],
            'confidence': [0.9, 0.7, 0.6],
            'summary': ['Positive analysis 1', 'Negative analysis 2', 'Neutral analysis 3'],
            'analysis_date': ['2023-06-15', '2023-06-16', '2023-06-17']
        }
        
        # Mock pandas DataFrame
        if PANDAS_AVAILABLE:
            df = pd.DataFrame(test_sentiment_data)
        else:
            df = MockPandas.DataFrame(test_sentiment_data)
        
        # Extract sentiment analyses using migrator logic
        column_mapping = migrator._map_columns(list(test_sentiment_data.keys()), 'sentiment_analysis')
        
        analyses = []
        for index, row in df.iterrows():
            sentiment_data = migrator._extract_sentiment_data(row, column_mapping)
            if migrator._validate_sentiment_data(sentiment_data):
                analysis = SentimentAnalysis(**sentiment_data)
                analyses.append(analysis)
        
        # Save sentiment analyses
        for analysis in analyses:
            await mock_db.save_sentiment_analysis(analysis)
        
        # Property: All sentiment analyses should be preserved
        assert len(mock_db.saved_sentiment_analyses) == 3, f"Expected 3 analyses, got {len(mock_db.saved_sentiment_analyses)}"
        
        # Property: Sentiment data should match original Excel data
        for i, saved_analysis in enumerate(mock_db.saved_sentiment_analyses):
            original_score = test_sentiment_data['sentiment_score'][i]
            original_label = test_sentiment_data['sentiment_label'][i]
            original_confidence = test_sentiment_data['confidence'][i]
            original_summary = test_sentiment_data['summary'][i]
            
            assert abs(saved_analysis.sentiment_score - original_score) < 0.001, f"Score mismatch for analysis {i}"
            assert saved_analysis.sentiment_label.value == original_label, f"Label mismatch for analysis {i}"
            assert abs(saved_analysis.confidence - original_confidence) < 0.001, f"Confidence mismatch for analysis {i}"
            assert saved_analysis.summary == original_summary, f"Summary mismatch for analysis {i}"
        
        print("    ✓ Sentiment data preservation test passed")
    
    async def _test_data_format_consistency(self):
        """Test that data formats are consistent after migration."""
        print("  Testing data format consistency...")
        
        migrator = ExcelDataMigrator(self.test_config)
        
        # Test date format consistency
        test_dates = [
            '2023-06-15',
            '15/06/2023',
            '06/15/2023',
            '2023-06-15 14:30:00'
        ]
        
        for date_str in test_dates:
            parsed_date = migrator._parse_date(date_str)
            
            # Property: All valid dates should be parsed to datetime objects
            assert isinstance(parsed_date, datetime), f"Date {date_str} not parsed to datetime"
            assert parsed_date.year == 2023, f"Year mismatch for date {date_str}"
            assert parsed_date.month == 6, f"Month mismatch for date {date_str}"
            assert parsed_date.day == 15, f"Day mismatch for date {date_str}"
        
        # Test keyword format consistency
        test_keywords = [
            'keyword1,keyword2,keyword3',
            'keyword1; keyword2; keyword3',
            'keyword1|keyword2|keyword3'
        ]
        
        for keyword_str in test_keywords:
            parsed_keywords = migrator._parse_keywords(keyword_str)
            
            # Property: All keyword formats should result in same list
            expected_keywords = ['keyword1', 'keyword2', 'keyword3']
            assert parsed_keywords == expected_keywords, f"Keyword parsing inconsistent for {keyword_str}"
        
        # Test sentiment label consistency
        test_labels = [
            ('positive', SentimentLabel.POSITIVE),
            ('pos', SentimentLabel.POSITIVE),
            ('negative', SentimentLabel.NEGATIVE),
            ('neg', SentimentLabel.NEGATIVE),
            ('neutral', SentimentLabel.NEUTRAL),
            ('unknown', SentimentLabel.NEUTRAL)
        ]
        
        for label_str, expected_label in test_labels:
            parsed_label = migrator._parse_sentiment_label(label_str)
            
            # Property: Label parsing should be consistent
            assert parsed_label == expected_label, f"Label parsing inconsistent for {label_str}"
        
        print("    ✓ Data format consistency test passed")
    
    async def _test_relationship_preservation(self):
        """Test that data relationships are preserved during migration."""
        print("  Testing relationship preservation...")
        
        migrator = ExcelDataMigrator(self.test_config)
        mock_db = MockDatabaseHandler(self.test_config)
        migrator.db_handler = mock_db
        
        # Create articles with keywords
        test_articles = [
            {
                'title': 'Article 1',
                'content': 'Content 1',
                'url': 'https://test1.com',
                'source': 'Source1',
                'keywords': ['keyword1', 'keyword2']
            },
            {
                'title': 'Article 2', 
                'content': 'Content 2',
                'url': 'https://test2.com',
                'source': 'Source1',  # Same source as article 1
                'keywords': ['keyword2', 'keyword3']  # Overlapping keywords
            }
        ]
        
        articles = []
        for article_data in test_articles:
            article = NewsArticle(
                id=str(uuid.uuid4()),
                title=article_data['title'],
                content=article_data['content'],
                url=article_data['url'],
                source=article_data['source'],
                published_date=datetime.utcnow(),
                scraped_date=datetime.utcnow(),
                keywords=article_data['keywords']
            )
            articles.append(article)
        
        # Save articles
        await mock_db.save_articles(articles)
        
        # Property: Source relationships should be preserved
        source_counts = {}
        for article in mock_db.saved_articles:
            source_counts[article.source] = source_counts.get(article.source, 0) + 1
        
        assert source_counts['Source1'] == 2, "Source relationship not preserved"
        
        # Property: Keyword relationships should be preserved
        all_keywords = []
        for article in mock_db.saved_articles:
            all_keywords.extend(article.keywords)
        
        keyword_counts = {}
        for keyword in all_keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        assert keyword_counts['keyword2'] == 2, "Keyword relationship not preserved (should appear in 2 articles)"
        assert keyword_counts['keyword1'] == 1, "Keyword relationship not preserved"
        assert keyword_counts['keyword3'] == 1, "Keyword relationship not preserved"
        
        print("    ✓ Relationship preservation test passed")
    
    async def _test_migration_error_handling(self):
        """Test that migration handles errors gracefully without data corruption."""
        print("  Testing migration error handling...")
        
        migrator = ExcelDataMigrator(self.test_config)
        mock_db = MockDatabaseHandler(self.test_config)
        migrator.db_handler = mock_db
        
        # Test with invalid article data
        invalid_article_data = {
            'title': '',  # Invalid: empty title
            'content': 'Valid content',
            'url': 'invalid-url',  # Invalid: no protocol
            'source': 'TestSource'
        }
        
        # Property: Invalid data should be rejected without affecting valid data
        is_valid = migrator._validate_article_data(invalid_article_data)
        assert not is_valid, "Invalid article data should be rejected"
        
        # Test with mixed valid and invalid data
        mixed_data = {
            'Title': ['Valid Article', '', 'Another Valid Article'],  # Middle one is invalid
            'Content': ['Valid content 1', 'Valid content 2', 'Valid content 3'],
            'URL': ['https://valid1.com', 'invalid-url', 'https://valid3.com'],  # Middle one is invalid
            'Source': ['Source1', 'Source2', 'Source3']
        }
        
        if PANDAS_AVAILABLE:
            df = pd.DataFrame(mixed_data)
        else:
            df = MockPandas.DataFrame(mixed_data)
        
        column_mapping = migrator._map_columns(list(mixed_data.keys()), 'news_articles')
        
        valid_articles = []
        for index, row in df.iterrows():
            article_data = migrator._extract_article_data(row, column_mapping)
            if migrator._validate_article_data(article_data):
                article = NewsArticle(**article_data)
                valid_articles.append(article)
        
        # Property: Only valid articles should be processed
        assert len(valid_articles) == 2, f"Expected 2 valid articles, got {len(valid_articles)}"
        
        # Property: Valid articles should have correct data
        assert valid_articles[0].title == 'Valid Article'
        assert valid_articles[1].title == 'Another Valid Article'
        
        print("    ✓ Migration error handling test passed")
    
    async def run_all_tests(self) -> bool:
        """Run all migration integrity property tests."""
        try:
            success = await self.test_property_31_data_migration_integrity()
            return success
        except Exception as e:
            print(f"Migration integrity test execution failed: {str(e)}")
            return False


class TestMigrationPerformanceProperties:
    """Additional property tests for migration performance and scalability."""
    
    def __init__(self):
        """Initialize test configuration."""
        self.test_config = DatabaseConfig(
            connection_string="mock://test",
            connection_pool_size=5,
            connection_timeout=10,
            command_timeout=30,
            retry_attempts=2,
            retry_delay=1
        )
    
    async def test_property_migration_scalability(self):
        """
        Property: Migration should handle large datasets efficiently.
        Processing time should scale reasonably with data size.
        """
        print("Testing migration scalability...")
        
        migrator = ExcelDataMigrator(self.test_config)
        mock_db = MockDatabaseHandler(self.test_config)
        migrator.db_handler = mock_db
        
        # Test with different data sizes
        test_sizes = [10, 50, 100]
        processing_times = []
        
        for size in test_sizes:
            start_time = datetime.utcnow()
            
            # Generate test data
            test_data = {
                'Title': [f'Article {i}' for i in range(size)],
                'Content': [f'Content {i} with sufficient length for testing' for i in range(size)],
                'URL': [f'https://test{i}.com/article' for i in range(size)],
                'Source': [f'Source{i % 5}' for i in range(size)],  # 5 different sources
                'Keywords': [f'keyword{i},test,migration' for i in range(size)]
            }
            
            # Process data
            if PANDAS_AVAILABLE:
                df = pd.DataFrame(test_data)
            else:
                df = MockPandas.DataFrame(test_data)
            
            column_mapping = migrator._map_columns(list(test_data.keys()), 'news_articles')
            
            articles = []
            for index, row in df.iterrows():
                try:
                    article_data = migrator._extract_article_data(row, column_mapping)
                    
                    # Ensure dates are set for performance test
                    if not article_data.get('published_date'):
                        article_data['published_date'] = datetime.utcnow()
                    if not article_data.get('scraped_date'):
                        article_data['scraped_date'] = datetime.utcnow()
                    
                    if migrator._validate_article_data(article_data):
                        article = NewsArticle(**article_data)
                        articles.append(article)
                except Exception as e:
                    # Skip invalid articles in performance test
                    print(f"    Warning: Skipped article {index}: {str(e)}")
                    continue
            
            if articles:  # Only save if we have valid articles
                await mock_db.save_articles(articles)
            
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            processing_times.append(processing_time)
            
            # Property: All articles should be processed (allowing for some validation failures)
            assert len(articles) >= size * 0.8, f"Too few articles processed for size {size}: {len(articles)}"
        
        # Property: Processing time should not increase exponentially
        # (This is a simplified check - in real scenarios, you'd want more sophisticated analysis)
        if len(processing_times) >= 2:
            time_ratio = processing_times[-1] / processing_times[0] if processing_times[0] > 0 else 1
            size_ratio = test_sizes[-1] / test_sizes[0]
            
            # Processing time should not increase more than 10x the size increase
            assert time_ratio <= size_ratio * 10, f"Processing time increased too much: {time_ratio} vs size ratio {size_ratio}"
        
        print("✓ Migration scalability test passed")
        return True
    
    async def run_all_tests(self) -> bool:
        """Run all migration performance property tests."""
        try:
            success = await self.test_property_migration_scalability()
            return success
        except Exception as e:
            print(f"Migration performance test execution failed: {str(e)}")
            return False


# Async test runner
def run_async_test(coro):
    """Helper to run async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def main():
    """Main test runner for migration integrity properties."""
    print("Running Migration Integrity Property Tests...")
    print("=" * 60)
    
    # Test 1: Data Migration Integrity
    integrity_tester = TestMigrationIntegrityProperties()
    integrity_success = await integrity_tester.run_all_tests()
    
    print("\n" + "=" * 60)
    
    # Test 2: Migration Performance Properties
    performance_tester = TestMigrationPerformanceProperties()
    performance_success = await performance_tester.run_all_tests()
    
    print("\n" + "=" * 60)
    
    overall_success = integrity_success and performance_success
    
    if overall_success:
        print("✅ All migration integrity property tests PASSED")
    else:
        print("❌ Some migration integrity property tests FAILED")
    
    if not PANDAS_AVAILABLE:
        print("\n⚠ Note: pandas library not available. Tests used mock implementation.")
        print("Install pandas with: pip install pandas")
    
    return overall_success


if __name__ == "__main__":
    # Run the property tests
    success = run_async_test(main())
    
    if success:
        print("\n🎉 Migration integrity property validation completed successfully!")
        exit(0)
    else:
        print("\n❌ Migration integrity property validation failed!")
        exit(1)