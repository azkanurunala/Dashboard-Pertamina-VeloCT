
import asyncio
import os
import sys

# Add azure_functions to path
sys.path.append(os.path.join(os.getcwd(), 'azure_functions'))

from scrapers.tempo_scraper import TempoNewsScraper
from shared.models import ScrapingConfig
import logging

# Setup logging to console
logging.basicConfig(level=logging.INFO)

async def test_diagnostic_save():
    scraper = TempoNewsScraper()
    url = "https://www.tempo.co/sains-sitemap.xml"
    print(f"Testing diagnostic save for {url}...")
    
    # We call the internal method directly to ensure we hit the parse logic
    articles = await scraper._scrape_from_sitemap(url)
    
    print(f"Done. Check for failed_sains-sitemap.xml in the root directory.")

if __name__ == "__main__":
    asyncio.run(test_diagnostic_save())
