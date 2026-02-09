import pyodbc
import asyncio
import os
import sys

# Add parent directory to path
parent_dir = os.path.abspath(os.path.join(os.getcwd(), 'azure_functions'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from shared.config import config_manager

async def test_conn():
    print("Testing connection...")
    try:
        conn_str = await config_manager.get_database_connection_string()
        print(f"Connection string: {conn_str[:50]}...")
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        row = cursor.fetchone()
        print(f"Connected! Version: {row[0]}")
        conn.close()
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_conn())
