import asyncio
import os
import sys
import logging
import pandas as pd

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
from scripts.seed_all_structured_data import DataSeeder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed():
    config_manager.reload()
    try:
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return

    seeder = DataSeeder(db_handler)
    target_file = r'azure_functions\references\data\(Data)Bioetanol.csv'
    
    if not os.path.exists(target_file):
        logger.error(f"File not found: {target_file}")
        return

    try:
        df = pd.read_csv(target_file)
        logger.info(f"Loaded {len(df)} rows from {target_file}")
        
        data = seeder.map_bioetanol(df)
        logger.info(f"Mapped {len(data)} rows")
        
        await db_handler.save_structured_data('data_bioetanol_hip', data)
        logger.info("Successfully seeded data_bioetanol_hip")
        
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
    finally:
        if hasattr(db_handler, 'close'):
            await db_handler.close()

if __name__ == "__main__":
    asyncio.run(seed())
