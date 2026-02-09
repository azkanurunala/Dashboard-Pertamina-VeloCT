import pyodbc
import os
from dotenv import load_dotenv

load_dotenv('azure_functions/.env')

def get_schema():
    # Updated connection string based on user screenshot
    # Encrypt=Optional -> removed or no
    # TrustServerCertificate=yes
    conn_str = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Uid=CloudSAa33fbc7c;Pwd=uRahcie3&105272;Encrypt=no;TrustServerCertificate=yes;Connection Timeout=30;"

    print(f"Connecting to DB with parameters: Encrypt=no, TrustServerCertificate=yes...")
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        
        tables = ['news_articles', 'news_sources', 'keywords', 'article_keywords']
        
        for table in tables:
            print(f"\n--- Schema for table: {table} ---")
            cursor.execute(f"SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table}'")
            columns = cursor.fetchall()
            if not columns:
                print("No columns found or table doesn't exist.")
            for col in columns:
                print(f"Column: {col[0]}, Type: {col[1]}, Nullable: {col[2]}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_schema()
