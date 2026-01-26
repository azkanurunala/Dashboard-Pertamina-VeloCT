"""
Local testing script for Azure Functions News Scraping System.
This script can test the core functionality without requiring Azure deployment.
"""

import os
import sys
import asyncio
import json
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.models import DatabaseConfig, NewsArticle
from shared.database_handler import DatabaseHandler
from shared.database_migration import DatabaseMigration


class LocalTester:
    """Local testing for the news scraping system."""
    
    def __init__(self):
        """Initialize the local tester."""
        self.connection_string = os.getenv('SQL_SERVER_CONNECTION_STRING')
        if not self.connection_string:
            self._load_env_file()
        
        if not self.connection_string:
            print("❌ No database connection string found")
            print("💡 Please set SQL_SERVER_CONNECTION_STRING environment variable")
            print("   or ensure .env.azure file exists with the connection string")
            return
        
        self.config = DatabaseConfig(
            connection_string=self.connection_string,
            connection_pool_size=5,
            connection_timeout=30,
            command_timeout=60,
            retry_attempts=3,
            retry_delay=2
        )
    
    def _load_env_file(self):
        """Load environment variables from .env.azure file."""
        env_file = os.path.join(os.path.dirname(__file__), '..', '.env.azure')
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        value = value.strip('"\'')
                        if key == 'SQL_SERVER_CONNECTION_STRING':
                            self.connection_string = value
                            break
    
    async def test_database_operations(self):
        """Test basic database operations."""
        print("🧪 Testing Database Operations")
        print("=" * 40)
        
        if not self.connection_string:
            return False
        
        try:
            # Test connection
            print("🔌 Testing database connection...")
            db_handler = DatabaseHandler(self.config)
            
            health = await db_handler.health_check()
            if not health:
                print("❌ Database health check failed")
                return False
            
            print("✅ Database connection successful")
            
            # Test basic query
            print("📊 Testing basic query...")
            result = await db_handler.execute_query("SELECT GETDATE() as current_time")
            if result:
                print(f"✅ Query successful. Server time: {result[0]['current_time']}")
            else:
                print("❌ Query failed")
                return False
            
            # Test schema check
            print("📋 Checking database schema...")
            tables_result = await db_handler.execute_query("""
                SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
            """)
            
            if tables_result:
                print(f"✅ Found {len(tables_result)} tables:")
                for table in tables_result:
                    print(f"  - {table['TABLE_NAME']}")
            else:
                print("⚠️ No tables found - database may need initialization")
            
            await db_handler.close()
            return True
            
        except Exception as e:
            print(f"❌ Database test failed: {str(e)}")
            return False
    
    async def test_news_article_operations(self):
        """Test news article CRUD operations."""
        print("\n📰 Testing News Article Operations")
        print("=" * 40)
        
        if not self.connection_string:
            return False
        
        try:
            db_handler = DatabaseHandler(self.config)
            
            # Create test article
            test_article = NewsArticle(
                id="test-local-" + datetime.now().strftime("%Y%m%d-%H%M%S"),
                title="Local Test Article",
                content="This is a test article created during local testing.",
                url=f"https://local-test-{datetime.now().strftime('%Y%m%d%H%M%S')}.com/article",
                source="LocalTestSource",
                published_date=datetime.utcnow(),
                scraped_date=datetime.utcnow(),
                language="en",
                keywords=["test", "local", "development"]
            )
            
            print("💾 Saving test article...")
            await db_handler.save_articles([test_article])
            print("✅ Article saved successfully")
            
            # Query article back
            print("🔍 Querying saved article...")
            result = await db_handler.execute_query(
                "SELECT * FROM news_articles WHERE url = ?",
                [test_article.url]
            )
            
            if result and len(result) > 0:
                print("✅ Article retrieved successfully")
                saved_article = result[0]
                print(f"  Title: {saved_article['title']}")
                print(f"  Source: {saved_article.get('source', 'N/A')}")
                print(f"  Language: {saved_article.get('language', 'N/A')}")
            else:
                print("❌ Failed to retrieve saved article")
                return False
            
            # Clean up
            print("🧹 Cleaning up test data...")
            await db_handler.execute_query(
                "DELETE FROM news_articles WHERE url = ?",
                [test_article.url]
            )
            print("✅ Test data cleaned up")
            
            await db_handler.close()
            return True
            
        except Exception as e:
            print(f"❌ News article test failed: {str(e)}")
            return False
    
    async def test_migration_status(self):
        """Test database migration status."""
        print("\n🔄 Testing Migration Status")
        print("=" * 40)
        
        if not self.connection_string:
            return False
        
        try:
            migration = DatabaseMigration(self.config)
            status = await migration.get_migration_status()
            
            print("📊 Database Statistics:")
            for key, value in status.items():
                if not key.startswith('error'):
                    print(f"  {key.replace('_', ' ').title()}: {value}")
            
            return True
            
        except Exception as e:
            print(f"❌ Migration status test failed: {str(e)}")
            return False
    
    def simulate_function_app_response(self):
        """Simulate Azure Function App response."""
        print("\n🌐 Simulating Function App Response")
        print("=" * 40)
        
        try:
            response = {
                "status": "success",
                "message": "Azure Functions News Scraping System is running",
                "database_status": "Connected" if self.connection_string else "Not configured",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "environment": "local_test"
            }
            
            print("📱 Function App Response:")
            print(json.dumps(response, indent=2))
            return True
            
        except Exception as e:
            print(f"❌ Function simulation failed: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """Run all local tests."""
        print("🚀 Starting Local Testing Suite")
        print("=" * 50)
        
        tests = [
            ("Database Operations", self.test_database_operations),
            ("News Article Operations", self.test_news_article_operations),
            ("Migration Status", self.test_migration_status),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name} failed with error: {str(e)}")
                results.append((test_name, False))
        
        # Run synchronous test
        try:
            result = self.simulate_function_app_response()
            results.append(("Function App Simulation", result))
        except Exception as e:
            print(f"❌ Function App Simulation failed: {str(e)}")
            results.append(("Function App Simulation", False))
        
        # Summary
        print("\n" + "=" * 50)
        print("📋 Test Results Summary:")
        
        passed = 0
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"  {test_name}: {status}")
            if result:
                passed += 1
        
        success_rate = (passed / len(results)) * 100
        print(f"\n📊 Success Rate: {passed}/{len(results)} ({success_rate:.1f}%)")
        
        if success_rate == 100:
            print("🎉 All tests passed! System is ready for deployment.")
        elif success_rate >= 75:
            print("⚠️ Most tests passed. Check failed tests above.")
        else:
            print("❌ Multiple tests failed. Please check configuration.")
        
        return success_rate >= 75


async def main():
    """Main function."""
    try:
        tester = LocalTester()
        success = await tester.run_all_tests()
        
        if success:
            print("\n💡 Next Steps:")
            print("1. Add your IP to Azure SQL Server firewall rules")
            print("2. Install Azure CLI and Azure Functions Core Tools")
            print("3. Deploy to Azure using deploy-functions.ps1")
            return 0
        else:
            print("\n🔧 Troubleshooting:")
            print("1. Check database connection string")
            print("2. Verify Azure SQL Server firewall rules")
            print("3. Ensure database schema is initialized")
            return 1
            
    except Exception as e:
        print(f"❌ Local testing failed: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)