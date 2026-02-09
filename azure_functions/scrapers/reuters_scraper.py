"""
Reuters News Scraper for Azure Functions.
Implements scraping functionality for Reuters news articles using sitemap and direct scraping.
"""

import asyncio
import re
import sys
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin
import random

from bs4 import BeautifulSoup

# Add parent directory to Python path for absolute imports in Azure Functions
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from scrapers.base_scraper import BaseNewsScraper
from scrapers.exceptions import ScrapingError, NetworkError, ContentExtractionError
from shared.models import NewsArticle, ScrapingConfig


class ReutersNewsScraper(BaseNewsScraper):
    """
    Reuters News Scraper implementation.
    Scrapes news articles from Reuters using sitemap and direct content extraction.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize Reuters scraper with default configuration."""
        if config is None:
            config = ScrapingConfig(
                source_name="Reuters",
                base_url="https://www.reuters.com",
                selectors={
                    "sitemap_index": "https://www.reuters.com/arc/outboundfeeds/news-sitemap-index/?outputType=xml",
                    "article_body": "div.article-body-module__content__bnXL1, div[data-testid='article-body'], article",
                    "title": "h1",
                    "content": "div[data-testid^='paragraph-'], p",
                    "unwanted": "div[data-testid*='promo-box'], div[data-testid*='ad'], div[data-testid*='banner'], div[data-testid*='CnxPlayer']"
                },
                rate_limit_delay=2,
                max_retries=3,
                timeout=30,
                use_selenium=False  # Can be enabled for more complex scraping
            )
        
        super().__init__(config)
        self.sitemap_url = self.config.selectors.get("sitemap_index", "https://www.reuters.com/arc/outboundfeeds/news-sitemap-index/?outputType=xml")

    async def _scrape_articles_from_source(self, keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
        """
        Scrape articles from Reuters source.
        
        Args:
            keywords: Keywords to search for
            start_date: Start date for article search
            end_date: End date for article search
            **kwargs: Additional parameters
            
        Returns:
            List of scraped NewsArticle objects
        """
        try:
            # 1. Fetch sitemap index or article sitemaps
            all_articles_info = []
            sitemap_entries = await self._fetch_sitemap_robust(self.sitemap_url)
            
            # Identify article sitemaps (if index) or direct articles
            article_sitemaps = []
            direct_articles = []
            
            for entry in sitemap_entries:
                loc = entry['loc']
                # arc/outboundfeeds/news-sitemap typically contains articles
                # If loc ends with .xml or looks like a sub-sitemap, queue it
                if (loc.endswith('.xml') or 'sitemap' in loc.lower()) and loc != self.sitemap_url:
                    article_sitemaps.append(loc)
                elif any(p in loc for p in ['/article/', '/news/', '/world/', '/business/']):
                    direct_articles.append(entry)
            
            # If we found direct articles in the initial fetch, use them
            if direct_articles and not article_sitemaps:
                self.logger.info(f"Found {len(direct_articles)} articles directly in sitemap")
                initial_info = direct_articles
            else:
                # Limit to first few sitemaps for performance if it's an index
                process_sitemaps = article_sitemaps[:3]
                self.logger.info(f"Processing {len(process_sitemaps)} Reuters sub-sitemaps")
                initial_info = []
                
                for s_url in process_sitemaps:
                    try:
                        sub_entries = await self._fetch_sitemap_robust(s_url)
                        initial_info.extend(sub_entries)
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        self.logger.warning(f"Failed sub-sitemap {s_url}: {e}")
            
            # 2. Filter articles
            for info in initial_info:
                url = info['loc']
                title = info.get('title', '')
                date_str = info.get('date', '')
                
                # Skip non-article URLs
                if not any(pattern in url for pattern in ['/article/', '/news/', '/world/', '/business/', '/technology/']):
                    continue

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
            
            self.logger.info(f"Found {len(all_articles_info)} total candidate articles")
            
            if not all_articles_info:
                return []
            
            # Limit the number of articles to process
            max_articles = kwargs.get('max_articles', 25)
            if len(all_articles_info) > max_articles:
                all_articles_info = random.sample(all_articles_info, max_articles)
                self.logger.info(f"Limited to {max_articles} random articles for processing")
            
            # 3. Extract content
            articles = []
            for i, article_data in enumerate(all_articles_info):
                try:
                    self.logger.info(f"[{i+1}/{len(all_articles_info)}] Processing: {article_data['title'][:50]}...")
                    content = await self._extract_article_content(article_data['url'])
                    
                    published_date = datetime.utcnow()
                    if article_data['date']:
                        try:
                            published_date = datetime.strptime(article_data['date'], '%Y-%m-%d')
                        except ValueError:
                            pass
                    
                    article = self._create_article(
                        title=article_data['title'],
                        content=content,
                        url=article_data['url'],
                        published_date=published_date,
                        keywords=[]
                    )
                    articles.append(article)
                    await asyncio.sleep(2)  # Conservative rate limit for Reuters
                    
                except Exception as e:
                    self.logger.error(f"Failed article {article_data['url']}: {e}")
                    continue
            
            self.logger.info(f"Successfully scraped {len(articles)} articles from Reuters")
            return articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape Reuters: {str(e)}", source=self.source_name)


# Azure Function wrapper
async def scrape_reuters_news(keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
    """
    Azure Function entry point for Reuters news scraping.
    """
    async with ReutersNewsScraper() as scraper:
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)
