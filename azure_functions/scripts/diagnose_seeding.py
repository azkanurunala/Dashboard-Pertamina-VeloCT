
import sys
import os
print("Python executable:", sys.executable)
print("Current Working Directory:", os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'azure_functions'))
print("System Path:", sys.path)

try:
    print("Attempting to import shared.database_handler...")
    from shared.database_handler import DatabaseHandler
    print("Import successful!")
    
    print("Attempting to import shared.config...")
    from shared.config import config_manager
    print("Import successful!")
    
    print("Attempting to load database config...")
    import asyncio
    async def test():
        try:
            config_manager.reload()
            db_config = await config_manager.get_database_config()
            print("Database config loaded:", {k: v for k, v in vars(db_config).items() if 'password' not in k.lower()})
            print("Attempting to initialize DatabaseHandler...")
            db_handler = DatabaseHandler(db_config)
            print("DatabaseHandler initialized!")
        except Exception as e:
            print(f"Inner error: {e}")
    
    asyncio.run(test())
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
