import pyodbc
import json
import os

settings_path = r'azure_functions\local.settings.json'
with open(settings_path, 'r') as f:
    data = json.load(f)
    conn_str = data.get('Values', {}).get('SQL_SERVER_CONNECTION_STRING')

# Use local settings
conn_str = conn_str.replace("Encrypt=yes", "Encrypt=no").replace("TrustServerCertificate=no", "TrustServerCertificate=yes")

print(f"Testing connection string: {conn_str}")
try:
    conn = pyodbc.connect(conn_str, timeout=5)
    print("Success!")
    conn.close()
except Exception as e:
    print(f"Failure: {e}")
