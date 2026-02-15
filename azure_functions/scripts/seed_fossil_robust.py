import asyncio
import os
import sys
import logging
import pandas as pd
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RobustSeeder:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def clean_float(self, val):
        if pd.isna(val) or val == '': return 0.0
        if isinstance(val, (int, float)): return float(val)
        cleaned = str(val).replace(',', '').replace('$', '').replace('IDR', '').strip()
        try: return float(cleaned)
        except: return 0.0

    def parse_date(self, date_val):
        if pd.isna(date_val) or date_val == '': return None
        try:
            return pd.to_datetime(date_val).to_pydatetime()
        except:
            return None

    def map_fossil(self, df):
        data = []
        for _, row in df.iterrows():
            try:
                time_val = row.get('Time') or row.get('time')
                item = {
                    'time': self.parse_date(time_val),
                    'brent': self.clean_float(row.get('Brent')),
                    'gasoline': self.clean_float(row.get('Gasoline')),
                    'diesel': self.clean_float(row.get('Diesel')),
                    'avtur': self.clean_float(row.get('Avtur'))
                }
                data.append(item)
            except Exception:
                continue
        return data

async def seed():
    # Setup file logging
    # file_handler = logging.FileHandler('robust_pl_log.txt', mode='w', encoding='utf-8')
    # file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    # logger.addHandler(file_handler)

    config_manager.reload()
    print("Config reloaded")
    try:
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
    except Exception as e:
        print(f"Failed to initialize database: {e}")
        return

    target_file = r'azure_functions\references\data\(Data)Input_Fosil.csv'
    if not os.path.exists(target_file):
         print(f"File not found: {target_file}")
         return

    print("Starting Robust Fossil Data Seeding...")

    try:
        # Clear existing data to avoid duplicates/conflicts during re-seed
        await db_handler.execute_query("TRUNCATE TABLE data_fossil")
        print("Table truncated.")

        df = pd.read_csv(target_file)
        print(f"Loaded CSV with {len(df)} rows.")
        
        seeder = RobustSeeder(db_handler)
        data = seeder.map_fossil(df)
        print(f"Mapped {len(data)} rows.")

        # Save in chunks
        chunk_size = 50
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            print(f"Saving chunk {i // chunk_size + 1} ({len(chunk)} rows)...")
            try:
                await db_handler.save_structured_data('data_fossil', chunk)
                print(f"Chunk {i // chunk_size + 1} saved.")
            except Exception as e:
                print(f"Failed to save chunk {i // chunk_size + 1}: {e}")
                # Optional: break or continue depending on desired behavior
                
        print("Data seeding completed.")

    except Exception as e:
        print(f"Seeding failed: {e}")
        traceback.print_exc()
    finally:
        if hasattr(db_handler, 'close'):
            await db_handler.close()

if __name__ == "__main__":
    asyncio.run(seed())
