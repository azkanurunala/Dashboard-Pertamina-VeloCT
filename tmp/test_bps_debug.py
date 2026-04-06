import asyncio, sys
sys.path.insert(0, 'c:/RunningProjects/Dashboard-Pertamina-VeloCT/azure_functions')
from datetime import datetime
from scrapers.bps_scraper import BPSScraper

async def test():
    async with BPSScraper(api_key='8199b1a60c76d284ee3d2228a51b3743') as s:
        result = await s.scrape_news(
            ['energi', 'minyak', 'inflasi'],
            datetime(2026,3,1), datetime(2026,4,5), max_pages=2
        )
        print(f'Total: {len(result)} artikel')
        urls = [a.url for a in result]
        print(f'Duplikat URL: {len(urls) - len(set(urls))}')
        for a in result:
            print(f'  - {a.published_date.date()} | {a.url[-60:]} | {a.title[:50]}')

asyncio.run(test())
