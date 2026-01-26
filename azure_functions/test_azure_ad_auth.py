"""
Test Azure AD authentication methods for Azure SQL Server
"""
import pyodbc
import os

def test_azure_ad_interactive():
    """Test Azure AD Interactive authentication."""
    print("🔐 Testing Azure AD Interactive Authentication...")
    print("   This will open a browser window for authentication")
    
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
        print("   Opening browser for authentication...")
        connection = pyodbc.connect(connection_string, timeout=30)
        cursor = connection.cursor()
        cursor.execute("SELECT 1 as test, SYSTEM_USER as current_user")
        result = cursor.fetchone()
        connection.close()
        
        if result:
            print(f"✅ Azure AD Interactive: SUCCESS")
            print(f"   Current user: {result[1]}")
            return True
        else:
            print("❌ Azure AD Interactive: Failed - no result")
            return False
            
    except Exception as e:
        print(f"❌ Azure AD Interactive: Failed - {str(e)}")
        return False

def main():
    """Test Azure AD authentication."""
    print("🧪 Testing Azure AD Authentication Methods")
    print("=" * 50)
    
    success = test_azure_ad_interactive()
    
    if success:
        print("\n✅ Azure AD authentication works!")
        print("💡 You can use Azure AD authentication instead of SQL authentication")
        print("   Update your .env.azure file to use:")
        print('   SQL_SERVER_CONNECTION_STRING="Driver={ODBC Driver 17 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Authentication=ActiveDirectoryInteractive;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"')
    else:
        print("\n❌ Azure AD authentication failed")
        print("💡 You need to enable SQL Server authentication in Azure Portal")
        print("   Go to: Azure Portal > SQL Server 'pei-dashboard' > Azure Active Directory > Disable 'Azure Active Directory only authentication'")

if __name__ == "__main__":
    main()