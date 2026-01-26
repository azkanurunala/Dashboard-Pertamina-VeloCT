"""
Kontan News Scraper for Azure Functions.
Implements scraping functionality for Kontan news articles using sitemap crawling.
"""

import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import gzip
import io

from bs4 import BeautifulSoup

from .base_scraper import BaseNewsScraper
from .exceptions import ScrapingError, NetworkError, ContentExtractionError
from ..shared.models import NewsArticle, ScrapingConfig


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

    async def _fetch_sitemap_data(self, url: str) -> bytes:
        """
        Fetch and decompress sitemap data.
        
        Args:
            url: Sitemap URL
            
        Returns:
            Raw sitemap XML data
        """
        try:
            response = await self._make_request(url)
            content = await response.read()
            
            # Handle gzipped content
            if url.endswith('.gz') or content[:2] == b'\x1f\x8b':
                try:
                    with gzip.GzipFile(fileobj=io.BytesIO(content)) as f:
                        content = f.read()
                except Exception as e:
                    self.logger.warning(f"Failed to decompress gzip {url}: {e}")
            
            return content
            
        except Exception as e:
            raise NetworkError(f"Failed to fetch sitemap: {str(e)}", source=self.source_name, url=url)

    async def _get_subsitemap_urls(self, root) -> List[str]:
        """
        Get all subsitemap URLs from main sitemap.
        
        Args:
            root: XML root element
            
        Returns:
            List of subsitemap URLs
        """
        namespaces = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = []
        
        # Get all <loc> elements that might be sub-sitemaps
        for loc in root.findall('.//sm:loc', namespaces):
            if loc.text:
                href = loc.text.strip()
                # Include URLs that end with .xml or .xml.gz or contain 'sitemap' or '/sitemaps/'
                if (href.endswith('.xml') or href.endswith('.xml.gz') or 
                    'sitemap' in href or '/sitemaps/' in href):
                    urls.append(href)
        
        # Deduplicate while preserving order
        seen = set()
        unique_urls = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        return unique_urls

    def _extract_article_info_from_sitemap(self, url_tag, namespaces: Dict[str, str]) -> Optional[Dict[str, str]]:
        """
        Extract article information from sitemap URL entry.
        
        Args:
            url_tag: XML URL element
            namespaces: XML namespaces
            
        Returns:
            Dictionary with article info or None if invalid
        """
        try:
            # Extract URL
            loc_element = url_tag.find('sm:loc', namespaces)
            if loc_element is None or not loc_element.text:
                return None
            
            url = loc_element.text.strip()
            
            # Extract news-specific information
            news_namespaces = {'news': 'http://www.google.com/schemas/sitemap-news/0.9'}
            news_element = url_tag.find('news:news', news_namespaces)
            
            title = ""
            date = ""
            keywords = ""
            
            if news_element is not None:
                title_element = news_element.find('news:title', news_namespaces)
                date_element = news_element.find('news:publication_date', news_namespaces)
                keywords_element = news_element.find('news:keywords', news_namespaces)
                
                if title_element is not None and title_element.text:
                    title = title_element.text.strip()
                
                if date_element is not None and date_element.text:
                    date_raw = date_element.text.strip()
                    # Extract date part before 'T' if present
                    date = date_raw.split('T')[0].strip() if 'T' in date_raw else date_raw.strip()
                
                if keywords_element is not None and keywords_element.text:
                    keywords = keywords_element.text.strip()
            
            # Generate title from URL if not available
            if not title:
                title = url.rstrip('/').split('/')[-1].replace('-', ' ').title()
            
            return {
                'title': title,
                'url': url,
                'date': date or '-',
                'keywords': keywords
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to extract article info: {e}")
            return None

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

    async def _scrape_from_sitemaps(self, keywords: List[str], start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Scrape articles from Kontan sitemaps.
        
        Args:
            keywords: Keywords to filter articles
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            List of article data dictionaries
        """
        try:
            # Fetch main sitemap
            main_sitemap_data = await self._fetch_sitemap_data(self.sitemap_url)
            root = ET.fromstring(main_sitemap_data)
            
            # Get all subsitemap URLs
            subsitemap_urls = await self._get_subsitemap_urls(root)
            self.logger.info(f"Found {len(subsitemap_urls)} subsitemaps")
            
            all_articles = []
            namespaces = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            # Process each subsitemap
            for i, subsitemap_url in enumerate(subsitemap_urls):
                try:
                    self.logger.debug(f"Processing subsitemap {i+1}/{len(subsitemap_urls)}: {subsitemap_url}")
                    
                    # Fetch subsitemap data
                    subsitemap_data = await self._fetch_sitemap_data(subsitemap_url)
                    subroot = ET.fromstring(subsitemap_data)
                    
                    # Extract articles from this subsitemap
                    for url_tag in subroot.findall('.//sm:url', namespaces):
                        article_info = self._extract_article_info_from_sitemap(url_tag, namespaces)
                        if not article_info or not article_info.get('url'):
                            continue
                        
                        # Filter by keywords if provided
                        if keywords:
                            title = article_info.get('title', '').lower()
                            keywords_text = article_info.get('keywords', '').lower()
                            url_text = article_info.get('url', '').lower()
                            
                            # Check if any keyword matches
                            keyword_match = False
                            for keyword in keywords:
                                keyword_lower = keyword.lower()
                                if (keyword_lower in title or 
                                    keyword_lower in keywords_text or 
                                    keyword_lower in url_text):
                                    keyword_match = True
                                    break
                            
                            if not keyword_match:
                                continue
                        
                        all_articles.append(article_info)
                    
                    # Rate limiting between subsitemaps
                    await asyncio.sleep(0.15)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process subsitemap {subsitemap_url}: {e}")
                    continue
            
            self.logger.info(f"Found {len(all_articles)} articles across all sitemaps")
            
            # Filter by date if specified
            if start_date and end_date:
                filtered_articles = []
                for article in all_articles:
                    if article['date'] and article['date'] != '-':
                        try:
                            article_date = datetime.strptime(article['date'], '%Y-%m-%d')
                            if start_date <= article_date <= end_date:
                                filtered_articles.append(article)
                        except ValueError:
                            # Include articles with unparseable dates
                            filtered_articles.append(article)
                    else:
                        # Include articles without dates
                        filtered_articles.append(article)
                
                all_articles = filtered_articles
                self.logger.info(f"Date filtering resulted in {len(all_articles)} articles")
            
            return all_articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape from sitemaps: {str(e)}", source=self.source_name)

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
            # Get articles from sitemaps
            sitemap_articles = await self._scrape_from_sitemaps(keywords, start_date, end_date)
            
            if not sitemap_articles:
                return []
            
            # Limit articles for performance
            max_articles = kwargs.get('max_articles', 25)
            if len(sitemap_articles) > max_articles:
                sitemap_articles = sitemap_articles[:max_articles]
                self.logger.info(f"Limited to {max_articles} articles for processing")
            
            # Extract content for each article
            articles = []
            for i, article_data in enumerate(sitemap_articles):
                try:
                    self.logger.info(f"Processing article {i+1}/{len(sitemap_articles)}: {article_data['title'][:50]}...")
                    
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
                        keywords=article_data.get('keywords', '').split(',') if article_data.get('keywords') else []
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