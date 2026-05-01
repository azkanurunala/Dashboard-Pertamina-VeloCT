"""
S&P Global News Scraper for Azure Functions.
Fetches news articles from S&P Global News Insights API.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import aiohttp

from bs4 import BeautifulSoup

# Add parent directory to Python path
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from scrapers.base_scraper import BaseNewsScraper
from scrapers.exceptions import ScrapingError
from shared.models import NewsArticle, ScrapingConfig


class SAndPNewsScraper(BaseNewsScraper):
    """
    S&P Global News Scraper.
    Fetches news articles from S&P Global News Insights API.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize S&P News scraper."""
        if config is None:
            config = ScrapingConfig(
                source_name="S&P Global News",
                base_url="https://api.ci.spglobal.com",
                selectors={
                    "auth_url": "https://api.ci.spglobal.com/auth/api",
                    "search_url": "https://api.ci.spglobal.com/news-insights/v1/search/story",
                    "content_url": "https://api.ci.spglobal.com/news-insights/v1/content/"
                },
                rate_limit_delay=1.0,
                max_retries=3,
                timeout=60
            )
        
        super().__init__(config)
        self._access_token = None
        self._sp_username = os.getenv("S&P_USERNAME") or os.getenv("SP_USERNAME")
        self._sp_password = os.getenv("S&P_PASSWORD") or os.getenv("SP_PASSWORD")

    async def _login(self) -> Optional[str]:
        """Authenticate with S&P Global API."""
        if not self._sp_username or not self._sp_password:
            self.logger.error("S&P credentials not found in environment")
            return None
        
        try:
            await self._ensure_session()
            
            auth_url = self.config.selectors.get("auth_url")
            payload = {
                "username": self._sp_username,
                "password": self._sp_password
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            
            async with self._session.post(auth_url, data=payload, headers=headers,
                                          timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                data = await response.json()
                
                access_token = data.get('access_token')
                if access_token:
                    self.logger.info("S&P Global login successful")
                    self._access_token = access_token
                    return access_token
                    
        except Exception as e:
            self.logger.error(f"S&P Global login failed: {e}")
        
        return None

    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract clean text from HTML content."""
        if not html_content:
            return ""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text(separator=' ', strip=True)
        text = ' '.join(text.split())
        return text

    async def _get_article_content(self, article_id: str) -> str:
        """Fetch full article content."""
        if not self._access_token:
            await self._login()
        
        if not self._access_token:
            return ""
        
        try:
            await self._ensure_session()
            
            url = f"{self.config.selectors['content_url']}{article_id}"
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json"
            }
            
            async with self._session.get(url, headers=headers,
                                         timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                data = await response.json()
                
                if data and 'envelope' in data and 'content' in data['envelope']:
                    body_html = data['envelope']['content'].get('body', '')
                    return self._extract_text_from_html(body_html)
                    
        except Exception as e:
            self.logger.error(f"Error fetching content for article {article_id}: {e}")
        
        return ""

    async def _search_news(
        self, 
        query: str, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None,
        page_size: int = 100
    ) -> List[Dict]:
        """Search for news articles."""
        if not self._access_token:
            await self._login()
        
        if not self._access_token:
            raise ScrapingError("Failed to authenticate with S&P Global", source=self.source_name)
        
        try:
            await self._ensure_session()
            
            params = {
                "q": query,
                "pagesize": page_size
            }
            
            if start_date and end_date:
                params["filter"] = f'updatedDate >= "{start_date}" AND updatedDate < "{end_date}"'
            
            headers = {
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json"
            }
            
            url = self.config.selectors["search_url"]
            
            async with self._session.get(url, params=params, headers=headers,
                                         timeout=aiohttp.ClientTimeout(total=60)) as response:
                response.raise_for_status()
                data = await response.json()
                
                if data and 'results' in data:
                    return data['results']
                    
        except Exception as e:
            self.logger.error(f"Error searching news: {e}")
            raise ScrapingError(f"Search failed: {str(e)}", source=self.source_name)
        
        return []

    async def _scrape_articles_from_source(
        self, 
        keywords: List[str], 
        start_date: datetime, 
        end_date: datetime, 
        **kwargs
    ) -> List[NewsArticle]:
        """Scrape news articles from S&P Global."""
        try:
            query = keywords[0] if keywords else "SAF"
            max_articles = kwargs.get('max_articles', 50)
            
            # Format dates for API
            start_str = f"{start_date.strftime('%Y-%m-%d')} 00:00:00"
            next_day = end_date + timedelta(days=1)
            end_str = f"{next_day.strftime('%Y-%m-%d')} 00:00:00"
            
            self.logger.info(f"Searching S&P News for: {query}")
            
            # Login first
            if not await self._login():
                raise ScrapingError("Failed to login to S&P Global", source=self.source_name)
            
            # Search for articles
            results = await self._search_news(query, start_str, end_str, max_articles)

            # Deduplicate by (title, updatedDate) — mirrors src/code_scrapping/scrape_sandp_news.py
            if results:
                seen = set()
                unique_results = []
                for item in results:
                    title_key = (item.get('headline') or "").strip().lower()
                    date_key = item.get('updatedDate') or ""
                    key = (title_key, date_key)
                    if key in seen:
                        continue
                    seen.add(key)
                    unique_results.append(item)
                if len(unique_results) != len(results):
                    self.logger.info(
                        f"Deduplicated S&P results: {len(results)} -> {len(unique_results)}"
                    )
                results = unique_results

            if not results:
                self.logger.info("No articles found")
                return []

            self.logger.info(f"Found {len(results)} articles, fetching content...")
            
            articles = []
            for idx, item in enumerate(results):
                try:
                    article_id = item.get('id', '')
                    headline = item.get('headline', '')
                    updated_date = item.get('updatedDate', '')
                    document_url = item.get('documentUrl', '')
                    
                    # Parse date
                    date_obj = datetime.now()
                    if updated_date:
                        try:
                            date_obj = datetime.fromisoformat(updated_date.replace('Z', '+00:00'))
                        except:
                            pass
                    
                    # Get content
                    self.logger.info(f"[{idx+1}/{len(results)}] Fetching: {headline[:50]}...")
                    content = await self._get_article_content(article_id)
                    
                    article = self._create_article(
                        title=headline,
                        content=content if content else "N/A",
                        url=document_url,
                        published_date=date_obj.replace(tzinfo=None)
                    )
                    articles.append(article)
                    
                    await asyncio.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    self.logger.error(f"Error processing article: {e}")
                    continue
            
            self.logger.info(f"Successfully scraped {len(articles)} articles from S&P Global")
            return articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape S&P Global News: {str(e)}", source=self.source_name)


async def scrape_sandp_news(
    keywords: List[str], 
    start_date: datetime, 
    end_date: datetime, 
    **kwargs
) -> List[NewsArticle]:
    """Azure Function entry point for S&P Global news scraping."""
    async with SAndPNewsScraper() as scraper:
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)
