"""
Quick test for a single function with detailed error output
"""
import requests
import json

FUNCTION_APP_URL = "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net"
FUNCTION_KEY = "QRn4YL31yW-bZBFHDlt8znrvRmlfbvD8owXwCBegfk7TAzFuLEZIFg=="

# Test the test_function first (simplest one)
print("=" * 80)
print("Testing test_function (simplest function)")
print("=" * 80)

url = f"{FUNCTION_APP_URL}/api/test_function?code={FUNCTION_KEY}"
print(f"URL: {url}\n")

try:
    response = requests.get(url, timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}\n")
    print(f"Response Body:")
    print(response.text)
    print()
    
    if response.status_code == 200:
        print("✓ SUCCESS!")
    else:
        print("✗ FAILED!")
        
except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "=" * 80)
print("Testing CNBC scraper with detailed error")
print("=" * 80)

url = f"{FUNCTION_APP_URL}/api/cnbc_scraper_function?code={FUNCTION_KEY}"
payload = {
    "keywords": ["energy"],
    "start_date": "2026-01-27",
    "end_date": "2026-01-28"
}

print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}\n")

try:
    response = requests.post(url, json=payload, timeout=120)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body:")
    print(response.text)
    print()
    
    if response.status_code == 200:
        print("✓ SUCCESS!")
        try:
            result = response.json()
            print(f"\nArticles found: {result.get('results', {}).get('articles_found', 0)}")
            print(f"Articles saved: {result.get('results', {}).get('articles_saved', 0)}")
        except:
            pass
    else:
        print("✗ FAILED!")
        
except Exception as e:
    print(f"✗ Error: {e}")
