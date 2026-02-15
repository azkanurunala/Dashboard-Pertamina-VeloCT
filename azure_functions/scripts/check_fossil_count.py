import asyncio
import os
import sys
import logging

sys.path.append(os.path.join(os.getcwd(), 'azure_functions'))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.getcwd(), 'azure_functions', '.env'))
except ImportError:
    pass

if os.getenv('SQL_SERVER_CONNECTION_STRING') is None and os.getenv('DatabaseConnectionString'):
    os.environ['SQL_SERVER_CONNECTION_STRING'] = os.getenv('DatabaseConnectionString')

from shared.database_handler import DatabaseHandler
from shared.config import config_manager

async def check():
    config_manager.reload()
    try:
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
        
        # Count total
        count_query = "SELECT COUNT(*) as count FROM data_fossil"
        res_count = await db_handler.execute_query(count_query)
        total = res_count[0]['count']
        
        # Count distinct dates
        distinct_query = "SELECT COUNT(DISTINCT time) as count FROM data_fossil"
        res_distinct = await db_handler.execute_query(distinct_query)
        distinct = res_distinct[0]['count']
        
        with open('fossil_check.txt', 'w') as f:
            f.write(f"Total rows: {total}\n")
            f.write(f"Distinct days: {distinct}\n")
            
            if total > distinct:
                f.write("DUPLICATES FOUND!\n")
                # Show some duplicates
                dup_query = "SELECT time, COUNT(*) as c FROM data_fossil GROUP BY time HAVING COUNT(*) > 1"
                dups = await db_handler.execute_query(dup_query)
                f.write(f"Duplicate example: {dups[0] if dups else 'None'}\n")
            else:
                f.write("No duplicates found (by time).\n")

    except Exception as e:
        with open('fossil_check.txt', 'w') as f:
             f.write(f"Check failed: {e}")
    finally:
        if hasattr(db_handler, 'close'):
            await db_handler.close()

if __name__ == "__main__":
    asyncio.run(check())
