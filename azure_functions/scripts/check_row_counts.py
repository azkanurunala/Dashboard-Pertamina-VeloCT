
import asyncio
import os
import sys

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.database_handler import DatabaseHandler
from shared.config import config_manager

def load_env():
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    parts = line.strip().split('=', 1)
                    if len(parts) == 2:
                        key, value = parts
                        os.environ[key.strip()] = value.strip().strip('"').strip("'")
    config_manager.reload()

async def check_counts():
    load_env()
    try:
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
        
        tables = [
            'data_fossil', 
            'data_biodiesel_hip', 
            'data_bioetanol_hip', 
            'data_nuclear', 
            'news_articles',
            'sentiment_analyses'
        ]
        
        print(f"--- Database Row Counts ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
        for table in tables:
            try:
                result = await db_handler.execute_query(f"SELECT COUNT(*) as c FROM {table}")
                count = result[0]['c'] if result else 0
                print(f"{table:25}: {count}")
            except Exception as e:
                print(f"{table:25}: ERROR - {str(e)[:50]}...")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(check_counts())
