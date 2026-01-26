"""
Simple database initialization script using Azure AD Interactive authentication
"""
import pyodbc
import os

def initialize_database():
    """Initialize database schema."""
    print("🗄️ Initializing Database Schema...")
    
    # Connection string for Azure AD Interactive
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
        print("🔐 Connecting to database (may open browser for authentication)...")
        connection = pyodbc.connect(connection_string, timeout=60)
        cursor = connection.cursor()
        
        print("✅ Connected successfully!")
        
        # Read schema file
        schema_file = os.path.join(os.path.dirname(__file__), 'shared', 'database_schema.sql')
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        print("📋 Executing database schema...")
        
        # Split SQL into individual statements
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        success_count = 0
        for i, statement in enumerate(statements):
            if not statement or statement.startswith('--'):
                continue
                
            try:
                cursor.execute(statement)
                success_count += 1
                if i % 10 == 0:  # Progress indicator
                    print(f"   Executed {i+1}/{len(statements)} statements...")
            except Exception as e:
                # Some statements might fail if objects already exist
                if "already exists" in str(e) or "There is already an object" in str(e):
                    print(f"   ⚠️ Skipped existing object: {str(e)[:100]}...")
                else:
                    print(f"   ❌ Error in statement {i+1}: {str(e)[:100]}...")
        
        connection.commit()
        connection.close()
        
        print(f"✅ Database schema initialization completed!")
        print(f"   Successfully executed {success_count}/{len(statements)} statements")
        
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {str(e)}")
        return False

def verify_schema():
    """Verify that schema was created successfully."""
    print("\n🔍 Verifying Database Schema...")
    
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
        connection = pyodbc.connect(connection_string, timeout=30)
        cursor = connection.cursor()
        
        # Check tables
        cursor.execute("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"📋 Found {len(tables)} tables:")
        for table in tables:
            print(f"   ✅ {table}")
        
        # Check views
        cursor.execute("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.VIEWS 
            ORDER BY TABLE_NAME
        """)
        views = [row[0] for row in cursor.fetchall()]
        
        print(f"\n👁️ Found {len(views)} views:")
        for view in views:
            print(f"   ✅ {view}")
        
        # Check stored procedures
        cursor.execute("""
            SELECT ROUTINE_NAME FROM INFORMATION_SCHEMA.ROUTINES 
            WHERE ROUTINE_TYPE = 'PROCEDURE'
            ORDER BY ROUTINE_NAME
        """)
        procedures = [row[0] for row in cursor.fetchall()]
        
        print(f"\n⚙️ Found {len(procedures)} stored procedures:")
        for proc in procedures:
            print(f"   ✅ {proc}")
        
        connection.close()
        
        # Check if we have the minimum required objects
        required_tables = ['news_sources', 'keywords', 'news_articles', 'sentiment_analyses']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            print(f"\n⚠️ Missing required tables: {', '.join(missing_tables)}")
            return False
        else:
            print(f"\n✅ All required tables are present!")
            return True
            
    except Exception as e:
        print(f"❌ Schema verification failed: {str(e)}")
        return False

def main():
    """Main function."""
    print("🚀 Simple Database Initialization")
    print("=" * 50)
    
    # Initialize schema
    if initialize_database():
        # Verify schema
        if verify_schema():
            print("\n🎉 Database initialization completed successfully!")
            print("\n💡 Next Steps:")
            print("1. Test database connection: python scripts/local-test.py")
            print("2. Deploy Azure Functions code")
            return True
        else:
            print("\n⚠️ Schema verification failed")
            return False
    else:
        print("\n❌ Database initialization failed")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)