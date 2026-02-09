
import pyodbc
import os
from dotenv import load_dotenv

load_dotenv('azure_functions/.env')

connection_string = os.getenv('SQL_SERVER_CONNECTION_STRING')

def check_db_schema():
    if not connection_string:
        print("❌ No connection string found in .env")
        return

    print("🔍 Connecting to database...")
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        
        print("\n📊 Table Info for ScrapedArticles:")
        cursor.execute("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'ScrapedArticles'")
        columns = cursor.fetchall()
        
        if not columns:
            print("  ❌ Table 'ScrapedArticles' not found!")
        else:
            for col in columns:
                print(f"  - {col[0]} ({col[1]})")
        
        conn.close()
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    check_db_schema()
