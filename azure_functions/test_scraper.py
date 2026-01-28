"""Test individual scraper functions"""
import requests
import json
import sys
import time

FUNCTION_APP_URL = "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net"
FUNCTION_KEY = "QRn4YL31yW-bZBFHDlt8znrvRmlfbvD8owXwCBegfk7TAzFuLEZIFg=="

SCRAPERS = {
    "cnbc": "cnbc_scraper_function",
    "cnn": "cnn_scraper_function",
    "reuters": "reuters_scraper_function",
    "theguardian": "theguardian_scraper_function",
    "oilprice": "oilprice_scraper_function",
    "bisnis_indonesia": "bisnis_indonesia_scraper_function",
    "cnbc_indonesia": "cnbc_indonesia_scraper_function",
    "kompas": "kompas_scraper_function",
    "kontan": "kontan_scraper_function",
    "tempo": "tempo_scraper_function",
    "bps": "bps_scraper_function"
}

def test_scraper(scraper_name):
    """Test a specific scraper function"""
    
    if scraper_name not in SCRAPERS:
        print(f"Error: Unknown scraper '{scraper_name}'")
        print(f"Available scrapers: {', '.join(SCRAPERS.keys())}")
        return False
    
    function_name = SCRAPERS[scraper_name]
    
    print("=" * 70)
    print(f"Testing {scraper_name.upper()} Scraper")
    print("=" * 70)
    print()
    
    url = f"{FUNCTION_APP_URL}/api/{function_name}?code={FUNCTION_KEY}"
    
    # Default payload
    payload = {
        "keywords": ["energy", "oil", "gas"],
        "start_date": "2026-01-27",
        "end_date": "2026-01-28",
        "save_to_db": True
    }
    
    print(f"Function: {function_name}")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()
    print("Sending request... (may take 30-120 seconds)")
    print()
    
    try:
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=180)
        elapsed = time.time() - start_time
        
        print(f"Status Code: {response.status_code}")
        print(f"Elapsed Time: {elapsed:.1f}s")
        print()
        
        if response.status_code == 200:
            result = response.json()
            print("✓ SUCCESS!")
            print()
            print("Results:")
            print(f"  Status: {result.get('status', 'unknown')}")
            print(f"  Source: {result.get('source', 'unknown')}")
            print(f"  Articles Found: {result.get('results', {}).get('articles_found', 0)}")
            print(f"  Articles Saved: {result.get('results', {}).get('articles_saved', 0)}")
            print(f"  Execution Time: {result.get('execution_time_seconds', 0):.1f}s")
            
            articles = result.get('results', {}).get('articles', [])
            if articles:
                print()
                print("Sample articles:")
                for i, article in enumerate(articles[:3], 1):
                    print(f"\n{i}. {article.get('title', 'N/A')[:60]}...")
                    print(f"   URL: {article.get('url', 'N/A')}")
                    print(f"   Date: {article.get('published_date', 'N/A')}")
            
            print()
            if result.get('results', {}).get('articles_saved', 0) > 0:
                print("✓✓✓ DATA SUCCESSFULLY SAVED TO DATABASE! ✓✓✓")
                return True
            else:
                print("⚠ No articles saved (might be normal if no matches found)")
                return True
        else:
            print("✗ FAILED!")
            print()
            print("Response:")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2))
            except:
                print(response.text)
            return False
            
    except requests.exceptions.Timeout:
        print("✗ Request timed out (>180s)")
        print("The function might still be running. Check Azure Portal logs.")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    finally:
        print()
        print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_scraper.py <scraper_name>")
        print()
        print("Available scrapers:")
        for name in sorted(SCRAPERS.keys()):
            print(f"  - {name}")
        print()
        print("Example: python test_scraper.py cnbc")
        sys.exit(1)
    
    scraper_name = sys.argv[1].lower()
    success = test_scraper(scraper_name)
    sys.exit(0 if success else 1)
