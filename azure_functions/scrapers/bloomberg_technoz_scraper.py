"""
Bloomberg Technoz News Scraper for Azure Functions.
Implements scraping functionality for Bloomberg Technoz news articles.
"""

import asyncio
import re
import sys
import os
import locale
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from bs4 import BeautifulSoup

# Add parent directory to Python path for absolute imports in Azure Functions
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from scrapers.base_scraper import BaseNewsScraper
from scrapers.exceptions import ScrapingError, NetworkError
from shared.models import NewsArticle, ScrapingConfig


class BloombergTechnozScraper(BaseNewsScraper):
    """
    Bloomberg Technoz News Scraper implementation.
    Scrapes news articles from Bloomberg Technoz website with search and pagination.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize Bloomberg Technoz scraper with default configuration."""
        if config is None:
            config = ScrapingConfig(
                source_name="Bloomberg Technoz",
                base_url="https://www.bloombergtechnoz.com",
                selectors={
                    "search_url": "https://www.bloombergtechnoz.com/cari?q=",
                    "article_list": "div.cardnews",
                    "article_title": "h3.cardnews__title a",
                    "article_date": "span.cardnews__date",
                    "article_content": "div.detailText",
                    "pagination": "a.pagination__link"
                },
                rate_limit_delay=1.5,
                max_retries=3,
                timeout=25
            )
        
        super().__init__(config)
        self.search_base_url = self.config.selectors.get("search_url")

    def _clean_date(self, raw_date: str) -> Optional[str]:
        """
        Clean and format date string to YYYY-MM-DD.
        
        Args:
            raw_date: Raw date string from the page
            
        Returns:
            Date in YYYY-MM-DD format or None
        """
        if not raw_date:
            return None
        
        raw_date = raw_date.strip()
        
        # Handle "Kemarin" (Yesterday)
        if "kemarin" in raw_date.lower():
            yesterday = datetime.now() - timedelta(days=1)
            return yesterday.strftime("%Y-%m-%d")
        
        # Handle "Hari Ini" (Today)
        if "hari ini" in raw_date.lower():
            return datetime.now().strftime("%Y-%m-%d")
        
        # Parse various date formats
        date_formats = [
            "%d %B %Y",     # 15 Januari 2024
            "%d %b %Y",     # 15 Jan 2024
            "%Y-%m-%d",     # 2024-01-15
            "%d/%m/%Y",     # 15/01/2024
        ]
        
        # Indonesian month mapping
        bulan_mapping = {
            'januari': 'January', 'februari': 'February', 'maret': 'March',
            'april': 'April', 'mei': 'May', 'juni': 'June',
            'juli': 'July', 'agustus': 'August', 'september': 'September',
            'oktober': 'October', 'november': 'November', 'desember': 'December'
        }
        
        # Replace Indonesian months with English
        date_lower = raw_date.lower()
        for indo, eng in bulan_mapping.items():
            date_lower = date_lower.replace(indo, eng)
        
        for fmt in date_formats:
            try:
                parsed = datetime.strptime(date_lower, fmt)
                return parsed.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        return None

    async def _get_total_pages(self, soup) -> int:
        """Get total number of pages from pagination."""
        try:
            pagination_links = soup.select(self.config.selectors.get("pagination", "a.pagination__link"))
            if not pagination_links:
                return 1
            
            max_page = 1
            for link in pagination_links:
                text = link.get_text(strip=True)
                try:
                    page_num = int(text)
                    if page_num > max_page:
                        max_page = page_num
                except ValueError:
                    continue
            
            return max_page
        except Exception:
            return 1

    async def _parse_search_page(self, query: str, page: int = 1) -> tuple:
        """
        Parse search results page.
        
        Args:
            query: Search query
            page: Page number
            
        Returns:
            Tuple of (articles list, total pages)
        """
        try:
            url = f"{self.search_base_url}{query}&page={page}"
            content = await self._fetch_content(url)
            soup = BeautifulSoup(content, 'html.parser')
            
            total_pages = await self._get_total_pages(soup) if page == 1 else None
            
            articles = []
            article_items = soup.select(self.config.selectors.get("article_list", "div.cardnews"))
            
            for item in article_items:
                try:
                    # Extract title and URL
                    title_elem = item.select_one(self.config.selectors.get("article_title", "h3.cardnews__title a"))
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get('href', '')
                    if url and not url.startswith('http'):
                        url = f"{self.config.base_url}{url}"
                    
                    # Extract date
                    date_elem = item.select_one(self.config.selectors.get("article_date", "span.cardnews__date"))
                    date_str = date_elem.get_text(strip=True) if date_elem else None
                    formatted_date = self._clean_date(date_str)
                    
                    articles.append({
                        'title': title,
                        'url': url,
                        'date': formatted_date
                    })
                    
                except Exception as e:
                    self.logger.warning(f"Failed to parse article item: {e}")
                    continue
            
            return articles, total_pages
            
        except Exception as e:
            self.logger.error(f"Failed to parse search page: {e}")
            return [], None

    async def _extract_article_content(self, url: str) -> str:
        """
        Extract article content from Bloomberg Technoz article page.
        
        Args:
            url: Article URL
            
        Returns:
            Extracted article content
        """
        try:
            content = await self._fetch_content(url)
            soup = BeautifulSoup(content, 'html.parser')
            
            content_div = soup.select_one(self.config.selectors.get("article_content", "div.detailText"))
            if not content_div:
                self.logger.warning(f"Content div not found for {url}")
                return "N/A"
            
            # Remove unwanted elements
            for unwanted in content_div.select('script, style, iframe, aside, div.related'):
                unwanted.decompose()
            
            paragraphs = content_div.find_all(['p', 'li', 'h2', 'h3'])
            content_text = []
            
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 30:
                    content_text.append(text)
            
            if content_text:
                return "\n\n".join(content_text)
            
            return "N/A"
            
        except Exception as e:
            self.logger.error(f"Failed to extract content from {url}: {e}")
            return "N/A"

    async def _scrape_articles_from_source(
        self, 
        keywords: List[str], 
        start_date: datetime, 
        end_date: datetime, 
        **kwargs
    ) -> List[NewsArticle]:
        """
        Scrape articles from Bloomberg Technoz.
        
        Args:
            keywords: Keywords to search for
            start_date: Start date for article search
            end_date: End date for article search
            **kwargs: Additional parameters
            
        Returns:
            List of scraped NewsArticle objects
        """
        try:
            query = keywords[0] if keywords else ""
            target_date = end_date.strftime("%Y-%m-%d")
            max_pages = kwargs.get('max_pages', 5)
            
            self.logger.info(f"Scraping Bloomberg Technoz for: {query}, date: {target_date}")
            
            all_articles = []
            total_pages = None
            should_stop = False
            
            for page in range(1, max_pages + 1):
                if should_stop:
                    break
                
                self.logger.info(f"Processing page {page}...")
                
                page_articles, pages = await self._parse_search_page(query, page)
                
                if pages and total_pages is None:
                    total_pages = min(pages, max_pages)
                
                if not page_articles:
                    self.logger.info(f"No more articles on page {page}")
                    break
                
                # Filter by date
                for article in page_articles:
                    if not article['date']:
                        continue
                    
                    try:
                        article_date = datetime.strptime(article['date'], "%Y-%m-%d")
                        
                        if article_date < start_date:
                            self.logger.info(f"Found older article ({article['date']}), stopping")
                            should_stop = True
                            break
                        
                        if start_date <= article_date <= end_date:
                            all_articles.append(article)
                            
                    except ValueError:
                        continue
                
                await asyncio.sleep(1.0)  # Rate limiting
            
            if not all_articles:
                self.logger.info("No articles found for date range")
                return []
            
            self.logger.info(f"Found {len(all_articles)} articles, extracting content...")
            
            # Extract content for each article
            articles = []
            for i, article_data in enumerate(all_articles):
                try:
                    self.logger.info(f"Processing {i+1}/{len(all_articles)}: {article_data['title'][:60]}...")
                    
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
            
            self.logger.info(f"Successfully scraped {len(articles)} articles from Bloomberg Technoz")
            return articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape Bloomberg Technoz: {str(e)}", source=self.source_name)


# Azure Function wrapper
async def scrape_bloomberg_technoz_news(
    keywords: List[str], 
    start_date: datetime, 
    end_date: datetime, 
    **kwargs
) -> List[NewsArticle]:
    """
    Azure Function entry point for Bloomberg Technoz news scraping.
    
    Args:
        keywords: Keywords to search for
        start_date: Start date for article search
        end_date: End date for article search
        **kwargs: Additional parameters
        
    Returns:
        List of scraped NewsArticle objects
    """
    async with BloombergTechnozScraper() as scraper:
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)
