import asyncio
import aiohttp
import json
import time
from datetime import datetime

# Local function host URL
BASE_URL = "http://localhost:7071/api"

# All scraper functions
SCRAPERS = [
    "bank_indonesia_scraper_function",
    "biodiesel_esdm_scraper_function",
    "bioenergytimes_scraper_function",
    "bioetanol_esdm_scraper_function",
    "bisnis_indonesia_scraper_function",
    "bloomberg_technoz_scraper_function",
    "bps_scraper_function",
    "cnbc_indonesia_scraper_function",
    "cnbc_scraper_function",
    "cnn_scraper_function",
    "cpo_scraper_function",
    "energiesmedia_scraper_function",
    "google_news_scraper_function",
    "iaea_pris_scraper_function",
    "kompas_scraper_function",
    "kontan_bbm_scraper_function",
    "kontan_biodiesel_scraper_function",
    "kontan_scraper_function",
    "migas_eia_scraper_function",
    "migas_esdm_scraper_function",
    "oilprice_scraper_function",
    "reuters_scraper_function",
    "sandp_data_scraper_function",
    "sandp_news_scraper_function",
    "scmp_scraper_function",
    "sipsn_scraper_function",
    "tempo_scraper_function",
    "theguardian_scraper_function"
]

async def run_scraper(session, scraper_name, payload):
    url = f"{BASE_URL}/{scraper_name}"
    start_time = time.time()
    
    try:
        async with session.post(url, json=payload, timeout=300) as response:
            status = response.status
            try:
                result = await response.json()
            except:
                result = await response.text()
            
            duration = time.time() - start_time
            
            if status == 200:
                articles_found = result.get('results', {}).get('articles_found', 0)
                articles_saved = result.get('results', {}).get('articles_saved', 0)
                error = result.get('results', {}).get('persistence_error')
                
                print(f"✅ {scraper_name:<40} | Status: {status} | Found: {articles_found:>3} | Saved: {articles_saved:>3} | Time: {duration:5.2f}s")
                if error:
                    print(f"   ⚠️ persistence_error: {error}")
                return True
            else:
                print(f"❌ {scraper_name:<40} | Status: {status} | Time: {duration:5.2f}s | Error: {str(result)[:100]}")
                return False
                
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ {scraper_name:<40} | Exception: {str(e)[:100]} | Time: {duration:5.2f}s")
        return False

async def main():
    print("=" * 100)
    print(f"Starting Parallel Execution of {len(SCRAPERS)} Scrapers")
    print(f"Range: 2025-01-01 to 2026-02-09")
    print("=" * 100)
    print()
    
    payload = {
        "keywords": ["pertamina", "energi", "oil", "gas"],
        "start_date": "2025-01-01",
        "end_date": "2026-02-09",
        "save_to_db": True
    }
    
    start_total = time.time()
    
    # Use a connector to limit the number of simultaneous connections if needed
    # (Azure Functions Core Tools might struggle with 28 at once)
    conn = aiohttp.TCPConnector(limit=10) # Process 10 at a time
    
    async with aiohttp.ClientSession(connector=conn) as session:
        tasks = [run_scraper(session, scraper, payload) for scraper in SCRAPERS]
        results = await asyncio.gather(*tasks)
        
    total_duration = time.time() - start_total
    success_count = sum(1 for r in results if r)
    
    print()
    print("=" * 100)
    print(f"Parallel Execution Complete!")
    print(f"Total Success: {success_count}/{len(SCRAPERS)}")
    print(f"Total duration: {total_duration:5.2f}s")
    print("=" * 100)
    print("\nRun `python azure_functions/verify_database_data.py` to check the results.")

if __name__ == "__main__":
    asyncio.run(main())
