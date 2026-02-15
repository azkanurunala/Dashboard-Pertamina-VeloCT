
import asyncio
import os
import sys
import logging
import pandas as pd
import traceback

# Add azure_functions to path
sys.path.append(os.path.join(os.getcwd(), 'azure_functions'))

from shared.database_handler import DatabaseHandler
from shared.config import config_manager
from scripts.seed_all_structured_data import DataSeeder

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


async def seed():
    config_manager.reload()
    try:
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return

    seeder = DataSeeder(db_handler)
    target_file = r'azure_functions\references\data\(Data)RUPTL.csv'
    
    if not os.path.exists(target_file):
        logger.error(f"File not found: {target_file}")
        return

    try:
        logger.info(f"Reading file: {target_file}")
        # Try different encodings
        for encoding in ['latin-1', 'cp1252', 'utf-8']:
            try:
                df = pd.read_csv(target_file, encoding=encoding)
                logger.info(f"Loaded {len(df)} rows with {encoding}")
                break
            except:
                continue
        
        data = seeder.map_ruptl(df)
        logger.info(f"Mapped {len(data)} rows")
        
        # Clear existing data
        logger.info("Truncating table data_ruptl_projects...")
        await db_handler.execute_query("TRUNCATE TABLE data_ruptl_projects")
        logger.info("Table truncated.")

        # Chunked insertion
        chunk_size = 50
        total_chunks = (len(data) + chunk_size - 1) // chunk_size
        
        logger.info(f"Starting insertion of {len(data)} rows in {total_chunks} chunks...")
        
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            current_chunk = (i // chunk_size) + 1
            
            try:
                await db_handler.save_structured_data('data_ruptl_projects', chunk)
                logger.info(f"Chunk {current_chunk}/{total_chunks} ({len(chunk)} rows) saved successfully.")
            except Exception as e:
                logger.error(f"Failed to save chunk {current_chunk}: {e}")
                # traceback.print_exc()

        logger.info("Successfully seeded data_ruptl_projects")
        
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        logger.error(traceback.format_exc())
    finally:
        if hasattr(db_handler, 'close'):
            await db_handler.close()
        logger.info("Database handler closed.")

if __name__ == "__main__":
    asyncio.run(seed())
