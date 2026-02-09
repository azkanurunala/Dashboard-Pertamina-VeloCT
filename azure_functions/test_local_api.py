import requests
import json
from datetime import datetime, timedelta
import time
import sys

# Configuration
BASE_URL = "http://localhost:7071/api"
START_DATE = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
END_DATE = datetime.now().strftime('%Y-%m-%d')
KEYWORDS_EN = "energy"
KEYWORDS_ID = "energi"

# List of functions to test
FUNCTIONS = [
    {"name": "bank_indonesia_scraper_function", "params": {"keywords": KEYWORDS_ID, "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "biodiesel_esdm_scraper_function", "params": {"keywords": KEYWORDS_ID, "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "bioenergytimes_scraper_function", "params": {"keywords": KEYWORDS_EN, "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "bioetanol_esdm_scraper_function", "params": {"keywords": KEYWORDS_ID, "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "bisnis_indonesia_scraper_function", "params": {"keywords": KEYWORDS_ID, "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "bloomberg_technoz_scraper_function", "params": {"keywords": KEYWORDS_ID, "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "bps_scraper_function", "params": {"indicators": "inflation", "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "cnbc_indonesia_scraper_function", "params": {"keywords": KEYWORDS_ID, "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "cnbc_scraper_function", "params": {"keywords": KEYWORDS_EN, "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "cnn_scraper_function", "params": {"keywords": KEYWORDS_EN, "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "cpo_scraper_function", "params": {"keywords": KEYWORDS_EN, "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "database_maintenance_function", "params": {}}, # Likely POST but trying GET first or specific params
    {"name": "deduplication_function", "params": {}},
    {"name": "energiesmedia_scraper_function", "params": {"keywords": KEYWORDS_EN, "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "google_news_scraper_function", "params": {"keywords": KEYWORDS_EN, "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "health_check_function", "params": {}},
    {"name": "iaea_pris_scraper_function", "params": {"keywords": KEYWORDS_EN, "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "kompas_scraper_function", "params": {"keywords": KEYWORDS_ID, "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "kontan_bbm_scraper_function", "params": {"keywords": "bbm", "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "kontan_biodiesel_scraper_function", "params": {"keywords": "biodiesel", "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "kontan_scraper_function", "params": {"keywords": KEYWORDS_ID, "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "migas_eia_scraper_function", "params": {"keywords": "oil", "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "migas_esdm_scraper_function", "params": {"keywords": "migas", "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "oilprice_scraper_function", "params": {"keywords": KEYWORDS_EN, "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "reuters_scraper_function", "params": {"keywords": KEYWORDS_EN, "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "sandp_data_scraper_function", "params": {"keywords": KEYWORDS_EN, "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "sandp_news_scraper_function", "params": {"keywords": KEYWORDS_EN, "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "scmp_scraper_function", "params": {"keywords": KEYWORDS_EN, "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "sipsn_scraper_function", "params": {"keywords": "waste", "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "tempo_scraper_function", "params": {"keywords": KEYWORDS_ID, "start_date": START_DATE, "end_date": END_DATE}},
    {"name": "test_env_function", "params": {}},
    {"name": "test_function", "params": {}},
    {"name": "test_imports_function", "params": {}},
    {"name": "test_new_deploy_function", "params": {}},
    {"name": "theguardian_scraper_function", "params": {"keywords": KEYWORDS_EN, "start_date": START_DATE, "end_date": END_DATE}},
]

def test_api():
    print(f"Testing {len(FUNCTIONS)} functions at {BASE_URL}...")
    
    results = []
    
    for func in FUNCTIONS:
        # Handle custom routes
        if func['name'] == "database_maintenance_function":
            url = f"{BASE_URL}/maintenance"
        elif func['name'] == "deduplication_function":
            url = f"{BASE_URL}/deduplicate"
        elif func['name'] == "health_check_function":
            url = f"{BASE_URL}/health"
        else:
            url = f"{BASE_URL}/{func['name']}"
            
        print(f"\nTesting: {func['name']}")
        print(f"URL: {url}")
        
        try:
            start_time = time.time()
            # Adding max_articles=1 to scrape quickly for testing
            params = func['params'].copy()
            if 'keywords' in params: # It's likely a scraper
                params['max_articles'] = '5'
                params['save_to_db'] = 'true'
            
            response = requests.get(url, params=params, timeout=300)
            duration = time.time() - start_time
            
            status = "SUCCESS" if response.status_code == 200 else "FAILED"
            print(f"Status: {response.status_code} ({status})")
            print(f"Duration: {duration:.2f}s")
            
            try:
                data = response.json()
                # print(f"Response: {str(data)[:100]}...")
                if 'results' in data and 'articles_found' in data['results']:
                    print(f"Articles: {data['results']['articles_found']}")
            except:
                print("Response is not JSON")
                
            results.append({
                "name": func['name'],
                "status": status,
                "code": response.status_code,
                "duration": duration
            })
            
        except Exception as e:
            print(f"Error: {e}")
            results.append({
                "name": func['name'],
                "status": "ERROR",
                "code": 0,
                "duration": 0,
                "error": str(e)
            })

    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    success_count = sum(1 for r in results if r['status'] == 'SUCCESS')
    print(f"Total: {len(results)}")
    print(f"Success: {success_count}")
    print(f"Failed: {len(results) - success_count}")
    
    print("\nDetails:")
    for r in results:
        icon = "✓" if r['status'] == 'SUCCESS' else "✗"
        print(f"{icon} {r['name']:<40} {r['code']} ({r['duration']:.2f}s)")
        
    # Write to file
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    test_api()
