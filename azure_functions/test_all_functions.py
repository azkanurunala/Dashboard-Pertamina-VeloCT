"""
Comprehensive testing script for all Azure Functions
Tests each function and verifies data in SQL Server database
"""
import requests
import json
import time
import pyodbc
from datetime import datetime, timedelta

# Configuration
FUNCTION_APP_URL = "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net"
FUNCTION_KEY = "QRn4YL31yW-bZBFHDlt8znrvRmlfbvD8owXwCBegfk7TAzFuLEZIFg=="  # Default function key
DB_CONNECTION_STRING = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Uid=CloudSAa33fbc7c;Pwd=uRahcie3&105272;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

# Test configuration
TEST_START_DATE = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
TEST_END_DATE = datetime.now().strftime("%Y-%m-%d")
TEST_KEYWORDS = ["energy", "oil", "gas"]

# Functions to test
SCRAPER_FUNCTIONS = [
    "cnbc_scraper_function",
    "cnn_scraper_function",
    "reuters_scraper_function",
    "theguardian_scraper_function",
    "oilprice_scraper_function",
    "kompas_scraper_function",
    "tempo_scraper_function",
    "kontan_scraper_function",
    "bisnis_indonesia_scraper_function",
    "cnbc_indonesia_scraper_function",
    "bps_scraper_function"
]

UTILITY_FUNCTIONS = [
    "test_function",
    "deduplication_function",
    "database_maintenance_function"
]

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)

def print_subheader(text):
    """Print formatted subheader"""
    print(f"\n--- {text} ---")

def test_function(function_name, payload=None, timeout=60):
    """Test a single Azure Function"""
    url = f"{FUNCTION_APP_URL}/api/{function_name}"
    
    # Add function key to URL
    url_with_key = f"{url}?code={FUNCTION_KEY}"
    
    print(f"\n[Testing] {function_name}")
    print(f"  URL: {url}")
    
    try:
        if payload:
            print(f"  Payload: {json.dumps(payload, indent=2)}")
            response = requests.post(url_with_key, json=payload, timeout=timeout)
        else:
            response = requests.get(url_with_key, timeout=timeout)
        
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"  [OK] Success!")
                print(f"  Response: {json.dumps(result, indent=2)[:500]}...")
                return True, result
            except:
                print(f"  [OK] Success! (Non-JSON response)")
                print(f"  Response: {response.text[:200]}...")
                return True, response.text
        else:
            print(f"  [FAIL] Failed!")
            print(f"  Error: {response.text[:200]}")
            return False, None
            
    except requests.exceptions.Timeout:
        print(f"  [WARN] Timeout after {timeout}s (function may still be running)")
        return None, None
    except Exception as e:
        print(f"  [ERROR] Error: {str(e)}")
        return False, None

def check_database_connection():
    """Test database connection"""
    print_subheader("Testing Database Connection")
    try:
        conn = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        print(f"  [OK] Connected to SQL Server")
        print(f"  Version: {version[:100]}...")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"  [ERROR] Connection failed: {e}")
        return False

def get_article_count():
    """Get total article count from database"""
    try:
        conn = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM news_articles")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    except Exception as e:
        print(f"  Error getting count: {e}")
        return None

def get_recent_articles(limit=5):
    """Get recent articles from database"""
    try:
        conn = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP (?) 
                title, 
                source_id, 
                published_date, 
                scraped_date,
                url
            FROM news_articles 
            ORDER BY scraped_date DESC
        """, limit)
        
        articles = []
        for row in cursor.fetchall():
            articles.append({
                'title': row[0],
                'source_id': row[1],
                'published_date': str(row[2]),
                'scraped_date': str(row[3]),
                'url': row[4]
            })
        
        cursor.close()
        conn.close()
        return articles
    except Exception as e:
        print(f"  Error getting articles: {e}")
        return []

def get_articles_by_source():
    """Get article count by source"""
    try:
        conn = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                ns.name,
                COUNT(na.id) as article_count
            FROM news_sources ns
            LEFT JOIN news_articles na ON ns.id = na.source_id
            GROUP BY ns.name
            ORDER BY article_count DESC
        """)
        
        sources = []
        for row in cursor.fetchall():
            sources.append({
                'source': row[0],
                'count': row[1]
            })
        
        cursor.close()
        conn.close()
        return sources
    except Exception as e:
        print(f"  Error getting sources: {e}")
        return []

