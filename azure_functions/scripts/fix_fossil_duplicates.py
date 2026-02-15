import asyncio
import os
import sys
import logging

sys.path.append(os.path.join(os.getcwd(), 'azure_functions'))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.getcwd(), 'azure_functions', '.env'))
except ImportError:
    pass

if os.getenv('SQL_SERVER_CONNECTION_STRING') is None and os.getenv('DatabaseConnectionString'):
    os.environ['SQL_SERVER_CONNECTION_STRING'] = os.getenv('DatabaseConnectionString')

from shared.database_handler import DatabaseHandler
from shared.config import config_manager

async def fix():
    config_manager.reload()
    try:
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
        
        # Delete duplicates, keeping the most recent insertion (or just one of them)
        # Using creating_at desc to keep latest
        query = """
        WITH CTE AS (
            SELECT *, 
            ROW_NUMBER() OVER (PARTITION BY time ORDER BY created_at DESC) as rn 
            FROM data_fossil
        )
        DELETE FROM CTE WHERE rn > 1;
        """
        await db_handler.execute_query(query)
        print("Duplicates deleted.")
        
        # Verify count
        count_query = "SELECT COUNT(*) as count FROM data_fossil"
        res = await db_handler.execute_query(count_query)
        print(f"Remaining rows: {res[0]['count']}")

    except Exception as e:
        print(f"Fix failed: {e}")
    finally:
        if hasattr(db_handler, 'close'):
            await db_handler.close()

if __name__ == "__main__":
    asyncio.run(fix())
