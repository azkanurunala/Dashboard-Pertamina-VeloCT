import os
import json
import pyodbc
from dotenv import load_dotenv


def _load_conn_str() -> str:
    conn = os.getenv("SQL_SERVER_CONNECTION_STRING")
    if not conn:
        settings_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "local.settings.json"))
        if os.path.exists(settings_path):
            with open(settings_path) as f:
                conn = json.load(f).get("Values", {}).get("SQL_SERVER_CONNECTION_STRING")
    if not conn:
        raise RuntimeError("SQL_SERVER_CONNECTION_STRING not set (env var or local.settings.json).")
    return conn


def execute_migration():
    print("Starting full database migration...")
    load_dotenv()

    conn_str = _load_conn_str()
    
    sql_file_path = r"azure_functions\scripts\migrate_all_tables.sql"
    
    if not os.path.exists(sql_file_path):
        print(f"Error: SQL file not found at {sql_file_path}")
        return

    try:
        print("Connecting to database...")
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print(f"Reading SQL file: {sql_file_path}")
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        print("Executing migration script...")
        # Split into individual statements if needed, but IF NOT EXISTS is fine in one block for T-SQL
        cursor.execute(sql_script)
        conn.commit()
        
        print("Migration completed successfully!")
        conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    execute_migration()
