"""
Google News Scraper for Azure Functions.
Scrapes news from Google News RSS feeds with support for multiple platforms.
"""

import asyncio
import re
import sys
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

# Add parent directory to Python path
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from scrapers.base_scraper import BaseNewsScraper
from scrapers.exceptions import ScrapingError, NetworkError
from shared.models import NewsArticle, ScrapingConfig


class GoogleNewsScraper(BaseNewsScraper):
    """
    Google News Scraper implementation.
    Fetches news from Google News RSS feeds and extracts content from linked articles.
    """
    
    # Platform-specific content selectors
    PLATFORM_SELECTORS = {
        'cnbc.com': {
            'content': 'div.ArticleBody-articleBody',
            'title': 'h1.ArticleHeader-headline'
        },
        'cnn.com': {
            'content': 'div.article__content',
            'title': 'h1.pg-headline'
        },
        'kompas.com': {
            'content': 'div.read__content',
            'title': 'h1'
        },
        'tempo.co': {
            'content': 'div.detail-konten',
            'title': 'h1'
        },
        'default': {
            'content': 'article, main, div.content, div.article-content',
            'title': 'h1'
        }
    }
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize Google News scraper."""
        if config is None:
            config = ScrapingConfig(
                source_name="Google News",
                base_url="https://news.google.com",
                selectors={
                    "rss_url": "https://news.google.com/rss/search?q={query}&hl={lang}&gl={country}&ceid={country}:{lang}",
                    "item": "item",
                    "title": "title",
                    "link": "link",
                    "pubDate": "pubDate"
                },
                rate_limit_delay=2.0,
                max_retries=3,
                timeout=30
            )
        
        super().__init__(config)
        self._language = 'id'
        self._country = 'ID'

    def _build_rss_url(self, query: str) -> str:
        """Build Google News RSS URL for a query."""
        encoded_query = quote_plus(query)
        rss_template = self.config.selectors.get("rss_url")
        return rss_template.format(
            query=encoded_query,
            lang=self._language,
            country=self._country
        )

    def _parse_pubdate(self, date_str: str) -> Optional[datetime]:
        """Parse RFC 822 date format from RSS."""
        if not date_str:
            return None
        
        # RFC 822 format: "Mon, 15 Jan 2024 10:30:00 GMT"
        formats = [
            "%a, %d %b %Y %H:%M:%S %Z",
            "%a, %d %b %Y %H:%M:%S %z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None

    def _get_platform_selectors(self, url: str) -> Dict[str, str]:
        """Get content selectors based on the article URL's platform."""
        for platform, selectors in self.PLATFORM_SELECTORS.items():
            if platform in url.lower():
                return selectors
        return self.PLATFORM_SELECTORS['default']

    async def _parse_rss_feed(self, query: str) -> List[Dict]:
        """
        Parse Google News RSS feed for a query.
        
        Args:
            query: Search query
            
        Returns:
            List of article info dictionaries
        """
        try:
            rss_url = self._build_rss_url(query)
            content = await self._fetch_content(rss_url)
            
            # Parse XML
            root = ET.fromstring(content)
            channel = root.find('channel')
            
            if channel is None:
                self.logger.warning("No channel found in RSS feed")
                return []
            
            articles = []
            items = channel.findall('item')
            
            for item in items:
                try:
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    pubdate_elem = item.find('pubDate')
                    
                    if title_elem is None or link_elem is None:
                        continue
                    
                    title = title_elem.text or ""
                    link = link_elem.text or ""
                    pubdate_str = pubdate_elem.text if pubdate_elem is not None else ""
                    
                    # Google News links are redirects, try to extract actual URL
                    actual_url = await self._resolve_google_url(link)
                    
                    articles.append({
                        'title': title.strip(),
                        'url': actual_url or link,
                        'google_url': link,
                        'pubDate': pubdate_str,
                        'parsed_date': self._parse_pubdate(pubdate_str)
                    })
                    
                except Exception as e:
                    self.logger.warning(f"Failed to parse RSS item: {e}")
                    continue
            
            return articles
            
        except Exception as e:
            self.logger.error(f"Failed to parse RSS feed: {e}")
            return []

    async def _resolve_google_url(self, google_url: str) -> Optional[str]:
        """
        Resolve Google News redirect URL to actual article URL.
        
        Args:
            google_url: Google News redirect URL
            
        Returns:
            Resolved article URL or None
        """
        try:
            # Try to fetch and get final URL
            content = await self._fetch_content(google_url, use_selenium=False)
            
            # Look for canonical URL or redirect
            soup = BeautifulSoup(content, 'html.parser')
            
            # Check for canonical link
            canonical = soup.find('link', rel='canonical')
            if canonical and canonical.get('href'):
                return canonical['href']
            
            # Check for meta refresh
            meta_refresh = soup.find('meta', attrs={'http-equiv': 'refresh'})
            if meta_refresh:
                content_attr = meta_refresh.get('content', '')
                match = re.search(r'url=([^"\']+)', content_attr, re.IGNORECASE)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Could not resolve Google URL: {e}")
            return None

    async def _extract_article_content(self, url: str) -> str:
        """
        Extract article content from the actual news site.
        
        Args:
            url: Article URL
            
        Returns:
            Extracted article content
        """
        try:
            # Get platform-specific selectors
            selectors = self._get_platform_selectors(url)
            
            content = await self._fetch_content(url)
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove unwanted elements
            for unwanted in soup.select('script, style, iframe, aside, nav, footer, header, div.related, div.ads'):
                unwanted.decompose()
            
            # Try to find content using platform-specific selector
            content_div = soup.select_one(selectors['content'])
            
            if not content_div:
                # Fallback: try to find main content area
                for selector in ['article', 'main', 'div[role="main"]', 'div.content']:
                    content_div = soup.select_one(selector)
                    if content_div:
                        break
            
            if not content_div:
                self.logger.warning(f"Content not found for {url}")
                return "N/A"
            
            paragraphs = content_div.find_all(['p', 'li'])
            content_text = []
            
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 30:
                    content_text.append(text)
            
            if content_text:
                return "\n\n".join(content_text)
            
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
        Scrape articles from Google News.
        
        Args:
            keywords: Keywords to search for
            start_date: Start date for filtering
            end_date: End date for filtering
            **kwargs: Additional parameters (platform, max_articles, etc.)
            
        Returns:
            List of scraped NewsArticle objects
        """
        try:
            platform_filter = kwargs.get('platform', None)  # e.g., 'cnbc.com', 'kompas.com'
            max_articles = kwargs.get('max_articles', 20)
            
            all_articles = []
            
            for keyword in keywords:
                # Add platform to query if specified
                query = f"{keyword} site:{platform_filter}" if platform_filter else keyword
                
                self.logger.info(f"Searching Google News for: {query}")
                
                rss_articles = await self._parse_rss_feed(query)
                
                # Filter by date
                for article_data in rss_articles:
                    parsed_date = article_data.get('parsed_date')
                    
                    if parsed_date:
                        if not (start_date <= parsed_date <= end_date):
                            continue
                    
                    # Apply platform filter
                    if platform_filter and platform_filter not in article_data['url']:
                        continue
                    
                    all_articles.append(article_data)
                
                await asyncio.sleep(1.0)  # Rate limiting between queries
            
            # Limit articles
            if len(all_articles) > max_articles:
                all_articles = all_articles[:max_articles]
            
            if not all_articles:
                self.logger.info("No articles found")
                return []
            
            self.logger.info(f"Found {len(all_articles)} articles, extracting content...")
            
            # Extract content for each article
            articles = []
            for i, article_data in enumerate(all_articles):
                try:
                    self.logger.info(f"Processing {i+1}/{len(all_articles)}: {article_data['title'][:60]}...")
                    
                    content = await self._extract_article_content(article_data['url'])
                    
                    published_date = article_data.get('parsed_date') or datetime.now()
                    
                    article = self._create_article(
                        title=article_data['title'],
                        content=content,
                        url=article_data['url'],
                        published_date=published_date
                    )
                    
                    articles.append(article)
                    await asyncio.sleep(2.0)  # Rate limiting between article fetches
                    
                except Exception as e:
                    self.logger.error(f"Failed to process article: {e}")
                    continue
            
            self.logger.info(f"Successfully scraped {len(articles)} articles from Google News")
            return articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape Google News: {str(e)}", source=self.source_name)


# Azure Function wrapper
async def scrape_google_news(
    keywords: List[str], 
    start_date: datetime, 
    end_date: datetime, 
    **kwargs
) -> List[NewsArticle]:
    """
    Azure Function entry point for Google News scraping.
    
    Args:
        keywords: Keywords to search for
        start_date: Start date for filtering
        end_date: End date for filtering
        **kwargs: Additional parameters (platform, max_articles, language, country)
        
    Returns:
        List of scraped NewsArticle objects
    """
    async with GoogleNewsScraper() as scraper:
        # Set language and country if specified
        if 'language' in kwargs:
            scraper._language = kwargs['language']
        if 'country' in kwargs:
            scraper._country = kwargs['country']
        
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)
