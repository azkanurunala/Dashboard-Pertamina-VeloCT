import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scrapers.tempo_scraper import TempoNewsScraper

async def verify_scraper():
    print(f"\n--- Verifying Tempo ---", flush=True)
    async with TempoNewsScraper() as scraper:
        try:
            print(f"Fetching sitemap from: {scraper.sitemap_url}", flush=True)
            # Add a timeout to the fetch
            entries = await asyncio.wait_for(scraper._fetch_sitemap_robust(scraper.sitemap_url), timeout=30.0)
            print(f"SUCCESS: Found {len(entries)} entries", flush=True)
            if entries:
                print(f"Sample Entry: {entries[0]['loc']}", flush=True)
                if 'title' in entries[0]:
                    print(f"Sample Title: {entries[0]['title']}", flush=True)
                if 'date' in entries[0]:
                    print(f"Sample Date: {entries[0]['date']}", flush=True)
            return True
        except asyncio.TimeoutError:
            print("FAILED: Timeout fetching sitemap", flush=True)
            return False
        except Exception as e:
            print(f"FAILED: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    asyncio.run(verify_scraper())
