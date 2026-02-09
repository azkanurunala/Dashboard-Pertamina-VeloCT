import requests
import json

def test_function(name, url):
    print(f"Testing {name}...")
    try:
        r = requests.get(url, timeout=120)
        print(f"  Status: {r.status_code}")
        try:
            data = r.json()
            print(f"  Articles Found: {data.get('results', {}).get('articles_found', 0)}")
            print(f"  Articles Saved: {data.get('results', {}).get('articles_saved', 0)}")
        except:
            print(f"  Response: {r.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")
    print("-" * 30)

base_url = "http://localhost:7071/api"
targets = [
    ("Tempo", f"{base_url}/tempo_scraper_function?save_to_db=true&max_articles=1"),
    ("CNBC", f"{base_url}/cnbc_scraper_function?save_to_db=true&max_articles=1"),
    ("Kompas", f"{base_url}/kompas_scraper_function?save_to_db=true&max_articles=1"),
    ("Kontan", f"{base_url}/kontan_scraper_function?save_to_db=true&max_articles=1")
]

for name, url in targets:
    test_function(name, url)
