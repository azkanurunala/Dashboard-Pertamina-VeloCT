import os
from dotenv import load_dotenv

env_path = os.path.join(os.getcwd(), 'azure_functions', '.env')
print(f"Loading env from: {env_path}")
load_dotenv(env_path)

conn_str = os.getenv('SQL_SERVER_CONNECTION_STRING')
print(f"Connection string found: {'Yes' if conn_str else 'No'}")
if conn_str:
    print(f"Prefix: {conn_str[:20]}...")
