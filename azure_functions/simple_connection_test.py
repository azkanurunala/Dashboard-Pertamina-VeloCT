#!/usr/bin/env python3
"""
Simple test to verify Azure SQL Server connection.
"""

import pyodbc
import os
from dotenv import load_dotenv

def test_connection():
    """Test basic connection to Azure SQL Server."""
    
    # Load environment variables
    load_dotenv('.env.azure')
    
    # Connection string
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
    
    print("🔍 Testing Azure SQL Server connection...")
    print("Server: pei-dashboard.database.windows.net")
    print("Database: pei-dashboard")
    print("User: CloudSAa33fbc7c")
    
    try:
        print("\n📡 Attempting to connect...")
        conn = pyodbc.connect(connection_string)
        
        print("✅ Connection successful!")
        
        # Test a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test_value")
        result = cursor.fetchone()
        
        if result:
            print(f"✅ Query test successful! Result: {result[0]}")
        else:
            print("⚠️  Query returned no results")
        
        # Check if we can see tables
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        tables = cursor.fetchall()
        
        if tables:
            print(f"✅ Found {len(tables)} tables in database:")
            for table in tables[:5]:  # Show first 5 tables
                print(f"  - {table[0]}")
            if len(tables) > 5:
                print(f"  ... and {len(tables) - 5} more")
        else:
            print("ℹ️  No tables found in database")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 Azure SQL Server connection test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = test_connection()
    if not success:
        print("\n💥 Connection test failed!")
        exit(1)
    else:
        print("\n✅ All tests passed!")