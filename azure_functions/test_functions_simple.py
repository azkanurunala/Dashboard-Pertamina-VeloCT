# -*- coding: utf-8 -*-
"""
Simple testing script for Azure Functions - ASCII only
"""
import requests
import json
import time
import pyodbc
from datetime import datetime, timedelta
import sys

# Set UTF-8 encoding for console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Configuration
FUNCTION_APP_URL = "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net"
FUNCTION_KEY = "QRn4YL31yW-bZBFHDlt8znrvRmlfbvD8owXwCBegfk7TAzFuLEZIFg=="
DB_CONN = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Uid=CloudSAa33fbc7c;Pwd=uRahcie3&105272;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

# Test dates
START_DATE = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
END_DATE = datetime.now().strftime("%Y-%m-%d")

print("="*80)
print("Azure Functions Testing")
print("="*80)
print(f"URL: {FUNCTION_APP_URL}")
print(f"Period: {START_DATE} to {END_DATE}")
print()

# Test database
print("Testing database connection...")
try:
    conn = pyodbc.connect(DB_CONN)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM news_articles")
    initial_count = cursor.fetchone()[0]
    print(f"[OK] Database connected. Current articles: {initial_count}")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"[ERROR] Database connection failed: {e}")
    sys.exit(1)

# Test one scraper function
print("\n" + "="*80)
print("Testing CNBC Scraper Function")
print("="*80)

url = f"{FUNCTION_APP_URL}/api/cnbc_scraper_function?code={FUNCTION_KEY}"
payload = {
    "keywords": ["energy", "oil"],
    "start_date": START_DATE,
    "end_date": END_DATE
}

print(f"URL: {url[:80]}...")
print(f"Payload: {json.dumps(payload)}")
print("\nSending request...")

try:
    response = requests.post(url, json=payload, timeout=120)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        print("[OK] Function executed successfully!")
        try:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)[:500]}")
        except:
            print(f"Response: {response.text[:500]}")
    else:
        print(f"[FAIL] Function failed!")
        print(f"Error: {response.text[:500]}")
        
except requests.exceptions.Timeout:
    print("[WARN] Request timed out (function may still be running)")
except Exception as e:
    print(f"[ERROR] Request failed: {e}")

# Wait and check database
print("\nWaiting 15 seconds for data to be written...")
time.sleep(15)

print("\nChecking database for new articles...")
try:
    conn = pyodbc.connect(DB_CONN)
    cursor = conn.cursor()
    
    # Get count
    cursor.execute("SELECT COUNT(*) FROM news_articles")
    final_count = cursor.fetchone()[0]
    new_articles = final_count - initial_count
    
    print(f"Initial count: {initial_count}")
    print(f"Final count: {final_count}")
    print(f"New articles: {new_articles}")
    
    if new_articles > 0:
        print(f"\n[OK] {new_articles} new articles added!")
        
        # Show recent articles
        cursor.execute("""
            SELECT TOP 5 title, url, published_date 
            FROM news_articles 
            ORDER BY scraped_date DESC
        """)
        
        print("\nRecent articles:")
        for i, row in enumerate(cursor.fetchall(), 1):
            print(f"\n{i}. {row[0][:80]}")
            print(f"   URL: {row[1][:80]}")
            print(f"   Date: {row[2]}")
    else:
        print("\n[WARN] No new articles added")
        print("Check function logs in Azure Portal for errors")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"[ERROR] Database check failed: {e}")

print("\n" + "="*80)
print("Testing Complete!")
print("="*80)
print("\nNext steps:")
print("1. Check Azure Portal > Function App > Monitor for detailed logs")
print("2. Test other scraper functions")
print("3. Configure Copilot API for sentiment analysis")
