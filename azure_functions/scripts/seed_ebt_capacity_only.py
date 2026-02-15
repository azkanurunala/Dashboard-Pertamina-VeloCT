import asyncio
import os
import sys
import pandas as pd
import logging
from typing import List, Dict, Any

# Add azure_functions to path
sys.path.append(os.path.join(os.getcwd(), 'azure_functions'))

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.getcwd(), 'azure_functions', '.env')
    if not os.path.exists(env_path):
        env_path = os.path.join(os.getcwd(), '..', '.env')
    if not os.path.exists(env_path):
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

async def seed_ebt_capacity():
    config_manager.reload()
    try:
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
        seeder = DataSeeder(db_handler)
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        return

    mappings = [
        ('(Data)Kapasitas_EBT.csv', 'data_ebt_capacity', seeder.map_ebt_capacity),
    ]

    references_path = os.path.join(os.getcwd(), 'azure_functions', 'references', 'data')
    if not os.path.exists(references_path):
        references_path = os.path.join(os.getcwd(), '..', 'references', 'data')

    try:
        for file_name, table_name, map_func in mappings:
            file_path = os.path.join(references_path, file_name)
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                continue

            logger.info(f"Seeding {file_name} into {table_name}...")
            
            # Truncate table first
            await db_handler.execute_query(f"TRUNCATE TABLE {table_name}")
            
            df = pd.read_csv(file_path)
            data = map_func(df)
            
            if data:
                total_inserted = await seeder.bulk_insert(table_name, data)
                logger.info(f"Successfully seeded {total_inserted} rows into {table_name}")
            else:
                logger.warning(f"No data mapped for {file_name}")

        logger.info("✅ EBT Capacity Seeding completed successfully.")

    except Exception as e:
        logger.error(f"Seeding failed: {e}")
    finally:
        if hasattr(db_handler, 'close'):
            await db_handler.close()

if __name__ == "__main__":
    asyncio.run(seed_ebt_capacity())
