"""
Simple connection test with different drivers and passwords
"""
import pyodbc

def test_connection(driver, password):
    """Test connection with specific driver and password."""
    connection_string = (
        f"Driver={{{driver}}};"
        "Server=tcp:pei-dashboard.database.windows.net,1433;"
        "Database=pei-dashboard;"
        "Uid=CloudSAa33fbc7c;"
        f"Pwd={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )
    
    print(f"🔍 Testing with {driver}...")
    print(f"   Password: {password[:5]}...")
    
    try:
        connection = pyodbc.connect(connection_string, timeout=30)
        cursor = connection.cursor()
        cursor.execute("SELECT 1 as test, SYSTEM_USER as current_user")
        result = cursor.fetchone()
        connection.close()
        
        if result:
            print(f"✅ SUCCESS with {driver}")
            print(f"   Current user: {result[1]}")
            return True
        else:
            print(f"❌ FAILED with {driver} - no result")
            return False
            
    except Exception as e:
        print(f"❌ FAILED with {driver}: {str(e)[:100]}...")
        return False

def main():
    """Test different combinations."""
    print("🧪 Testing SQL Server Connection")
    print("=" * 40)
    
    # Available drivers
    drivers = pyodbc.drivers()
    print("Available drivers:")
    for driver in drivers:
        if "SQL Server" in driver:
            print(f"  - {driver}")
    
    print("\n" + "=" * 40)
    
    # Test passwords
    passwords = [
        "{uRahcie3&105272}",  # Original with braces
        "uRahcie3&105272",    # Without braces
        "{uRahcie3&105272}",  # With URL encoding
    ]
    
    # Test drivers
    test_drivers = [
        "ODBC Driver 17 for SQL Server",
        "ODBC Driver 18 for SQL Server",
        "SQL Server"
    ]
    
    success = False
    for driver in test_drivers:
        if driver in drivers:
            for password in passwords:
                if test_connection(driver, password):
                    print(f"\n🎉 Working combination found!")
                    print(f"   Driver: {driver}")
                    print(f"   Password: {password}")
                    success = True
                    break
            if success:
                break
        else:
            print(f"⚠️ {driver} not available")
    
    if not success:
        print("\n❌ No working combination found")
        print("💡 Possible issues:")
        print("   1. Password might be incorrect")
        print("   2. SQL Server authentication might not be enabled")
        print("   3. User might not have proper permissions")

if __name__ == "__main__":
    main()