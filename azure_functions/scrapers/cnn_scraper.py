"""
CNN News Scraper for Azure Functions.
Implements scraping functionality for CNN news articles using sitemap and direct scraping.
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
            date_raw = lastmod_element.text.strip() if lastmod_element is not None else ''
            
            # Extract news-specific information
            news_element = url_tag.find('news:news', namespaces)
            title = ""
            
            if news_element is not None:
                title_element = news_element.find('news:title', namespaces)
                pub_element = news_element.find('news:publication_date', namespaces)
                
                if title_element is not None and title_element.text:
                    title = title_element.text.strip()
                
                # Use publication date if available, otherwise use lastmod
                if pub_element is not None and pub_element.text:
                    date_raw = pub_element.text.strip()
            
            # Parse date
            date = '-'
            if date_raw:
                # Extract date part (before 'T' if present)
                date = date_raw.split('T')[0] if 'T' in date_raw else date_raw
            
            # Generate title from URL if not available
            if not title:
                title = url.rstrip('/').split('/')[-1].replace('-', ' ').title()
            
            return {
                'title': title,
                'url': url,
                'date': date
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to extract article info: {e}")
            return None

    async def _extract_article_content(self, url: str) -> str:
        """
        Extract article content from CNN article page.
        
        Args:
            url: Article URL
            
        Returns:
            Extracted article content
        """
        try:
            content = await self._fetch_content(url)
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove "top headlines" section if present
            top_headlines = soup.find('h2', id='top-headlines')
            if top_headlines:
                next_sibling = top_headlines.find_next_sibling()
                while next_sibling:
                    if next_sibling.name == 'div' and next_sibling.find('ul'):
                        next_sibling.decompose()
                        break
                    next_sibling = next_sibling.find_next_sibling()
                top_headlines.decompose()
            
            # Remove list-elevate divs that follow top headlines
            for list_div in soup.find_all('div', class_='list-elevate'):
                prev_h2 = list_div.find_previous('h2')
                if prev_h2 and 'top headlines' in prev_h2.get_text().lower():
                    list_div.decompose()
            
            # Extract content from article containers
            paragraphs = []
            content_selectors = self.config.selectors.get("article_content", "").split(", ")
            
            for selector in content_selectors:
                container = soup.select_one(selector.strip())
                if container:
                    for element in container.find_all(['h2', 'p', 'li']):
                        text = element.get_text(strip=True)
                        if self._is_valid_paragraph(text, min_length=8) and text not in paragraphs:
                            paragraphs.append(text)
                    
                    if len(paragraphs) >= 3:
                        break
            
            # Fallback to general paragraph extraction
            if len(paragraphs) < 2:
                for element in soup.find_all(['h2', 'p', 'li']):
                    text = element.get_text(strip=True)
                    if self._is_valid_paragraph(text, min_length=10) and text not in paragraphs:
                        paragraphs.append(text)
            
            if not paragraphs:
                return 'N/A'
            
            # Clean and join paragraphs
            cleaned_content = self._clean_cnn_text("\n\n".join(paragraphs))
            return cleaned_content if cleaned_content else 'N/A'
            
        except Exception as e:
            self.logger.error(f"Failed to extract content from {url}: {e}")
            return 'N/A'

    async def _get_all_sitemap_urls(self) -> List[str]:
        """
        Get all sitemap URLs from the sitemap index.
        
        Returns:
            List of sitemap URLs
        """
        try:
            sitemap_data = await self._fetch_sitemap_data()
            root = ET.fromstring(sitemap_data)
            
            namespaces = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            # Check if this is a sitemap index
            if root.tag.endswith('sitemapindex'):
                # Extract individual sitemap URLs
                sitemap_urls = []
                for sitemap in root.findall('.//sm:sitemap', namespaces):
                    loc = sitemap.find('sm:loc', namespaces)
                    if loc is not None and loc.text:
                        sitemap_urls.append(loc.text.strip())
                return sitemap_urls
            else:
                # This is a direct sitemap
                return [self.sitemap_url]
                
        except Exception as e:
            self.logger.warning(f"Failed to get sitemap URLs: {e}")
            return [self.sitemap_url]

    async def _scrape_from_sitemap(self, keywords: List[str], start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Scrape articles from CNN sitemap(s).
        
        Args:
            keywords: Keywords to filter articles
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            List of article data dictionaries
        """
        try:
            # Get all sitemap URLs
            sitemap_urls = await self._get_all_sitemap_urls()
            self.logger.info(f"Found {len(sitemap_urls)} sitemap(s) to process")
            
            all_articles = []
            namespaces = {
                'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                'news': 'http://www.google.com/schemas/sitemap-news/0.9'
            }
            
            # Process each sitemap
            for sitemap_url in sitemap_urls:
                try:
                    response = await self._make_request(sitemap_url)
                    sitemap_data = await response.read()
                    
                    # Handle gzipped content
                    if sitemap_url.endswith('.gz') or sitemap_data[:2] == b'\x1f\x8b':
                        with gzip.GzipFile(fileobj=io.BytesIO(sitemap_data)) as f:
                            sitemap_data = f.read()
                    
                    # Parse XML
                    root = ET.fromstring(sitemap_data)
                    
                    # Extract articles from this sitemap
                    for url_tag in root.findall('.//sm:url', namespaces):
                        article_info = self._extract_article_info_from_sitemap(url_tag, namespaces)
                        if article_info:
                            all_articles.append(article_info)
                    
                    # Rate limiting between sitemaps
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process sitemap {sitemap_url}: {e}")
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
            raise ScrapingError(f"Failed to scrape from sitemap: {str(e)}", source=self.source_name)

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
            # Get articles from sitemap
            sitemap_articles = await self._scrape_from_sitemap(keywords, start_date, end_date)
            
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
                        keywords=[]  # Will be populated by keyword filtering
                    )
                    
                    articles.append(article)
                    
                    # Rate limiting
                    await asyncio.sleep(1)  # CNN requires more conservative rate limiting
                    
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
    
    Args:
        keywords: Keywords to search for
        start_date: Start date for article search
        end_date: End date for article search
        **kwargs: Additional parameters
        
    Returns:
        List of scraped NewsArticle objects
    """
    async with CNNNewsScraper() as scraper:
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)