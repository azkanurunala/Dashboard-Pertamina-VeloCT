
import asyncio
import sys
import os
import logging

# Add parent directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from shared.config import config_manager
from shared.database_handler import create_database_handler

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    if len(sys.argv) < 2:
        print("Usage: python execute_sql_file.py <path_to_sql_file>")
        return

    sql_file_path = sys.argv[1]
    if not os.path.exists(sql_file_path):
        print(f"Error: File {sql_file_path} not found.")
        return

    try:
        # initialize configuration
        config = await config_manager.get_database_config()
        db_handler = await create_database_handler(config)
        
        # Read SQL file
        with open(sql_file_path, 'r') as f:
            sql_content = f.read()
            
        # Split by GO if necessary, but pytodbc might not handle GO.
        # Usually we split by 'GO' on separate lines for MS SQL Server scripts.
        batches = [batch.strip() for batch in sql_content.split('\nGO\n') if batch.strip()]
        if not batches:
             batches = [batch.strip() for batch in sql_content.split('\nGO') if batch.strip()]
        
        if not batches: # Single batch
            batches = [sql_content]

        logger.info(f"Executing {len(batches)} SQL batches from {sql_file_path}...")
        
        for i, batch in enumerate(batches):
            logger.info(f"Executing batch {i+1}...")
            # Remove GO if it's still there (at the end)
            if batch.endswith('GO'):
                batch = batch[:-2]
                
            await db_handler.execute_query(batch)
            logger.info(f"Batch {i+1} completed successfully.")
            
        logger.info("All batches executed successfully.")
        await db_handler.close()
        
    except Exception as e:
        logger.error(f"Execution failed: {str(e)}")
        # Print full traceback
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
