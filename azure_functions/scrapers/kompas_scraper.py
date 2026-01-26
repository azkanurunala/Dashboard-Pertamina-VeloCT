"""
Kompas News Scraper for Azure Functions.
Implements scraping functionality for Kompas news articles using sitemap and direct scraping.
"""

import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin
import gzip
import io

from bs4 import BeautifulSoup

from .base_scraper import BaseNewsScraper
from .exceptions import ScrapingError, NetworkError, ContentExtractionError
from ..shared.models import NewsArticle, ScrapingConfig


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

    async def _fetch_sitemap_data(self) -> bytes:
        """
        Fetch and decompress sitemap data.
        
        Returns:
            Raw sitemap XML data
        """
        try:
            response = await self._make_request(self.sitemap_url)
            content = await response.read()
            
            # Handle gzipped content
            if self.sitemap_url.endswith('.gz') or content[:2] == b'\x1f\x8b':
                with gzip.GzipFile(fileobj=io.BytesIO(content)) as f:
                    content = f.read()
            
            return content
            
        except Exception as e:
            raise NetworkError(f"Failed to fetch sitemap: {str(e)}", source=self.source_name, url=self.sitemap_url)

    def _is_sitemap_index(self, root, namespaces: Dict[str, str]) -> bool:
        """Check if this is a sitemap index or direct sitemap."""
        has_sitemap_tags = root.findall('.//sm:sitemap', namespaces)
        has_url_tags = root.findall('.//sm:url', namespaces)
        return len(has_sitemap_tags) > 0 and len(has_url_tags) == 0

    async def _get_article_sitemaps(self, root, depth: int = 0, max_depth: int = 3) -> List[str]:
        """
        Recursively get all article sitemaps from sitemap index.
        
        Args:
            root: XML root element
            depth: Current recursion depth
            max_depth: Maximum recursion depth
            
        Returns:
            List of article sitemap URLs
        """
        if depth > max_depth:
            self.logger.warning(f"Max depth reached ({max_depth})")
            return []
        
        namespaces = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        article_sitemaps = []
        
        sitemap_tags = root.findall('.//sm:sitemap', namespaces)
        if not sitemap_tags:
            return []
        
        for sitemap_tag in sitemap_tags:
            loc = sitemap_tag.find('sm:loc', namespaces)
            if loc is None or not loc.text:
                continue
            
            href = loc.text.strip()
            if 'news' not in href.lower():
                continue
            
            try:
                response = await self._make_request(href)
                content = await response.read()
                
                # Handle gzipped content
                if href.endswith('.gz') or content[:2] == b'\x1f\x8b':
                    with gzip.GzipFile(fileobj=io.BytesIO(content)) as f:
                        content = f.read()
                
                subroot = ET.fromstring(content)
                
                if self._is_sitemap_index(subroot, namespaces):
                    self.logger.debug(f"Sitemap index found, drilling down: {href}")
                    nested = await self._get_article_sitemaps(subroot, depth + 1, max_depth)
                    article_sitemaps.extend(nested)
                else:
                    url_tags = subroot.findall('.//sm:url', namespaces)
                    self.logger.debug(f"Article sitemap found with {len(url_tags)} URLs: {href}")
                    article_sitemaps.append(href)
                
                await asyncio.sleep(0.1)  # Rate limiting
                
            except Exception as e:
                self.logger.warning(f"Failed to process sitemap {href}: {e}")
                continue
        
        return article_sitemaps

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
                    date = date_element.text.strip().split('T')[0]  # Extract date part only
                
                if keywords_element is not None and keywords_element.text:
                    keywords = keywords_element.text.strip()
            
            # Generate title from URL if not available
            if not title:
                title = url.rstrip('/').split('/')[-1].replace('-', ' ').title()
            
            return {
                'title': title or '(No Title)',
                'url': url,
                'date': date or '-',
                'keywords': keywords
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to extract article info: {e}")
            return None

    async def _extract_article_content(self, url: str) -> str:
        """
        Extract article content from Kompas article page.
        
        Args:
            url: Article URL
            
        Returns:
            Extracted article content
        """
        try:
            # Handle multi-page articles
            all_content = []
            base_url = url.split('?')[0]
            
            # Fetch first page
            content = await self._fetch_content(base_url)
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove unwanted elements
            unwanted_selector = self.config.selectors.get("unwanted", "")
            if unwanted_selector:
                for unwanted in soup.select(unwanted_selector):
                    unwanted.decompose()
            
            # Extract content from main container
            content_div = soup.select_one("div.read__content")
            if not content_div:
                self.logger.warning(f"Missing content div in {base_url}")
                return "N/A"
            
            # Clean and extract text
            cleaned_content = self._extract_and_clean_content(content_div)
            if cleaned_content and cleaned_content != "-":
                all_content.append(cleaned_content)
            
            # Check for pagination
            total_pages = self._get_total_pages(soup)
            if total_pages > 1:
                self.logger.info(f"Multi-page article detected: {total_pages} pages")
                for page_num in range(2, min(total_pages + 1, 6)):  # Limit to 5 pages max
                    page_url = f"{base_url}?page={page_num}"
                    try:
                        page_content = await self._fetch_content(page_url)
                        page_soup = BeautifulSoup(page_content, 'html.parser')
                        
                        page_content_div = page_soup.select_one("div.read__content")
                        if page_content_div:
                            page_cleaned = self._extract_and_clean_content(page_content_div)
                            if page_cleaned and page_cleaned != "-":
                                all_content.append(page_cleaned)
                        
                        await asyncio.sleep(0.5)  # Rate limiting between pages
                    except Exception as e:
                        self.logger.warning(f"Failed to fetch page {page_num}: {e}")
                        continue
            
            if not all_content:
                return "N/A"
            
            return "\n\n".join(all_content)
            
        except Exception as e:
            self.logger.error(f"Failed to extract content from {url}: {e}")
            return "N/A"

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

    async def _scrape_from_sitemap(self, keywords: List[str], start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Scrape articles from Kompas sitemap.
        
        Args:
            keywords: Keywords to filter articles
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            List of article data dictionaries
        """
        try:
            # Fetch main sitemap
            sitemap_data = await self._fetch_sitemap_data()
            root = ET.fromstring(sitemap_data)
            
            # Get all article sitemaps
            article_sitemaps = await self._get_article_sitemaps(root)
            if not article_sitemaps:
                self.logger.warning("No article sitemaps found")
                return []
            
            self.logger.info(f"Found {len(article_sitemaps)} article sitemap(s)")
            
            # Extract articles from all sitemaps
            all_articles = []
            namespaces = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            for sitemap_url in article_sitemaps:
                try:
                    response = await self._make_request(sitemap_url)
                    content = await response.read()
                    
                    # Handle gzipped content
                    if sitemap_url.endswith('.gz') or content[:2] == b'\x1f\x8b':
                        with gzip.GzipFile(fileobj=io.BytesIO(content)) as f:
                            content = f.read()
                    
                    subroot = ET.fromstring(content)
                    
                    for url_tag in subroot.findall('.//sm:url', namespaces):
                        article_info = self._extract_article_info_from_sitemap(url_tag, namespaces)
                        if article_info:
                            all_articles.append(article_info)
                    
                    await asyncio.sleep(0.15)  # Rate limiting
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process sitemap {sitemap_url}: {e}")
                    continue
            
            self.logger.info(f"Found {len(all_articles)} articles in sitemaps")
            
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
            raise ScrapingError(f"Failed to scrape from sitemap: {str(e)}", source=self.source_name)

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
            # Get articles from sitemap
            sitemap_articles = await self._scrape_from_sitemap(keywords, start_date, end_date)
            
            # Limit articles for performance
            max_articles = kwargs.get('max_articles', 30)
            if len(sitemap_articles) > max_articles:
                sitemap_articles = sitemap_articles[:max_articles]
                self.logger.info(f"Limited to {max_articles} articles for processing")
            
            # Extract content for each article
            articles = []
            for i, article_data in enumerate(sitemap_articles):
                try:
                    self.logger.info(f"Processing article {i+1}/{len(sitemap_articles)}: {article_data['title'][:60]}...")
                    
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