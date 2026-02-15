
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

async def inspect():
    print("Initializing...")
    config_manager.reload()
    db_config = await config_manager.get_database_config()
    db_handler = DatabaseHandler(db_config)
    
    print("Querying data_fossil...")
    try:
        # Get top 5 rows
        query = "SELECT TOP 10 * FROM data_fossil ORDER BY id DESC"
        result = await db_handler.execute_query(query)
        
        if not result:
            print("Table is empty (or query returned nothing).")
        else:
            # Print columns if possible (handled in Row object usually)
            # Just print raw result
            for i, row in enumerate(result):
                print(f"Row {i}: {row}")
                
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(inspect())
