import asyncio
import os
import sys
import logging

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
    if os.path.exists(env_path):
        load_dotenv(env_path)
        logger.info(f"Loaded .env from {env_path}")
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
        table_name = 'data_oil_prices'
        logger.info(f"Inspecting table: {table_name}")
        
        count_query = f"SELECT COUNT(*) as total FROM {table_name}"
        count_res = await db_handler.execute_query(count_query)
        logger.info(f"Total rows: {count_res[0]['total']}")
        
        sample_query = f"SELECT TOP 5 * FROM {table_name}"
        sample_res = await db_handler.execute_query(sample_query)
        for row in sample_res:
            logger.info(row)
            
    except Exception as e:
        logger.error(f"Inspection failed: {e}")
    finally:
        if hasattr(db_handler, 'close'):
            await db_handler.close()
        logger.info("Database handler closed.")

if __name__ == "__main__":
    asyncio.run(inspect())
