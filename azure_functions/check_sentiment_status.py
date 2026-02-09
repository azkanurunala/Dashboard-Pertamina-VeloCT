import pyodbc
import json
from datetime import datetime

# Database connection details
SERVER = "pei-dashboard.database.windows.net"
DATABASE = "pei-dashboard"
USERNAME = "CloudSAa33fbc7c"
PASSWORD = "uRahcie3&105272"

connection_string = (
    f"Driver={{ODBC Driver 17 for SQL Server}};"
    f"Server=tcp:{SERVER},1433;"
    f"Database={DATABASE};"
    f"Uid={USERNAME};"
    f"Pwd={PASSWORD};"
    f"Encrypt=yes;"
    f"TrustServerCertificate=no;"
    f"Connection Timeout=30;"
)

def check_sentiment():
    print("=" * 70)
    print("Checking Sentiment Analyses Table")
    print("=" * 70)
    
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        
        # Check sentiment_analyses table
        cursor.execute("SELECT COUNT(*) FROM sentiment_analyses")
        count = cursor.fetchone()[0]
        print(f"Total sentiment analyses: {count}")
        
        if count > 0:
            cursor.execute("""
                SELECT TOP 5 
                    sentiment_score, sentiment_label, confidence, summary, analysis_date 
                FROM sentiment_analyses 
                ORDER BY analysis_date DESC
            """)
            rows = cursor.fetchall()
            for i, row in enumerate(rows, 1):
                print(f"\n{i}. Date: {row[4]}")
                print(f"   Score: {row[0]}, Label: {row[1]}, Confidence: {row[2]}")
                print(f"   Summary: {row[3][:100]}...")
        
        # Check sentiment_analysis_articles table
        cursor.execute("SELECT COUNT(*) FROM sentiment_analysis_articles")
        rel_count = cursor.fetchone()[0]
        print(f"\nTotal analysis-article relationships: {rel_count}")
        
        # Check execution logs for analysis functions
        print("\nRecent analysis execution logs:")
        cursor.execute("""
            SELECT TOP 5 function_name, status, start_time, error_message 
            FROM execution_logs 
            WHERE function_name LIKE '%analysis%' OR function_name LIKE '%summary%'
            ORDER BY start_time DESC
        """)
        logs = cursor.fetchall()
        for log in logs:
            print(f"- {log[0]}: {log[1]} at {log[2]} (Error: {log[3]})")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_sentiment()
