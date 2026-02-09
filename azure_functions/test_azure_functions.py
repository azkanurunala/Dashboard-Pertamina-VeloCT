import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:7071" # Changed to root for Admin API access

# Configuration for test params
START_DATE = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
END_DATE = datetime.now().strftime('%Y-%m-%d')
KEYWORDS_EN = "energy"
KEYWORDS_ID = "energi"

# Comprehensive list of all 39 functions (35 HTTP + 4 Timers)
FUNCTIONS = [
    # HTTP Scrapers & APIs (35)
    {"name": "bank_indonesia_scraper_function", "params": {"keywords": KEYWORDS_ID}},
    {"name": "biodiesel_esdm_scraper_function", "params": {"keywords": KEYWORDS_ID}},
    {"name": "bioenergytimes_scraper_function", "params": {"keywords": KEYWORDS_EN}},
    {"name": "bioetanol_esdm_scraper_function", "params": {"keywords": KEYWORDS_ID}},
    {"name": "bisnis_indonesia_scraper_function", "params": {"keywords": KEYWORDS_ID}},
    {"name": "bloomberg_technoz_scraper_function", "params": {"keywords": KEYWORDS_ID}},
    {"name": "bps_scraper_function", "params": {"indicators": "inflation"}},
    {"name": "cnbc_indonesia_scraper_function", "params": {"keywords": KEYWORDS_ID}},
    {"name": "cnbc_scraper_function", "params": {"keywords": KEYWORDS_EN}},
    {"name": "cnn_scraper_function", "params": {"keywords": KEYWORDS_EN}},
    {"name": "cpo_scraper_function", "params": {"keywords": KEYWORDS_EN}},
    {"name": "database_maintenance_function", "route": "api/maintenance", "params": {"operation": "health_check"}},
    {"name": "deduplication_function", "route": "api/deduplicate"},
    {"name": "energiesmedia_scraper_function", "params": {"keywords": KEYWORDS_EN}},
    {"name": "google_news_scraper_function", "params": {"keywords": KEYWORDS_EN}},
    {"name": "health_check_function", "route": "api/health"},
    {"name": "iaea_pris_scraper_function", "params": {"keywords": KEYWORDS_EN}},
    {"name": "kompas_scraper_function", "params": {"keywords": KEYWORDS_ID}},
    {"name": "kontan_bbm_scraper_function", "params": {"keywords": "bbm"}},
    {"name": "kontan_biodiesel_scraper_function", "params": {"keywords": "biodiesel"}},
    {"name": "kontan_scraper_function", "params": {"keywords": KEYWORDS_ID}},
    {"name": "migas_eia_scraper_function", "params": {"keywords": "oil"}},
    {"name": "migas_esdm_scraper_function", "params": {"keywords": "migas"}},
    {"name": "oilprice_scraper_function", "params": {"keywords": KEYWORDS_EN}},
    {"name": "reuters_scraper_function", "params": {"keywords": KEYWORDS_EN}},
    {"name": "sandp_data_scraper_function", "params": {"keywords": KEYWORDS_EN}},
    {"name": "sandp_news_scraper_function", "params": {"keywords": KEYWORDS_EN}},
    {"name": "scmp_scraper_function", "params": {"keywords": KEYWORDS_EN}},
    {"name": "sipsn_scraper_function", "params": {"keywords": "waste"}},
    {"name": "tempo_scraper_function", "params": {"keywords": KEYWORDS_ID}},
    {"name": "test_env_function", "route": "api/test_env_function"},
    {"name": "test_function", "route": "api/test_function"},
    {"name": "test_imports_function", "route": "api/test_imports_function"},
    {"name": "test_new_deploy_function", "route": "api/test_new_deploy_function"},
    {"name": "theguardian_scraper_function", "params": {"keywords": KEYWORDS_EN}},
    
    # Timer Triggers (4) - Triggered via Admin API locally
    {"name": "daily_afternoon_timer", "is_timer": True},
    {"name": "daily_morning_timer", "is_timer": True},
    {"name": "monthly_aggregation_timer", "is_timer": True},
    {"name": "weekly_summary_timer", "is_timer": True},
]

def test_all():
    print(f"🧪 Testing {len(FUNCTIONS)} Azure Functions at {BASE_URL}")
    print("="*65)
    results = []
    
    for func_cfg in FUNCTIONS:
        name = func_cfg["name"]
        is_timer = func_cfg.get("is_timer", False)
        
        if is_timer:
            url = f"{BASE_URL}/admin/functions/{name}"
            method = "POST"
            payload = {"input": "{}"}
        else:
            route = func_cfg.get("route", f"api/{name}")
            url = f"{BASE_URL}/{route}"
            method = "GET"
            payload = None
        
        # Build params for HTTP Scrapers
        params = func_cfg.get("params", {}).copy()
        if not is_timer:
            params["start_date"] = START_DATE
            params["end_date"] = END_DATE
            # Optimization for local testing
            if "keywords" in params or "indicators" in params:
                params["max_articles"] = "3"
                params["save_to_db"] = "true"
        
        print(f"\nTesting: {name} ({'Timer' if is_timer else 'HTTP'})...")
        
        start_time = time.time()
        try:
            if method == "POST":
                response = requests.post(url, json=payload, timeout=3000)
            else:
                response = requests.get(url, params=params, timeout=3000)
                
            duration = time.time() - start_time
            
            # For POST /admin, 202 is or 204 is success, for GET 200 is success
            success_codes = [200, 202, 204]
            
            if response.status_code in success_codes:
                status = "✅ SUCCESS"
                print(f"  Status: {status}")
            else:
                status = f"❌ FAILED ({response.status_code})"
                print(f"  Status: {status}")
                # Print response body for debugging if failed
                try:
                    print(f"  Response: {response.text[:500]}") # Limit to 500 chars
                except Exception:
                    print(f"  Response: Could not decode response body.")
            
            print(f"  Time: {duration:.2f}s")
            results.append({"name": name, "status": status, "time": f"{duration:.2f}s"})
            
        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            results.append({"name": name, "status": "❌ ERROR", "time": "N/A"})

    print("\n" + "="*65)
    print("📊 FINAL SUMMARY")
    print("="*65)
    success_count = sum(1 for r in results if "SUCCESS" in r["status"])
    for res in results:
        print(f"{res['name']:<45} | {res['status']:<15} | {res['time']}")
    print("="*65)
    print(f"Total: {len(results)} | Success: {success_count} | Failed: {len(results) - success_count}")
    print("="*65)

if __name__ == "__main__":
    test_all()
