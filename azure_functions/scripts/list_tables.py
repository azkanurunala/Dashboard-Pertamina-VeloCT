
import asyncio
import sys
import os
import json

# Add parent directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from shared.config import config_manager
from shared.database_handler import create_database_handler

async def list_tables():
    config = await config_manager.get_database_config()
    db_handler = await create_database_handler(config)
    
    try:
        query = """
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
        """
        results = await db_handler.execute_query(query)
        tables = [row['TABLE_NAME'] for row in results]
        print(json.dumps(tables))
    finally:
        await db_handler.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(list_tables())
