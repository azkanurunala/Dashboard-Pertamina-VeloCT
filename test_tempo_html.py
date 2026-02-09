
import asyncio
import os
import sys
from datetime import datetime

# Add azure_functions to path
sys.path.append(os.path.join(os.getcwd(), 'azure_functions'))

from scrapers.tempo_scraper import TempoNewsScraper

async def test_html_parsing():
    scraper = TempoNewsScraper()
    # Use one of the failed sitemaps as a local source for testing
    sitemap_path = os.path.join(os.getcwd(), 'failed_politik-sitemap.xml')
    
    if not os.path.exists(sitemap_path):
        print(f"ERROR: {sitemap_path} does not exist.")
        return

    print(f"Reading local sitemap: {sitemap_path}")
    with open(sitemap_path, 'rb') as f:
        content = f.read()

    print("Parsing manually using the new logic...")
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(content, 'html.parser')
    table = soup.find('table', id='sitemap')
    if table:
        rows = table.find_all('tr')[1:] # Skip header
        print(f"Found {len(rows)} rows in table.")
        
        limit = 5
        count = 0
        for row in rows:
            if count >= limit: break
            info = scraper._extract_article_info_from_sitemap_robust(row)
            print(f"Article {count+1}:")
            print(f"  Title: {info.get('title') if info else 'None'}")
            print(f"  URL:   {info.get('url') if info else 'None'}")
            print(f"  Date:  {info.get('date') if info else 'None'}")
            count += 1
    else:
        print("ERROR: table#sitemap not found.")

if __name__ == "__main__":
    asyncio.run(test_html_parsing())
