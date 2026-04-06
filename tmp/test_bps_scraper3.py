import asyncio, sys, logging
sys.path.insert(0, 'c:/RunningProjects/Dashboard-Pertamina-VeloCT/azure_functions')

logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

from datetime import datetime
from scrapers.bps_scraper import BPSScraper

async def test():
    async with BPSScraper(api_key='8199b1a60c76d284ee3d2228a51b3743') as s:
        # Test _get_news_list langsung
        print("=== Test _get_news_list ===")
        try:
            resp = await s._get_news_list(page=0, keyword='energi')
            print(f"Status: {resp.get('status')}")
            print(f"Data-availability: {resp.get('data-availability')}")
            items, meta = s._parse_api_response(resp)
            print(f"Items: {len(items)}, Meta: {meta}")
            if items:
                print(f"First item: {items[0].get('title','')[:60]} | date: {items[0].get('rl_date')}")
        except Exception as e:
            print(f"ERROR: {e}")

asyncio.run(test())
