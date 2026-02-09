"""
CNN News Scraper for Azure Functions.
Implements scraping functionality for CNN news articles using sitemap and direct scraping.
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


class CNNNewsScraper(BaseNewsScraper):
    """
    CNN News Scraper implementation.
    Scrapes news articles from CNN using sitemap and direct content extraction.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize CNN scraper with default configuration."""
        if config is None:
            config = ScrapingConfig(
                source_name="CNN",
                base_url="https://www.cnn.com",
                selectors={
                    "sitemap": "https://www.cnn.com/sitemap/news.xml",
                    "article_content": "div.article__content, div.video-resource__description, main, article",
                    "title": "h1",
                    "content": "div.article__content p, main p, article p",
                    "unwanted": "script, style, nav, header, footer, aside, iframe, noscript"
                },
                rate_limit_delay=1,
                max_retries=3,
                timeout=20
            )
        
        super().__init__(config)
        self.sitemap_url = self.config.selectors.get("sitemap", "https://www.cnn.com/sitemap/news.xml")

    def _clean_cnn_text(self, text: str) -> str:
        """
        Clean CNN-specific text patterns.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        if not text or text == 'N/A':
            return text
        
        # CNN-specific patterns to remove
        patterns = [
            r'Sign up for CNN.*',
            r'Read more:.*',
            r'Watch:.*',
            r"CNN\'s\s+[\w\s,]+contributed to this report\.?",
            r'This story.*contributed to this report\.?'
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Clean up extra whitespace
        text = re.sub(r' {2,}', ' ', text).strip()
        
        return text

    def _is_valid_paragraph(self, text: str, min_length: int = 10) -> bool:
        """
        Check if a paragraph is valid content.
        
        Args:
            text: Text to validate
            min_length: Minimum length for valid paragraph
            
        Returns:
            True if paragraph is valid
        """
        if not text or len(text) < min_length:
            return False
        
        # Spam/unwanted content indicators
        spam_keywords = [
            'cookie', 'privacy policy', 'terms of service', 'subscribe', 
            'sign up', 'newsletter', 'follow us', 'advertisement'
        ]
        
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in spam_keywords):
            return False
        
        # Check if it's just numbers, dates, or punctuation
        if re.match(r'^[\d\s\-:,\.]+$', text):
            return False
        
        return True

    async def _scrape_articles_from_source(self, keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
        """
        Scrape articles from CNN source.
        
        Args:
            keywords: Keywords to search for
            start_date: Start date for article search
            end_date: End date for article search
            **kwargs: Additional parameters
            
        Returns:
            List of scraped NewsArticle objects
        """
        try:
            # 1. Fetch sitemap(s)
            # The base method _fetch_sitemap_robust already handles sitemap indices recursively
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
            
            self.logger.info(f"Found {len(all_articles_info)} candidate articles after filtering")
            
            if not all_articles_info:
                return []
            
            # Limit for performance
            max_articles = kwargs.get('max_articles', 30)
            if len(all_articles_info) > max_articles:
                all_articles_info = all_articles_info[:max_articles]
                self.logger.info(f"Limited to {max_articles} articles for processing")
            
            # 3. Extract content for each article
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
                        keywords=[]
                    )
                    
                    articles.append(article)
                    
                    # Rate limiting
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"Failed to process article {article_data['url']}: {e}")
                    continue
            
            self.logger.info(f"Successfully scraped {len(articles)} articles from CNN")
            return articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape CNN articles: {str(e)}", source=self.source_name)


# Azure Function wrapper
async def scrape_cnn_news(keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
    """
    Azure Function entry point for CNN news scraping.
    """
    async with CNNNewsScraper() as scraper:
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)
