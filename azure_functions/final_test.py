"""
Final system test with SQL Server Authentication
"""
import pyodbc

def main():
    print("🚀 Final System Test - SQL Server Authentication")
    print("=" * 60)
    
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
        connection = pyodbc.connect(connection_string, timeout=30)
        cursor = connection.cursor()
        
        print("✅ Database connection successful")
        
        # Check tables
        cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
        table_count = cursor.fetchone()[0]
        print(f"✅ Database tables: {table_count}")
        
        connection.close()
        
        print("\n🎉 System is ready for deployment!")
        print("\n💡 Next Steps:")
        print("1. Install Azure CLI: Download from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-windows")
        print("2. Install Azure Functions Core Tools: npm install -g azure-functions-core-tools@4 --unsafe-perm true")
        print("3. Login to Azure: az login")
        print("4. Deploy functions: .\\scripts\\deploy-functions.ps1 -FunctionAppName 'pei-dashboard'")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    main()