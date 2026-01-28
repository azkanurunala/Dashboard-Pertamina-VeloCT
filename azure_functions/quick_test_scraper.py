"""Test CNBC scraper function to verify database writes"""
import requests
import json
import time

FUNCTION_APP_URL = "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net"
FUNCTION_KEY = "QRn4YL31yW-bZBFHDlt8znrvRmlfbvD8owXwCBegfk7TAzFuLEZIFg=="

print("=" * 70)
print("Testing CNBC Scraper Function")
print("=" * 70)
print()

url = f"{FUNCTION_APP_URL}/api/cnbc_scraper_function?code={FUNCTION_KEY}"

# Test with a simple request
payload = {
    "keywords": ["energy", "oil"],
    "start_date": "2026-01-27",
    "end_date": "2026-01-28",
    "save_to_db": True
}

print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print()
print("Sending request... (this may take 30-60 seconds)")
print()

try:
    start_time = time.time()
    response = requests.post(url, json=payload, timeout=120)
    elapsed = time.time() - start_time
    
    print(f"Status Code: {response.status_code}")
    print(f"Elapsed Time: {elapsed:.1f}s")
    print()
    
    if response.status_code == 200:
        result = response.json()
        print("✓ SUCCESS!")
        print()
        print("Results:")
        print(f"  - Articles Found: {result.get('results', {}).get('articles_found', 0)}")
        print(f"  - Articles Saved to DB: {result.get('results', {}).get('articles_saved', 0)}")
        print(f"  - Execution Time: {result.get('execution_time_seconds', 0):.1f}s")
        print()
        
        if result.get('results', {}).get('articles_saved', 0) > 0:
            print("✓✓✓ DATA SUCCESSFULLY WRITTEN TO DATABASE! ✓✓✓")
            print()
            print("Sample articles:")
            for i, article in enumerate(result.get('results', {}).get('articles', [])[:3], 1):
                print(f"\n{i}. {article.get('title', 'N/A')}")
                print(f"   URL: {article.get('url', 'N/A')}")
                print(f"   Date: {article.get('published_date', 'N/A')}")
        else:
            print("⚠ No articles were saved to database")
            print("This might be normal if no articles matched the criteria")
    else:
        print("✗ FAILED!")
        print()
        print("Response:")
        print(response.text)
        
except requests.exceptions.Timeout:
    print("✗ Request timed out (>120s)")
    print("The function might still be running. Check Azure Portal logs.")
except Exception as e:
    print(f"✗ Error: {e}")

print()
print("=" * 70)
