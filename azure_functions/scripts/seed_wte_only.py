import asyncio
import pandas as pd
import os
import sys
import logging
from typing import List, Dict, Any

# Add azure_functions to path
sys.path.append(os.path.join(os.getcwd(), 'azure_functions'))

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.getcwd(), 'azure_functions', '.env')
    if not os.path.exists(env_path):
        # Fallback if running from inside azure_functions/scripts
        env_path = os.path.join(os.getcwd(), '..', '.env')
    if not os.path.exists(env_path):
        # Fallback if running from inside azure_functions/scripts (another level)
        env_path = os.path.join(os.getcwd(), '..', '..', '.env')
    load_dotenv(env_path)
except ImportError:
    pass

# Ensure the DB handler can find the connection string
if os.getenv('SQL_SERVER_CONNECTION_STRING') is None and os.getenv('DatabaseConnectionString'):
    os.environ['SQL_SERVER_CONNECTION_STRING'] = os.getenv('DatabaseConnectionString')

from shared.database_handler import DatabaseHandler
from shared.config import config_manager
from scripts.seed_all_structured_data import DataSeeder

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    config_manager.reload()
    try:
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return

    seeder = DataSeeder(db_handler)
    data_dir = r'azure_functions\references\data'

    wte_mappings = [
        ('(Data)WTE_Timbulan.csv', 'data_wte_timbulan', seeder.map_wte_timbulan),
        ('(Data)WTE_Sumber.csv', 'data_wte_sumber', seeder.map_wte_sumber),
        ('(Data)WTE_Komposisi.csv', 'data_wte_komposisi', seeder.map_wte_komposisi),
    ]

    for pattern, table, func in wte_mappings:
        file_path = os.path.join(data_dir, pattern)
        if os.path.exists(file_path):
            # Truncate table before seeding to ensure fresh data
            logger.info(f"Truncating {table}...")
            await db_handler.execute_query(f"TRUNCATE TABLE {table}")
            
            await seeder.seed_file(file_path, table, func)
        else:
            logger.warning(f"NOT FOUND: {file_path}")

    logger.info("🎯 WTE Seeding completed.")

if __name__ == "__main__":
    asyncio.run(main())
