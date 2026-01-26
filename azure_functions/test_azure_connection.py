#!/usr/bin/env python3
"""
Test Azure SQL Server connection with the updated configuration.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.config import DatabaseConfig
from shared.database_handler import DatabaseHandler

async def test_azure_connection():
    """Test connection to Azure SQL Server."""
    
    # Load environment variables
    load_dotenv('.env.azure')
    
    # Get connection string from environment
    connection_string = os.getenv(
        'SQL_SERVER_CONNECTION_STRING',
        'Driver={ODBC Driver 17 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Uid=CloudSAa33fbc7c;Pwd=uRahcie3&105272;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'
    )
    
    print("🔍 Testing Azure SQL Server connection...")
    print(f"Server: pei-dashboard.database.windows.net")
    print(f"Database: pei-dashboard")
    print(f"User: CloudSAa33fbc7c")
    
    try:
        # Create database configuration
        config = DatabaseConfig(
            connection_string=connection_string,
            connection_pool_size=5,
            connection_timeout=30,
            command_timeout=60,
            retry_attempts=3,
            retry_delay=2
        )
        
        # Create database handler
        db_handler = DatabaseHandler(config)
        
        # Test connection
        print("\n📡 Attempting to connect...")
        await db_handler.initialize()
        
        # Test a simple query
        print("✅ Connection successful! Testing query...")
        result = await db_handler.execute_query("SELECT 1 as test_value", {})
        
        if result and len(result) > 0:
            print(f"✅ Query test successful! Result: {result[0]}")
        else:
            print("⚠️  Query returned no results")
        
        # Clean up
        await db_handler.close()
        print("✅ Connection test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_azure_connection())
    if success:
        print("\n🎉 Azure SQL Server connection is working!")
        sys.exit(0)
    else:
        print("\n💥 Azure SQL Server connection failed!")
        sys.exit(1)