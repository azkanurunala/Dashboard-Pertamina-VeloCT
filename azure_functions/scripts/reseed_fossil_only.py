
import asyncio
import os
import sys

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
from scripts.seed_all_structured_data import DataSeeder

async def reseed():
    print("Initializing...")
    config_manager.reload()
    db_config = await config_manager.get_database_config()
    db_handler = DatabaseHandler(db_config)
    seeder = DataSeeder(db_handler)
    
    data_dir = r'azure_functions\references\data'
    
    # 1. Truncate tables to remove bad data
    print("Truncating data_fossil and data_fossil_prediction...")
    try:
        await db_handler.execute_query("TRUNCATE TABLE data_fossil")
        await db_handler.execute_query("TRUNCATE TABLE data_fossil_prediction")
        print("Truncated.")
    except Exception as e:
        print(f"Error truncating: {e}")
        return

    # 2. Seed specific files
    mappings = [
        ('(Data)Input_Fosil.csv', 'data_fossil', seeder.map_fossil),
        ('(Data)Input_Fosil_Prediction.csv', 'data_fossil_prediction', seeder.map_fossil_prediction)
    ]

    for pattern, table, func in mappings:
        file_path = os.path.join(data_dir, pattern)
        print(f"Seeding {file_path} to {table}...")
        if os.path.exists(file_path):
            await seeder.seed_file(file_path, table, func)
        else:
            print(f"NOT FOUND: {file_path}")

    print("Reseeding complete.")

if __name__ == "__main__":
    asyncio.run(reseed())
