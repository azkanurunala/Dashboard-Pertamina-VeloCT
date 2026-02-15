
import asyncio
import os
import sys
import logging
import pandas as pd
from datetime import datetime

# Add azure_functions to path
sys.path.append(os.path.join(os.getcwd(), 'azure_functions'))

try:
    from shared.database_handler import DatabaseHandler
    from shared.config import config_manager
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.getcwd(), 'azure_functions', '.env'))
except: pass

if os.getenv('SQL_SERVER_CONNECTION_STRING') is None and os.getenv('DatabaseConnectionString'):
    os.environ['SQL_SERVER_CONNECTION_STRING'] = os.getenv('DatabaseConnectionString')

# Mock a simple Seeder class for isolation
class SimpleSeeder:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def clean_float(self, val):
        if pd.isna(val) or val == '': return 0.0
        try: return float(str(val).replace(',', '').replace('$', '').strip())
        except: return 0.0

    async def run(self):
        config_manager.reload()
        db_config = await config_manager.get_database_config()
        handler = DatabaseHandler(db_config)
        
        path = r"c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\references\data\(Data)CPO.csv"
        print(f"Checking path: {path}")
        if not os.path.exists(path):
            print("ERROR: File not found")
            return

        print("Reading file...")
        df = pd.read_csv(path, encoding='latin-1')
        print(f"Columns found: {df.columns.tolist()}")
        
        data = []
        for _, row in df.iterrows():
            data.append({
                'upload_date': datetime.now(), # Placeholder
                'price_date': datetime.now(), # Placeholder
                'px_last': self.clean_float(row.get('PX_LAST') or row.iloc[2]) # Try by name or index
            })
        
        print(f"Transformed {len(data)} rows. Saving to DB...")
        saved = await handler.save_structured_data('data_cpo_prices', data)
        print(f"SUCCESS: Saved {saved} rows")

if __name__ == "__main__":
    asyncio.run(SimpleSeeder(None).run())
