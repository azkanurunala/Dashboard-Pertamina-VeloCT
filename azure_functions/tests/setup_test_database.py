"""
Setup test database for Azure Functions testing.
Creates the necessary database and tables for testing.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False
    print("⚠️  pyodbc not available. Install with: pip install pyodbc")

from shared.models import DatabaseConfig


class DatabaseSetup:
    """Setup test database and tables."""
    
    def __init__(self):
        """Initialize database setup."""
        # Azure SQL Server connection strings
        self.master_connection_string = (
            "Driver={ODBC Driver 17 for SQL Server};"
            "Server=tcp:pei-dashboard.database.windows.net,1433;"
            "Database=master;"
            "Uid=CloudSAa33fbc7c;"
            "Pwd=uRahcie3&105272;"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=30;"
        )
        
        self.test_db_name = "pei-dashboard"
        
        self.test_connection_string = (
            f"Driver={{ODBC Driver 17 for SQL Server}};"
            f"Server=tcp:pei-dashboard.database.windows.net,1433;"
            f"Database={self.test_db_name};"
            f"Uid=CloudSAa33fbc7c;"
            f"Pwd=uRahcie3&105272;"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )
    
    async def create_database(self):
        """Create test database if it doesn't exist."""
        if not PYODBC_AVAILABLE:
            print("❌ Cannot create database: pyodbc not available")
            return False
        
        try:
            print(f"Creating database '{self.test_db_name}'...")
            
            # Connect to master database
            conn = pyodbc.connect(self.master_connection_string)
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute("""
                SELECT database_id 
                FROM sys.databases 
                WHERE name = ?
            """, self.test_db_name)
            
            if cursor.fetchone():
                print(f"✅ Database '{self.test_db_name}' already exists")
            else:
                # Create database
                cursor.execute(f"CREATE DATABASE [{self.test_db_name}]")
                print(f"✅ Database '{self.test_db_name}' created successfully")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Failed to create database: {str(e)}")
            return False
    
    async def create_tables(self):
        """Create necessary tables for testing."""
        if not PYODBC_AVAILABLE:
            print("❌ Cannot create tables: pyodbc not available")
            return False
        
        try:
            print("Creating database tables...")
            
            # Connect to test database
            conn = pyodbc.connect(self.test_connection_string)
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Create news_sources table
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='news_sources' AND xtype='U')
                CREATE TABLE news_sources (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    name NVARCHAR(100) NOT NULL UNIQUE,
                    base_url NVARCHAR(500) NOT NULL,
                    country VARCHAR(10),
                    language VARCHAR(10),
                    category NVARCHAR(50),
                    is_active BIT DEFAULT 1,
                    created_at DATETIME2 DEFAULT GETUTCDATE()
                )
            """)
            print("✅ news_sources table created/verified")
            
            # Create keywords table
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='keywords' AND xtype='U')
                CREATE TABLE keywords (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    keyword NVARCHAR(100) NOT NULL UNIQUE,
                    category NVARCHAR(50),
                    is_active BIT DEFAULT 1,
                    created_at DATETIME2 DEFAULT GETUTCDATE()
                )
            """)
            print("✅ keywords table created/verified")
            
            # Create news_articles table
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='news_articles' AND xtype='U')
                CREATE TABLE news_articles (
                    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
                    title NVARCHAR(500) NOT NULL,
                    content NTEXT NOT NULL,
                    url NVARCHAR(1000) NOT NULL UNIQUE,
                    source_id INT NOT NULL,
                    published_date DATETIME2 NOT NULL,
                    scraped_date DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
                    language VARCHAR(10) DEFAULT 'en',
                    author NVARCHAR(200),
                    category NVARCHAR(100),
                    created_at DATETIME2 DEFAULT GETUTCDATE(),
                    updated_at DATETIME2 DEFAULT GETUTCDATE(),
                    
                    FOREIGN KEY (source_id) REFERENCES news_sources(id)
                )
            """)
            print("✅ news_articles table created/verified")
            
            # Create article_keywords table
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='article_keywords' AND xtype='U')
                CREATE TABLE article_keywords (
                    article_id UNIQUEIDENTIFIER NOT NULL,
                    keyword_id INT NOT NULL,
                    relevance_score FLOAT DEFAULT 1.0,
                    
                    PRIMARY KEY (article_id, keyword_id),
                    FOREIGN KEY (article_id) REFERENCES news_articles(id) ON DELETE CASCADE,
                    FOREIGN KEY (keyword_id) REFERENCES keywords(id)
                )
            """)
            print("✅ article_keywords table created/verified")
            
            # Create sentiment_analyses table
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sentiment_analyses' AND xtype='U')
                CREATE TABLE sentiment_analyses (
                    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
                    analysis_date DATETIME2 NOT NULL,
                    date_range_start DATETIME2 NOT NULL,
                    date_range_end DATETIME2 NOT NULL,
                    sentiment_score FLOAT NOT NULL,
                    sentiment_label VARCHAR(20) NOT NULL,
                    confidence FLOAT NOT NULL,
                    summary NTEXT NOT NULL,
                    model_version VARCHAR(50) NOT NULL,
                    role_context NVARCHAR(200),
                    article_count INT NOT NULL,
                    created_at DATETIME2 DEFAULT GETUTCDATE()
                )
            """)
            print("✅ sentiment_analyses table created/verified")
            
            # Create sentiment_analysis_articles table
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sentiment_analysis_articles' AND xtype='U')
                CREATE TABLE sentiment_analysis_articles (
                    sentiment_analysis_id UNIQUEIDENTIFIER NOT NULL,
                    article_id UNIQUEIDENTIFIER NOT NULL,
                    
                    PRIMARY KEY (sentiment_analysis_id, article_id),
                    FOREIGN KEY (sentiment_analysis_id) REFERENCES sentiment_analyses(id) ON DELETE CASCADE,
                    FOREIGN KEY (article_id) REFERENCES news_articles(id)
                )
            """)
            print("✅ sentiment_analysis_articles table created/verified")
            
            # Create indexes
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_news_articles_published_date')
                CREATE INDEX IX_news_articles_published_date ON news_articles(published_date)
            """)
            
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_news_articles_source_date')
                CREATE INDEX IX_news_articles_source_date ON news_articles(source_id, published_date)
            """)
            
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name='IX_news_articles_url')
                CREATE INDEX IX_news_articles_url ON news_articles(url)
            """)
            
            print("✅ Database indexes created/verified")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Failed to create tables: {str(e)}")
            return False
    
    async def test_connection(self):
        """Test database connection."""
        if not PYODBC_AVAILABLE:
            print("❌ Cannot test connection: pyodbc not available")
            return False
        
        try:
            print("Testing database connection...")
            
            conn = pyodbc.connect(self.test_connection_string)
            cursor = conn.cursor()
            
            # Test query
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            
            if result and result[0] == 1:
                print("✅ Database connection successful")
                
                # Check tables exist
                cursor.execute("""
                    SELECT COUNT(*) as table_count
                    FROM information_schema.tables 
                    WHERE table_type = 'BASE TABLE'
                    AND table_name IN ('news_sources', 'keywords', 'news_articles', 'article_keywords', 'sentiment_analyses', 'sentiment_analysis_articles')
                """)
                
                table_count = cursor.fetchone()[0]
                print(f"✅ Found {table_count}/6 required tables")
                
                cursor.close()
                conn.close()
                return table_count == 6
            else:
                print("❌ Database connection test failed")
                return False
                
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            return False
    
    async def setup_complete_database(self):
        """Complete database setup process."""
        print("=" * 60)
        print("SETTING UP TEST DATABASE")
        print("=" * 60)
        
        # Step 1: Create database
        db_created = await self.create_database()
        if not db_created:
            return False
        
        # Step 2: Create tables
        tables_created = await self.create_tables()
        if not tables_created:
            return False
        
        # Step 3: Test connection
        connection_ok = await self.test_connection()
        if not connection_ok:
            return False
        
        print("\n" + "=" * 60)
        print("✅ DATABASE SETUP COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f"Database: {self.test_db_name}")
        print(f"Connection: {self.test_connection_string}")
        print("\nYou can now run the database tests with:")
        print("python azure_functions/tests/run_database_tests.py")
        
        return True


async def main():
    """Main setup function."""
    setup = DatabaseSetup()
    success = await setup.setup_complete_database()
    return success


if __name__ == "__main__":
    # Run the setup
    success = asyncio.run(main())
    exit(0 if success else 1)