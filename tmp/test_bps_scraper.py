import asyncio
import sys
import os
from datetime import datetime

# Add azure_functions to path so we can import 'scrapers'
sys.path.insert(0, os.path.abspath('azure_functions'))

from scrapers.bps_scraper import BPSScraper

async def test():
    # BPS API Key from local.settings.json
    api_key = "8199b1a60c76d284ee3d2228a51b3743"
    
    try:
        # Note: BPSScraper constructor expects api_key
        async with BPSScraper(api_key=api_key) as s:
            print(f"Starting BPS scrape test...")
            result = await s.scrape_news(['energi', 'minyak', 'inflasi'], datetime(2026, 3, 25), datetime(2026, 4, 2))
            print(f'Berhasil: {len(result)} artikel')
            for a in result[:10]:
                published_date = getattr(a, 'published_date', None)
                date_str = published_date.date() if published_date else "N/A"
                print(f'  - {date_str} | {a.title[:70]}')
    except Exception as e:
        print(f"Error during BPS test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
