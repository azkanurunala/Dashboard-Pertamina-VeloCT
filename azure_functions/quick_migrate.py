"""
Quick database migration - minimal authentication
"""
import pyodbc
import os

def quick_migrate():
    """Quick database migration."""
    print("🚀 Quick Database Migration")
    print("=" * 30)
    
    connection_string = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=tcp:pei-dashboard.database.windows.net,1433;"
        "Database=pei-dashboard;"
        "Authentication=ActiveDirectoryInteractive;"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )
    
    try:
        print("🔐 Connecting (browser may open)...")
        connection = pyodbc.connect(connection_string, timeout=30)
        cursor = connection.cursor()
        print("✅ Connected!")
        
        # Quick essential tables creation
        essential_sql = [
            # News sources table
            """
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'news_sources')
            CREATE TABLE news_sources (
                id INT IDENTITY(1,1) PRIMARY KEY,
                name NVARCHAR(100) NOT NULL UNIQUE,
                base_url NVARCHAR(500) NOT NULL,
                country VARCHAR(10) NULL,
                language VARCHAR(10) NULL DEFAULT 'en',
                category NVARCHAR(50) NULL,
                is_active BIT NOT NULL DEFAULT 1,
                created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
                updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE()
            )
            """,
            
            # Keywords table
            """
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'keywords')
            CREATE TABLE keywords (
                id INT IDENTITY(1,1) PRIMARY KEY,
                keyword NVARCHAR(100) NOT NULL UNIQUE,
                category NVARCHAR(50) NULL,
                is_active BIT NOT NULL DEFAULT 1,
                created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE()
            )
            """,
            
            # News articles table
            """
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'news_articles')
            CREATE TABLE news_articles (
                id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
                title NVARCHAR(500) NOT NULL,
                content NTEXT NOT NULL,
                url NVARCHAR(1000) NOT NULL UNIQUE,
                source_id INT NOT NULL,
                published_date DATETIME2 NOT NULL,
                scraped_date DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
                language VARCHAR(10) NOT NULL DEFAULT 'en',
                author NVARCHAR(200) NULL,
                category NVARCHAR(100) NULL,
                created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
                updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE()
            )
            """,
            
            # Sentiment analyses table
            """
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'sentiment_analyses')
            CREATE TABLE sentiment_analyses (
                id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
                analysis_date DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
                date_range_start DATETIME2 NOT NULL,
                date_range_end DATETIME2 NOT NULL,
                sentiment_score FLOAT NOT NULL,
                sentiment_label VARCHAR(20) NOT NULL,
                confidence FLOAT NOT NULL,
                summary NTEXT NOT NULL,
                model_version VARCHAR(50) NOT NULL DEFAULT 'copilot-1.0',
                role_context NVARCHAR(200) NULL,
                article_count INT NOT NULL DEFAULT 0,
                created_at DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
                updated_at DATETIME2 NOT NULL DEFAULT GETUTCDATE()
            )
            """,
            
            # Insert initial data
            """
            IF NOT EXISTS (SELECT * FROM news_sources WHERE name = 'CNBC')
            INSERT INTO news_sources (name, base_url, country, language, category) VALUES
            ('CNBC', 'https://www.cnbc.com', 'US', 'en', 'business'),
            ('CNN', 'https://www.cnn.com', 'US', 'en', 'news'),
            ('Reuters', 'https://www.reuters.com', 'UK', 'en', 'news'),
            ('Kompas', 'https://www.kompas.com', 'ID', 'id', 'news'),
            ('Bisnis Indonesia', 'https://www.bisnis.com', 'ID', 'id', 'business')
            """,
            
            """
            IF NOT EXISTS (SELECT * FROM keywords WHERE keyword = 'energy')
            INSERT INTO keywords (keyword, category) VALUES
            ('energy', 'sector'),
            ('oil', 'commodity'),
            ('gas', 'commodity'),
            ('renewable', 'energy_type'),
            ('biodiesel', 'biofuel'),
            ('palm oil', 'commodity')
            """
        ]
        
        print("📋 Creating essential tables...")
        success_count = 0
        
        for i, sql in enumerate(essential_sql):
            try:
                cursor.execute(sql)
                success_count += 1
                print(f"   ✅ Step {i+1}/{len(essential_sql)} completed")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"   ⚠️ Step {i+1}/{len(essential_sql)} skipped (already exists)")
                else:
                    print(f"   ❌ Step {i+1}/{len(essential_sql)} failed: {str(e)[:50]}...")
        
        connection.commit()
        print("✅ Changes committed!")
        
        # Verify
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
        tables = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT COUNT(*) FROM news_sources")
        source_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM keywords")
        keyword_count = cursor.fetchone()[0]
        
        print(f"\n📊 Migration Results:")
        print(f"   Tables created: {len(tables)}")
        print(f"   News sources: {source_count}")
        print(f"   Keywords: {keyword_count}")
        
        connection.close()
        
        required_tables = ['news_sources', 'keywords', 'news_articles', 'sentiment_analyses']
        missing = [t for t in required_tables if t not in tables]
        
        if not missing:
            print("🎉 Essential migration completed successfully!")
            return True
        else:
            print(f"⚠️ Missing tables: {', '.join(missing)}")
            return False
            
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = quick_migrate()
    if success:
        print("\n💡 Next: Test with 'python test_system.py'")
    exit(0 if success else 1)