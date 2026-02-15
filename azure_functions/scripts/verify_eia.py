import asyncio
import os
import sys
import logging

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

async def verify():
    config_manager.reload()
    try:
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
        
        query = "SELECT COUNT(*) as count FROM data_eia_market"
        result = await db_handler.execute_query(query)
        count = result[0]['count']
        
        with open('eia_verification.txt', 'w') as f:
            f.write(f"COUNT: {count}")
            
    except Exception as e:
        with open('eia_verification.txt', 'w') as f:
            f.write(f"ERROR: {e}")
    finally:
         if hasattr(db_handler, 'close'):
            await db_handler.close()

if __name__ == "__main__":
    asyncio.run(verify())
