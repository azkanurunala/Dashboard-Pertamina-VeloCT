import asyncio
import os
import sys
import logging
import pandas as pd
from datetime import datetime
import traceback

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
        return pd.to_datetime(date_val).to_pydatetime() if not pd.isna(date_val) else None

    def map_eia_market(self, df):
        data = []
        with open('eia_mapping_debug.txt', 'w') as f:
            f.write(f"Processing {len(df)} rows\n")
            for i, row in df.iterrows():
                try:
                    item = {
                        'bulan': str(row.get('Bulan', '')),
                        'tahun': int(row.get('Tahun', 0)),
                        'world_total_production': self.clean_float(row.get('World Total Production')),
                        'opec': self.clean_float(row.get('OPEC')),
                        'non_opec': self.clean_float(row.get('Non-OPEC')),
                        'crude_oil': self.clean_float(row.get('Crude Oil')),
                        'other_liquids': self.clean_float(row.get('Other Liquids')),
                        'world_total_consumption': self.clean_float(row.get('World Total Consumption')),
                        'oecd': self.clean_float(row.get('OECD')),
                        'non_oecd': self.clean_float(row.get('Non-OECD')),
                        'next_release_date': self.parse_date(row.get('Next Release Date'))
                    }
                    data.append(item)
                    if i < 3: f.write(f"Mapped row {i}: {item}\n")
                except Exception as e:
                    f.write(f"Error row {i}: {e}\n")
        return data

async def debug_seed():
    config_manager.reload()
    try:
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
    except Exception as e:
        with open('seeding_error.txt', 'w') as f:
            f.write(f"DB Init Error: {e}\n")
        return

    file_path = r'azure_functions\references\data\(Data)eia.csv'
    if not os.path.exists(file_path):
        with open('seeding_error.txt', 'w') as f:
             f.write(f"File not found: {file_path}\n")
        return

    try:
        df = pd.read_csv(file_path) # Try default encoding first
        seeder = DebugSeeder(db_handler)
        data = seeder.map_eia_market(df)
        
        with open('seeding_debug_count.txt', 'w') as f:
            f.write(f"Mapped {len(data)} rows. Inserting...\n")
            
        await db_handler.save_structured_data('data_eia_market', data)
        
        with open('seeding_success.txt', 'w') as f:
            f.write("Success!")
            
    except Exception as e:
        with open('seeding_error.txt', 'w') as f:
            f.write(f"Seeding Error: {e}\n{traceback.format_exc()}\n")
    finally:
        if hasattr(db_handler, 'close'):
            await db_handler.close()

if __name__ == "__main__":
    asyncio.run(debug_seed())
