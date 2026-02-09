"""
Bank Indonesia News Scraper for Azure Functions.
Implements scraping functionality for Bank Indonesia press releases using Selenium.
"""

import asyncio
import re
import sys
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

from bs4 import BeautifulSoup

# Add parent directory to Python path for absolute imports in Azure Functions
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from scrapers.base_scraper import BaseNewsScraper
from scrapers.exceptions import ScrapingError, NetworkError
from shared.models import NewsArticle, ScrapingConfig

# Indonesian month names for date parsing
BULAN_INDONESIA = {
    'januari': '01', 'februari': '02', 'maret': '03', 'april': '04',
    'mei': '05', 'juni': '06', 'juli': '07', 'agustus': '08',
    'september': '09', 'oktober': '10', 'november': '11', 'desember': '12'
}


class BankIndonesiaScraper(BaseNewsScraper):
    """
    Bank Indonesia News Scraper implementation.
    Scrapes press releases from Bank Indonesia website using Selenium for dynamic content.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize Bank Indonesia scraper with default configuration."""
        if config is None:
            config = ScrapingConfig(
                source_name="Bank Indonesia",
                base_url="https://www.bi.go.id",
                selectors={
                    "news_url": "https://www.bi.go.id/id/publikasi/ruang-media/news-release/Default.aspx",
                    "article_list": ".media.media--pers",
                    "article_title": ".media__title",
                    "article_subtitle": ".media__subtitle",
                    "content_div": "#ctl00_PlaceHolderMain_ctl05__ControlWrapper_RichHtmlField",
                    "pagination_next": "input.next[type='image']"
                },
                rate_limit_delay=2.0,
                max_retries=3,
                timeout=30
            )
        
        super().__init__(config)
        self.news_url = self.config.selectors.get("news_url")
        self.requires_selenium = True

    def _parse_indonesian_date(self, date_str: str) -> Optional[str]:
        """
        Parse Indonesian date format to YYYY-MM-DD.
        
        Args:
            date_str: Date string like "15 Januari 2024"
            
        Returns:
            Date string in YYYY-MM-DD format or None
        """
        if not date_str or date_str == 'N/A':
            return None
        
        match = re.search(r'(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})', date_str)
        if match:
            day = match.group(1).zfill(2)
            month = BULAN_INDONESIA.get(match.group(2).lower(), '01')
            year = match.group(3)
            return f"{year}-{month}-{day}"
        return None

    async def _fetch_news_list_selenium(self, keyword: Optional[str] = None) -> str:
        """
        Fetch news list page using Selenium with optional search.
        
        Args:
            keyword: Optional keyword to search for
            
        Returns:
            Page HTML content
        """
        try:
            content = await self._fetch_content_selenium(self.news_url)
            return content
        except Exception as e:
            self.logger.error(f"Failed to fetch news list: {e}")
            raise NetworkError(f"Failed to fetch Bank Indonesia news list", 
                             source=self.source_name, url=self.news_url)

    def _extract_articles_from_page(self, page_source: str, target_date: str) -> tuple:
        """
        Extract articles from page source.
        
        Args:
            page_source: HTML page source
            target_date: Target date in YYYY-MM-DD format
            
        Returns:
            Tuple of (articles_list, should_stop_flag)
        """
        soup = BeautifulSoup(page_source, 'html.parser')
        articles = []
        should_stop = False
        
        news_items = soup.select(self.config.selectors.get("article_list", ".media.media--pers"))
        self.logger.info(f"Found {len(news_items)} news items on page")
        
        target_datetime = datetime.strptime(target_date, "%Y-%m-%d")
        
        for item in news_items:
            try:
                # Extract title and URL
                title_elem = item.select_one(self.config.selectors.get("article_title", ".media__title"))
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                if url and not url.startswith('http'):
                    url = f"{self.config.base_url}{url}"
                
                # Extract date from subtitle
                subtitle_elem = item.select_one(self.config.selectors.get("article_subtitle", ".media__subtitle"))
                if not subtitle_elem:
                    continue
                
                subtitle_text = subtitle_elem.get_text(strip=True)
                parts = subtitle_text.split("•")
                date_str = parts[0].strip() if parts else None
                
                formatted_date = self._parse_indonesian_date(date_str)
                if not formatted_date:
                    self.logger.warning(f"Could not parse date: {date_str}")
                    continue
                
                article_datetime = datetime.strptime(formatted_date, "%Y-%m-%d")
                
                # Check if article is older than target date
                if article_datetime < target_datetime:
                    self.logger.info(f"Found older article ({formatted_date}), stopping")
                    should_stop = True
                    break
                
                # Only include articles matching target date
                if formatted_date == target_date:
                    articles.append({
                        'title': title,
                        'date': formatted_date,
                        'url': url,
                        'content': None  # Will be filled later
                    })
                    self.logger.info(f"Match: {title[:60]}... ({formatted_date})")
                
            except Exception as e:
                self.logger.warning(f"Failed to parse news item: {e}")
                continue
        
        return articles, should_stop

    async def _extract_article_content(self, url: str) -> str:
        """
        Extract article content from Bank Indonesia article page.
        
        Args:
            url: Article URL
            
        Returns:
            Extracted article content
        """
        try:
            content = await self._fetch_content_selenium(url)
            soup = BeautifulSoup(content, 'html.parser')
            
            content_selector = self.config.selectors.get(
                "content_div", 
                "#ctl00_PlaceHolderMain_ctl05__ControlWrapper_RichHtmlField"
            )
            content_div = soup.select_one(content_selector)
            
            if not content_div:
                self.logger.warning(f"Content div not found for {url}")
                return "N/A"
            
            paragraphs = content_div.find_all('p')
            content_text = []
            
            for p in paragraphs:
                text = p.get_text(strip=True)
                if not text or len(text) < 5:
                    continue
                
                # Skip footer patterns
                if "Jakarta," in text and "Departemen Komunikasi" in text:
                    continue
                if text.startswith("No. ") and "DKom" in text:
                    continue
                
                if len(text) >= 30:
                    content_text.append(text)
            
            if content_text:
                return "\n\n".join(content_text).strip()
            
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
        Scrape articles from Bank Indonesia source.
        
        Args:
            keywords: Keywords to search for
            start_date: Start date for article search
            end_date: End date for article search
            **kwargs: Additional parameters
            
        Returns:
            List of scraped NewsArticle objects
        """
        try:
            target_date = end_date.strftime("%Y-%m-%d")
            keyword = keywords[0] if keywords else None
            
            self.logger.info(f"Scraping Bank Indonesia for date: {target_date}")
            if keyword:
                self.logger.info(f"Keyword filter: {keyword}")
            
            # Fetch news list
            page_source = await self._fetch_news_list_selenium(keyword)
            
            # Extract articles matching date
            article_list, _ = self._extract_articles_from_page(page_source, target_date)
            
            if not article_list:
                self.logger.info("No articles found for the target date")
                return []
            
            self.logger.info(f"Found {len(article_list)} articles, extracting content...")
            
            # Extract content for each article
            articles = []
            for i, article_data in enumerate(article_list):
                try:
                    self.logger.info(f"Processing article {i+1}/{len(article_list)}: {article_data['title'][:60]}...")
                    
                    content = await self._extract_article_content(article_data['url'])
                    
                    # Filter by keyword if specified
                    if keyword:
                        keyword_lower = keyword.lower()
                        title_match = keyword_lower in article_data['title'].lower()
                        content_match = content != "N/A" and keyword_lower in content.lower()
                        
                        if not (title_match or content_match):
                            self.logger.debug(f"Skipping article - keyword not found")
                            continue
                    
                    article = self._create_article(
                        title=article_data['title'],
                        content=content,
                        url=article_data['url'],
                        published_date=datetime.strptime(article_data['date'], '%Y-%m-%d')
                    )
                    
                    articles.append(article)
                    
                    # Rate limiting
                    await asyncio.sleep(2.0)
                    
                except Exception as e:
                    self.logger.error(f"Failed to process article: {e}")
                    continue
            
            self.logger.info(f"Successfully scraped {len(articles)} articles from Bank Indonesia")
            return articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape Bank Indonesia: {str(e)}", source=self.source_name)


# Azure Function wrapper
async def scrape_bank_indonesia_news(
    keywords: List[str], 
    start_date: datetime, 
    end_date: datetime, 
    **kwargs
) -> List[NewsArticle]:
    """
    Azure Function entry point for Bank Indonesia news scraping.
    
    Args:
        keywords: Keywords to search for
        start_date: Start date for article search
        end_date: End date for article search
        **kwargs: Additional parameters
        
    Returns:
        List of scraped NewsArticle objects
    """
    async with BankIndonesiaScraper() as scraper:
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)
