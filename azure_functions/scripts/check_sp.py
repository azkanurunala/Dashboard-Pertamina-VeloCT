
import asyncio
import sys
import os

# Add parent directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from shared.config import config_manager
from shared.database_handler import create_database_handler

async def main():
    try:
        config = await config_manager.get_database_config()
        db_handler = await create_database_handler(config)
        
        results = await db_handler.execute_query("SELECT OBJECT_ID('sp_DeduplicateArticles') as id")
        
        with open("sp_status.txt", "w") as f:
            if results and results[0]['id'] is not None:
                f.write("EXISTS")
            else:
                f.write("MISSING")
                
        await db_handler.close()
    except Exception as e:
        with open("sp_status.txt", "w") as f:
            f.write(f"ERROR: {str(e)}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
