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
            
            # Extract last modified date
            lastmod_element = url_tag.find('sm:lastmod', namespaces)
            date = lastmod_element.text.strip()[:10] if lastmod_element is not None and lastmod_element.text else ''
            
            # Extract keywords from URL
            url_keywords = self._extract_keywords_from_url(url)
            
            # Generate title from keywords
            title = ' '.join([k.capitalize() for k in url_keywords]) if url_keywords else url.split('/')[-1]
            
            return {
                'title': title,
                'url': url,
                'date': date,
                'url_keywords': url_keywords
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to extract article info: {e}")
            return None

    def _extract_article_info_from_sitemap_robust(self, url_tag) -> Optional[Dict[str, Any]]:
        """
        Extract article information from sitemap URL entry, robustly handling ET, Tag, or HTML tr.
        """
        try:
            url = None
            date = ''
            
            # Case 1: HTML <tr> from Tempo's visual sitemaps
            if hasattr(url_tag, 'name') and url_tag.name == 'tr':
                tds = url_tag.find_all('td')
                if len(tds) >= 3:
                    a_tag = tds[0].find('a')
                    if a_tag and a_tag.get('href'):
                        url = a_tag.get('href').strip()
                    
                    date_text = tds[2].get_text(strip=True)
                    if date_text:
                        # Format "2026-02-09 18:25 Z" -> "2026-02-09"
                        date = date_text[:10]
            
            # Case 2: ET style or Standard BeautifulSoup Tag
            elif hasattr(url_tag, 'find'):
                loc = url_tag.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc is not None:
                    url = loc.text.strip()
                    lastmod = url_tag.find('{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
                    date = lastmod.text.strip()[:10] if lastmod is not None and lastmod.text else ''
                else:
                    # Try BeautifulSoup style or direct tag find
                    loc = url_tag.find('loc')
                    if loc is None or not loc.text:
                        # Try direct access for ET without namespace if BS
                        url = url_tag.get_text().strip() if hasattr(url_tag, 'get_text') else None
                        if not url or not url.startswith('http'): return None
                        date = ''
                    else:
                        url = loc.text.strip()
                        lastmod = url_tag.find('lastmod')
                        date = lastmod.text.strip()[:10] if lastmod is not None and lastmod.text else ''
            
            if not url or not url.startswith('http'):
                return None

            url_keywords = self._extract_keywords_from_url(url)
            
            # Case 1: Title from HTML <tr> (usually in the link text)
            title = ''
            if hasattr(url_tag, 'name') and url_tag.name == 'tr':
                tds = url_tag.find_all('td')
                a_tag = tds[0].find('a')
                if a_tag:
                    title = a_tag.get_text(strip=True)

            # Case 2: XML news:title or title tag
            if not title and hasattr(url_tag, 'find'):
                title_tag = url_tag.find('{http://www.google.com/schemas/sitemap-news/0.9}title')
                if title_tag is None:
                    title_tag = url_tag.find('news:title')
                if title_tag is None:
                    title_tag = url_tag.find('title')
                
                title = title_tag.text.strip() if title_tag is not None and title_tag.text else ''
            
            if not title:
                title = ' '.join([k.capitalize() for k in url_keywords]) if url_keywords else url.split('/')[-1]
            
            return {
                'title': title,
                'url': url,
                'date': date,
                'url_keywords': url_keywords
            }
        except Exception as e:
            self.logger.warning(f"Robust extraction failed: {e}")
            return None

    async def _extract_article_content(self, url: str) -> str:
        """
        Extract article content from Tempo article page.
        
        Args:
            url: Article URL
            
        Returns:
            Extracted article content
        """
        try:
            content = await self._fetch_content(url)
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find main content container
            content_selectors = self.config.selectors.get("article_content", "").split(", ")
            container = None
            
            for selector in content_selectors:
                container = soup.select_one(selector.strip())
                if container:
                    break
            
            if not container:
                container = soup  # Fallback to entire page
            
            # Remove unwanted elements
            unwanted_selector = self.config.selectors.get("unwanted", "")
            if unwanted_selector:
                for unwanted in container.select(unwanted_selector):
                    unwanted.decompose()
            
            # Extract paragraphs
            paragraphs = []
            for p in container.find_all('p'):
                text = re.sub(r'\s+', ' ', p.get_text(" ", strip=True))
                if len(text) > 30:
                    paragraphs.append(text)
            
            if not paragraphs:
                return "N/A"
            
            content_text = "\n\n".join(paragraphs)
            return self._clean_tempo_text(content_text)
            
        except Exception as e:
            self.logger.error(f"Failed to extract content from {url}: {e}")
            return "N/A"

    async def _scrape_from_sitemap(self, sitemap_url: str, keywords: List[str], start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Scrape articles from a single Tempo sitemap.
        
        Args:
            sitemap_url: Sitemap URL to scrape
            keywords: Keywords to filter articles
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            List of article data dictionaries
        """
        content = None
        
        # Try aiohttp first
        try:
            response = await self._make_request(sitemap_url)
            content = await response.read()
        except Exception as e:
            # Try Selenium fallback for sitemap
            self.logger.info(f"aiohttp failed for sitemap {sitemap_url}, trying Selenium fallback: {e}")
            try:
                content_str = await self._fetch_sitemap_selenium(sitemap_url)
                content = content_str.encode('utf-8')
            except Exception as selenium_error:
                self.logger.warning(f"Selenium fallback also failed for {sitemap_url}: {selenium_error}")
                return []
        
        if not content:
            return []
        
        try:
            # Parse XML
            try:
                # Force XML headers for aiohttp request
                headers = {'Accept': 'application/xml, text/xml, */*'}
                response = await self._make_request(sitemap_url, headers=headers)
                content = await response.read()

                root = ET.fromstring(content)
                namespaces = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                url_tags = root.findall('.//sm:url', namespaces)
            except Exception as e:
                self.logger.warning(f"XML parsing failed for {sitemap_url}, trying BeautifulSoup fallback: {e}")
                
                # Save failed content for diagnostics as requested by user
                try:
                    sitemap_filename = sitemap_url.split('/')[-1]
                    # Save to project root (2 levels up from azure_functions/scrapers/)
                    root_dir = os.path.abspath(os.path.join(os.path.dirname(__get_file__ if '__get_file__' in locals() else __file__), '..', '..'))
                    failed_log_path = os.path.join(root_dir, f"failed_{sitemap_filename}")
                    with open(failed_log_path, 'wb') as f:
                        f.write(content)
                    self.logger.info(f"Saved failed sitemap content to {failed_log_path} for analysis")
                except Exception as log_e:
                    self.logger.error(f"Failed to save diagnostic sitemap file: {log_e}")

                soup = BeautifulSoup(content, 'xml') # Try XML parser first
                url_tags = soup.find_all('url')
                
                if not url_tags:
                    # Fallback to HTML table parsing (observed in Tempo's visual sitemaps)
                    soup = BeautifulSoup(content, 'html.parser')
                    # Look for rows in table#sitemap
                    table = soup.find('table', id='sitemap')
                    if table:
                        # Skip header row if it exists (usually <thead> or first <tr>)
                        url_tags = table.find_all('tr')[1:] 
                        self.logger.info(f"Detected HTML table sitemap. Found {len(url_tags)} rows.")
                    else:
                        url_tags = soup.find_all('url') # Last resort
            
            articles = []
            for url_tag in url_tags:
                article_info = self._extract_article_info_from_sitemap_robust(url_tag)
                if not article_info:
                    continue
                
                # Filter by keywords if provided
                if keywords:
                    keyword_match = False
                    for keyword in keywords:
                        k_lower = keyword.lower()
                        if self._check_keyword_match(article_info['url_keywords'], keyword) or \
                           (article_info['title'] and k_lower in article_info['title'].lower()):
                            keyword_match = True
                            break
                    
                    if not keyword_match:
                        continue
                
                # Filter by date if provided
                if start_date and end_date and article_info['date']:
                    try:
                        article_date = datetime.strptime(article_info['date'], '%Y-%m-%d')
                        if not (start_date <= article_date <= end_date):
                            continue
                    except ValueError:
                        # Include articles with unparseable dates
                        pass
                
                # Remove url_keywords before adding to results
                result_info = {k: v for k, v in article_info.items() if k != 'url_keywords'}
                articles.append(result_info)
            
            return articles
            
        except Exception as e:
            self.logger.warning(f"Failed to scrape sitemap {sitemap_url}: {e}")
            return []

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
            # Scrape from all sitemaps
            all_articles = []
            
            for sitemap_url in self.sitemap_urls:
                try:
                    sitemap_articles = await self._scrape_from_sitemap(sitemap_url, keywords, start_date, end_date)
                    all_articles.extend(sitemap_articles)
                    self.logger.info(f"Found {len(sitemap_articles)} articles from {sitemap_url}")
                    
                    # Rate limiting between sitemaps
                    await asyncio.sleep(0.2)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process sitemap {sitemap_url}: {e}")
                    continue
            
            self.logger.info(f"Found {len(all_articles)} total articles from Tempo")
            
            if not all_articles:
                return []
            
            # Limit articles for performance
            max_articles = kwargs.get('max_articles', 25)
            if len(all_articles) > max_articles:
                all_articles = all_articles[:max_articles]
                self.logger.info(f"Limited to {max_articles} articles for processing")
            
            # Extract content for each article
            articles = []
            for i, article_data in enumerate(all_articles):
                try:
                    self.logger.info(f"Processing article {i+1}/{len(all_articles)}: {article_data['title'][:60]}...")
                    
                    # Extract content
                    content = await self._extract_article_content(article_data['url'])
                    
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
                        keywords=[]  # Will be populated by keyword filtering
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