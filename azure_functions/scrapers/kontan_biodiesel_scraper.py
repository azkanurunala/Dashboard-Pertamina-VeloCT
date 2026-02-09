"""
Kontan Biodiesel Specialized Scraper for Azure Functions.
Scrapes biodiesel and biofuel related news from Kontan website.
"""

import asyncio
import re
import sys
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

from bs4 import BeautifulSoup

# Add parent directory to Python path
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from scrapers.base_scraper import BaseNewsScraper
from scrapers.exceptions import ScrapingError
from shared.models import NewsArticle, ScrapingConfig


# Biodiesel-related keywords for filtering
BIODIESEL_KEYWORDS = [
    "biodiesel", "biofuel", "biosolar", "b20", "b30", "b35", "b40", "b50",
    "fame", "minyak sawit", "kelapa sawit", "cpo", "crude palm oil",
    "minyak nabati", "sawit", "hip biodiesel", "hip bbn",
    "bahan bakar nabati", "bioetanol", "ethanol", "etanol"
]


class KontanBiodieselScraper(BaseNewsScraper):
    """
    Kontan Biodiesel Specialized Scraper.
    Filters Kontan articles to only include biodiesel/biofuel-related content.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize Kontan Biodiesel scraper."""
        if config is None:
            config = ScrapingConfig(
                source_name="Kontan Biodiesel",
                base_url="https://www.kontan.co.id",
                selectors={
                    "search_url": "https://www.kontan.co.id/search/?search=",
                    "article_list": "div.list-search-news",
                    "article_title": "h3 a",
                    "article_date": "span.fs14",
                    "article_content": "div.detail-content"
                },
                rate_limit_delay=1.5,
                max_retries=3,
                timeout=25
            )
        
        super().__init__(config)

    def _is_biodiesel_related(self, title: str, content: str = "") -> bool:
        """Check if article is biodiesel-related based on title and content."""
        text_to_check = (title + " " + content).lower()
        return any(keyword in text_to_check for keyword in BIODIESEL_KEYWORDS)

    def _parse_kontan_date(self, date_str: str) -> Optional[str]:
        """Parse Kontan date format."""
        if not date_str:
            return None
        
        bulan = {
            'januari': '01', 'februari': '02', 'maret': '03', 'april': '04',
            'mei': '05', 'juni': '06', 'juli': '07', 'agustus': '08',
            'september': '09', 'oktober': '10', 'november': '11', 'desember': '12'
        }
        
        match = re.search(r'(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})', date_str)
        if match:
            day = match.group(1).zfill(2)
            month = bulan.get(match.group(2).lower(), '01')
            year = match.group(3)
            return f"{year}-{month}-{day}"
        return None

    async def _search_articles(self, query: str, page: int = 1) -> List[Dict]:
        """Search Kontan for articles."""
        try:
            url = f"{self.config.selectors['search_url']}{query}&page={page}"
            content = await self._fetch_content(url)
            soup = BeautifulSoup(content, 'html.parser')
            
            articles = []
            items = soup.select(self.config.selectors.get("article_list", "div.list-search-news"))
            
            for item in items:
                try:
                    title_elem = item.select_one(self.config.selectors.get("article_title", "h3 a"))
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    article_url = title_elem.get('href', '')
                    if article_url and not article_url.startswith('http'):
                        article_url = f"{self.config.base_url}{article_url}"
                    
                    date_elem = item.select_one(self.config.selectors.get("article_date", "span.fs14"))
                    date_str = date_elem.get_text(strip=True) if date_elem else None
                    formatted_date = self._parse_kontan_date(date_str)
                    
                    articles.append({
                        'title': title,
                        'url': article_url,
                        'date': formatted_date
                    })
                    
                except Exception as e:
                    self.logger.warning(f"Failed to parse article: {e}")
                    continue
            
            return articles
            
        except Exception as e:
            self.logger.error(f"Failed to search articles: {e}")
            return []

    async def _extract_article_content(self, url: str) -> str:
        """Extract article content from Kontan page."""
        try:
            content = await self._fetch_content(url)
            soup = BeautifulSoup(content, 'html.parser')
            
            content_div = soup.select_one(self.config.selectors.get("article_content", "div.detail-content"))
            if not content_div:
                return "N/A"
            
            for unwanted in content_div.select('script, style, iframe, aside, div.related, div.box-related'):
                unwanted.decompose()
            
            paragraphs = content_div.find_all('p')
            content_text = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True) and len(p.get_text(strip=True)) > 20]
            
            return "\n\n".join(content_text) if content_text else "N/A"
            
        except Exception as e:
            self.logger.error(f"Failed to extract content: {e}")
            return "N/A"

    async def _scrape_articles_from_source(
        self, 
        keywords: List[str], 
        start_date: datetime, 
        end_date: datetime, 
        **kwargs
    ) -> List[NewsArticle]:
        """Scrape biodiesel-related articles from Kontan."""
        try:
            query = keywords[0] if keywords else "biodiesel"
            target_date = end_date.strftime("%Y-%m-%d")
            max_pages = kwargs.get('max_pages', 3)
            
            self.logger.info(f"Scraping Kontan Biodiesel for: {query}, date: {target_date}")
            
            all_articles = []
            
            for page in range(1, max_pages + 1):
                page_articles = await self._search_articles(query, page)
                
                if not page_articles:
                    break
                
                for article in page_articles:
                    if article['date'] == target_date:
                        if self._is_biodiesel_related(article['title']):
                            all_articles.append(article)
                    elif article['date'] and article['date'] < target_date:
                        break
                
                await asyncio.sleep(1.0)
            
            if not all_articles:
                return []
            
            articles = []
            for article_data in all_articles:
                try:
                    content = await self._extract_article_content(article_data['url'])
                    
                    if not self._is_biodiesel_related(article_data['title'], content):
                        continue
                    
                    article = self._create_article(
                        title=article_data['title'],
                        content=content,
                        url=article_data['url'],
                        published_date=datetime.strptime(article_data['date'], '%Y-%m-%d')
                    )
                    articles.append(article)
                    await asyncio.sleep(1.0)
                    
                except Exception as e:
                    self.logger.error(f"Failed to process article: {e}")
                    continue
            
            self.logger.info(f"Successfully scraped {len(articles)} biodiesel articles from Kontan")
            return articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape Kontan Biodiesel: {str(e)}", source=self.source_name)


# Azure Function wrapper
async def scrape_kontan_biodiesel_news(
    keywords: List[str], 
    start_date: datetime, 
    end_date: datetime, 
    **kwargs
) -> List[NewsArticle]:
    """Azure Function entry point for Kontan Biodiesel news scraping."""
    async with KontanBiodieselScraper() as scraper:
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)
