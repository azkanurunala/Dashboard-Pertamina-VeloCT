"""
Test different connection methods to Azure SQL Server
"""
import pyodbc
import os

def test_connection_method(connection_string, method_name):
    """Test a specific connection method."""
    print(f"\n🔍 Testing {method_name}...")
    try:
        connection = pyodbc.connect(connection_string, timeout=30)
        cursor = connection.cursor()
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        connection.close()
        
        if result and result[0] == 1:
            print(f"✅ {method_name}: SUCCESS")
            return True
        else:
            print(f"❌ {method_name}: Failed - no result")
            return False
    except Exception as e:
        print(f"❌ {method_name}: Failed - {str(e)}")
        return False

def main():
    """Test various connection methods."""
    server = "pei-dashboard.database.windows.net"
    database = "pei-dashboard"
    
    # Test different connection methods
    methods = [
        ("SQL Authentication", f"Driver={{ODBC Driver 17 for SQL Server}};Server=tcp:{server},1433;Database={database};Uid=CloudSAa33fbc7c;Pwd={{uRahcie3&105272}};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"),
        ("Azure AD Integrated", f"Driver={{ODBC Driver 17 for SQL Server}};Server=tcp:{server},1433;Database={database};Authentication=ActiveDirectoryIntegrated;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"),
        ("Azure AD Interactive", f"Driver={{ODBC Driver 17 for SQL Server}};Server=tcp:{server},1433;Database={database};Authentication=ActiveDirectoryInteractive;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"),
        ("Windows Authentication", f"Driver={{ODBC Driver 17 for SQL Server}};Server=tcp:{server},1433;Database={database};Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"),
    ]
    
    print("🧪 Testing Azure SQL Server Connection Methods")
    print("=" * 50)
    
    successful_methods = []
    for method_name, connection_string in methods:
        if test_connection_method(connection_string, method_name):
            successful_methods.append((method_name, connection_string))
    
    print("\n" + "=" * 50)
    print("📋 Results Summary:")
    
    if successful_methods:
        print(f"✅ {len(successful_methods)} method(s) worked:")
        for method_name, connection_string in successful_methods:
            print(f"  - {method_name}")
            print(f"    Connection String: {connection_string}")
    else:
        print("❌ No connection methods worked")
        print("\n💡 Possible solutions:")
        print("1. Install Azure CLI and login: az login")
        print("2. Enable SQL authentication on the Azure SQL Server")
        print("3. Add your IP to the SQL Server firewall rules")
        print("4. Check if you have proper permissions to the database")

if __name__ == "__main__":
    main()