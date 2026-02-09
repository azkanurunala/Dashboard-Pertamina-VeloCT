"""
Base scraper class with common functionality for all news scrapers.
Implements rate limiting, retry logic, error handling, and standardized article extraction.
"""

import asyncio
import logging
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set
from urllib.parse import urljoin, urlparse
import aiohttp
import gzip
import io
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

import sys
import os

# Add parent directory to Python path for absolute imports in Azure Functions
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from shared.models import NewsArticle, ScrapingConfig
from shared.interfaces import INewsScraperFunction
from scrapers.exceptions import ScrapingError, RateLimitError, ValidationError, NetworkError, ContentExtractionError

# Selenium helper for fallback
try:
    from shared.selenium_helper import fetch_with_selenium, fetch_sitemap_with_selenium
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    fetch_with_selenium = None
    fetch_sitemap_with_selenium = None


class BaseNewsScraper(INewsScraperFunction, ABC):
    """
    Abstract base class for all news scrapers.
    Provides common functionality including rate limiting, retry logic, and article validation.
    """
    
    def __init__(self, config: ScrapingConfig):
        """
        Initialize the base scraper with configuration.
        
        Args:
            config: Scraping configuration including source details and limits
        """
        self.config = config
        self.logger = logging.getLogger(f"scraper.{config.source_name}")
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_request_time = 0.0
        self._request_count = 0
        self._rate_limit_window_start = time.time()
        self._failed_urls: Set[str] = set()
        
        # Default headers
        self._default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
        self._default_headers.update(config.headers)
        
        # Selenium fallback settings
        self._use_selenium_fallback = os.getenv("SCRAPER_USE_SELENIUM", "true").lower() == "true"
        self._aiohttp_failed = False  # Track if aiohttp consistently fails

    @property
    def source_name(self) -> str:
        """Get the name of the news source."""
        return self.config.source_name

    @property
    def base_url(self) -> str:
        """Get the base URL of the news source."""
        return self.config.base_url

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self):
        """Ensure HTTP session is initialized."""
        if self._session is None or self._session.closed:
            # Force IPv4 and disable SSL verification for stability
            import socket
            connector = aiohttp.TCPConnector(
                family=socket.AF_INET,
                ssl=False, 
                limit=10, 
                limit_per_host=5
            )
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(
                headers=self._default_headers,
                timeout=timeout,
                connector=connector
            )

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def handle_rate_limiting(self) -> None:
        """
        Handle rate limiting by implementing appropriate delays.
        Uses both time-based and request-count-based rate limiting.
        """
        current_time = time.time()
        
        # Time-based rate limiting
        time_since_last = current_time - self._last_request_time
        if time_since_last < self.config.rate_limit_delay:
            delay = self.config.rate_limit_delay - time_since_last
            self.logger.debug(f"Rate limiting: waiting {delay:.2f}s")
            await asyncio.sleep(delay)
        
        # Request count-based rate limiting (60 requests per minute)
        window_duration = 60.0  # 1 minute
        if current_time - self._rate_limit_window_start >= window_duration:
            self._request_count = 0
            self._rate_limit_window_start = current_time
        
        if self._request_count >= 60:  # Max 60 requests per minute
            wait_time = window_duration - (current_time - self._rate_limit_window_start)
            if wait_time > 0:
                self.logger.info(f"Request limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self._request_count = 0
                self._rate_limit_window_start = time.time()
        
        self._last_request_time = time.time()
        self._request_count += 1

    async def _create_session(self) -> aiohttp.ClientSession:
        """Create a new aiohttp session with optimized settings for Azure Environment."""
        if self._session and not self._session.closed:
            return self._session
            
        import socket
        # Force IPv4 and disable SSL verification for stability in Azure Sandbox
        # Use a smaller pool limit to avoid overwhelming the restricted environment
        connector = aiohttp.TCPConnector(
            family=socket.AF_INET,
            ssl=False,
            limit=5,
            force_close=True,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(
            total=self.config.timeout,
            connect=10,
            sock_connect=10,
            sock_read=self.config.timeout
        )
        
        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self._default_headers
        )
        return self._session

    async def _make_request(self, url: str, method: str = 'GET', **kwargs) -> aiohttp.ClientResponse:
        """
        Make an HTTP request with retry logic and error handling.
        
        Args:
            url: URL to request
            method: HTTP method
            **kwargs: Additional request parameters
            
        Returns:
            HTTP response
            
        Raises:
            NetworkError: If request fails after all retries
            RateLimitError: If rate limited by server
        """
        await self._ensure_session()
        
        for attempt in range(self.config.max_retries + 1):
            response = None
            try:
                self.logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                response = await self._session.request(method, url, **kwargs)
                
                # Handle rate limiting responses
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    await response.release()
                    raise RateLimitError(
                        f"Rate limited by server",
                        retry_after=retry_after,
                        source=self.source_name
                    )
                
                # Handle other HTTP errors
                if response.status >= 400:
                    if attempt < self.config.max_retries:
                        delay = 2 ** attempt  # Exponential backoff
                        self.logger.warning(f"HTTP {response.status} for {url}, retrying in {delay}s")
                        await response.release()
                        await asyncio.sleep(delay)
                        continue
                    else:
                        status = response.status
                        await response.release()
                        raise NetworkError(
                            f"HTTP request failed with status {status}",
                            status_code=status,
                            source=self.source_name,
                            url=url
                        )
                
                return response
                
            except aiohttp.ClientError as e:
                if response:
                    await response.release()
                if attempt < self.config.max_retries:
                    delay = 2 ** attempt
                    self.logger.warning(f"Request failed: {e}, retrying in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    raise NetworkError(
                        f"Network request failed: {str(e)}",
                        source=self.source_name,
                        url=url
                    )
            except RateLimitError:
                raise
            except Exception as e:
                if response:
                    await response.release()
                if attempt < self.config.max_retries:
                    delay = 2 ** attempt
                    self.logger.warning(f"Unexpected error: {e}, retrying in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    raise ScrapingError(
                        f"Request failed after {self.config.max_retries} retries: {str(e)}",
                        source=self.source_name,
                        url=url
                    )

    async def _fetch_content(self, url: str, use_selenium: bool = False) -> str:
        """
        Fetch HTML content from a URL with Selenium fallback.
        
        Args:
            url: URL to fetch
            use_selenium: Force Selenium usage
            
        Returns:
            HTML content as string
            
        Raises:
            NetworkError: If content cannot be fetched
        """
        if url in self._failed_urls:
            raise NetworkError(f"URL previously failed", source=self.source_name, url=url)
        
        # Use Selenium directly if forced or if aiohttp has been failing
        if use_selenium or (self._aiohttp_failed and self._use_selenium_fallback and SELENIUM_AVAILABLE):
            return await self._fetch_content_selenium(url)
        
        try:
            response = await self._make_request(url)
            try:
                content = await response.text()
                self.logger.debug(f"Fetched {len(content)} characters from {url}")
                return content
            finally:
                await response.release()
        except Exception as e:
            # Try Selenium fallback if available and enabled
            if self._use_selenium_fallback and SELENIUM_AVAILABLE:
                self.logger.info(f"aiohttp failed for {url}, trying Selenium fallback...")
                self._aiohttp_failed = True
                try:
                    return await self._fetch_content_selenium(url)
                except Exception as selenium_error:
                    self.logger.error(f"Selenium fallback also failed: {selenium_error}")
                    self._failed_urls.add(url)
                    raise NetworkError(
                        f"Both aiohttp and Selenium failed: {str(e)}",
                        source=self.source_name,
                        url=url
                    )
            else:
                self._failed_urls.add(url)
                raise
    
    async def _fetch_content_selenium(self, url: str) -> str:
        """
        Fetch content using Selenium.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content
        """
        if not SELENIUM_AVAILABLE or fetch_with_selenium is None:
            raise NetworkError(
                "Selenium is not available",
                source=self.source_name,
                url=url
            )
        
        try:
            self.logger.info(f"Fetching with Selenium: {url}")
            content = await fetch_with_selenium(url)
            self.logger.debug(f"Selenium fetched {len(content)} characters from {url}")
            return content
        except Exception as e:
            raise NetworkError(
                f"Selenium fetch failed: {str(e)}",
                source=self.source_name,
                url=url
            )
    
    async def _fetch_sitemap_selenium(self, url: str) -> str:
        """
        Fetch sitemap using Selenium.
        
        Args:
            url: Sitemap URL
            
        Returns:
            Sitemap XML content
        """
        if not SELENIUM_AVAILABLE or fetch_sitemap_with_selenium is None:
            raise NetworkError(
                "Selenium is not available",
                source=self.source_name,
                url=url
            )
        
        try:
            self.logger.info(f"Fetching sitemap with Selenium: {url}")
            content = await fetch_sitemap_with_selenium(url)
            self.logger.debug(f"Selenium fetched sitemap ({len(content)} chars) from {url}")
            return content
        except Exception as e:
            raise NetworkError(
                f"Selenium sitemap fetch failed: {str(e)}",
                source=self.source_name,
                url=url
            )

    async def _fetch_sitemap_robust(self, url: str, _depth: int = 0) -> List[Dict[str, str]]:
        """
        Centralized robust sitemap fetching and parsing.
        Handles:
        1. Gzip compression (automatic or manual)
        2. XML format (standard)
        3. HTML format fallback (some sites return HTML tables for sitemaps)
        4. Malformed XML handling via BeautifulSoup
        5. Sitemap Index support (recursive discovery)
        6. Diagnostic saving of failed parsing attempts
        
        Args:
            url: Sitemap URL
            _depth: Internal recursion depth for indices
            
        Returns:
            List of dictionaries containing article info (loc, title, date)
        """
        if _depth > 1:  # Limit recursion to 1 level for index -> sub-sitemap
            return []
        
        content = None
        
        # 1. Fetch content
        try:
            headers = self._default_headers.copy()
            headers['Accept'] = 'application/xml,application/xhtml+xml,text/html;q=0.9,text/xml;q=0.8'
            
            response = await self._make_request(url, headers=headers)
            try:
                content_bytes = await response.read()
                
                # Handle potential manual gzip decompression if headers are missing
                if content_bytes.startswith(b'\x1f\x8b'):
                    try:
                        content_bytes = gzip.decompress(content_bytes)
                        self.logger.debug("Manually decompressed Gzip content")
                    except Exception as e:
                        self.logger.warning(f"Manual Gzip decompression failed: {e}")
                
                content = content_bytes.decode('utf-8', errors='replace')
            finally:
                await response.release()
        except Exception as e:
            self.logger.error(f"Failed to fetch sitemap {url}: {e}")
            if self._use_selenium_fallback and SELENIUM_AVAILABLE:
                self.logger.info("Trying Selenium fallback for sitemap...")
                try:
                    content = await self._fetch_sitemap_selenium(url)
                except Exception as se:
                    self.logger.error(f"Sitemap Selenium fallback failed: {se}")
                    return []
            else:
                return []

        if not content:
            return []

        # 2. Parse Content - Step 1: Standard ElementTree
        articles = []
        try:
            # Strip potential BOM or whitespace
            clean_content = content.strip()
            root = ET.fromstring(clean_content)
            
            # Map common sitemap namespaces
            namespaces = {
                'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                'news': 'http://www.google.com/schemas/sitemap-news/0.9',
                'image': 'http://www.google.com/schemas/sitemap-image/1.1',
                'video': 'http://www.google.com/schemas/sitemap-video/1.1'
            }
            
            # Handle default namespace if present
            if 'http://www.sitemaps.org/schemas/sitemap/0.9' in clean_content:
                url_tags = root.findall('.//sm:url', namespaces) if 'sm' in namespaces else root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url')
            else:
                url_tags = root.findall('.//url')
            
            if url_tags:
                for url_tag in url_tags:
                    info = self._extract_article_info_robust(url_tag, namespaces)
                    if info:
                        articles.append(info)
                
                if articles:
                    self.logger.info(f"Successfully parsed {len(articles)} articles using ElementTree")
                    return articles
            
            # 2.2 Parse Content - Step 1.1: Sitemap Index if no URLs found
            if 'http://www.sitemaps.org/schemas/sitemap/0.9' in clean_content:
                sitemap_tags = root.findall('.//sm:sitemap', namespaces) if 'sm' in namespaces else root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap')
            else:
                sitemap_tags = root.findall('.//sitemap')
            
            if sitemap_tags:
                self.logger.info(f"Found {len(sitemap_tags)} potential sub-sitemaps in index")
                results = []
                # Only process the first few sub-sitemaps to stay recent and avoid over-fetching
                processed_count = 0
                for s_tag in sitemap_tags:
                    loc_node = s_tag.find('loc') or s_tag.find('sm:loc', namespaces or {})
                    if loc_node is not None:
                        loc = loc_node.get_text() if hasattr(loc_node, 'get_text') else loc_node.text
                        if loc:
                            loc = loc.strip()
                            # Basic filtering: skip non-xml (unless index)
                            # Most sub-sitemaps follow a year/month pattern or say 'sitemap'
                            self.logger.info(f"Recursing into sub-sitemap: {loc}")
                            sub_articles = await self._fetch_sitemap_robust(loc, _depth + 1)
                            results.extend(sub_articles)
                            processed_count += 1
                            if processed_count >= 3: # Limit to top 3 sub-sitemaps
                                break
                
                if results:
                    return results
        except Exception as e:
            self.logger.debug(f"ElementTree parsing failed for {url}: {e}. Trying BeautifulSoup (XML)...")

        # 3. Parse Content - Step 2: BeautifulSoup (XML)
        try:
            soup = BeautifulSoup(content, 'xml')
            url_tags = soup.find_all('url')
            if url_tags:
                for url_tag in url_tags:
                    info = self._extract_article_info_robust(url_tag)
                    if info:
                        articles.append(info)
                
                if articles:
                    self.logger.info(f"Successfully parsed {len(articles)} articles using BeautifulSoup (XML)")
                    return articles
        except Exception as e:
            self.logger.debug(f"BeautifulSoup (XML) parsing failed for {url}: {e}. Trying BeautifulSoup (HTML)...")

        # 4. Parse Content - Step 3: BeautifulSoup (HTML) - Fallback for "Pretty" sitemaps
        try:
            soup = BeautifulSoup(content, 'html.parser')
            # Look for <table> or <ul> that might contain links
            rows = soup.find_all(['tr', 'li'])
            for row in rows:
                link_tag = row.find('a', href=True)
                if link_tag:
                    loc = urljoin(url, link_tag['href'])
                    title = link_tag.get_text(strip=True)
                    
                    # Try to find a date in sibling cells/elements
                    date_val = ""
                    # Simple heuristic: find text that looks like a date (YYYY-MM-DD or similar)
                    date_match = re.search(r'\d{4}-\d{2}-\d{2}', row.get_text())
                    if date_match:
                        date_val = date_match.group(0)
                        
                    articles.append({
                        'loc': loc,
                        'title': title,
                        'date': date_val
                    })
            
            if articles:
                self.logger.info(f"Successfully extracted {len(articles)} links using HTML fallback for {url}")
                return articles
        except Exception as e:
            self.logger.error(f"All parsing stages failed for {url}: {e}")

        # 5. Diagnostic: Save failed sitemap
        self._save_failed_sitemap(url, content)
        return []

    def _extract_article_info_robust(self, url_tag, namespaces: Optional[Dict[str, str]] = None) -> Optional[Dict[str, str]]:
        """
        Robustly extract loc, title, and date from a sitemap <url> tag.
        Handles various namespaces and tag names.
        
        Args:
            url_tag: XML element or BS4 tag
            namespaces: Optional namespace map for ElementTree
            
        Returns:
            Dictionary with loc, title, date or None
        """
        try:
            loc = ""
            title = ""
            date = ""
            
            # Extract Loc
            if hasattr(url_tag, 'find'): # BS4 or ElementTree
                loc_node = url_tag.find('loc') or url_tag.find('sm:loc', namespaces or {})
                if loc_node is not None:
                    loc = loc_node.get_text() if hasattr(loc_node, 'get_text') else loc_node.text
            
            if not loc:
                return None
                
            loc = loc.strip()
            
            # Extract Title and Date (News Search)
            # Support both ET and BS4
            news_nodes = []
            if hasattr(url_tag, 'find_all'): # BS4
                news_nodes = url_tag.find_all('news:news') + url_tag.find_all('news')
            elif hasattr(url_tag, 'findall'): # ElementTree
                news_nodes = url_tag.findall('.//news:news', namespaces or {}) + url_tag.findall('.//news')
                
            for news in news_nodes:
                # Title
                title_node = news.find('news:title', namespaces or {}) or news.find('title')
                if title_node is not None:
                    title = title_node.get_text() if hasattr(title_node, 'get_text') else title_node.text
                
                # Date
                date_node = news.find('news:publication_date', namespaces or {}) or news.find('publication_date')
                if date_node is not None:
                    date_val = date_node.get_text() if hasattr(date_node, 'get_text') else date_node.text
                    if date_val:
                        # Extract YYYY-MM-DD
                        match = re.search(r'\d{4}-\d{2}-\d{2}', date_val)
                        if match:
                            date = match.group(0)

            # Fallback for date: lastmod
            if not date:
                lastmod_node = url_tag.find('lastmod') or url_tag.find('sm:lastmod', namespaces or {})
                if lastmod_node is not None:
                    lastmod_val = lastmod_node.get_text() if hasattr(lastmod_node, 'get_text') else lastmod_node.text
                    if lastmod_val:
                        match = re.search(r'\d{4}-\d{2}-\d{2}', lastmod_val)
                        if match:
                            date = match.group(0)

            return {
                'loc': loc,
                'title': title.strip() if title else "",
                'date': date
            }
        except Exception as e:
            self.logger.warning(f"Error extracting info from sitemap tag: {e}")
            return None

    def _save_failed_sitemap(self, url: str, content: str):
        """Save failed sitemap content for diagnostic purposes."""
        try:
            diag_dir = os.path.join(os.getcwd(), 'failed_sitemaps')
            if not os.path.exists(diag_dir):
                os.makedirs(diag_dir)
            
            filename = re.sub(r'[^\w\-_]', '_', url) + f"_{int(time.time())}.txt"
            filepath = os.path.join(diag_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"URL: {url}\n")
                f.write(f"TIMESTAMP: {datetime.now().isoformat()}\n")
                f.write("-" * 40 + "\n")
                f.write(content)
                
            self.logger.info(f"Saved failed sitemap diagnostic to {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to save diagnostic sitemap: {e}")

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text content.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common unwanted patterns
        patterns_to_remove = [
            r'Sign up for.*?newsletter',
            r'Subscribe to.*?updates',
            r'Follow us on.*?social media',
            r'Advertisement\s*',
            r'Sponsored content\s*',
            r'Read more:.*',
            r'Related:.*',
            r'Also read:.*',
            r'Continue reading.*',
        ]
        
        for pattern in patterns_to_remove:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove excessive punctuation
        text = re.sub(r'[.]{3,}', '...', text)
        text = re.sub(r'[-]{3,}', '---', text)
        
        return text.strip()

    def _extract_text_from_element(self, element, min_length: int = 10) -> List[str]:
        """
        Extract meaningful text from HTML elements.
        
        Args:
            element: BeautifulSoup element
            min_length: Minimum length for text to be considered meaningful
            
        Returns:
            List of extracted text strings
        """
        if not element:
            return []
        
        # Remove unwanted elements
        for unwanted in element.find_all(['script', 'style', 'nav', 'header', 'footer', 
                                         'aside', 'iframe', 'noscript']):
            unwanted.decompose()
        
        # Remove elements with unwanted classes/ids
        unwanted_patterns = [
            'ad', 'advertisement', 'promo', 'social', 'share', 'comment',
            'related', 'sidebar', 'navigation', 'menu', 'footer', 'header'
        ]
        
        for pattern in unwanted_patterns:
            for elem in element.find_all(attrs={'class': re.compile(pattern, re.I)}):
                elem.decompose()
            for elem in element.find_all(attrs={'id': re.compile(pattern, re.I)}):
                elem.decompose()
        
        # Extract text from paragraphs and headings
        text_elements = []
        for tag in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']:
            for elem in element.find_all(tag):
                text = self._clean_text(elem.get_text())
                if len(text) >= min_length:
                    text_elements.append(text)
        
        return text_elements

    async def validate_article(self, article: NewsArticle) -> bool:
        """
        Validate a scraped article for completeness and quality.
        
        Args:
            article: Article to validate
            
        Returns:
            True if article is valid, False otherwise
        """
        try:
            # Check required fields
            if not article.title or not article.title.strip():
                raise ValidationError("Title is empty", field="title")
            
            if not article.content or not article.content.strip():
                raise ValidationError("Content is empty", field="content")
            
            if not article.url or not article.url.strip():
                raise ValidationError("URL is empty", field="url")
            
            if not article.source or not article.source.strip():
                raise ValidationError("Source is empty", field="source")
            
            # Validate URL format
            parsed_url = urlparse(article.url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValidationError("Invalid URL format", field="url", value=article.url)
            
            # Check content quality
            if len(article.content) < 100:
                raise ValidationError("Content too short", field="content", 
                                    value=f"Length: {len(article.content)}")
            
            # Check for spam indicators
            spam_indicators = [
                'click here', 'buy now', 'limited time', 'act now',
                'free trial', 'no obligation', 'risk free'
            ]
            content_lower = article.content.lower()
            spam_count = sum(1 for indicator in spam_indicators if indicator in content_lower)
            if spam_count >= 3:
                raise ValidationError("Content appears to be spam", field="content")
            
            # Validate date
            if article.published_date > datetime.utcnow() + timedelta(days=1):
                raise ValidationError("Published date is in the future", field="published_date",
                                    value=article.published_date.isoformat())
            
            return True
            
        except ValidationError as e:
            self.logger.warning(f"Article validation failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected validation error: {e}")
            return False

    def _create_article(self, title: str, content: str, url: str, 
                       published_date: datetime, **kwargs) -> NewsArticle:
        """
        Create a NewsArticle instance with standardized data.
        
        Args:
            title: Article title
            content: Article content
            url: Article URL
            published_date: Publication date
            **kwargs: Additional article attributes
            
        Returns:
            NewsArticle instance
        """
        # Clean and validate inputs
        title = self._clean_text(title)
        content = self._clean_text(content)
        
        # Ensure URL is absolute
        if not url.startswith(('http://', 'https://')):
            url = urljoin(self.base_url, url)
        
        return NewsArticle(
            title=title,
            content=content,
            url=url,
            source=self.source_name,
            published_date=published_date,
            scraped_date=datetime.utcnow(),
            keywords=kwargs.get('keywords', []),
            language=kwargs.get('language', 'en'),
            author=kwargs.get('author'),
            category=kwargs.get('category')
        )

    def _filter_by_keywords(self, articles: List[NewsArticle], 
                           keywords: List[str]) -> List[NewsArticle]:
        """
        Filter articles by keywords.
        
        Args:
            articles: List of articles to filter
            keywords: Keywords to search for
            
        Returns:
            Filtered list of articles
        """
        if not keywords:
            return articles
        
        filtered_articles = []
        keyword_patterns = [re.compile(r'\b' + re.escape(kw.lower()) + r'\b') 
                           for kw in keywords]
        
        for article in articles:
            # Search in title and content
            search_text = f"{article.title} {article.content}".lower()
            
            # Check if any keyword matches
            if any(pattern.search(search_text) for pattern in keyword_patterns):
                # Add matching keywords to article
                matching_keywords = []
                for kw, pattern in zip(keywords, keyword_patterns):
                    if pattern.search(search_text):
                        matching_keywords.append(kw)
                
                article.keywords.extend(matching_keywords)
                article.keywords = list(set(article.keywords))  # Remove duplicates
                filtered_articles.append(article)
        
        return filtered_articles

    def _filter_by_date_range(self, articles: List[NewsArticle], 
                             start_date: datetime, end_date: datetime) -> List[NewsArticle]:
        """
        Filter articles by date range.
        
        Args:
            articles: List of articles to filter
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            Filtered list of articles
        """
        return [
            article for article in articles
            if start_date <= article.published_date <= end_date
        ]

    @abstractmethod
    async def _scrape_articles_from_source(self, keywords: List[str], 
                                          start_date: datetime, 
                                          end_date: datetime,
                                          **kwargs) -> List[NewsArticle]:
        """
        Abstract method to scrape articles from the specific news source.
        Must be implemented by each scraper subclass.
        
        Args:
            keywords: Keywords to search for
            start_date: Start date for article search
            end_date: End date for article search
            **kwargs: Additional scraper-specific parameters
            
        Returns:
            List of scraped articles
        """
        pass

    async def scrape_news(self, keywords: List[str], start_date: datetime, 
                         end_date: datetime, **kwargs) -> List[NewsArticle]:
        """
        Main scraping method that orchestrates the entire scraping process.
        
        Args:
            keywords: Keywords to search for
            start_date: Start date for article search
            end_date: End date for article search
            **kwargs: Additional scraper-specific parameters
            
        Returns:
            List of validated and filtered articles
        """
        self.logger.info(f"Starting scrape for {self.source_name} with keywords: {keywords}")
        
        try:
            # Scrape articles from source
            articles = await self._scrape_articles_from_source(
                keywords, start_date, end_date, **kwargs
            )
            
            self.logger.info(f"Scraped {len(articles)} raw articles")
            
            # Validate articles
            valid_articles = []
            for article in articles:
                if await self.validate_article(article):
                    valid_articles.append(article)
                else:
                    self.logger.debug(f"Invalid article filtered out: {article.url}")
            
            self.logger.info(f"Validated {len(valid_articles)} articles")
            
            # Filter by keywords if provided
            if keywords:
                valid_articles = self._filter_by_keywords(valid_articles, keywords)
                self.logger.info(f"Keyword filtering resulted in {len(valid_articles)} articles")
            
            # Filter by date range
            valid_articles = self._filter_by_date_range(valid_articles, start_date, end_date)
            self.logger.info(f"Date filtering resulted in {len(valid_articles)} articles")
            
            return valid_articles
            
        except Exception as e:
            self.logger.error(f"Scraping failed for {self.source_name}: {e}")
            raise ScrapingError(f"Scraping failed: {str(e)}", source=self.source_name)
        finally:
            await self.close()