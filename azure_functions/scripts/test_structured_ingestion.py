
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

async def test_ingestion():
    print("Testing structured data ingestion...")
    
    # Reload config to pick up os.environ changes
    config_manager.reload()
    
    # Initialize DB Handler
    db_config = await config_manager.get_database_config()
    conn_str = db_config.connection_string
    print(f"Debug: Connection string length: {len(conn_str)}")
    
    # Direct test
    try:
        import pyodbc
        print("Debug: Testing direct pyodbc connection...")
        conn = pyodbc.connect(conn_str, timeout=5)
        print("Debug: Direct connection successful!")
        conn.close()
    except Exception as e:
        print(f"Debug: Direct connection failed: {e}")
        return

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
                # Map headers to table schema: Date -> published_date, Bulan HIP -> hip_month, HIP Biodiesel IDR/L -> price_idr_liter
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
    # Just test first 10 rows
    count = await db_handler.save_structured_data('data_biodiesel_hip', data[:10])
    print(f"Successfully ingested {count} rows!")

if __name__ == "__main__":
    asyncio.run(test_ingestion())
