import asyncio
import os
import sys
import logging
import pandas as pd
import traceback

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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add file handler to capture logs reliably
file_handler = logging.FileHandler('seed_harga_ebt_debug.log', mode='w', encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

async def seed():
    config_manager.reload()
    try:
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return

    seeder = DataSeeder(db_handler)
    target_file = r'azure_functions\references\data\(Data)HargaEBT.csv'
    
    if not os.path.exists(target_file):
        logger.error(f"File not found: {target_file}")
        return

    try:
        logger.info(f"Reading file: {target_file}")
        df = pd.read_csv(target_file)
        logger.info(f"Loaded {len(df)} rows from {target_file}")
        
        data = seeder.map_harga_ebt(df)
        logger.info(f"Mapped {len(data)} rows")
        
        # Clear existing data
        logger.info("Truncating table data_ebt_prices...")
        await db_handler.execute_query("TRUNCATE TABLE data_ebt_prices")
        logger.info("Table truncated.")

        # Chunked insertion
        chunk_size = 50
        total_chunks = (len(data) + chunk_size - 1) // chunk_size
        
        logger.info(f"Starting insertion of {len(data)} rows in {total_chunks} chunks...")
        
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            current_chunk = (i // chunk_size) + 1
            
            try:
                await db_handler.save_structured_data('data_ebt_prices', chunk)
                logger.info(f"Chunk {current_chunk}/{total_chunks} ({len(chunk)} rows) saved successfully.")
            except Exception as e:
                logger.error(f"Failed to save chunk {current_chunk}: {e}")
                # traceback.print_exc()

        logger.info("Successfully seeded data_ebt_prices")
        
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        logger.error(traceback.format_exc())
    finally:
        if hasattr(db_handler, 'close'):
            await db_handler.close()
        logger.info("Database handler closed.")

if __name__ == "__main__":
    asyncio.run(seed())
