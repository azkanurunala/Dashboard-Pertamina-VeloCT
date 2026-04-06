import asyncio
import sys
import os
from datetime import datetime

# Add azure_functions to path
sys.path.insert(0, os.path.abspath('azure_functions'))

from scrapers.bps_scraper import BPSScraper

async def test():
    api_key = '8199b1a60c76d284ee3d2228a51b3743'
    print(f"Testing BPS API key: {api_key[:5]}...")
    try:
        async with BPSScraper(api_key=api_key) as s:
            print("Fetching news list...")
            data = await s._get_news_list(page=0, keyword='energi')
            print(f"Status: {data.get('status')}")
            if data.get('status') == 'OK':
                items, metadata = s._parse_api_response(data)
                print(f"Articles found: {len(items)}")
                for item in items[:2]:
                    print(f" - {item.get('title')}")
            else:
                print(f"API Error: {data}")
    except Exception as e:
        print(f"Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test())
