import pyodbc
import json

try:
    with open('local.settings.json', 'r') as f:
        data = json.load(f)
        conn_str = data.get('Values', {}).get('SQL_SERVER_CONNECTION_STRING')
        
    print(f"Connection string length: {len(conn_str)}")
    
    conn = pyodbc.connect(conn_str, timeout=15)
    cr = conn.cursor()
    
    cr.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'execution_logs'
    """)
    
    cols = cr.fetchall()
    print("\nColumns in execution_logs:")
    for c in cols:
        print(f" - {c.COLUMN_NAME}: {c.DATA_TYPE} (Nullable: {c.IS_NULLABLE})")
        
    conn.close()
    print("Done.")
except Exception as e:
    print(f"Error: {e}")
