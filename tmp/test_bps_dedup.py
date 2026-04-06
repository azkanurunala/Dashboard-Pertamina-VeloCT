"""
Debug kenapa duplikat URL terjadi di BPS scraper.
Cek apakah artikel yang sama muncul di dua halaman berbeda.
"""
import asyncio, sys
sys.path.insert(0, 'c:/RunningProjects/Dashboard-Pertamina-VeloCT/azure_functions')
from datetime import datetime
from scrapers.bps_scraper import BPSScraper

async def test():
    async with BPSScraper(api_key='8199b1a60c76d284ee3d2228a51b3743') as s:
        # Cek apakah news_id 890 (Surplus Neraca) muncul di page 0 dan page 1
        for page in range(2):
            resp = await s._get_news_list(page=page, keyword=None)
            items, meta = s._parse_api_response(resp)
            print(f"\nPage {page}: {len(items)} items")
            for item in items:
                nid = item.get('news_id')
                title = item.get('title','')[:50]
                date = item.get('rl_date','')
                print(f"  [{nid}] {date} | {title}")

asyncio.run(test())
