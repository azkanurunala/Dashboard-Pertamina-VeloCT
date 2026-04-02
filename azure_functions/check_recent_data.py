import pyodbc
import json
import os
from datetime import datetime, timedelta

settings_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\local.settings.json'
with open(settings_path, 'r') as f:
    data = json.load(f)
    conn_str = data.get('Values', {}).get('SQL_SERVER_CONNECTION_STRING')

conn_str = conn_str.replace("Encrypt=yes", "Encrypt=no").replace("TrustServerCertificate=no", "TrustServerCertificate=yes")

try:
    conn = pyodbc.connect(conn_str, timeout=5)
    cursor = conn.cursor()
    
    # Let's list all tables first to see what we have
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
    tables = [row[0] for row in cursor.fetchall()]
    print("Tables in database:", tables)
    
    # Check max date or recent rows from some tables
    for table in tables:
        if table in ['news_articles', 'cpo_data', 'eia_data', 'macro_indicators']:
            try:
                # Find date column
                cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='{table}' AND DATA_TYPE IN ('date', 'datetime', 'datetime2')")
                date_cols = [row[0] for row in cursor.fetchall()]
                
                if date_cols:
                    date_col = date_cols[0] # Pick the first one, e.g., published_date or date
                    if 'created_at' in date_cols:
                        date_col = 'created_at'
                    if 'scraped_date' in date_cols:
                        date_col = 'scraped_date'
                    if 'tanggal' in date_cols:
                        date_col = 'tanggal'
                    if 'date' in date_cols:
                         date_col = 'date'

                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    total = cursor.fetchone()[0]
                    
                    cursor.execute(f"SELECT MAX({date_col}) FROM {table}")
                    max_date = cursor.fetchone()[0]
                     
                    # 7 days ago
                    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                    cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {date_col} >= '{seven_days_ago}'")
                    recent = cursor.fetchone()[0]
                    
                    print(f"Table {table}: Total={total}, Max {date_col}={max_date}, Recently inserted (last 7 days)={recent}")
            except Exception as e:
                print(f"Error querying {table}: {e}")

    conn.close()
except Exception as e:
    print(f"Connection/Query Failure: {e}")
