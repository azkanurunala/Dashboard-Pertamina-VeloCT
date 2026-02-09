"""
OilPrice News Scraper for Azure Functions.
Implements scraping functionality for OilPrice news articles using sitemap and direct scraping.
"""

import asyncio
import re
import sys
import os
import xml.etree.ElementTree as ET
import json
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


class OilPriceNewsScraper(BaseNewsScraper):
    """
    OilPrice.com News Scraper implementation.
    Scrapes news articles from OilPrice.com using sitemap and JSON-LD extraction.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize OilPrice scraper with default configuration."""
        if config is None:
            config = ScrapingConfig(
                source_name="OilPrice",
                base_url="https://oilprice.com",
                selectors={
                    "sitemap": "https://oilprice.com/googlenews.xml",
                    "article_content": "div#article-content.wysiwyg.clear",
                    "json_ld": "script[type='application/ld+json']"
                },
                rate_limit_delay=1.0,
                max_retries=3,
                timeout=25
            )
        
        super().__init__(config)
        self.sitemap_url = self.config.selectors.get("sitemap", "https://oilprice.com/googlenews.xml")

    def _clean_oilprice_text(self, text: str) -> str:
        """
        Clean OilPrice-specific text patterns.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        if not text or text == 'N/A':
            return text
        
        # Replace HTML entities
        replacements = {
            '&nbsp;': ' ',
            '&rsquo;': "'",
            '&ldquo;': '"',
            '&rdquo;': '"',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>'
        }
        
        for entity, replacement in replacements.items():
            text = text.replace(entity, replacement)
        
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    async def _scrape_articles_from_source(self, keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
        """
        Scrape articles from OilPrice source.
        
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
            sitemap_entries = await self._fetch_sitemap_robust(self.sitemap_url)
            
            # 2. Filter articles
            all_articles_info = []
            for info in sitemap_entries:
                url = info['loc']
                title = info.get('title', '')
                date_str = info.get('date', '')
                # OilPrice often provides 'keywords' in the sitemap tags
                sitemap_keywords = info.get('raw_tags', {}).get('keywords', '').lower()
                
                # Filter by keywords if provided
                if keywords:
                    keyword_match = False
                    info_text = f"{title} {url} {sitemap_keywords}".lower()
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
                    'date': date_str,
                    'keywords': sitemap_keywords
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
                    
                    # Extract content using JSON-LD method
                    content = await self._extract_article_content_json_ld(article_data['url'])
                    
                    # Parse published date
                    published_date = datetime.utcnow()
                    if article_data['date']:
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
                        keywords=article_data.get('keywords', '').split(',') if article_data.get('keywords') else []
                    )
                    
                    articles.append(article)
                    
                    # Rate limiting
                    await asyncio.sleep(1.0)
                    
                except Exception as e:
                    self.logger.error(f"Failed to process article {article_data['url']}: {e}")
                    continue
            
            self.logger.info(f"Successfully scraped {len(articles)} articles from OilPrice")
            return articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape OilPrice articles: {str(e)}", source=self.source_name)


# Azure Function wrapper
async def scrape_oilprice_news(keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
    """
    Azure Function entry point for OilPrice news scraping.
    
    Args:
        keywords: Keywords to search for
        start_date: Start date for article search
        end_date: End date for article search
        **kwargs: Additional parameters
        
    Returns:
        List of scraped NewsArticle objects
    """
    async with OilPriceNewsScraper() as scraper:
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)