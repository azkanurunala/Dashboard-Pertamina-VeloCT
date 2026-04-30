import os
import json
import pyodbc


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


conn_str = _load_conn_str()

def check_schema():
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        print("--- Columns in data_fossil ---")
        for column in cursor.columns(table='data_fossil'):
            print(f"Column: {column.column_name}, Type: {column.type_name}")
        
        print("\n--- Columns in data_fossil_prediction ---")
        for column in cursor.columns(table='data_fossil_prediction'):
            print(f"Column: {column.column_name}, Type: {column.type_name}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schema()
