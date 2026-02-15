import asyncio
import os
import sys
import logging
import traceback
from datetime import datetime

# Add azure_functions to path
sys.path.append(os.path.join(os.getcwd(), 'azure_functions'))

# Load environment variables
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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_minimal():
    # Setup file logging
    file_handler = logging.FileHandler('debug_minimal_log.txt', mode='w')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

    config_manager.reload()
    try:
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return

    logger.info("🚀 Starting Minimal Fossil Data Insertion...")

    try:
        # Try inserting one row manually
        insert_query = """
        INSERT INTO data_fossil (time, brent, gasoline, diesel, avtur)
        VALUES ('2025-01-01', 75.5, 80.2, 90.1, 95.5)
        """
        await db_handler.execute_query(insert_query)
        logger.info("✅ Single row inserted successfully.")
        
    except Exception as e:
        logger.error(f"❌ Insertion failed: {e}")
        logger.error(traceback.format_exc())
    finally:
        if hasattr(db_handler, 'close'):
            await db_handler.close()

if __name__ == "__main__":
    asyncio.run(debug_minimal())
