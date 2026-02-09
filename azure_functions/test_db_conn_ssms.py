import pyodbc

# Exact parameters from SSMS screenshot
server = 'pei-dashboard.database.windows.net'
database = 'pei-dashboard'
username = 'CloudSAa33fbc7c'
password = 'uRahcie3&105272'
driver = '{ODBC Driver 17 for SQL Server}'

# Encrypt=Optional (no)
# TrustServerCertificate=yes
conn_str = f'DRIVER={driver};SERVER={server};PORT=1433;DATABASE={database};UID={username};PWD={password};Encrypt=no;TrustServerCertificate=yes;Connection Timeout=10;'

def test_connection():
    print(f"Connecting to {server}...")
    try:
        conn = pyodbc.connect(conn_str, timeout=5)
        print("✅ SUCCESS: Connected to Azure SQL!")
        cursor = conn.cursor()
        
        print("\n--- Testing table check ---")
        cursor.execute("SELECT TOP 1 * FROM news_articles")
        row = cursor.fetchone()
        print(f"Data found: {'Yes' if row else 'No'}")
        
        print("\n--- Column List (news_articles) ---")
        cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'news_articles'")
        for r in cursor.fetchall():
            print(f"Column: {r[0]}")
            
        conn.close()
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")

if __name__ == "__main__":
    test_connection()
