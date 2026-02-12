
import asyncio
import sys
import os
import json
from datetime import datetime

# Add parent directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from shared.config import config_manager
from shared.database_handler import create_database_handler

def load_env():
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    parts = line.strip().split('=', 1)
                    if len(parts) == 2:
                        key, value = parts
                        # Remove quotes if present
                        value = value.strip().strip('"').strip("'")
                        os.environ[key.strip()] = value
    # Force reload of config manager
    config_manager.reload()

async def verify_data():
    load_env()
    config = await config_manager.get_database_config()
    db_handler = await create_database_handler(config)
    
    print(f"=== DATA VERIFICATION REPORT ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===")
    
    try:
        # 1. Get List of Tables
        query = """
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE' 
          AND (
            TABLE_NAME LIKE 'data_%' 
            OR TABLE_NAME IN (
                'news_articles', 'sentiment_analyses', 'news_sources', 
                'keywords', 'article_keywords', 'execution_logs', 
                'configuration', 'sentiment_analysis_articles'
            )
          )
        ORDER BY TABLE_NAME
        """
        results = await db_handler.execute_query(query)
        target_tables = [row['TABLE_NAME'] for row in results]
        
        print(f"Found {len(target_tables)} tables to verify.")

        # 2. Verify Each Table
        for table in target_tables:
            print(f"\n--- Table: {table} ---")
            
            # DASH-01: Total Record
            count_res = await db_handler.execute_query(f"SELECT COUNT(*) as c FROM {table}")
            count = count_res[0]['c']
            print(f"Total Records: {count}")
            
            # DASH-02: Date Range (Heuristic: look for common date columns)
            col_query = f"""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = '{table}' 
              AND COLUMN_NAME LIKE '%date%'
            """
            col_res = await db_handler.execute_query(col_query)
            date_cols = [row['COLUMN_NAME'] for row in col_res]
            
            if date_cols:
                date_col = next((c for c in date_cols if c in ['published_date', 'analysis_date', 'date', 'tanggal']), date_cols[0])
                range_res = await db_handler.execute_query(f"SELECT MIN({date_col}) as min_d, MAX({date_col}) as max_d FROM {table}")
                if range_res and range_res[0]['min_d']:
                     print(f"Date Range ({date_col}): {range_res[0]['min_d']} to {range_res[0]['max_d']}")
                else:
                     print(f"Date Range ({date_col}): No data or nulls.")
            else:
                 print("Date Range: No date column found.")
            
            # DASH-03: Consistency Kategori (Sentiment specific)
            if table == 'sentiment_analyses':
                sent_res = await db_handler.execute_query("SELECT sentiment_label, COUNT(*) as c FROM sentiment_analyses GROUP BY sentiment_label")
                print("Sentiment Distribution:")
                for row in sent_res:
                    print(f"  - {row['sentiment_label']}: {row['c']}")
            
            # DASH-04: Duplikasi (Heuristic)
            if table == 'news_articles':
                dup_res = await db_handler.execute_query("SELECT COUNT(*) as c FROM (SELECT url, COUNT(*) as cnt FROM news_articles GROUP BY url HAVING COUNT(*) > 1) as sub")
                dup_count = dup_res[0]['c']
                print(f"Duplicate URLs: {dup_count}")

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        await db_handler.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify_data())
