"""
BPS (Badan Pusat Statistik / Statistics Indonesia) news scraper.
Uses the official BPS API to fetch news articles.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from html import unescape
from bs4 import BeautifulSoup

from .base_scraper import BaseNewsScraper
from ..shared.models import NewsArticle, ScrapingConfig
from .exceptions import ScrapingError, NetworkError


class BPSScraper(BaseNewsScraper):
    """
    Scraper for BPS (Statistics Indonesia) news using official API.
    """
    
    def __init__(self, api_key: str, config: Optional[ScrapingConfig] = None):
        """
        Initialize BPS scraper.
        
        Args:
            api_key: BPS API key for authentication
            config: Optional scraping configuration
        """
        if config is None:
            config = ScrapingConfig(
                source_name="BPS",
                base_url="https://www.bps.go.id",
                rate_limit_delay=1,
                max_retries=3,
                timeout=15,
                headers={}
            )
        
        super().__init__(config)
        self.api_key = api_key
        self.api_base_url = "https://webapi.bps.go.id/v1/api"
        self.domain = "0000"  # National domain
        self.language = "ind"  # Indonesian language
        
    async def _get_news_list(self, page: int = 0, keyword: Optional[str] = None) -> dict:
        """
        Get news list from BPS API.
        
        Args:
            page: Page number (0-indexed)
            keyword: Optional keyword filter
            
        Returns:
            API response as dictionary
        """
        url = f"{self.api_base_url}/list/model/news/domain/{self.domain}/page/{page}/key/{self.api_key}"
        
        params = {}
        if keyword:
            params['keyword'] = keyword
        
        try:
            response = await self._make_request(url, params=params)
            data = await response.json()
            return data
        except Exception as e:
            self.logger.error(f"Failed to fetch news list: {e}")
            raise NetworkError(f"API request failed: {str(e)}", source=self.source_name, url=url)
    
    async def _get_news_detail(self, news_id: str) -> Optional[str]:
        """
        Get detailed news content from BPS API.
        
        Args:
            news_id: News article ID
            
        Returns:
            Cleaned article content or None if failed
        """
        url = f"{self.api_base_url}/view/domain/{self.domain}/model/news/lang/{self.language}/id/{news_id}/key/{self.api_key}"
        
        try:
            response = await self._make_request(url)
            data = await response.json()
            
            if data.get('status') != 'OK':
                self.logger.warning(f"API returned non-OK status for news {news_id}")
                return None
            
            html_content = data.get('data', {}).get('news', '')
            if not html_content:
                return None
            
            # Unescape HTML entities
            html_content = unescape(html_content)
            
            # Parse HTML and extract text
            soup = BeautifulSoup(html_content, 'html.parser')
            paragraphs = soup.find_all('p')
            
            # Filter out contact information and unwanted content
            block_keywords = [
                'narahubung', 'contact', 'telp', 'fax', 'email',
                '@bps.go.id', 'jl.', 'jakarta'
            ]
            
            content_parts = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if not text:
                    continue
                
                # Skip paragraphs with contact information
                if any(keyword in text.lower() for keyword in block_keywords):
                    continue
                
                content_parts.append(text)
            
            return "\n\n".join(content_parts) if content_parts else None
            
        except Exception as e:
            self.logger.error(f"Failed to fetch news detail for {news_id}: {e}")
            return None
    
    def _parse_api_response(self, api_response: dict) -> tuple[List[dict], Optional[dict]]:
        """
        Parse BPS API response.
        
        Args:
            api_response: Raw API response
            
        Returns:
            Tuple of (news items list, metadata dict)
        """
        if not api_response:
            return [], None
        
        if api_response.get('status') != 'OK':
            return [], None
        
        if api_response.get('data-availability') != 'available':
            return [], None
        
        data = api_response.get('data', [])
        if len(data) < 2:
            return [], None
        
        metadata = data[0]
        news_items = data[1]
        
        return news_items, metadata
    
    def _build_article_url(self, news_id: str, title: str, date_str: str) -> str:
        """
        Build article URL from news ID and metadata.
        
        Args:
            news_id: News article ID
            title: Article title
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            Full article URL
        """
        # Create URL slug from title
        slug = title.lower()
        slug = ''.join(c if c.isalnum() or c.isspace() or c == '-' else '' for c in slug)
        slug = '-'.join(slug.split())
        slug = slug[:100]  # Limit length
        
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            year = date_obj.strftime("%Y")
            month = date_obj.strftime("%m")
            day = date_obj.strftime("%d")
            return f"{self.base_url}/id/news/{year}/{month}/{day}/{news_id}/{slug}.html"
        except:
            return f"{self.base_url}/id/news/{news_id}"
    
    async def _scrape_articles_from_source(self, keywords: List[str], 
                                          start_date: datetime, 
                                          end_date: datetime,
                                          max_pages: Optional[int] = None,
                                          **kwargs) -> List[NewsArticle]:
        """
        Scrape articles from BPS using their API.
        
        Args:
            keywords: Keywords to search for (uses first keyword if multiple)
            start_date: Start date for article search
            end_date: End date for article search
            max_pages: Maximum number of pages to scrape
            **kwargs: Additional parameters
            
        Returns:
            List of scraped articles
        """
        articles = []
        page = 0
        total_pages = None
        should_stop = False
        
        # Use first keyword if multiple provided
        search_keyword = keywords[0] if keywords else None
        
        self.logger.info(f"Starting BPS scrape with keyword: {search_keyword}")
        
        while not should_stop:
            try:
                # Fetch news list for current page
                api_response = await self._get_news_list(page=page, keyword=search_keyword)
                news_items, metadata = self._parse_api_response(api_response)
                
                if not news_items:
                    self.logger.info(f"No more news items found at page {page}")
                    break
                
                # Get total pages from metadata
                if metadata and total_pages is None:
                    total_pages = metadata.get("pages", 1)
                    if max_pages:
                        total_pages = min(total_pages, max_pages)
                    self.logger.info(f"Total pages to scrape: {total_pages}")
                
                # Process each news item
                for item in news_items:
                    try:
                        title = item.get('title', '')
                        date_str = item.get('rl_date', '')
                        news_id = item.get('news_id', '')
                        category = item.get('newscat_name', '')
                        
                        if not title or not date_str or not news_id:
                            continue
                        
                        # Parse date
                        try:
                            published_date = datetime.strptime(date_str, "%Y-%m-%d")
                        except:
                            self.logger.warning(f"Failed to parse date: {date_str}")
                            continue
                        
                        # Check if date is before start_date (stop scraping)
                        if published_date < start_date:
                            self.logger.info(f"Found article older than start_date, stopping")
                            should_stop = True
                            break
                        
                        # Skip if date is after end_date
                        if published_date > end_date:
                            continue
                        
                        # Build article URL
                        url = self._build_article_url(news_id, title, date_str)
                        
                        # Fetch article content
                        content = await self._get_news_detail(news_id)
                        if not content:
                            self.logger.warning(f"No content for article {news_id}")
                            continue
                        
                        # Create article object
                        article = self._create_article(
                            title=title,
                            content=content,
                            url=url,
                            published_date=published_date,
                            keywords=keywords if keywords else [],
                            language='id',  # Indonesian
                            category=category
                        )
                        
                        articles.append(article)
                        self.logger.debug(f"Scraped article: {title[:60]}...")
                        
                    except Exception as e:
                        self.logger.error(f"Error processing news item: {e}")
                        continue
                
                if should_stop:
                    break
                
                # Check if we've reached max pages
                if max_pages and page + 1 >= max_pages:
                    self.logger.info(f"Reached max pages limit: {max_pages}")
                    break
                
                if total_pages and page + 1 >= total_pages:
                    self.logger.info(f"Reached last page: {total_pages}")
                    break
                
                page += 1
                
                # Rate limiting between pages
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error scraping page {page}: {e}")
                break
        
        self.logger.info(f"Scraped {len(articles)} articles from BPS")
        return articles


async def create_bps_scraper(api_key: str) -> BPSScraper:
    """
    Factory function to create and initialize BPS scraper.
    
    Args:
        api_key: BPS API key
        
    Returns:
        Initialized BPS scraper
    """
    scraper = BPSScraper(api_key=api_key)
    await scraper._ensure_session()
    return scraper
