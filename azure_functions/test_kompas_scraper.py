"""Test Kompas scraper on Azure"""
import requests
import json

FUNCTION_APP_URL = "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net"
FUNCTION_KEY = "QRn4YL31yW-bZBFHDlt8znrvRmlfbvD8owXwCBegfk7TAzFuLEZIFg=="

print("Testing Kompas Scraper...")
print("=" * 70)

url = f"{FUNCTION_APP_URL}/api/kompas_scraper_function?code={FUNCTION_KEY}"

# Test payload
payload = {
    "keywords": ["energi"],
    "start_date": "2026-01-28",
    "end_date": "2026-01-28",
    "max_articles": 10
}

print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print()

try:
    response = requests.post(url, json=payload, timeout=120)
    print(f"Status Code: {response.status_code}")
    print()
    
    # Try to parse as JSON
    try:
        result = response.json()
        print("Response (JSON):")
        print(json.dumps(result, indent=2))
    except:
        print("Response (Text):")
        print(response.text)
        
except Exception as e:
    print(f"Error: {e}")

print()
print("=" * 70)
