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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def inspect():
    config_manager.reload()
    try:
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return

    logger.info("🔍 Inspecting data_fossil table...")

    try:
        # Check columns
        query = "SELECT TOP 1 * FROM data_fossil"
        result = await db_handler.execute_query(query)
        
        if not result:
            logger.info("Table exists but is empty.")
            schema_query = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'data_fossil'"
            columns = await db_handler.execute_query(schema_query)
            logger.info(f"Columns: {[c['COLUMN_NAME'] for c in columns]}")
        else:
            logger.info(f"Columns found: {list(result[0].keys())}")
            logger.info(f"First row: {result[0]}")
            
        # Count rows
        count_query = "SELECT COUNT(*) as count FROM data_fossil"
        count_res = await db_handler.execute_query(count_query)
        logger.info(f"Total rows: {count_res[0]['count']}")

    except Exception as e:
        logger.error(f"❌ Inspection failed: {e}")
    finally:
        if hasattr(db_handler, 'close'):
            await db_handler.close()

if __name__ == "__main__":
    asyncio.run(inspect())
