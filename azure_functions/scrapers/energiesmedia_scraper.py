"""
EnergiesMedia News Scraper for Azure Functions.
Scrapes energy news from EnergiesMedia.com.
"""

import asyncio
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


class EnergiesMediaScraper(BaseNewsScraper):
    """
    EnergiesMedia News Scraper implementation.
    Scrapes energy news from EnergiesMedia.com.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize EnergiesMedia scraper."""
        if config is None:
            config = ScrapingConfig(
                source_name="EnergiesMedia",
                base_url="https://energiesmedia.com",
                selectors={
                    "search_url": "https://energiesmedia.com/?s=",
                    "article_list": "article.jeg_post.jeg_pl_lg_2",
                    "article_title": "h3.jeg_post_title a",
                    "article_date": "div.jeg_meta_date a",
                    "article_content": "div.content-inner"
                },
                rate_limit_delay=2.0,
                max_retries=3,
                timeout=60
            )
        
        super().__init__(config)

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse EnergiesMedia date format."""
        if not date_str:
            return None
        
        # Format: "January 15, 2024"
        try:
            dt = datetime.strptime(date_str.strip(), "%B %d, %Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None

    async def _search_articles(self, keyword: str, page: int = 1) -> List[Dict]:
        """Search EnergiesMedia for articles."""
        try:
            keyword_formatted = keyword.replace(' ', '+')
            if page == 1:
                url = f"{self.config.selectors['search_url']}{keyword_formatted}"
            else:
                url = f"{self.config.base_url}/page/{page}/?s={keyword_formatted}"
            
            content = await self._fetch_content(url)
            soup = BeautifulSoup(content, 'html.parser')
            
            articles = []
            items = soup.select(self.config.selectors.get("article_list", "article"))
            
            for item in items:
                try:
                    title_elem = item.select_one(self.config.selectors.get("article_title", "h3 a"))
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get('href', '').strip()
                    
                    date_elem = item.select_one(self.config.selectors.get("article_date", "div.jeg_meta_date a"))
                    date_str = date_elem.get_text(strip=True) if date_elem else None
                    formatted_date = self._parse_date(date_str)
                    
                    if title and link:
                        articles.append({
                            'title': title,
                            'url': link,
                            'date': formatted_date
                        })
                        
                except Exception as e:
                    self.logger.warning(f"Failed to parse article: {e}")
                    continue
            
            return articles
            
        except Exception as e:
            self.logger.error(f"Failed to search page {page}: {e}")
            return []

    async def _extract_article_content(self, url: str) -> str:
        """Extract article content from EnergiesMedia page."""
        try:
            content = await self._fetch_content(url)
            soup = BeautifulSoup(content, 'html.parser')
            
            content_div = soup.select_one(self.config.selectors.get("article_content", "div.content-inner"))
            if not content_div:
                return "N/A"
            
            # Remove unwanted elements
            for unwanted in content_div.select('div.jnews_inline_related_post_wrapper, div.oilma-article-content-banner, div.m-a-box, script'):
                unwanted.decompose()
            
            # Extract text from paragraphs and headers
            content_parts = []
            for elem in content_div.find_all(['p', 'h2', 'h3', 'blockquote']):
                text = elem.get_text(strip=True)
                if text and len(text) > 10:
                    content_parts.append(text)
            
            if content_parts:
                return "\n\n".join(content_parts)
            
            return "N/A"
            
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
        """Scrape articles from EnergiesMedia."""
        try:
            keyword = keywords[0] if keywords else "oil"
            max_pages = kwargs.get('max_pages', 5)
            
            self.logger.info(f"Scraping EnergiesMedia for: {keyword}")
            
            all_articles = []
            should_stop = False
            
            for page in range(1, max_pages + 1):
                if should_stop:
                    break
                
                self.logger.info(f"Scraping page {page}...")
                page_articles = await self._search_articles(keyword, page)
                
                if not page_articles:
                    break
                
                for article in page_articles:
                    if article['date']:
                        try:
                            article_date = datetime.strptime(article['date'], "%Y-%m-%d")
                            if article_date < start_date:
                                self.logger.info(f"Found older article ({article['date']}), stopping")
                                should_stop = True
                                break
                            elif start_date <= article_date <= end_date:
                                all_articles.append(article)
                        except ValueError:
                            continue
                
                await asyncio.sleep(2.0)  # Rate limiting
            
            self.logger.info(f"Found {len(all_articles)} articles to process")
            
            if not all_articles:
                return []
            
            # Extract content
            articles = []
            for i, article_data in enumerate(all_articles):
                try:
                    self.logger.info(f"[{i+1}/{len(all_articles)}] {article_data['title'][:60]}...")
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
            
            self.logger.info(f"Successfully scraped {len(articles)} articles from EnergiesMedia")
            return articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape EnergiesMedia: {str(e)}", source=self.source_name)


async def scrape_energiesmedia_news(
    keywords: List[str], 
    start_date: datetime, 
    end_date: datetime, 
    **kwargs
) -> List[NewsArticle]:
    """Azure Function entry point for EnergiesMedia news scraping."""
    async with EnergiesMediaScraper() as scraper:
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)
