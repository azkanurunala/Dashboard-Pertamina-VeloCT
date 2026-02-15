
import asyncio
import os
import sys
# Add azure_functions to path
sys.path.append(os.path.join(os.getcwd(), 'azure_functions'))
from shared.database_handler import DatabaseHandler
from shared.config import config_manager
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.getcwd(), 'azure_functions', '.env'))
except: pass

if os.getenv('SQL_SERVER_CONNECTION_STRING') is None and os.getenv('DatabaseConnectionString'):
    os.environ['SQL_SERVER_CONNECTION_STRING'] = os.getenv('DatabaseConnectionString')

async def check():
    try:
        config_manager.reload()
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
        res = await db_handler.execute_raw_query("SELECT COUNT(*) FROM data_cpo_prices")
        print(f"CPO_ROW_COUNT:{res[0][0]}")
    except Exception as e:
        print(f"ERROR:{e}")

if __name__ == "__main__":
    asyncio.run(check())
