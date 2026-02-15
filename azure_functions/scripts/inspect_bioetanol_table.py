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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def inspect():
    config_manager.reload()
    try:
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
        
        query = "SELECT TOP 5 * FROM data_bioetanol_hip"
        rows = await db_handler.execute_query(query)
        
        print(f"Rows found: {len(rows)}")
        for row in rows:
            print(row)
            
        count_query = "SELECT COUNT(*) as count FROM data_bioetanol_hip"
        count = await db_handler.execute_query(count_query)
        print(f"Total count: {count[0]['count']}")

    except Exception as e:
        logger.error(f"Inspection failed: {e}")
    finally:
        if hasattr(db_handler, 'close'):
            await db_handler.close()

if __name__ == "__main__":
    asyncio.run(inspect())
