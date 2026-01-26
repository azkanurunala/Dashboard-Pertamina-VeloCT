"""
Test script untuk memverifikasi koneksi database Azure SQL Server.
Script ini akan menguji koneksi dan menjalankan operasi dasar database.
"""

import os
import sys
import asyncio
from datetime import datetime
import uuid

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False
    print("⚠️ pyodbc tidak tersedia. Install dengan: pip install pyodbc")

from shared.models import DatabaseConfig, NewsArticle
from shared.database_handler import DatabaseHandler
from shared.database_migration import DatabaseMigration


class DatabaseConnectionTester:
    """Test koneksi dan operasi database Azure SQL Server."""
    
    def __init__(self):
        """Initialize tester dengan konfigurasi dari environment variables."""
        self.connection_string = os.getenv('SQL_SERVER_CONNECTION_STRING')
        if not self.connection_string:
            # Fallback ke .env.azure file
            self._load_env_file()
        
        if not self.connection_string:
            raise ValueError("SQL_SERVER_CONNECTION_STRING tidak ditemukan di environment variables atau .env.azure")
        
        self.config = DatabaseConfig(
            connection_string=self.connection_string,
            connection_pool_size=5,
            connection_timeout=30,
            command_timeout=60,
            retry_attempts=3,
            retry_delay=2
        )
    
    def _load_env_file(self):
        """Load environment variables dari .env.azure file."""
        env_file = os.path.join(os.path.dirname(__file__), '..', '.env.azure')
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # Remove quotes if present
                        value = value.strip('"\'')
                        if key == 'SQL_SERVER_CONNECTION_STRING':
                            self.connection_string = value
                            break
    
    async def test_basic_connection(self) -> bool:
        """Test koneksi dasar ke database."""
        print("🔌 Testing basic database connection...")
        
        if not PYODBC_AVAILABLE:
            print("❌ pyodbc tidak tersedia")
            return False
        
        try:
            # Test direct pyodbc connection
            connection = pyodbc.connect(
                self.connection_string,
                timeout=30
            )
            cursor = connection.cursor()
            cursor.execute("SELECT 1 as test_connection")
            result = cursor.fetchone()
            connection.close()
            
            if result and result[0] == 1:
                print("✅ Basic database connection successful")
                return True
            else:
                print("❌ Basic database connection failed - no result")
                return False
                
        except Exception as e:
            print(f"❌ Basic database connection failed: {str(e)}")
            return False
    
    async def test_database_handler(self) -> bool:
        """Test DatabaseHandler class."""
        print("🔧 Testing DatabaseHandler...")
        
        try:
            db_handler = DatabaseHandler(self.config)
            
            # Test health check
            health = await db_handler.health_check()
            if health:
                print("✅ DatabaseHandler health check passed")
            else:
                print("❌ DatabaseHandler health check failed")
                return False
            
            # Test simple query
            result = await db_handler.execute_query("SELECT GETDATE() as current_time")
            if result and len(result) > 0:
                print(f"✅ Query execution successful. Current time: {result[0]['current_time']}")
            else:
                print("❌ Query execution failed")
                return False
            
            await db_handler.close()
            return True
            
        except Exception as e:
            print(f"❌ DatabaseHandler test failed: {str(e)}")
            return False
    
    async def test_schema_existence(self) -> bool:
        """Test apakah schema database sudah ada."""
        print("📋 Testing database schema...")
        
        try:
            db_handler = DatabaseHandler(self.config)
            
            # Check for main tables
            tables_to_check = [
                'news_sources', 'keywords', 'news_articles', 
                'sentiment_analyses', 'execution_logs', 'configuration'
            ]
            
            missing_tables = []
            for table in tables_to_check:
                result = await db_handler.execute_query(f"""
                    SELECT COUNT(*) as count FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_NAME = '{table}'
                """)
                
                if not result or result[0]['count'] == 0:
                    missing_tables.append(table)
            
            if missing_tables:
                print(f"⚠️ Missing tables: {', '.join(missing_tables)}")
                print("💡 Run database schema initialization script")
                return False
            else:
                print("✅ All required tables exist")
            
            # Check for views
            views_to_check = ['vw_articles_with_source', 'vw_sentiment_analyses_summary']
            missing_views = []
            
            for view in views_to_check:
                result = await db_handler.execute_query(f"""
                    SELECT COUNT(*) as count FROM INFORMATION_SCHEMA.VIEWS 
                    WHERE TABLE_NAME = '{view}'
                """)
                
                if not result or result[0]['count'] == 0:
                    missing_views.append(view)
            
            if missing_views:
                print(f"⚠️ Missing views: {', '.join(missing_views)}")
            else:
                print("✅ All required views exist")
            
            await db_handler.close()
            return len(missing_tables) == 0
            
        except Exception as e:
            print(f"❌ Schema check failed: {str(e)}")
            return False
    
    async def test_basic_operations(self) -> bool:
        """Test operasi CRUD dasar."""
        print("🔄 Testing basic CRUD operations...")
        
        try:
            db_handler = DatabaseHandler(self.config)
            
            # Test insert article
            test_article = NewsArticle(
                id=str(uuid.uuid4()),
                title="Test Article for Connection",
                content="This is a test article to verify database operations.",
                url=f"https://test-connection-{uuid.uuid4().hex[:8]}.com/article",
                source="TestConnectionSource",
                published_date=datetime.utcnow(),
                scraped_date=datetime.utcnow(),
                language="en",
                keywords=["test", "connection", "database"]
            )
            
            # Save article
            await db_handler.save_articles([test_article])
            print("✅ Article insert successful")
            
            # Query article back
            result = await db_handler.execute_query(
                "SELECT * FROM news_articles WHERE url = ?",
                [test_article.url]
            )
            
            if result and len(result) > 0:
                print("✅ Article query successful")
                saved_article = result[0]
                
                # Verify data
                if (saved_article['title'] == test_article.title and 
                    saved_article['content'] == test_article.content):
                    print("✅ Data integrity verified")
                else:
                    print("⚠️ Data integrity issue detected")
            else:
                print("❌ Article query failed")
                return False
            
            # Clean up test data
            await db_handler.execute_query(
                "DELETE FROM news_articles WHERE url = ?",
                [test_article.url]
            )
            print("✅ Test data cleanup successful")
            
            await db_handler.close()
            return True
            
        except Exception as e:
            print(f"❌ Basic operations test failed: {str(e)}")
            return False
    
    async def test_migration_functionality(self) -> bool:
        """Test database migration functionality."""
        print("🔄 Testing database migration functionality...")
        
        try:
            migration = DatabaseMigration(self.config)
            
            # Get migration status
            status = await migration.get_migration_status()
            
            print(f"📊 Migration Status:")
            print(f"  Articles: {status.get('news_articles_count', 0)}")
            print(f"  Sources: {status.get('news_sources_count', 0)}")
            print(f"  Keywords: {status.get('keywords_count', 0)}")
            print(f"  Sentiment Analyses: {status.get('sentiment_analyses_count', 0)}")
            print(f"  Schema Version: {status.get('schema_version', 'Unknown')}")
            print(f"  Migration Complete: {status.get('migration_complete', False)}")
            
            if status.get('migration_complete', False):
                print("✅ Database migration status check successful")
                return True
            else:
                print("⚠️ Database schema may need initialization")
                return False
                
        except Exception as e:
            print(f"❌ Migration functionality test failed: {str(e)}")
            return False
    
    async def run_all_tests(self) -> bool:
        """Jalankan semua test."""
        print("🧪 Starting Azure SQL Server Database Connection Tests")
        print("=" * 60)
        
        tests = [
            ("Basic Connection", self.test_basic_connection),
            ("Database Handler", self.test_database_handler),
            ("Schema Existence", self.test_schema_existence),
            ("Basic Operations", self.test_basic_operations),
            ("Migration Functionality", self.test_migration_functionality)
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\n🔍 Running: {test_name}")
            try:
                result = await test_func()
                results.append((test_name, result))
                if result:
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
            except Exception as e:
                print(f"❌ {test_name}: ERROR - {str(e)}")
                results.append((test_name, False))
        
        print("\n" + "=" * 60)
        print("📋 Test Summary:")
        
        passed = 0
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"  {test_name}: {status}")
            if result:
                passed += 1
        
        success_rate = (passed / len(results)) * 100
        print(f"\n📊 Success Rate: {passed}/{len(results)} ({success_rate:.1f}%)")
        
        if success_rate == 100:
            print("🎉 All tests passed! Database is ready for use.")
        elif success_rate >= 80:
            print("⚠️ Most tests passed. Check failed tests above.")
        else:
            print("❌ Multiple tests failed. Please check configuration and connectivity.")
        
        return success_rate >= 80


async def main():
    """Main function untuk menjalankan test."""
    try:
        tester = DatabaseConnectionTester()
        success = await tester.run_all_tests()
        
        if success:
            print("\n💡 Next Steps:")
            print("1. Deploy your Azure Functions code")
            print("2. Configure Copilot API credentials")
            print("3. Test end-to-end functionality")
            return 0
        else:
            print("\n🔧 Troubleshooting:")
            print("1. Check your connection string")
            print("2. Verify firewall rules allow your IP")
            print("3. Run database schema initialization")
            print("4. Check Azure SQL Server status")
            return 1
            
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)