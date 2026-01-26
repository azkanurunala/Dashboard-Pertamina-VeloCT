"""
Test SQL Server Authentication
"""
import pyodbc
import uuid
from datetime import datetime

def test_sql_connection():
    """Test SQL Server authentication."""
    print("🔐 Testing SQL Server Authentication...")
    
    connection_string = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=tcp:pei-dashboard.database.windows.net,1433;"
        "Database=pei-dashboard;"
        "Uid=CloudSAa33fbc7c;"
        "Pwd=uRahcie3&105272;"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )
    
    try:
        print("🔌 Connecting to database...")
        connection = pyodbc.connect(connection_string, timeout=30)
        cursor = connection.cursor()
        
        # Test basic query
        cursor.execute("SELECT 1 as test, USER_NAME() as username, GETDATE() as server_time")
        result = cursor.fetchone()
        
        if result:
            print(f"✅ SQL Authentication: SUCCESS")
            print(f"   Current user: {result[1]}")
            print(f"   Server time: {result[2]}")
            
            # Test database operations
            print("\n📋 Testing database operations...")
            
            # Check tables
            cursor.execute("""
                SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
            """)
            tables = [row[0] for row in cursor.fetchall()]
            print(f"✅ Found {len(tables)} tables: {', '.join(tables[:5])}...")
            
            # Check initial data
            cursor.execute("SELECT COUNT(*) FROM news_sources")
            source_count = cursor.fetchone()[0]
            print(f"✅ News sources: {source_count}")
            
            cursor.execute("SELECT COUNT(*) FROM keywords")
            keyword_count = cursor.fetchone()[0]
            print(f"✅ Keywords: {keyword_count}")
            
            # Test insert operation
            print("\n📝 Testing insert operation...")
            test_id = str(uuid.uuid4())
            test_url = f"https://test-sql-{uuid.uuid4().hex[:8]}.com/article"
            
            # Get or create test source
            cursor.execute("SELECT id FROM news_sources WHERE name = 'SQLTestSource'")
            source_result = cursor.fetchone()
            
            if source_result:
                source_id = source_result[0]
            else:
                cursor.execute("""
                    INSERT INTO news_sources (name, base_url, country, language, category)
                    VALUES ('SQLTestSource', 'https://sqltestsource.com', 'US', 'en', 'test')
                """)
                cursor.execute("SELECT SCOPE_IDENTITY()")
                source_id = cursor.fetchone()[0]
            
            # Insert test article
            cursor.execute("""
                INSERT INTO news_articles (id, title, content, url, source_id, published_date, scraped_date, language)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test_id,
                "SQL Test Article",
                "This is a test article to verify SQL Server authentication and database operations.",
                test_url,
                source_id,
                datetime.utcnow(),
                datetime.utcnow(),
                "en"
            ))
            
            # Verify insertion
            cursor.execute("SELECT title FROM news_articles WHERE id = ?", (test_id,))
            article_result = cursor.fetchone()
            
            if article_result:
                print("✅ Article insertion successful")
                
                # Clean up test data
                cursor.execute("DELETE FROM news_articles WHERE id = ?", (test_id,))
                print("✅ Test data cleanup successful")
            else:
                print("❌ Article insertion failed")
            
            connection.commit()
            connection.close()
            
            print("\n🎉 All SQL Server authentication tests passed!")
            return True
        else:
            print("❌ SQL Authentication: Failed - no result")
            return False
            
    except Exception as e:
        print(f"❌ SQL Authentication: Failed")
        print(f"   Error: {str(e)}")
        return False

def main():
    """Main test function."""
    print("🚀 SQL Server Authentication Test")
    print("=" * 50)
    
    success = test_sql_connection()
    
    if success:
        print("\n✅ SQL Server authentication is working perfectly!")
        print("💡 You can now proceed with:")
        print("1. Deploy Azure Functions code")
        print("2. Configure application settings")
        print("3. Test end-to-end functionality")
    else:
        print("\n❌ SQL Server authentication failed")
        print("💡 Please check:")
        print("1. Password is correct")
        print("2. SQL Server authentication is enabled")
        print("3. User has proper permissions")
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)