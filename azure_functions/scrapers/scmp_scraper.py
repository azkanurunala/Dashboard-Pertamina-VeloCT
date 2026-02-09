"""
SCMP (South China Morning Post) News Scraper for Azure Functions.
Scrapes news from SCMP using Selenium for dynamic content.
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


class SCMPScraper(BaseNewsScraper):
    """
    SCMP News Scraper implementation.
    Uses Selenium for dynamic content loading with scroll support.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize SCMP scraper."""
        if config is None:
            config = ScrapingConfig(
                source_name="SCMP",
                base_url="https://www.scmp.com",
                selectors={
                    "search_url": "https://www.scmp.com/search/{query}",
                    "article_list": "article.article-card",
                    "article_title": "h2.article-card__title a",
                    "article_date": "time",
                    "article_content": "div.article__body"
                },
                rate_limit_delay=2.0,
                max_retries=3,
                timeout=30
            )
        
        super().__init__(config)
        self.requires_selenium = True

    def _parse_scmp_date(self, date_str: str) -> Optional[str]:
        """Parse SCMP date formats."""
        if not date_str:
            return None
        
        # Handle relative dates
        if "hour" in date_str.lower() or "minute" in date_str.lower():
            return datetime.now().strftime("%Y-%m-%d")
        if "yesterday" in date_str.lower():
            return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        formats = [
            "%d %B %Y",     # 15 January 2024
            "%d %b %Y",     # 15 Jan 2024
            "%Y-%m-%d",     # 2024-01-15
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    async def _search_articles(self, query: str) -> List[Dict]:
        """Search SCMP for articles using Selenium."""
        try:
            url = self.config.selectors['search_url'].format(query=query)
            content = await self._fetch_content_selenium(url)
            soup = BeautifulSoup(content, 'html.parser')
            
            articles = []
            items = soup.select(self.config.selectors.get("article_list", "article"))
            
            self.logger.info(f"Found {len(items)} article items")
            
            for item in items:
                try:
                    title_elem = item.select_one(self.config.selectors.get("article_title", "h2 a"))
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    article_url = title_elem.get('href', '')
                    if article_url and not article_url.startswith('http'):
                        article_url = f"{self.config.base_url}{article_url}"
                    
                    date_elem = item.select_one(self.config.selectors.get("article_date", "time"))
                    date_str = date_elem.get('datetime', '') if date_elem else None
                    if not date_str and date_elem:
                        date_str = date_elem.get_text(strip=True)
                    
                    formatted_date = self._parse_scmp_date(date_str)
                    
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
        """Extract article content from SCMP page."""
        try:
            content = await self._fetch_content_selenium(url)
            soup = BeautifulSoup(content, 'html.parser')
            
            content_div = soup.select_one(self.config.selectors.get("article_content", "div.article__body"))
            if not content_div:
                # Try alternative selectors
                for selector in ['div.body__content', 'article', 'div.content']:
                    content_div = soup.select_one(selector)
                    if content_div:
                        break
            
            if not content_div:
                return "N/A"
            
            for unwanted in content_div.select('script, style, iframe, aside, div.related'):
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
        """Scrape articles from SCMP."""
        try:
            query = keywords[0] if keywords else "energy"
            target_date = end_date.strftime("%Y-%m-%d")
            
            self.logger.info(f"Scraping SCMP for: {query}, date: {target_date}")
            
            all_articles = await self._search_articles(query)
            
            # Filter by date
            filtered_articles = []
            for article in all_articles:
                if article['date']:
                    try:
                        article_date = datetime.strptime(article['date'], "%Y-%m-%d")
                        if start_date <= article_date <= end_date:
                            filtered_articles.append(article)
                    except ValueError:
                        continue
            
            if not filtered_articles:
                return []
            
            articles = []
            for article_data in filtered_articles[:10]:  # Limit for performance
                try:
                    content = await self._extract_article_content(article_data['url'])
                    
                    article = self._create_article(
                        title=article_data['title'],
                        content=content,
                        url=article_data['url'],
                        published_date=datetime.strptime(article_data['date'], '%Y-%m-%d')
                    )
                    articles.append(article)
                    await asyncio.sleep(2.0)
                    
                except Exception as e:
                    self.logger.error(f"Failed to process article: {e}")
                    continue
            
            self.logger.info(f"Successfully scraped {len(articles)} articles from SCMP")
            return articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape SCMP: {str(e)}", source=self.source_name)


async def scrape_scmp_news(
    keywords: List[str], 
    start_date: datetime, 
    end_date: datetime, 
    **kwargs
) -> List[NewsArticle]:
    """Azure Function entry point for SCMP news scraping."""
    async with SCMPScraper() as scraper:
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)
