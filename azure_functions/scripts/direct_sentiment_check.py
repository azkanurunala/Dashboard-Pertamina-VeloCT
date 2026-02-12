
import pyodbc
from datetime import datetime

def check_sentiment_direct():
    print(f"--- Direct Sentiment Check ({datetime.now()}) ---")
    conn_str = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Uid=CloudSAa33fbc7c;Pwd=uRahcie3&105272;Encrypt=no;TrustServerCertificate=yes;Connection Timeout=30;"
    
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Count
        cursor.execute("SELECT COUNT(*) as c FROM sentiment_analyses")
        row = cursor.fetchone()
        count = row[0] if row else 0
        print(f"Total Sentiment Records: {count}")

        if count > 0:
            cursor.execute("SELECT TOP 1 id, sentiment_score, sentiment_label, confidence, summary, analysis_date FROM sentiment_analyses ORDER BY analysis_date DESC")
            row = cursor.fetchone()
            if row:
                print("\nLatest Analysis:")
                print(f"  ID: {row[0]}")
                print(f"  Score: {row[1]}")
                print(f"  Label: {row[2]}")
                print(f"  Confidence: {row[3]}")
                print(f"  Date: {row[5]}")
        else:
            print("No sentiment records found.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_sentiment_direct()
