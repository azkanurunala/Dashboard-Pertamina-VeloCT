import pyodbc
import json
import os

settings_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\local.settings.json'
with open(settings_path, 'r') as f:
    data = json.load(f)
    conn_str = data.get('Values', {}).get('SQL_SERVER_CONNECTION_STRING')

conn_str = conn_str.replace("Encrypt=yes", "Encrypt=no").replace("TrustServerCertificate=no", "TrustServerCertificate=yes")

output_lines = []
try:
    conn = pyodbc.connect(conn_str, timeout=5)
    cursor = conn.cursor()
    
    # Check for 'indeks kepercayaan knsmn' category specifically
    cursor.execute("SELECT COUNT(*) FROM news_articles WHERE category = 'indeks kepercayaan knsmn'")
    total = cursor.fetchone()[0]
    
    output_lines.append(f"Total articles with category 'indeks kepercayaan knsmn': {total}")
    
    # Let's check what categories actually exist that are similar
    cursor.execute("SELECT category, COUNT(*) FROM news_articles WHERE LOWER(category) LIKE '%indeks%' OR LOWER(category) LIKE '%knsmn%' OR LOWER(category) LIKE '%konsumen%' OR LOWER(category) LIKE '%ikk%' GROUP BY category")
    similar_cats = cursor.fetchall()
    output_lines.append("\nSimilar categories found:")
    for cat in similar_cats:
        output_lines.append(f" - '{cat[0]}': {cat[1]} articles")

    # Let's check the date range for any available 'indeks kepercayaan knsmn' articles if any
    if total > 0:
        cursor.execute("SELECT MIN(published_date), MAX(published_date) FROM news_articles WHERE category = 'indeks kepercayaan knsmn'")
        dates = cursor.fetchone()
        output_lines.append(f"\nDate range for 'indeks kepercayaan knsmn': {dates[0]} to {dates[1]}")
        
    conn.close()
except Exception as e:
    output_lines.append(f"Connection/Query Failure: {e}")

with open("category_output.txt", "w") as f:
    f.write("\n".join(output_lines))
