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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DebugSeeder:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def clean_float(self, val):
        if pd.isna(val) or val == '': return 0.0
        if isinstance(val, (int, float)): return float(val)
        cleaned = str(val).replace(',', '').replace('$', '').replace('IDR', '').strip()
        try: return float(cleaned)
        except: return 0.0

    def parse_date(self, date_val):
        if pd.isna(date_val): return None
        try:
            return pd.to_datetime(date_val).to_pydatetime()
        except:
            return None

    def map_fossil(self, df):
        data = []
        with open('fossil_mapping_debug.txt', 'w') as f:
            f.write(f"Processing {len(df)} rows\n")
            f.write(f"Columns: {df.columns.tolist()}\n")
            for i, row in df.iterrows():
                try:
                    # Check for different case variations of Time
                    time_val = row.get('Time') or row.get('time')
                    
                    item = {
                        'time': self.parse_date(time_val),
                        'brent': self.clean_float(row.get('Brent')),
                        'gasoline': self.clean_float(row.get('Gasoline')),
                        'diesel': self.clean_float(row.get('Diesel')),
                        'avtur': self.clean_float(row.get('Avtur'))
                    }
                    data.append(item)
                    if i < 3: f.write(f"Mapped row {i}: {item}\n")
                except Exception as e:
                    f.write(f"Error row {i}: {e}\n")
        return data

async def debug_seed():
    # Setup file logging
    file_handler = logging.FileHandler('debug_fossil_log.txt', mode='w')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

    config_manager.reload()
    try:
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
    except Exception as e:
        with open('fossil_seeding_error.txt', 'w') as f:
            f.write(f"DB Init Error: {e}\n")
        return

    # Try both filenames seen in find_by_name
    file_path1 = r'azure_functions\references\data\(Data)Input_Fosil.csv'
    
    target_file = file_path1
    if not os.path.exists(target_file):
        with open('fossil_seeding_error.txt', 'w') as f:
             f.write(f"File not found: {target_file}\n")
        return

    try:
        df = pd.read_csv(target_file)
        seeder = DebugSeeder(db_handler)
        data = seeder.map_fossil(df)
        
        with open('fossil_seeding_debug_count.txt', 'w') as f:
            f.write(f"Mapped {len(data)} rows. Inserting to data_fossil...\n")
            
        await db_handler.save_structured_data('data_fossil', data)
        
        with open('fossil_seeding_success.txt', 'w') as f:
            f.write(f"Success! Inserted {len(data)} rows.")
            
    except Exception as e:
        with open('fossil_seeding_error.txt', 'w') as f:
            f.write(f"Seeding Error: {e}\n{traceback.format_exc()}\n")
    finally:
        if hasattr(db_handler, 'close'):
            await db_handler.close()

if __name__ == "__main__":
    asyncio.run(debug_seed())
