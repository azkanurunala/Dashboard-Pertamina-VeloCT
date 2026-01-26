"""
Script untuk inisialisasi database schema di Azure SQL Server.
Script ini akan membuat semua tabel, view, dan stored procedure yang diperlukan.
"""

import os
import sys
import asyncio
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False
    print("⚠️ pyodbc tidak tersedia. Install dengan: pip install pyodbc")

from shared.models import DatabaseConfig
from shared.database_migration import DatabaseMigration


class DatabaseInitializer:
    """Initialize database schema untuk Azure SQL Server."""
    
    def __init__(self):
        """Initialize dengan konfigurasi dari environment variables."""
        self.connection_string = os.getenv('SQL_SERVER_CONNECTION_STRING')
        if not self.connection_string:
            # Fallback ke .env.azure file
            self._load_env_file()
        
        if not self.connection_string:
            raise ValueError("SQL_SERVER_CONNECTION_STRING tidak ditemukan")
        
        self.config = DatabaseConfig(
            connection_string=self.connection_string,
            connection_pool_size=5,
            connection_timeout=30,
            command_timeout=120,  # Longer timeout for schema creation
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
                        value = value.strip('"\'')
                        if key == 'SQL_SERVER_CONNECTION_STRING':
                            self.connection_string = value
                            break
    
    async def initialize_schema(self) -> bool:
        """Initialize database schema."""
        print("🗄️ Initializing database schema...")
        
        if not PYODBC_AVAILABLE:
            print("❌ pyodbc tidak tersedia")
            return False
        
        try:
            migration = DatabaseMigration(self.config)
            success = await migration.initialize_database()
            
            if success:
                print("✅ Database schema initialized successfully")
                
                # Get and display statistics
                stats = await migration.get_migration_status()
                print("\n📊 Database Statistics:")
                for key, value in stats.items():
                    if not key.startswith('error'):
                        print(f"  {key.replace('_', ' ').title()}: {value}")
                
                return True
            else:
                print("❌ Database schema initialization failed")
                return False
                
        except Exception as e:
            print(f"❌ Schema initialization error: {str(e)}")
            return False
    
    async def verify_schema(self) -> bool:
        """Verify bahwa schema sudah terinstall dengan benar."""
        print("🔍 Verifying database schema...")
        
        try:
            # Test basic connection
            connection = pyodbc.connect(self.connection_string, timeout=30)
            cursor = connection.cursor()
            
            # Check tables
            required_tables = [
                'news_sources', 'keywords', 'news_articles', 'article_keywords',
                'sentiment_analyses', 'sentiment_analysis_articles', 
                'execution_logs', 'configuration'
            ]
            
            print("📋 Checking tables...")
            missing_tables = []
            for table in required_tables:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_NAME = '{table}'
                """)
                count = cursor.fetchone()[0]
                if count == 0:
                    missing_tables.append(table)
                    print(f"  ❌ {table}: Missing")
                else:
                    print(f"  ✅ {table}: Found")
            
            # Check views
            required_views = ['vw_articles_with_source', 'vw_sentiment_analyses_summary']
            print("\n👁️ Checking views...")
            missing_views = []
            for view in required_views:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.VIEWS 
                    WHERE TABLE_NAME = '{view}'
                """)
                count = cursor.fetchone()[0]
                if count == 0:
                    missing_views.append(view)
                    print(f"  ❌ {view}: Missing")
                else:
                    print(f"  ✅ {view}: Found")
            
            # Check stored procedures
            required_procedures = [
                'sp_GetOrCreateNewsSource', 
                'sp_GetOrCreateKeyword', 
                'sp_DeduplicateArticles'
            ]
            print("\n⚙️ Checking stored procedures...")
            missing_procedures = []
            for proc in required_procedures:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.ROUTINES 
                    WHERE ROUTINE_NAME = '{proc}' AND ROUTINE_TYPE = 'PROCEDURE'
                """)
                count = cursor.fetchone()[0]
                if count == 0:
                    missing_procedures.append(proc)
                    print(f"  ❌ {proc}: Missing")
                else:
                    print(f"  ✅ {proc}: Found")
            
            connection.close()
            
            # Summary
            total_missing = len(missing_tables) + len(missing_views) + len(missing_procedures)
            if total_missing == 0:
                print("\n✅ All database objects verified successfully!")
                return True
            else:
                print(f"\n⚠️ {total_missing} database objects are missing")
                if missing_tables:
                    print(f"Missing tables: {', '.join(missing_tables)}")
                if missing_views:
                    print(f"Missing views: {', '.join(missing_views)}")
                if missing_procedures:
                    print(f"Missing procedures: {', '.join(missing_procedures)}")
                return False
                
        except Exception as e:
            print(f"❌ Schema verification failed: {str(e)}")
            return False
    
    async def seed_initial_data(self) -> bool:
        """Seed database dengan data awal."""
        print("🌱 Seeding initial data...")
        
        try:
            connection = pyodbc.connect(self.connection_string, timeout=30)
            cursor = connection.cursor()
            
            # Check if data already exists
            cursor.execute("SELECT COUNT(*) FROM news_sources")
            source_count = cursor.fetchone()[0]
            
            if source_count > 0:
                print(f"✅ Initial data already exists ({source_count} sources)")
                connection.close()
                return True
            
            # Insert initial news sources (already in schema.sql, but let's verify)
            print("Adding initial news sources...")
            initial_sources = [
                ('CNBC', 'https://www.cnbc.com', 'US', 'en', 'business'),
                ('CNN', 'https://www.cnn.com', 'US', 'en', 'news'),
                ('Reuters', 'https://www.reuters.com', 'UK', 'en', 'news'),
                ('Kompas', 'https://www.kompas.com', 'ID', 'id', 'news'),
                ('Bisnis Indonesia', 'https://www.bisnis.com', 'ID', 'id', 'business')
            ]
            
            for name, url, country, language, category in initial_sources:
                cursor.execute("""
                    IF NOT EXISTS (SELECT 1 FROM news_sources WHERE name = ?)
                    INSERT INTO news_sources (name, base_url, country, language, category)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, name, url, country, language, category))
            
            # Insert initial keywords
            print("Adding initial keywords...")
            initial_keywords = [
                ('energy', 'sector'), ('oil', 'commodity'), ('gas', 'commodity'),
                ('renewable', 'energy_type'), ('solar', 'energy_type'), ('wind', 'energy_type'),
                ('biodiesel', 'biofuel'), ('bioethanol', 'biofuel'), ('palm oil', 'commodity'),
                ('coal', 'commodity'), ('electricity', 'utility'), ('fuel', 'commodity')
            ]
            
            for keyword, category in initial_keywords:
                cursor.execute("""
                    IF NOT EXISTS (SELECT 1 FROM keywords WHERE keyword = ?)
                    INSERT INTO keywords (keyword, category)
                    VALUES (?, ?)
                """, (keyword, keyword, category))
            
            # Insert initial configuration
            print("Adding initial configuration...")
            initial_config = [
                ('system.version', '1.0.0', 'string', 'Current system version'),
                ('system.environment', 'production', 'string', 'Current deployment environment'),
                ('scraper.default_rate_limit_delay', '1', 'int', 'Default delay between requests'),
                ('scraper.default_max_retries', '3', 'int', 'Default maximum retry attempts')
            ]
            
            for key, value, config_type, description in initial_config:
                cursor.execute("""
                    IF NOT EXISTS (SELECT 1 FROM configuration WHERE config_key = ?)
                    INSERT INTO configuration (config_key, config_value, config_type, description)
                    VALUES (?, ?, ?, ?)
                """, (key, key, value, config_type, description))
            
            connection.commit()
            connection.close()
            
            print("✅ Initial data seeded successfully")
            return True
            
        except Exception as e:
            print(f"❌ Initial data seeding failed: {str(e)}")
            return False
    
    async def run_initialization(self) -> bool:
        """Jalankan proses inisialisasi lengkap."""
        print("🚀 Starting Database Initialization")
        print("=" * 50)
        
        steps = [
            ("Initialize Schema", self.initialize_schema),
            ("Verify Schema", self.verify_schema),
            ("Seed Initial Data", self.seed_initial_data)
        ]
        
        for step_name, step_func in steps:
            print(f"\n🔄 {step_name}...")
            try:
                success = await step_func()
                if success:
                    print(f"✅ {step_name}: Completed")
                else:
                    print(f"❌ {step_name}: Failed")
                    return False
            except Exception as e:
                print(f"❌ {step_name}: Error - {str(e)}")
                return False
        
        print("\n" + "=" * 50)
        print("🎉 Database initialization completed successfully!")
        print("\n💡 Next Steps:")
        print("1. Test database connection: python tests/test_database_connection.py")
        print("2. Deploy Azure Functions code")
        print("3. Configure application settings")
        
        return True


async def main():
    """Main function."""
    try:
        initializer = DatabaseInitializer()
        success = await initializer.run_initialization()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Initialization failed: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)