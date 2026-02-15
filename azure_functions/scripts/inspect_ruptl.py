
import asyncio
import os
import sys
import logging
from datetime import datetime

# Add azure_functions to path
sys.path.append(os.path.join(os.getcwd(), 'azure_functions'))

from shared.database_handler import DatabaseHandler
from shared.config import config_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.getcwd(), 'azure_functions', '.env')
    load_dotenv(env_path)
except ImportError:
    pass

# Ensure the DB handler can find the connection string
if os.getenv('SQL_SERVER_CONNECTION_STRING') is None and os.getenv('DatabaseConnectionString'):
    os.environ['SQL_SERVER_CONNECTION_STRING'] = os.getenv('DatabaseConnectionString')


async def inspect():
    config_manager.reload()
    try:
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return

    try:
        table_name = 'data_ruptl_projects'
        logger.info(f"Inspecting table: {table_name}")
        
        # Count rows
        count_query = f"SELECT COUNT(*) as count FROM {table_name}"
        result = await db_handler.execute_query(count_query)
        count = result[0]['count'] if result else 0
        logger.info(f"Total rows: {count}")

        # Sample rows
        if count > 0:
            sample_query = f"SELECT TOP 5 * FROM {table_name}"
            rows = await db_handler.execute_query(sample_query)
            for row in rows:
                logger.info(row)
        
    except Exception as e:
        logger.error(f"Inspection failed: {e}")
    finally:
        if hasattr(db_handler, 'close'):
            await db_handler.close()
        logger.info("Database handler closed.")

if __name__ == "__main__":
    asyncio.run(inspect())
