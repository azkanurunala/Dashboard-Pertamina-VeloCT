
import os
import pyodbc
from dotenv import load_dotenv

print("Diagnostic script starting...")
load_dotenv()

conn_str = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Uid=CloudSAa33fbc7c;Pwd=uRahcie3&105272;Encrypt=no;TrustServerCertificate=yes;Connection Timeout=30;"
print(f"Attempting to connect with Driver 17...")

try:
    conn = pyodbc.connect(conn_str, timeout=10)
    print("SUCCESS: Connected to database!")
    cursor = conn.cursor()
    cursor.execute("SELECT @@VERSION")
    row = cursor.fetchone()
    print(f"Version: {row[0]}")
    conn.close()
except Exception as e:
    print(f"FAILED: {e}")
