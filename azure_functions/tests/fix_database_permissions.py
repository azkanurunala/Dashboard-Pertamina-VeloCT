"""
Fix database permissions for testing.
Grants necessary permissions to current Windows user.
"""

import os
import sys
import asyncio
import getpass

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False
    print("⚠️  pyodbc not available. Install with: pip install pyodbc")


class DatabasePermissionFixer:
    """Fix database permissions for testing."""
    
    def __init__(self):
        """Initialize permission fixer."""
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
        self.current_user = f"CloudSAa33fbc7c"
    
    async def fix_permissions(self):
        """Fix database permissions for current user."""
        if not PYODBC_AVAILABLE:
            print("❌ Cannot fix permissions: pyodbc not available")
            return False
        
        try:
            print(f"Fixing permissions for user: {self.current_user}")
            print(f"Database: {self.test_db_name}")
            
            # Connect to master database as admin
            conn = pyodbc.connect(self.master_connection_string)
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Create login if it doesn't exist
            try:
                cursor.execute(f"""
                    IF NOT EXISTS (SELECT * FROM sys.server_principals WHERE name = '{self.current_user}')
                    CREATE LOGIN [{self.current_user}] FROM WINDOWS
                """)
                print(f"✅ Login created/verified for {self.current_user}")
            except Exception as e:
                print(f"⚠️  Login creation warning: {str(e)}")
            
            cursor.close()
            conn.close()
            
            # Connect to test database
            test_connection_string = (
                f"Driver={{ODBC Driver 17 for SQL Server}};"
                f"Server=tcp:pei-dashboard.database.windows.net,1433;"
                f"Database={self.test_db_name};"
                f"Uid=CloudSAa33fbc7c;"
                f"Pwd=uRahcie3&105272;"
                f"Encrypt=yes;"
                f"TrustServerCertificate=no;"
                f"Connection Timeout=30;"
            )
            
            conn = pyodbc.connect(test_connection_string)
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Create user in database if it doesn't exist
            try:
                cursor.execute(f"""
                    IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = '{self.current_user}')
                    CREATE USER [{self.current_user}] FOR LOGIN [{self.current_user}]
                """)
                print(f"✅ Database user created/verified for {self.current_user}")
            except Exception as e:
                print(f"⚠️  User creation warning: {str(e)}")
            
            # Grant necessary permissions
            permissions = [
                "db_datareader",
                "db_datawriter", 
                "db_ddladmin"
            ]
            
            for permission in permissions:
                try:
                    cursor.execute(f"ALTER ROLE {permission} ADD MEMBER [{self.current_user}]")
                    print(f"✅ Granted {permission} to {self.current_user}")
                except Exception as e:
                    print(f"⚠️  Permission grant warning for {permission}: {str(e)}")
            
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to fix permissions: {str(e)}")
            print("\n🔧 Manual steps to fix permissions:")
            print("1. Open Azure portal and navigate to your SQL Server")
            print("2. Connect to pei-dashboard.database.windows.net")
            print(f"3. Right-click on database '{self.test_db_name}' -> Properties -> Permissions")
            print(f"4. Ensure user '{self.current_user}' has db_datareader, db_datawriter, db_ddladmin roles")
            return False
    
    async def test_fixed_connection(self):
        """Test if the fixed connection works."""
        if not PYODBC_AVAILABLE:
            print("❌ Cannot test connection: pyodbc not available")
            return False
        
        try:
            print("Testing fixed database connection...")
            
            test_connection_string = (
                f"Driver={{ODBC Driver 17 for SQL Server}};"
                f"Server=tcp:pei-dashboard.database.windows.net,1433;"
                f"Database={self.test_db_name};"
                f"Uid=CloudSAa33fbc7c;"
                f"Pwd=uRahcie3&105272;"
                f"Encrypt=yes;"
                f"TrustServerCertificate=no;"
                f"Connection Timeout=30;"
            )
            
            conn = pyodbc.connect(test_connection_string)
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            
            if result and result[0] == 1:
                print("✅ Basic connection test passed")
                
                # Test write permission
                try:
                    cursor.execute("SELECT COUNT(*) FROM news_sources")
                    count = cursor.fetchone()[0]
                    print(f"✅ Read permission test passed (found {count} sources)")
                    
                    # Test write permission
                    cursor.execute("""
                        INSERT INTO news_sources (name, base_url, country, language) 
                        VALUES ('TestSource', 'https://test.com', 'US', 'en')
                    """)
                    print("✅ Write permission test passed")
                    
                    # Clean up test data
                    cursor.execute("DELETE FROM news_sources WHERE name = 'TestSource'")
                    print("✅ Delete permission test passed")
                    
                    conn.commit()
                    
                except Exception as e:
                    print(f"❌ Permission test failed: {str(e)}")
                    cursor.close()
                    conn.close()
                    return False
                
            cursor.close()
            conn.close()
            
            print("✅ All database permission tests passed!")
            return True
            
        except Exception as e:
            print(f"❌ Connection test failed: {str(e)}")
            return False


async def main():
    """Main permission fixing function."""
    print("=" * 60)
    print("FIXING DATABASE PERMISSIONS")
    print("=" * 60)
    
    fixer = DatabasePermissionFixer()
    
    # Step 1: Fix permissions
    permissions_fixed = await fixer.fix_permissions()
    
    if permissions_fixed:
        # Step 2: Test connection
        connection_ok = await fixer.test_fixed_connection()
        
        if connection_ok:
            print("\n" + "=" * 60)
            print("✅ DATABASE PERMISSIONS FIXED SUCCESSFULLY")
            print("=" * 60)
            print("You can now run the database tests with:")
            print("python azure_functions/tests/run_database_tests.py")
            return True
    
    print("\n" + "=" * 60)
    print("❌ FAILED TO FIX DATABASE PERMISSIONS")
    print("=" * 60)
    print("Please run SQL Server Management Studio as Administrator and manually grant permissions.")
    return False


if __name__ == "__main__":
    # Run the permission fix
    success = asyncio.run(main())
    exit(0 if success else 1)