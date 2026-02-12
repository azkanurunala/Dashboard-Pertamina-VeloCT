
import asyncio
import os
import sys
# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.database_handler import DatabaseHandler
from shared.config import config_manager
from datetime import datetime

async def check_sentiment():
    print(f"--- Checking Sentiment Data ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
    
    # Load env manually to be safe
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

    try:
        db_config = await config_manager.get_database_config()
        # Ensure timeout is short to fail fast
        # db_config.timeout = 10 
        db_handler = DatabaseHandler(db_config)
        
        # 1. Count Total
        query_count = "SELECT COUNT(*) as c FROM sentiment_analyses"
        res_count = await db_handler.execute_query(query_count)
        count = res_count[0]['c'] if res_count else 0
        print(f"Total Sentiment Records: {count}")
        
        # 2. Get Statistics of latest entry
        if count > 0:
            query_latest = "SELECT TOP 1 id, sentiment_score, sentiment_label, confidence, summary, analysis_date FROM sentiment_analyses ORDER BY analysis_date DESC"
            res_latest = await db_handler.execute_query(query_latest)
            if res_latest:
                latest = res_latest[0]
                print("\nLatest Analysis:")
                print(f"  ID: {latest['id']}")
                print(f"  Date: {latest['analysis_date']}")
                print(f"  Score: {latest['sentiment_score']}")
                print(f"  Label: {latest['sentiment_label']}")
                print(f"  Confidence: {latest['confidence']}")
                print(f"  Summary Preview: {str(latest['summary'])[:100]}...")
        else:
            print("\nNo sentiment analysis found yet.")

    except Exception as e:
        print(f"Error checking sentiment: {e}")

if __name__ == "__main__":
    asyncio.run(check_sentiment())
