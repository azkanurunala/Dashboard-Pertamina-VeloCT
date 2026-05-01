"""
Tempo News Scraper for Azure Functions.
Implements scraping functionality for Tempo news articles using multiple category sitemaps.
"""

import asyncio
import re
import sys
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

# Add parent directory to Python path for absolute imports in Azure Functions
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from scrapers.base_scraper import BaseNewsScraper
from scrapers.exceptions import ScrapingError, NetworkError, ContentExtractionError
from shared.models import NewsArticle, ScrapingConfig


class TempoNewsScraper(BaseNewsScraper):
    """
    Tempo News Scraper implementation.
    Scrapes news articles from Tempo using multiple category sitemaps.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize Tempo scraper with default configuration."""
        if config is None:
            config = ScrapingConfig(
                source_name="Tempo",
                base_url="https://www.tempo.co",
                selectors={
                    "sitemaps": [
                        "https://www.tempo.co/politik-sitemap.xml",
                        "https://www.tempo.co/hukum-sitemap.xml",
                        "https://www.tempo.co/ekonomi-sitemap.xml",
                        "https://www.tempo.co/lingkungan-sitemap.xml",
                        "https://www.tempo.co/wawancara-sitemap.xml",
                        "https://www.tempo.co/sains-sitemap.xml",
                        "https://www.tempo.co/investigasi-sitemap.xml",
                        "https://www.tempo.co/cekfakta-sitemap.xml",
                        "https://www.tempo.co/kolom-sitemap.xml",
                        "https://www.tempo.co/hiburan-sitemap.xml",
                        "https://www.tempo.co/internasional-sitemap.xml",
                        "https://www.tempo.co/otomotif-sitemap.xml",
                        "https://www.tempo.co/olahraga-sitemap.xml",
                        "https://www.tempo.co/sepakbola-sitemap.xml",
                        "https://www.tempo.co/digital-sitemap.xml",
                        "https://www.tempo.co/gaya-hidup-sitemap.xml"
                    ],
                    "article_content": "div#isi, div.detail-content, article, div.detail-area",
                    "title": "h1",
                    "content": "p",
                    "unwanted": "script, style, iframe, figure, aside, nav, div[class*='ad'], div[class*='iklan'], div[class*='share'], div[class*='related'], div[class*='author'], div[class*='penulis'], div.text-neutral-900"
                },
                rate_limit_delay=0.5,
                max_retries=3,
                timeout=25
            )
        
        super().__init__(config)
        self.sitemap_urls = self.config.selectors.get("sitemaps", [])
        self.sitemap_url = self.sitemap_urls[0] if self.sitemap_urls else ""

    def _extract_keywords_from_url(self, url: str) -> List[str]:
        """
        Extract keywords from URL path for matching.
        
        Args:
            url: Article URL
            
        Returns:
            List of keywords extracted from URL
        """
        try:
            path = urlparse(url).path
            parts = path.strip('/').split('/')
            if len(parts) < 2:
                return []
            
            slug = parts[-1]
            # Remove date patterns from slug
            slug = re.sub(r'-\d{8,}$', '', slug)
            
            # Split by hyphens and filter short words
            keywords = [k.lower() for k in slug.split('-') if len(k) >= 3]
            return keywords
            
        except Exception:
            return []

    def _check_keyword_match(self, url_keywords: List[str], search_keyword: str) -> bool:
        """
        Check if search keyword matches any URL keywords.
        
        Args:
            url_keywords: Keywords extracted from URL
            search_keyword: Keyword to search for
            
        Returns:
            True if keyword matches
        """
        search_lower = search_keyword.lower()
        return any(search_lower in kw for kw in url_keywords)

    def _clean_tempo_text(self, text: str) -> str:
        """
        Clean Tempo-specific text patterns.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        if not text or text == 'N/A':
            return text
        
        # Tempo-specific patterns to remove
        patterns = [
            r'Baca berita.*?klik di sini',
            r'Scroll ke bawah.*',
            r'Lulus dari Jurusan.*?(hak asasi manusia)?',
            r'This is breaking news.*',
            r'CNN\'s\s+[\w\s,]+contributed to this report\.?',
            r'This story.*contributed to this report\.?'
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Clean up extra whitespace
        text = re.sub(r' {2,}', ' ', text).strip()
        
        return text

    async def _scrape_articles_from_source(self, keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
        """
        Scrape articles from Tempo source.
        
        Args:
            keywords: Keywords to search for
            start_date: Start date for article search
            end_date: End date for article search
            **kwargs: Additional parameters
            
        Returns:
            List of scraped NewsArticle objects
        """
        try:
            # Scrape from all sitemaps using base class robust mechanism
            all_articles_info = []
            
            for sitemap_url in self.sitemap_urls:
                try:
                    sitemap_articles = await self._fetch_sitemap_robust(sitemap_url)
                    
                    # Process and filter articles from this sitemap
                    for info in sitemap_articles:
                        url = info['loc']
                        title = info.get('title', '')
                        date_str = info.get('date', '')
                        
                        # Extract keywords from URL for matching
                        url_keywords = self._extract_keywords_from_url(url)
                        
                        # Filter by keywords if provided
                        if keywords:
                            keyword_match = False
                            for keyword in keywords:
                                k_lower = keyword.lower()
                                if self._check_keyword_match(url_keywords, keyword) or \
                                   (title and k_lower in title.lower()):
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
                        
                        # Store for processing
                        all_articles_info.append({
                            'title': title or ' '.join([k.capitalize() for k in url_keywords]),
                            'url': url,
                            'date': date_str
                        })
                        
                    self.logger.info(f"Found {len(sitemap_articles)} raw entries from {sitemap_url}")
                    
                    # Rate limiting between sitemaps
                    await asyncio.sleep(0.2)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process sitemap {sitemap_url}: {e}")
                    continue
            
            self.logger.info(f"Found {len(all_articles_info)} total articles after filtering entries from Tempo")
            
            if not all_articles_info:
                return []
            
            # Remove duplicates based on URL
            unique_articles = {}
            for art in all_articles_info:
                unique_articles[art['url']] = art
            all_articles_info = list(unique_articles.values())
            
            # Limit articles for performance
            max_articles = kwargs.get('max_articles', 25)
            if len(all_articles_info) > max_articles:
                all_articles_info = all_articles_info[:max_articles]
                self.logger.info(f"Limited to {max_articles} articles for processing")
            
            # Compile keyword patterns for post-filter on title+content (case-insensitive,
            # no word boundary — mirrors src/code_scrapping/tempo.py behaviour)
            keyword_patterns = []
            for kw in (keywords or []):
                kw_lower = (kw or "").lower().lstrip()
                if kw_lower:
                    keyword_patterns.append(re.compile(re.escape(kw_lower), re.IGNORECASE))

            # Extract content for each article
            articles = []
            for i, article_data in enumerate(all_articles_info):
                try:
                    self.logger.info(f"Processing article {i+1}/{len(all_articles_info)}: {article_data['title'][:60]}...")

                    # Extract content
                    content = await self._extract_article_content(article_data['url'])

                    if keyword_patterns:
                        title_text = article_data['title'] or ""
                        content_text = content or ""
                        if not any(
                            p.search(title_text) or p.search(content_text)
                            for p in keyword_patterns
                        ):
                            self.logger.debug(
                                f"Skip: keywords not found in title/content: {title_text!r}"
                            )
                            continue

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
                        keywords=[]  # Will be populated by keyword filtering in base class
                    )
                    
                    articles.append(article)
                    
                    # Rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    self.logger.error(f"Failed to process article {article_data['url']}: {e}")
                    continue
            
            self.logger.info(f"Successfully scraped {len(articles)} articles from Tempo")
            return articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape Tempo articles: {str(e)}", source=self.source_name)


# Azure Function wrapper
async def scrape_tempo_news(keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
    """
    Azure Function entry point for Tempo news scraping.
    
    Args:
        keywords: Keywords to search for
        start_date: Start date for article search
        end_date: End date for article search
        **kwargs: Additional parameters
        
    Returns:
        List of scraped NewsArticle objects
    """
    async with TempoNewsScraper() as scraper:
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)