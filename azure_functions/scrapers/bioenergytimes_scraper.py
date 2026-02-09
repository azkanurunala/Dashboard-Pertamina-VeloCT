"""
BioenergyTimes News Scraper for Azure Functions.
Scrapes bioenergy news articles from BioenergyTimes.com.
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


class BioenergyTimesScraper(BaseNewsScraper):
    """
    BioenergyTimes News Scraper implementation.
    Scrapes bioenergy-related news from BioenergyTimes.com.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize BioenergyTimes scraper."""
        if config is None:
            config = ScrapingConfig(
                source_name="BioenergyTimes",
                base_url="https://www.bioenergytimes.com",
                selectors={
                    "search_url": "https://www.bioenergytimes.com/?s=",
                    "article_list": "article.post",
                    "article_title": "h2.entry-title a",
                    "article_date": "time.entry-date",
                    "article_content": "div.entry-content"
                },
                rate_limit_delay=1.5,
                max_retries=3,
                timeout=25
            )
        
        super().__init__(config)

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to YYYY-MM-DD format."""
        if not date_str:
            return None
        
        formats = [
            "%B %d, %Y",    # January 15, 2024
            "%b %d, %Y",    # Jan 15, 2024
            "%Y-%m-%d",     # 2024-01-15
            "%d/%m/%Y"      # 15/01/2024
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    async def _search_articles(self, query: str, page: int = 1) -> List[Dict]:
        """Search BioenergyTimes for articles."""
        try:
            url = f"{self.config.selectors['search_url']}{query}"
            if page > 1:
                url += f"&page={page}"
            
            content = await self._fetch_content(url)
            soup = BeautifulSoup(content, 'html.parser')
            
            articles = []
            items = soup.select(self.config.selectors.get("article_list", "article.post"))
            
            for item in items:
                try:
                    title_elem = item.select_one(self.config.selectors.get("article_title", "h2.entry-title a"))
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    article_url = title_elem.get('href', '')
                    
                    date_elem = item.select_one(self.config.selectors.get("article_date", "time.entry-date"))
                    date_str = date_elem.get('datetime', '') if date_elem else None
                    if not date_str and date_elem:
                        date_str = date_elem.get_text(strip=True)
                    
                    formatted_date = self._parse_date(date_str) if date_str else None
                    
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
        """Extract article content from BioenergyTimes page."""
        try:
            content = await self._fetch_content(url)
            soup = BeautifulSoup(content, 'html.parser')
            
            content_div = soup.select_one(self.config.selectors.get("article_content", "div.entry-content"))
            if not content_div:
                return "N/A"
            
            for unwanted in content_div.select('script, style, iframe, aside, div.related, div.share'):
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
        """Scrape articles from BioenergyTimes."""
        try:
            query = keywords[0] if keywords else "bioenergy"
            target_date = end_date.strftime("%Y-%m-%d")
            max_pages = kwargs.get('max_pages', 3)
            
            self.logger.info(f"Scraping BioenergyTimes for: {query}")
            
            all_articles = []
            
            for page in range(1, max_pages + 1):
                page_articles = await self._search_articles(query, page)
                
                if not page_articles:
                    break
                
                for article in page_articles:
                    if article['date']:
                        try:
                            article_date = datetime.strptime(article['date'], "%Y-%m-%d")
                            if start_date <= article_date <= end_date:
                                all_articles.append(article)
                            elif article_date < start_date:
                                break
                        except ValueError:
                            continue
                
                await asyncio.sleep(1.0)
            
            if not all_articles:
                return []
            
            articles = []
            for article_data in all_articles:
                try:
                    content = await self._extract_article_content(article_data['url'])
                    
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
            
            self.logger.info(f"Successfully scraped {len(articles)} articles from BioenergyTimes")
            return articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape BioenergyTimes: {str(e)}", source=self.source_name)


async def scrape_bioenergytimes_news(
    keywords: List[str], 
    start_date: datetime, 
    end_date: datetime, 
    **kwargs
) -> List[NewsArticle]:
    """Azure Function entry point for BioenergyTimes news scraping."""
    async with BioenergyTimesScraper() as scraper:
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)
