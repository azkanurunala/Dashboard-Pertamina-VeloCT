import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scrapers.tempo_scraper import TempoNewsScraper
from scrapers.kontan_scraper import KontanNewsScraper
from scrapers.kompas_scraper import KompasNewsScraper
from scrapers.reuters_scraper import ReutersNewsScraper
from scrapers.cnn_scraper import CNNNewsScraper
from scrapers.cnbc_scraper import CNBCNewsScraper
from scrapers.oilprice_scraper import OilPriceNewsScraper

async def verify_scraper(scraper_class, name):
    print(f"\n--- Verifying {name} ---")
    async with scraper_class() as scraper:
        try:
            # We just want to see if it can fetch and parse the sitemap entries
            # The robust method is now called internally or we can call it directly for test
            print(f"Fetching sitemap from: {scraper.sitemap_url}")
            entries = await scraper._fetch_sitemap_robust(scraper.sitemap_url)
            print(f"SUCCESS: Found {len(entries)} entries")
            if entries:
                print(f"Sample Entry: {entries[0]['loc']}")
                if 'title' in entries[0]:
                    print(f"Sample Title: {entries[0]['title']}")
                if 'date' in entries[0]:
                    print(f"Sample Date: {entries[0]['date']}")
            return True
        except Exception as e:
            print(f"FAILED: {e}")
            return False

async def main():
    scrapers = [
        (TempoNewsScraper, "Tempo"),
        (KontanNewsScraper, "Kontan"),
        (KompasNewsScraper, "Kompas"),
        (ReutersNewsScraper, "Reuters"),
        (CNNNewsScraper, "CNN"),
        (CNBCNewsScraper, "CNBC"),
        (OilPriceNewsScraper, "OilPrice")
    ]
    
    results = {}
    for scraper_class, name in scrapers:
        results[name] = await verify_scraper(scraper_class, name)
        # Add a small delay between scrapers to be polite
        await asyncio.sleep(2)
    
    print("\n\n=== Final Results ===")
    all_passed = True
    for name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\nAll sitemap-driven scrapers verified successfully!")
    else:
        print("\nSome scrapers failed verification. Please check logs.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
