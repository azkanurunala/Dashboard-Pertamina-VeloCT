import pyodbc
import os
from dotenv import load_dotenv

load_dotenv('azure_functions/.env')

conn_str = os.getenv('SQL_SERVER_CONNECTION_STRING')
print(f"Connecting to server...")

try:
    conn = pyodbc.connect(conn_str, timeout=10)
    print("Connection Successful!")
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    print(f"Result: {cursor.fetchone()}")
    conn.close()
except Exception as e:
    print(f"Connection Failed: {e}")
