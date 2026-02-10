
import os
import asyncio
import pyodbc
from dotenv import load_dotenv

async def apply_migrations():
    load_dotenv()
    
    conn_str = os.getenv("SQL_SERVER_CONNECTION_STRING") or os.getenv("SQL_CONNECTION_STRING")
    
    if not conn_str:
        # Try reading from local.settings.json
        ls_path = os.path.join(os.path.dirname(__file__), "..", "local.settings.json")
        if os.path.exists(ls_path):
            import json
            with open(ls_path, "r") as f:
                settings = json.load(f)
                conn_str = settings.get("Values", {}).get("SQL_SERVER_CONNECTION_STRING")
    
    if not conn_str:
        print("SQL_SERVER_CONNECTION_STRING not found in .env or local.settings.json")
        return

    sql_file = os.path.join(os.path.dirname(__file__), "migrate_all_tables.sql")
    
    if not os.path.exists(sql_file):
        print(f"Migration file not found: {sql_file}")
        return

    with open(sql_file, "r") as f:
        sql_script = f.read()

    # Split by statements if needed, but the current script uses IF NOT EXISTS blocks
    # which can often be run as a single batch in many drivers, 
    # but strictly speaking, pyodbc prefers separate executions or specific batch markers.
    # Since there are no 'GO' markers in my generated script, I will execute it.

    try:
        print("Connecting to database...")
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("Executing migration script...")
        # Note: We execute the entire script. If using standard SQL Server batches, 
        # normally you'd split by 'GO'. My script doesn't have 'GO'.
        cursor.execute(sql_script)
        
        conn.commit()
        print("Success: Tables created or already exist.")
        
        # Verify tables
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
        tables = cursor.fetchall()
        print("\nCurrent Tables in Database:")
        for t in tables:
            print(f" - {t[0]}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(apply_migrations())
