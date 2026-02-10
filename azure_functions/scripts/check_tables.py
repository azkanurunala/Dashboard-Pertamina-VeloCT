import asyncio
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.database_handler import DatabaseHandler
from shared.config import config_manager

def load_env():
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")
    config_manager.reload()

async def check_tables():
    load_env()
    try:
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
        
        async def _get_tables():
            async with db_handler._get_connection() as conn:
                cursor = conn.cursor()
                print("--- Tables in Database ---")
                for table in cursor.tables(tableType='TABLE'):
                    print(f"Table: {table.table_name}")
            return True

        await db_handler._execute_with_retry(_get_tables)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_tables())
