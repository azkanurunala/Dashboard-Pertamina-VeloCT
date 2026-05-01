"""
Kontan News Scraper for Azure Functions.
Implements scraping functionality for Kontan news articles using sitemap and direct scraping.
"""

import asyncio
import re
import sys
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

# Add parent directory to Python path for absolute imports in Azure Functions
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from scrapers.base_scraper import BaseNewsScraper
from scrapers.exceptions import ScrapingError, NetworkError, ContentExtractionError
from shared.models import NewsArticle, ScrapingConfig


# Subdomains to exclude from Kontan scraping results.
# Mirrors src/code_scrapping/kontan.py EXCLUDED_SUBDOMAINS.
EXCLUDED_SUBDOMAINS = ["insight.kontan.co.id"]


class KontanNewsScraper(BaseNewsScraper):
    """
    Kontan News Scraper implementation.
    Scrapes news articles from Kontan using sitemap crawling and content extraction.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize Kontan scraper with default configuration."""
        if config is None:
            config = ScrapingConfig(
                source_name="Kontan",
                base_url="https://www.kontan.co.id",
                selectors={
                    "sitemap": "https://www.kontan.co.id/sitemap.xml",
                    "article_content": [
                        "div.article-detail-content",
                        "div.detail-content",
                        "div.content-article",
                        "div.article-content",
                        "div#article-content",
                        "article div.content",
                        "div.post-content",
                        "div.read__content"
                    ]
                },
                rate_limit_delay=1.0,
                max_retries=3,
                timeout=25
            )
        
        super().__init__(config)
        self.sitemap_url = self.config.selectors.get("sitemap", "https://www.kontan.co.id/sitemap.xml")

    def _clean_kontan_text(self, text: str) -> str:
        """
        Clean Kontan-specific text patterns.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        if not text or text == 'N/A':
            return text
        
        # Kontan-specific patterns to remove
        patterns = [
            r'Baca Juga.*',
            r'Cek Berita dan Artikel.*'
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Clean up extra whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    async def _extract_article_content(self, url: str) -> str:
        """
        Extract article content from Kontan article page.
        
        Args:
            url: Article URL
            
        Returns:
            Extracted article content
        """
        try:
            content = await self._fetch_content(url)
            soup = BeautifulSoup(content, 'html.parser')
            
            # Try different content selectors
            content_selectors = self.config.selectors.get("article_content", [])
            container = None
            
            for selector in content_selectors:
                container = soup.select_one(selector)
                if container:
                    # Extract paragraphs from this container
                    paragraphs = [p.get_text(strip=True) for p in container.find_all('p') 
                                if p.get_text(strip=True)]
                    if paragraphs:
                        content_text = '\n\n'.join(paragraphs)
                        return self._clean_kontan_text(content_text)
            
            # Fallback: extract all paragraphs from the page
            if not container:
                paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') 
                            if p.get_text(strip=True)]
                if len(paragraphs) > 3:  # Only if we have substantial content
                    content_text = '\n\n'.join(paragraphs)
                    return self._clean_kontan_text(content_text)
            
            return 'N/A'
            
        except Exception as e:
            self.logger.error(f"Failed to extract content from {url}: {e}")
            return 'N/A'

    async def _scrape_articles_from_source(self, keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
        """
        Scrape articles from Kontan source.
        
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
            
            self.logger.info(f"Found {len(all_articles_info)} articles after sitemap filtering")
            
            if not all_articles_info:
                return []
            
            # Limit articles for performance
            max_articles = kwargs.get('max_articles', 25)
            if len(all_articles_info) > max_articles:
                all_articles_info = all_articles_info[:max_articles]
                self.logger.info(f"Limited to {max_articles} articles for processing")
            
            # Extract content for each article
            articles = []
            for i, article_data in enumerate(all_articles_info):
                try:
                    self.logger.info(f"Processing article {i+1}/{len(all_articles_info)}: {article_data['title'][:50]}...")
                    
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
                        keywords=[]
                    )
                    
                    articles.append(article)
                    
                    # Rate limiting
                    await asyncio.sleep(1.0)
                    
                except Exception as e:
                    self.logger.error(f"Failed to process article {article_data['url']}: {e}")
                    continue
            
            self.logger.info(f"Successfully scraped {len(articles)} articles from Kontan")
            return articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape Kontan articles: {str(e)}", source=self.source_name)


# Azure Function wrapper
async def scrape_kontan_news(keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
    """
    Azure Function entry point for Kontan news scraping.
    
    Args:
        keywords: Keywords to search for
        start_date: Start date for article search
        end_date: End date for article search
        **kwargs: Additional parameters
        
    Returns:
        List of scraped NewsArticle objects
    """
    async with KontanNewsScraper() as scraper:
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)