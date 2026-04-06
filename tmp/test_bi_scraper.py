import asyncio
import sys
import os
from datetime import datetime

# Add azure_functions to path so we can import 'scrapers'
sys.path.insert(0, os.path.abspath('azure_functions'))

from scrapers.bank_indonesia_scraper import BankIndonesiaScraper

async def test():
    try:
        async with BankIndonesiaScraper() as s:
            # Test range: 2026-03-25 to 2026-04-02
            # (Note: Current time in metadata is 2026-04-03)
            result = await s.scrape_news([], datetime(2026, 3, 25), datetime(2026, 4, 2))
            print(f'Berhasil: {len(result)} artikel')
            for a in result:
                # Assuming 'a' is a NewsArticle object with published_date and title attributes
                published_date = getattr(a, 'published_date', None)
                date_str = published_date.date() if published_date else "N/A"
                print(f'  - {date_str} | {a.title[:70]}')
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
