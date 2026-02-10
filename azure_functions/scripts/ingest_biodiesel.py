
import asyncio
import csv
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add azure_functions to path
sys.path.append(os.path.join(os.getcwd(), 'azure_functions'))

# Load environment variables
load_dotenv(os.path.join(os.getcwd(), 'azure_functions', '.env'))

# Ensure the DB handler can find the connection string
if os.getenv('AZURE_SQL_CONNECTION_STRING'):
    os.environ['SQL_SERVER_CONNECTION_STRING'] = os.getenv('AZURE_SQL_CONNECTION_STRING')

from shared.database_handler import DatabaseHandler
from shared.config import config_manager

async def ingest_biodiesel():
    print("Starting Biodiesel Ingestion...")
    config_manager.reload()
    db_config = await config_manager.get_database_config()
    db_handler = DatabaseHandler(db_config)
    
    file_path = r'azure_functions\references\data\(Data)Biodesel.csv'
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return
        
    print(f"Reading {file_path}...")
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    price_str = row.get('HIP Biodiesel IDR/L', '0').replace(',', '')
                    price = float(price_str) if price_str else 0.0
                    
                    data.append({
                        'published_date': row['Date'],
                        'hip_month': row['Bulan HIP'],
                        'price_idr_liter': price
                    })
                except Exception as row_err:
                    print(f"Skipping row due to error: {row_err}")
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        return
            
    if not data:
        print("No data found to ingest.")
        return

    print(f"Saving {len(data)} rows to data_biodiesel_hip...")
    count = await db_handler.save_structured_data('data_biodiesel_hip', data)
    print(f"Successfully ingested {count} rows!")

if __name__ == "__main__":
    asyncio.run(ingest_biodiesel())
