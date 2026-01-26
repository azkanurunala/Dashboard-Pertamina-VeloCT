"""
Final database validation test with correct configuration.
Tests database operations with the working Azure SQL Server connection.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import List
import uuid

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.models import (
    NewsArticle, SentimentAnalysis, SentimentLabel, DatabaseConfig, ArticleFilters
)
from shared.database_handler import DatabaseHandler


class FinalDatabaseTest:
    """Final comprehensive database test."""
    
    def __init__(self):
        """Initialize test with working connection string."""
        self.test_config = DatabaseConfig(
            connection_string="Driver={ODBC Driver 17 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Uid=CloudSAa33fbc7c;Pwd=uRahcie3&105272;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;",
            connection_pool_size=5,
            connection_timeout=30,
            command_timeout=60,
            retry_attempts=3,
            retry_delay=2
        )
    
    async def test_database_connection(self):
        """Test basic database connection."""
        print("Testing database connection...")
        
        try:
            db_handler = DatabaseHandler(self.test_config)
            
            # Test health check
            is_healthy = await db_handler.health_check()
            assert is_healthy, "Database health check failed"
            
            print("✅ Database connection test passed")
            await db_handler.close()
            return True
            
        except Exception as e:
            print(f"❌ Database connection test failed: {str(e)}")
            return False
    
    async def test_article_operations(self):
        """Test article CRUD operations."""
        print("Testing article operations...")
        
        try:
            db_handler = DatabaseHandler(self.test_config)
            
            # Create test articles
            test_articles = []
            for i in range(3):
                article = NewsArticle(
                    id=str(uuid.uuid4()),
                    title=f"Test Article {i}",
                    content=f"Test content for article {i} with sufficient length for testing.",
                    url=f"https://test-final-{i}-{uuid.uuid4().hex[:8]}.com/article",
                    source=f"TestSource{i % 2}",  # 2 different sources
                    published_date=datetime.utcnow() - timedelta(days=i),
                    scraped_date=datetime.utcnow(),
                    language="en",
                    category="test",
                    keywords=[f"keyword{i}", "test", "final"]
                )
                test_articles.append(article)
            
            # Save articles
            await db_handler.save_articles(test_articles)
            print(f"✅ Saved {len(test_articles)} articles")
            
            # Retrieve articles
            filters = ArticleFilters(source="TestSource0")
            retrieved_articles = await db_handler.get_articles(filters)
            
            # Verify retrieval
            assert len(retrieved_articles) >= 1, "No articles retrieved"
            print(f"✅ Retrieved {len(retrieved_articles)} articles")
            
            # Test deduplication
            duplicate_count = await db_handler.deduplicate_articles()
            print(f"✅ Deduplication completed, removed {duplicate_count} duplicates")
            
            await db_handler.close()
            return True
            
        except Exception as e:
            print(f"❌ Article operations test failed: {str(e)}")
            return False
    
    async def test_sentiment_operations(self):
        """Test sentiment analysis operations."""
        print("Testing sentiment operations...")
        
        try:
            db_handler = DatabaseHandler(self.test_config)
            
            # First create some articles to reference
            test_articles = []
            for i in range(2):
                article = NewsArticle(
                    id=str(uuid.uuid4()),
                    title=f"Sentiment Test Article {i}",
                    content=f"Content for sentiment testing {i}.",
                    url=f"https://sentiment-test-{i}-{uuid.uuid4().hex[:8]}.com/article",
                    source="SentimentTestSource",
                    published_date=datetime.utcnow(),
                    scraped_date=datetime.utcnow(),
                    keywords=["sentiment", "test"]
                )
                test_articles.append(article)
            
            await db_handler.save_articles(test_articles)
            
            # Create sentiment analysis
            sentiment = SentimentAnalysis(
                id=str(uuid.uuid4()),
                sentiment_score=0.7,
                sentiment_label=SentimentLabel.POSITIVE,
                confidence=0.85,
                summary="This is a positive sentiment analysis for testing purposes.",
                analysis_date=datetime.utcnow(),
                model_version="test-1.0",
                role_context="test_analyst",
                article_ids=[article.id for article in test_articles]
            )
            
            # Save sentiment analysis
            await db_handler.save_sentiment_analysis(sentiment)
            print("✅ Sentiment analysis saved successfully")
            
            await db_handler.close()
            return True
            
        except Exception as e:
            print(f"❌ Sentiment operations test failed: {str(e)}")
            return False
    
    async def test_data_integrity(self):
        """Test data integrity constraints."""
        print("Testing data integrity...")
        
        try:
            db_handler = DatabaseHandler(self.test_config)
            
            # Test 1: Duplicate URL rejection
            article1 = NewsArticle(
                id=str(uuid.uuid4()),
                title="Integrity Test Article 1",
                content="Content for integrity testing.",
                url="https://integrity-test-duplicate.com/article",
                source="IntegrityTestSource",
                published_date=datetime.utcnow(),
                scraped_date=datetime.utcnow()
            )
            
            article2 = NewsArticle(
                id=str(uuid.uuid4()),
                title="Integrity Test Article 2",
                content="Different content but same URL.",
                url="https://integrity-test-duplicate.com/article",  # Same URL
                source="IntegrityTestSource",
                published_date=datetime.utcnow(),
                scraped_date=datetime.utcnow()
            )
            
            # Save first article
            await db_handler.save_articles([article1])
            print("✅ First article saved")
            
            # Try to save duplicate URL - should fail
            try:
                await db_handler.save_articles([article2])
                print("❌ Duplicate URL was accepted (should have been rejected)")
                return False
            except Exception:
                print("✅ Duplicate URL correctly rejected")
            
            await db_handler.close()
            return True
            
        except Exception as e:
            print(f"❌ Data integrity test failed: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """Run all database validation tests."""
        print("=" * 60)
        print("FINAL DATABASE VALIDATION TESTS")
        print("=" * 60)
        
        tests = [
            ("Database Connection", self.test_database_connection),
            ("Article Operations", self.test_article_operations),
            ("Sentiment Operations", self.test_sentiment_operations),
            ("Data Integrity", self.test_data_integrity)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"\n--- {test_name} ---")
            try:
                result = await test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {str(e)}")
                results.append((test_name, False))
        
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)
        
        all_passed = True
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name}: {status}")
            if not result:
                all_passed = False
        
        print("\n" + "=" * 60)
        
        if all_passed:
            print("🎉 ALL DATABASE TESTS PASSED!")
            print("\nDatabase layer validation completed successfully.")
            print("The database layer is ready for the next implementation phase.")
        else:
            print("❌ SOME DATABASE TESTS FAILED")
            print("\nPlease review and fix the failing tests before proceeding.")
        
        return all_passed


async def main():
    """Main test runner."""
    tester = FinalDatabaseTest()
    success = await tester.run_all_tests()
    return success


if __name__ == "__main__":
    # Run the final database validation
    success = asyncio.run(main())
    exit(0 if success else 1)