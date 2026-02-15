
import asyncio
import os
import sys

# Add azure_functions to path
sys.path.append(os.path.join(os.getcwd(), 'azure_functions'))

def manual_load_env():
    env_path = os.path.join(os.getcwd(), 'azure_functions', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")
    
    # Also check local.settings.json
    settings_path = os.path.join(os.getcwd(), 'azure_functions', 'local.settings.json')
    if os.path.exists(settings_path):
        import json
        with open(settings_path, 'r') as f:
            data = json.load(f)
            values = data.get('Values', {})
            for k, v in values.items():
                if k not in os.environ:
                    os.environ[k] = str(v)

async def check_count():
    manual_load_env()
    from shared.database_handler import DatabaseHandler
    from shared.config import config_manager
    config_manager.reload()
    try:
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
        
        query = "SELECT COUNT(*) as c FROM news_articles"
        results = await db_handler.execute_query(query)
        print(f"Total News Articles: {results[0]['c']}")
        
        query_sources = """
            SELECT s.source_name, COUNT(*) as c 
            FROM news_articles a 
            JOIN news_sources s ON a.source_id = s.id 
            GROUP BY s.source_name
        """
        results_sources = await db_handler.execute_query(query_sources)
        print("\nArticles per Source:")
        for row in results_sources:
            print(f"- {row['source_name']}: {row['c']}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_count())
