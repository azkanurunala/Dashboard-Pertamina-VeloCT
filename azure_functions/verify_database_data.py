"""Verify data was written to SQL Server database"""
import pyodbc
import os
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

print("=" * 70)
print("Verifying Database Data")
print("=" * 70)
print()

try:
    print("Connecting to database...")
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    print("✓ Connected successfully!")
    print()
    
    # Check news_articles table
    print("Checking news_articles table...")
    cursor.execute("SELECT COUNT(*) FROM news_articles")
    article_count = cursor.fetchone()[0]
    print(f"  Total articles: {article_count}")
    
    # Get recent articles
    cursor.execute("""
        SELECT TOP 5 
            na.title, 
            ns.name as source, 
            na.published_date,
            na.scraped_date
        FROM news_articles na
        JOIN news_sources ns ON na.source_id = ns.id
        ORDER BY na.scraped_date DESC
    """)
    
    recent_articles = cursor.fetchall()
    
    if recent_articles:
        print()
        print("Recent articles:")
        for i, (title, source, pub_date, scraped_date) in enumerate(recent_articles, 1):
            print(f"\n{i}. {title[:60]}...")
            print(f"   Source: {source}")
            print(f"   Published: {pub_date}")
            print(f"   Scraped: {scraped_date}")
    
    print()
    
    # Check by source
    print("Articles by source:")
    cursor.execute("""
        SELECT ns.name as source, COUNT(*) as count 
        FROM news_articles na
        JOIN news_sources ns ON na.source_id = ns.id
        GROUP BY ns.name 
        ORDER BY count DESC
    """)
    
    sources = cursor.fetchall()
    for source, count in sources:
        print(f"  {source}: {count} articles")
    
    print()
    
    # Check today's articles
    cursor.execute("""
        SELECT COUNT(*) 
        FROM news_articles 
        WHERE CAST(scraped_date AS DATE) = CAST(GETDATE() AS DATE)
    """)
    today_count = cursor.fetchone()[0]
    print(f"Articles scraped today: {today_count}")
    
    if today_count > 0:
        print()
        print("✓✓✓ DATA SUCCESSFULLY VERIFIED IN DATABASE! ✓✓✓")
    else:
        print()
        print("⚠ No articles scraped today yet")
    
    cursor.close()
    conn.close()
    
except pyodbc.Error as e:
    print(f"✗ Database error: {e}")
except Exception as e:
    print(f"✗ Error: {e}")

print()
print("=" * 70)
