import pyodbc
import datetime
import time

conn_str = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Uid=CloudSAa33fbc7c;Pwd=uRahcie3&105272;Encrypt=no;TrustServerCertificate=yes;"

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    print(f"Checking execution logs at {datetime.datetime.now()}")
    # Use WITH (NOLOCK) to read even if table is being written to
    cursor.execute("SELECT TOP 10 function_name, start_time, status, execution_id FROM execution_logs WITH (NOLOCK) ORDER BY start_time DESC")
    rows = cursor.fetchall()
    
    if not rows:
        print("No execution logs found.")
    else:
        for row in rows:
            print(f"Function: {row.function_name}, Start: {row.start_time}, Status: {row.status}, ID: {row.execution_id}")

    print("\n--- Row Counts ---")
    tables = ["news_articles", "sentiment_analyses", "data_biodiesel_hip", "data_bioetanol_hip", "data_fossil"]
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table} WITH (NOLOCK)")
            count = cursor.fetchone()[0]
            print(f"{table}: {count}")
        except Exception as e:
            print(f"Error counting {table}: {e}")
            
except Exception as e:
    print(f"Error checking logs: {e}")
