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


print("Diagnostic script starting...")
load_dotenv()

conn_str = _load_conn_str()
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
