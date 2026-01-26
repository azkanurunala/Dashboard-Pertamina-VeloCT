"""
Test script for Excel migration functionality.
Tests the Excel to SQL Server data migration without requiring actual database connection.
"""

import os
import sys
import asyncio
from datetime import datetime
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

from shared.models import DatabaseConfig, NewsArticle, SentimentAnalysis
from shared.excel_migration import ExcelDataMigrator


class MockDatabaseHandler:
    """Mock database handler for testing without actual database connection."""
    
    def __init__(self, config):
        self.config = config
        self.saved_articles = []
        self.saved_sentiment_analyses = []
    
    async def health_check(self) -> bool:
        return True
    
    async def save_articles(self, articles: List[NewsArticle]) -> None:
        self.saved_articles.extend(articles)
        print(f"Mock: Saved {len(articles)} articles")
    
    async def save_sentiment_analysis(self, analysis: SentimentAnalysis) -> None:
        self.saved_sentiment_analyses.append(analysis)
        print(f"Mock: Saved sentiment analysis: {analysis.summary[:50]}...")
    
    async def execute_query(self, query: str, params=None) -> List[Dict[str, Any]]:
        # Mock database statistics
        if "COUNT(*)" in query and "news_articles" in query:
            return [{'count': len(self.saved_articles)}]
        elif "COUNT(*)" in query and "sentiment_analyses" in query:
            return [{'count': len(self.saved_sentiment_analyses)}]
        else:
            return [{'count': 0}]
    
    async def close(self) -> None:
        pass