def main():
    """Main testing function"""
    print_header("Azure Functions Comprehensive Testing")
    print(f"Function App: {FUNCTION_APP_URL}")
    print(f"Test Period: {TEST_START_DATE} to {TEST_END_DATE}")
    print(f"Keywords: {', '.join(TEST_KEYWORDS)}")
    
    # Test database connection first
    print_header("1. Database Connection Test")
    if not check_database_connection():
        print("\n✗ Cannot proceed without database connection!")
        return
    
    # Get initial article count
    print_subheader("Initial Database State")
    initial_count = get_article_count()
    print(f"  Current articles in database: {initial_count}")
    
    # Test utility functions first
    print_header("2. Testing Utility Functions")
    
    # Test function
    print_subheader("Test Function")
    test_function("test_function")
    
    # Test scraper functions
    print_header("3. Testing Scraper Functions")
    
    scraper_results = {}
    
    for func_name in SCRAPER_FUNCTIONS:
        print_subheader(f"Testing {func_name}")
        
        # Prepare payload
        payload = {
            "keywords": TEST_KEYWORDS,
            "start_date": TEST_START_DATE,
            "end_date": TEST_END_DATE
        }
        
        # Test the function
        success, result = test_function(func_name, payload, timeout=120)
        scraper_results[func_name] = success
        
        # Wait a bit between requests
        time.sleep(2)
    
    # Wait for data to be written to database
    print_header("4. Waiting for Data Processing")
    print("  Waiting 10 seconds for data to be written to database...")
    time.sleep(10)
    
    # Check database for new articles
    print_header("5. Database Verification")
    
    print_subheader("Article Count")
    final_count = get_article_count()
    print(f"  Initial count: {initial_count}")
    print(f"  Final count: {final_count}")
    print(f"  New articles: {final_count - initial_count if final_count and initial_count else 'N/A'}")
    
    print_subheader("Recent Articles")
    recent = get_recent_articles(10)
    if recent:
        print(f"  Found {len(recent)} recent articles:")
        for i, article in enumerate(recent, 1):
            print(f"\n  {i}. {article['title'][:80]}")
            print(f"     Source ID: {article['source_id']}")
            print(f"     Published: {article['published_date']}")
            print(f"     URL: {article['url'][:80]}...")
    else:
        print("  No recent articles found")
    
    print_subheader("Articles by Source")
    by_source = get_articles_by_source()
    if by_source:
        print(f"\n  {'Source':<30} {'Count':>10}")
        print(f"  {'-'*30} {'-'*10}")
        for source in by_source:
            print(f"  {source['source']:<30} {source['count']:>10}")
    
    # Test deduplication
    print_header("6. Testing Deduplication Function")
    test_function("deduplicate", timeout=60)
    
    # Final summary
    print_header("7. Test Summary")
    
    print_subheader("Scraper Functions")
    success_count = sum(1 for v in scraper_results.values() if v == True)
    timeout_count = sum(1 for v in scraper_results.values() if v is None)
    failed_count = sum(1 for v in scraper_results.values() if v == False)
    
    print(f"  Total tested: {len(scraper_results)}")
    print(f"  [OK] Successful: {success_count}")
    print(f"  [WARN] Timeout: {timeout_count}")
    print(f"  [FAIL] Failed: {failed_count}")
    
    print("\n  Details:")
    for func, result in scraper_results.items():
        status = "[OK]" if result == True else "[WARN]" if result is None else "[FAIL]"
        print(f"    {status} {func}")
    
    print_subheader("Database Status")
    if final_count and initial_count:
        new_articles = final_count - initial_count
        if new_articles > 0:
            print(f"  [OK] {new_articles} new articles added to database")
        else:
            print(f"  [WARN] No new articles added (may need to check function logs)")
    
    print_header("Testing Complete!")
    print("\nNext steps:")
    print("  1. Review function logs in Azure Portal for any errors")
    print("  2. Check Application Insights for detailed metrics")
    print("  3. Verify data quality in database")
    print("  4. Configure Copilot API for sentiment analysis")
    print("  5. Enable timer triggers for automated scraping")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTesting interrupted by user")
    except Exception as e:
        print(f"\n\n[ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()
