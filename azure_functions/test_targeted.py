
import requests
import json
import time

BASE_URL = "http://localhost:7071/api"

FUNCTIONS = [
    {"name": "cpo_scraper_function", "params": {"save_to_db": "true"}},
    {"name": "biodiesel_esdm_scraper_function", "params": {"max_articles": "5", "save_to_db": "true"}},
    {"name": "sandp_data_scraper_function", "params": {"data_type": "bbm_forecast_short", "save_to_db": "true"}},
    {"name": "database_maintenance_function", "params": {}},
    {"name": "deduplication_function", "params": {}},
    {"name": "health_check_function", "params": {}},
]

def test_targeted():
    print(f"Testing {len(FUNCTIONS)} targeted functions at {BASE_URL}...")
    
    for func in FUNCTIONS:
        name = func['name']
        
        # Handle custom routes
        if name == "database_maintenance_function":
            url = f"{BASE_URL}/maintenance"
        elif name == "deduplication_function":
            url = f"{BASE_URL}/deduplicate"
        elif name == "health_check_function":
            url = f"{BASE_URL}/health"
        else:
            url = f"{BASE_URL}/{name}"
            
        print(f"\nTesting: {name}")
        print(f"URL: {url}")
        
        start_time = time.time()
        try:
            response = requests.get(url, params=func.get('params', {}), timeout=300)
            duration = time.time() - start_time
            
            status = "SUCCESS" if response.status_code in [200, 204] else f"FAILED ({response.status_code})"
            print(f"Status: {status}")
            print(f"Duration: {duration:.2f}s")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        print(f"Items: {len(data)}")
                    elif isinstance(data, dict):
                        print("Response: JSON Object")
                except:
                    print("Response is not JSON")
            else:
                print(f"Error: {response.text[:200]}")
                
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_targeted()
