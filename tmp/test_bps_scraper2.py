import asyncio, sys, os
sys.path.insert(0, 'c:/RunningProjects/Dashboard-Pertamina-VeloCT/azure_functions')
os.environ['BPS_API_KEY'] = '8199b1a60c76d284ee3d2228a51b3743'
from datetime import datetime
from scrapers.bps_scraper import BPSScraper

async def test():
    async with BPSScraper(api_key='8199b1a60c76d284ee3d2228a51b3743') as s:
        result = await s.scrape_news(['energi', 'minyak', 'inflasi'], datetime(2026,3,1), datetime(2026,4,2), max_pages=2)
        print(f'Berhasil: {len(result)} artikel')
        for a in result[:5]:
            print(f'  - {a.published_date.date()} | {a.title[:70]}')

asyncio.run(test())
