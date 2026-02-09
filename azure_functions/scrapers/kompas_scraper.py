"""
Kompas News Scraper for Azure Functions.
Implements scraping functionality for Kompas news articles using sitemap and direct scraping.
"""

import asyncio
import re
import sys
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin
import gzip
import io

from bs4 import BeautifulSoup

# Add parent directory to Python path for absolute imports in Azure Functions
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from scrapers.base_scraper import BaseNewsScraper
from scrapers.exceptions import ScrapingError, NetworkError, ContentExtractionError
from shared.models import NewsArticle, ScrapingConfig


class KompasNewsScraper(BaseNewsScraper):
    """
    Kompas News Scraper implementation.
    Scrapes news articles from Kompas using sitemap and direct content extraction.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize Kompas scraper with default configuration."""
        if config is None:
            config = ScrapingConfig(
                source_name="Kompas",
                base_url="https://www.kompas.com",
                selectors={
                    "sitemap": "https://www.kompas.com/sitemap.xml",
                    "article_content": "div.read__content",
                    "title": "h1",
                    "content": "div.read__content p",
                    "unwanted": "aside, script, style, iframe, noscript, div.kompasidRec__wrap, div.kompasidRec__subs, div.kompasidRec__title, div.articleRelated, div.article__related, div.inner__sidebar, div.inject-baca-juga, div.ads-on-body"
                },
                rate_limit_delay=1.5,
                max_retries=3,
                timeout=25
            )
        
        super().__init__(config)
        self.sitemap_url = self.config.selectors.get("sitemap", "https://www.kompas.com/sitemap.xml")

    def _clean_kompas_text(self, text: str) -> str:
        """
        Clean Kompas-specific text patterns.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        if not text or text == 'N/A':
            return text
        
        # Kompas-specific patterns to remove
        patterns = [
            r'Baca\s+juga.*',
            r'Download\s+sekarang.*',
            r'Dalam\s+segala\s+situasi.*',
            r'Cek Berita dan Artikel.*'
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text

    def _extract_and_clean_content(self, content_div) -> str:
        """Extract and clean content from content div."""
        if not content_div:
            return "-"
        
        # Extract meaningful text
        elements = content_div.find_all(["p", "li", "h2", "h3"])
        paragraphs = []
        
        for element in elements:
            text = element.get_text(strip=True)
            if not text or len(text) < 5:
                continue
            
            # Skip unwanted patterns
            if re.search(r'^(baca\s+juga|download\s+sekarang|dalam\s+segala\s+situasi)', text, re.IGNORECASE):
                continue
            
            paragraphs.append(text)
        
        if not paragraphs:
            return "-"
        
        content = "\n\n".join(paragraphs)
        return self._clean_kompas_text(content)

    def _get_total_pages(self, soup) -> int:
        """Get total number of pages for multi-page articles."""
        paging_wrap = soup.select_one("div.paging__wrap")
        if not paging_wrap:
            return 1
        
        paging_items = paging_wrap.select("div.paging__item")
        if not paging_items:
            return 1
        
        max_page = 1
        for item in paging_items:
            link = item.select_one("a.paging__link")
            if not link:
                continue
            
            href = link.get('href', '')
            if '?page=' in href:
                try:
                    page_num = int(href.split('?page=')[-1].split('&')[0])
                    if page_num > max_page:
                        max_page = page_num
                except (ValueError, IndexError):
                    continue
        
        return max_page

    async def _scrape_articles_from_source(self, keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
        """
        Scrape articles from Kompas source.
        
        Args:
            keywords: Keywords to search for
            start_date: Start date for article search
            end_date: End date for article search
            **kwargs: Additional parameters
            
        Returns:
            List of scraped NewsArticle objects
        """
        try:
            # 1. Fetch sitemap(s) - recursive discovery is handled by the base method
            sitemap_entries = await self._fetch_sitemap_robust(self.sitemap_url)
            
            # 2. Filter articles
            all_articles_info = []
            for info in sitemap_entries:
                url = info['loc']
                title = info.get('title', '')
                date_str = info.get('date', '')
                
                # Filter by keywords if provided
                if keywords:
                    keyword_match = False
                    info_text = f"{title} {url}".lower()
                    for kw in keywords:
                        if kw.lower() in info_text:
                            keyword_match = True
                            break
                    if not keyword_match:
                        continue
                
                # Filter by date if provided
                if start_date and end_date and date_str:
                    try:
                        article_date = datetime.strptime(date_str, '%Y-%m-%d')
                        if not (start_date <= article_date <= end_date):
                            continue
                    except ValueError:
                        pass
                
                all_articles_info.append({
                    'title': title or url.rstrip('/').split('/')[-1].replace('-', ' ').title(),
                    'url': url,
                    'date': date_str
                })
            
            
            # Limit articles for performance
            max_articles = kwargs.get('max_articles', 30)
            if len(all_articles_info) > max_articles:
                all_articles_info = all_articles_info[:max_articles]
                self.logger.info(f"Limited to {max_articles} articles for processing")
            
            # Extract content for each article
            articles = []
            for i, article_data in enumerate(all_articles_info):
                try:
                    self.logger.info(f"Processing article {i+1}/{len(all_articles_info)}: {article_data['title'][:60]}...")
                    
                    # Extract content
                    content = await self._extract_article_content(article_data['url'])
                    
                    # Parse published date
                    published_date = datetime.utcnow()
                    if article_data['date'] and article_data['date'] != '-':
                        try:
                            published_date = datetime.strptime(article_data['date'], '%Y-%m-%d')
                        except ValueError:
                            pass
                    
                    # Create article
                    article = self._create_article(
                        title=article_data['title'],
                        content=content,
                        url=article_data['url'],
                        published_date=published_date,
                        keywords=[] # Will be populated by base class if matching
                    )
                    
                    articles.append(article)
                    
                    # Rate limiting
                    await asyncio.sleep(1.0)
                    
                except Exception as e:
                    self.logger.error(f"Failed to process article {article_data['url']}: {e}")
                    continue
            
            self.logger.info(f"Successfully scraped {len(articles)} articles from Kompas")
            return articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape Kompas articles: {str(e)}", source=self.source_name)


# Azure Function wrapper
async def scrape_kompas_news(keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
    """
    Azure Function entry point for Kompas news scraping.
    
    Args:
        keywords: Keywords to search for
        start_date: Start date for article search
        end_date: End date for article search
        **kwargs: Additional parameters
        
    Returns:
        List of scraped NewsArticle objects
    """
    async with KompasNewsScraper() as scraper:
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)