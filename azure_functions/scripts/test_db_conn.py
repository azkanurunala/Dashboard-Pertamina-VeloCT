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

async def test_conn():
    config_manager.reload()
    try:
        db_config = await config_manager.get_database_config()
        logger.info(f"Connecting to: {db_config.get('server')}")
        db_handler = DatabaseHandler(db_config)
        
        logger.info("Running simple query...")
        res = await db_handler.execute_query("SELECT 1 as result")
        logger.info(f"Result: {res}")
        
        logger.info("✅ Connection successful!")
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
    finally:
        if 'db_handler' in locals() and hasattr(db_handler, 'close'):
            await db_handler.close()

if __name__ == "__main__":
    asyncio.run(test_conn())
