"""
Azure AD Authentication Setup and Database Initialization
"""
import pyodbc
import os
import time

def wait_for_authentication():
    """Wait for user to complete authentication."""
    print("🔐 Azure AD Authentication Required")
    print("=" * 50)
    print("📋 Steps to complete:")
    print("1. A browser window should open automatically")
    print("2. If not, manually open: https://login.microsoftonline.com")
    print("3. Login with your Azure account")
    print("4. Grant permissions when prompted")
    print("5. Return to this terminal")
    print()
    input("Press ENTER after completing authentication in browser...")

def test_connection():
    """Test Azure AD connection."""
    print("\n🔌 Testing database connection...")
    
    connection_string = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=tcp:pei-dashboard.database.windows.net,1433;"
        "Database=pei-dashboard;"
        "Authentication=ActiveDirectoryInteractive;"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=60;"
    )
    
    try:
        connection = pyodbc.connect(connection_string, timeout=60)
        cursor = connection.cursor()
        
        # Test basic query
        cursor.execute("SELECT 1 as test, SYSTEM_USER as current_user")
        result = cursor.fetchone()
        
        if result:
            print(f"✅ Connection successful!")
            print(f"   Logged in as: {result[1]}")
            
            # Check existing tables
            cursor.execute("""
                SELECT COUNT(*) as table_count 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_TYPE = 'BASE TABLE'
            """)
            table_count = cursor.fetchone()[0]
            print(f"   Existing tables: {table_count}")
            
            connection.close()
            return True
        else:
            print("❌ Connection failed - no result")
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

def initialize_database():
    """Initialize database schema."""
    print("\n🗄️ Initializing database schema...")
    
    connection_string = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=tcp:pei-dashboard.database.windows.net,1433;"
        "Database=pei-dashboard;"
        "Authentication=ActiveDirectoryInteractive;"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=60;"
    )
    
    try:
        connection = pyodbc.connect(connection_string, timeout=60)
        cursor = connection.cursor()
        
        # Read schema file
        schema_file = os.path.join(os.path.dirname(__file__), 'shared', 'database_schema.sql')
        if not os.path.exists(schema_file):
            print(f"❌ Schema file not found: {schema_file}")
            return False
        
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        print("📋 Executing database schema...")
        
        # Split SQL into individual statements
        statements = []
        current_statement = ""
        
        for line in schema_sql.split('\n'):
            line = line.strip()
            if not line or line.startswith('--'):
                continue
            
            current_statement += line + " "
            
            if line.endswith(';'):
                statements.append(current_statement.strip())
                current_statement = ""
        
        # Add any remaining statement
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        success_count = 0
        error_count = 0
        
        for i, statement in enumerate(statements):
            if not statement:
                continue
                
            try:
                cursor.execute(statement)
                success_count += 1
                
                if i % 5 == 0:  # Progress indicator
                    print(f"   Progress: {i+1}/{len(statements)} statements...")
                    
            except Exception as e:
                error_msg = str(e)
                # Some errors are expected (objects already exist)
                if any(keyword in error_msg.lower() for keyword in [
                    "already exists", "there is already an object", 
                    "cannot drop", "does not exist"
                ]):
                    print(f"   ⚠️ Skipped (already exists): Statement {i+1}")
                else:
                    print(f"   ❌ Error in statement {i+1}: {error_msg[:100]}...")
                    error_count += 1
        
        connection.commit()
        connection.close()
        
        print(f"\n✅ Database schema initialization completed!")
        print(f"   Successfully executed: {success_count} statements")
        print(f"   Errors/Skipped: {error_count} statements")
        
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {str(e)}")
        return False

def verify_setup():
    """Verify database setup."""
    print("\n🔍 Verifying database setup...")
    
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
        required_tables = ['news_sources', 'keywords', 'news_articles', 'sentiment_analyses']
        
        for table in required_tables:
            if table in tables:
                print(f"   ✅ {table}")
            else:
                print(f"   ❌ {table} (missing)")
        
        # Check if we have initial data
        if 'news_sources' in tables:
            cursor.execute("SELECT COUNT(*) FROM news_sources")
            source_count = cursor.fetchone()[0]
            print(f"\n📊 Initial data: {source_count} news sources")
        
        connection.close()
        
        missing_tables = [table for table in required_tables if table not in tables]
        return len(missing_tables) == 0
        
    except Exception as e:
        print(f"❌ Verification failed: {str(e)}")
        return False

def main():
    """Main setup process."""
    print("🚀 Azure Functions Database Setup with Azure AD")
    print("=" * 60)
    
    # Step 1: Wait for authentication
    wait_for_authentication()
    
    # Step 2: Test connection
    if not test_connection():
        print("\n❌ Connection test failed. Please check:")
        print("1. You completed Azure AD authentication")
        print("2. Your account has access to the SQL Server")
        print("3. You are added as Azure AD admin for the SQL Server")
        return False
    
    # Step 3: Initialize database
    if not initialize_database():
        print("\n❌ Database initialization failed")
        return False
    
    # Step 4: Verify setup
    if not verify_setup():
        print("\n⚠️ Database verification had issues")
        return False
    
    print("\n🎉 Database setup completed successfully!")
    print("\n💡 Next Steps:")
    print("1. Test the system: python scripts/local-test.py")
    print("2. Deploy Azure Functions code")
    print("3. Configure application settings")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)