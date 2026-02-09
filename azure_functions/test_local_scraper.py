"""Test local scraper function"""
import requests
import json

# Local function host URL
URL = "http://localhost:7071/api/tempo_scraper_function"

print("Testing Local Scraper (Tempo)...")
print("=" * 60)

# Payload for requested date range
payload = {
    "keywords": ["pertamina"],
    "start_date": "2025-01-01",
    "end_date": "2026-02-09",
    "save_to_db": True
}

print(f"URL: {URL}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print()

try:
    print("Sending request (this might take a few seconds)...")
    response = requests.post(URL, json=payload, timeout=120)
    print(f"Status Code: {response.status_code}")
    print()
    
    try:
        result = response.json()
        print("Response Summary:")
        print(f"  Source: {result.get('source')}")
        print(f"  Articles Found: {result.get('results', {}).get('articles_found')}")
        print(f"  Articles Saved: {result.get('results', {}).get('articles_saved')}")
        
        if result.get('results', {}).get('persistence_error'):
            print(f"  ❌ Persistence Error: {result['results']['persistence_error']}")
        elif result.get('results', {}).get('articles_saved', 0) > 0:
            print("  ✓ SUCCESS: Articles saved to database!")
            
    except Exception as e:
        print("Response (Text):")
        print(response.text)
        
except Exception as e:
    print(f"Error connecting to local host: {e}")
    print("Make sure `func host start` is running in another terminal.")

print()
print("=" * 60)
