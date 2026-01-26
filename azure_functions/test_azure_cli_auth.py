"""
Test Azure SQL connection using Azure CLI authentication
"""
import subprocess
import pyodbc
import json

def get_azure_access_token():
    """Get Azure access token using Azure CLI."""
    try:
        # Get access token for SQL Database
        result = subprocess.run([
            'az', 'account', 'get-access-token', 
            '--resource', 'https://database.windows.net/'
        ], capture_output=True, text=True, check=True)
        
        token_info = json.loads(result.stdout)
        return token_info['accessToken']
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to get Azure access token: {e}")
        print("💡 Please run: az login")
        return None
    except Exception as e:
        print(f"❌ Error getting access token: {e}")
        return None

def test_azure_cli_connection():
    """Test connection using Azure CLI token."""
    print("🔐 Testing Azure CLI Authentication...")
    
    # Get access token
    access_token = get_azure_access_token()
    if not access_token:
        return False
    
    print("✅ Access token obtained successfully")
    
    # Create connection string with access token
    connection_string = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=tcp:pei-dashboard.database.windows.net,1433;"
        "Database=pei-dashboard;"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )
    
    try:
        # Connect using access token
        connection = pyodbc.connect(connection_string, attrs_before={
            1256: access_token  # SQL_COPT_SS_ACCESS_TOKEN
        })
        
        cursor = connection.cursor()
        cursor.execute("SELECT 1 as test, SYSTEM_USER as current_user, GETDATE() as current_time")
        result = cursor.fetchone()
        connection.close()
        
        if result:
            print(f"✅ Azure CLI Authentication: SUCCESS")
            print(f"   Current user: {result[1]}")
            print(f"   Server time: {result[2]}")
            return True
        else:
            print("❌ Azure CLI Authentication: Failed - no result")
            return False
            
    except Exception as e:
        print(f"❌ Azure CLI Authentication: Failed - {str(e)}")
        return False

def check_azure_cli():
    """Check if Azure CLI is installed and logged in."""
    try:
        # Check if az command exists
        result = subprocess.run(['az', '--version'], capture_output=True, text=True, check=True)
        print("✅ Azure CLI is installed")
        
        # Check if logged in
        result = subprocess.run(['az', 'account', 'show'], capture_output=True, text=True, check=True)
        account_info = json.loads(result.stdout)
        print(f"✅ Logged in as: {account_info.get('user', {}).get('name', 'Unknown')}")
        return True
        
    except subprocess.CalledProcessError:
        print("❌ Azure CLI not installed or not logged in")
        print("💡 Install Azure CLI and run: az login")
        return False
    except Exception as e:
        print(f"❌ Error checking Azure CLI: {e}")
        return False

def main():
    """Test Azure CLI authentication."""
    print("🧪 Testing Azure CLI Authentication")
    print("=" * 40)
    
    # Check Azure CLI
    if not check_azure_cli():
        return False
    
    # Test connection
    success = test_azure_cli_connection()
    
    if success:
        print("\n✅ Azure CLI authentication works!")
        print("💡 You can use this method for database operations")
        print("   This requires Azure CLI to be installed and logged in")
    else:
        print("\n❌ Azure CLI authentication failed")
        print("💡 Make sure you have proper permissions to the database")
    
    return success

if __name__ == "__main__":
    main()