class TestExcelMigration:
    """Test class for Excel migration functionality."""
    
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
    
    async def test_column_mapping(self):
        """Test column mapping functionality."""
        print("Testing column mapping...")
        
        migrator = ExcelDataMigrator(self.test_config)
        
        # Test news articles column mapping
        excel_columns = ['Title', 'Content', 'URL', 'Source', 'Date', 'Author']
        mapping = migrator._map_columns(excel_columns, 'news_articles')
        
        expected_mappings = {
            'title': 'Title',
            'content': 'Content', 
            'url': 'URL',
            'source': 'Source',
            'published_date': 'Date',
            'author': 'Author'
        }
        
        for field, expected_col in expected_mappings.items():
            assert mapping.get(field) == expected_col, f"Column mapping failed for {field}"
        
        print("✓ Column mapping test passed")
    
    async def test_data_validation(self):
        """Test data validation functionality."""
        print("Testing data validation...")
        
        migrator = ExcelDataMigrator(self.test_config)
        
        # Test valid article data
        valid_article_data = {
            'title': 'Test Article',
            'content': 'This is test content for the article.',
            'url': 'https://test.com/article',
            'source': 'TestSource',
            'published_date': datetime.utcnow(),
            'scraped_date': datetime.utcnow(),
            'language': 'en',
            'author': 'Test Author',
            'category': 'test',
            'keywords': ['test', 'article']
        }
        
        assert migrator._validate_article_data(valid_article_data), "Valid article data should pass validation"
        
        # Test invalid article data (missing title)
        invalid_article_data = valid_article_data.copy()
        invalid_article_data['title'] = ''
        
        assert not migrator._validate_article_data(invalid_article_data), "Invalid article data should fail validation"
        
        # Test valid sentiment data
        valid_sentiment_data = {
            'sentiment_score': 0.5,
            'sentiment_label': 'neutral',
            'confidence': 0.8,
            'summary': 'This is a test sentiment analysis summary.',
            'analysis_date': datetime.utcnow(),
            'model_version': 'test-1.0',
            'role_context': 'test',
            'article_ids': []
        }
        
        assert migrator._validate_sentiment_data(valid_sentiment_data), "Valid sentiment data should pass validation"
        
        # Test invalid sentiment data (score out of range)
        invalid_sentiment_data = valid_sentiment_data.copy()
        invalid_sentiment_data['sentiment_score'] = 2.0  # Out of range
        
        assert not migrator._validate_sentiment_data(invalid_sentiment_data), "Invalid sentiment data should fail validation"
        
        print("✓ Data validation test passed")
    
    async def test_date_parsing(self):
        """Test date parsing functionality."""
        print("Testing date parsing...")
        
        migrator = ExcelDataMigrator(self.test_config)
        
        # Test various date formats
        test_dates = [
            ('2023-06-15 14:30:00', datetime(2023, 6, 15, 14, 30, 0)),
            ('2023-06-15', datetime(2023, 6, 15)),
            ('15/06/2023', datetime(2023, 6, 15)),
            ('06/15/2023', datetime(2023, 6, 15)),
            (datetime(2023, 6, 15), datetime(2023, 6, 15)),
            ('', None),
            (None, None)
        ]
        
        for date_input, expected in test_dates:
            result = migrator._parse_date(date_input)
            if expected is None:
                assert result is None, f"Expected None for input '{date_input}', got {result}"
            else:
                assert result is not None, f"Expected date for input '{date_input}', got None"
                # Compare dates (ignore time for date-only inputs)
                if result.time() == datetime.min.time() and expected.time() != datetime.min.time():
                    expected = expected.replace(hour=0, minute=0, second=0, microsecond=0)
                assert result.date() == expected.date(), f"Date mismatch for input '{date_input}'"
        
        print("✓ Date parsing test passed")
    
    async def test_keyword_parsing(self):
        """Test keyword parsing functionality."""
        print("Testing keyword parsing...")
        
        migrator = ExcelDataMigrator(self.test_config)
        
        # Test various keyword formats
        test_keywords = [
            ('keyword1,keyword2,keyword3', ['keyword1', 'keyword2', 'keyword3']),
            ('keyword1; keyword2; keyword3', ['keyword1', 'keyword2', 'keyword3']),
            ('keyword1|keyword2|keyword3', ['keyword1', 'keyword2', 'keyword3']),
            ('keyword1\nkeyword2\nkeyword3', ['keyword1', 'keyword2', 'keyword3']),
            ('single_keyword', ['single_keyword']),
            ('', []),
            (None, [])
        ]
        
        for keyword_input, expected in test_keywords:
            result = migrator._parse_keywords(keyword_input)
            assert result == expected, f"Keyword parsing failed for input '{keyword_input}': expected {expected}, got {result}"
        
        print("✓ Keyword parsing test passed")
    
    async def test_file_type_determination(self):
        """Test file type determination functionality."""
        print("Testing file type determination...")
        
        migrator = ExcelDataMigrator(self.test_config)
        
        # Test various filenames
        test_files = [
            ('news_scrapping.xlsx', 'news_articles'),
            ('sentiment_analysis.xlsx', 'sentiment_analysis'),
            ('berita_harian.xlsx', 'news_articles'),
            ('analisis_sentimen.xlsx', 'sentiment_analysis'),
            ('data_articles.xlsx', 'news_articles'),
            ('mood_analysis.xlsx', 'sentiment_analysis'),
            ('unknown_file.xlsx', 'unknown')
        ]
        
        for filename, expected_type in test_files:
            result = migrator._determine_file_type(filename)
            assert result == expected_type, f"File type determination failed for '{filename}': expected {expected_type}, got {result}"
        
        print("✓ File type determination test passed")
    
    async def test_mock_migration(self):
        """Test migration with mock database handler."""
        print("Testing mock migration...")
        
        # Create migrator with mock database handler
        migrator = ExcelDataMigrator(self.test_config)
        migrator.db_handler = MockDatabaseHandler(self.test_config)
        
        # Test article data extraction (without actual Excel file)
        if PANDAS_AVAILABLE:
            # Create mock pandas Series (simulating Excel row)
            import pandas as pd
            
            mock_row = pd.Series({
                'Title': 'Test Article Title',
                'Content': 'This is test content for the article.',
                'URL': 'https://test.com/article/1',
                'Source': 'TestSource',
                'Date': '2023-06-15',
                'Author': 'Test Author',
                'Keywords': 'test,article,migration'
            })
            
            column_mapping = {
                'title': 'Title',
                'content': 'Content',
                'url': 'URL',
                'source': 'Source',
                'published_date': 'Date',
                'author': 'Author',
                'keywords': 'Keywords'
            }
            
            article_data = migrator._extract_article_data(mock_row, column_mapping)
            
            # Validate extracted data
            assert article_data['title'] == 'Test Article Title'
            assert article_data['content'] == 'This is test content for the article.'
            assert article_data['url'] == 'https://test.com/article/1'
            assert article_data['source'] == 'TestSource'
            assert article_data['author'] == 'Test Author'
            assert 'test' in article_data['keywords']
            
            print("✓ Mock data extraction test passed")
        else:
            print("⚠ Pandas not available, skipping mock data extraction test")
        
        print("✓ Mock migration test completed")
    
    async def run_all_tests(self):
        """Run all Excel migration tests."""
        print("Running Excel Migration Tests...")
        print("=" * 50)
        
        try:
            await self.test_column_mapping()
            await self.test_data_validation()
            await self.test_date_parsing()
            await self.test_keyword_parsing()
            await self.test_file_type_determination()
            await self.test_mock_migration()
            
            print("\n" + "=" * 50)
            print("✅ All Excel migration tests PASSED!")
            return True
            
        except Exception as e:
            print(f"\n❌ Excel migration test FAILED: {str(e)}")
            return False


async def main():
    """Main test runner."""
    tester = TestExcelMigration()
    success = await tester.run_all_tests()
    
    if not PANDAS_AVAILABLE:
        print("\n⚠ Note: pandas library not available. Some tests were skipped.")
        print("Install pandas with: pip install pandas")
    
    return success


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(main())
    exit(0 if success else 1)