
import asyncio
import os
import sys

# Add azure_functions to path
sys.path.append(os.path.join(os.getcwd(), 'azure_functions'))

from scrapers.tempo_scraper import TempoNewsScraper
from shared.models import ScrapingConfig
from datetime import datetime, timedelta

async def trigger_failure():
    # Configure scraper to only target the failing sitemap
    config = ScrapingConfig(
        source_name="Tempo_Debug",
        base_url="https://www.tempo.co",
        selectors={
            "sitemaps": ["https://www.tempo.co/sains-sitemap.xml"],
            "article_content": "div#isi",
            "title": "h1",
            "content": "p",
            "unwanted": "script"
        },
        rate_limit_delay=0,
        max_retries=1,
        timeout=20
    )
    
    scraper = TempoNewsScraper(config)
    
    print("Starting targeted scrape for sains-sitemap.xml...")
    # Scrape for today
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now()
    
    try:
        articles = await scraper.scrape_news(
            keywords=[], 
            start_date=start_date, 
            end_date=end_date
        )
        print(f"Scrape completed. Found {len(articles)} articles.")
    except Exception as e:
        print(f"Scrape failed (Expected if it hits the parse error): {e}")

if __name__ == "__main__":
    asyncio.run(trigger_failure())
