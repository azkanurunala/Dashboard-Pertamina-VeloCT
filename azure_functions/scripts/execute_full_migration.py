
import os
import pyodbc
from dotenv import load_dotenv

def execute_migration():
    print("Starting full database migration...")
    load_dotenv()
    
    # Use the connection string that worked in direct_migrate_test.py
    conn_str = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Uid=CloudSAa33fbc7c;Pwd=uRahcie3&105272;Encrypt=no;TrustServerCertificate=yes;Connection Timeout=30;"
    
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
