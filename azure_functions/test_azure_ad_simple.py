"""
Simple Azure AD authentication test
"""
import pyodbc

def test_azure_ad_connection():
    """Test Azure AD Interactive authentication."""
    print("🔐 Testing Azure AD Interactive Authentication...")
    print("   This will open a browser window for authentication")
    print("   Please complete the login process in the browser")
    
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
        print("   Connecting...")
        connection = pyodbc.connect(connection_string, timeout=60)
        cursor = connection.cursor()
        
        # Test basic query
        cursor.execute("SELECT 1 as test, SYSTEM_USER as current_user, GETDATE() as server_time")
        result = cursor.fetchone()
        
        if result:
            print(f"✅ Azure AD Authentication: SUCCESS")
            print(f"   Current user: {result[1]}")
            print(f"   Server time: {result[2]}")
            
            # Test if we can create tables (check permissions)
            try:
                cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES")
                table_count = cursor.fetchone()[0]
                print(f"   Existing tables: {table_count}")
                
                # Try to create a test table
                cursor.execute("""
                    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'test_connection')
                    CREATE TABLE test_connection (id INT, message NVARCHAR(100))
                """)
                cursor.execute("DROP TABLE IF EXISTS test_connection")
                connection.commit()
                print("   ✅ Database write permissions: OK")
                
            except Exception as e:
                print(f"   ⚠️ Database write test failed: {str(e)[:100]}...")
            
            connection.close()
            return True
        else:
            print("❌ Azure AD Authentication: Failed - no result")
            return False
            
    except Exception as e:
        print(f"❌ Azure AD Authentication: Failed")
        print(f"   Error: {str(e)}")
        return False

def main():
    """Main function."""
    print("🧪 Azure AD Authentication Test")
    print("=" * 40)
    
    success = test_azure_ad_connection()
    
    if success:
        print("\n🎉 Azure AD authentication works!")
        print("💡 You can proceed with database initialization using Azure AD")
        print("   Run: python init_database_simple.py")
    else:
        print("\n❌ Azure AD authentication failed")
        print("💡 You may need to:")
        print("   1. Setup SQL Server admin user")
        print("   2. Check your Azure AD permissions")
        print("   3. Ensure you're added as Azure AD admin for the SQL Server")

if __name__ == "__main__":
    main()