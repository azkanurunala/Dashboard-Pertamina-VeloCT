"""
CNBC News Scraper for Azure Functions.
Implements scraping functionality for CNBC news articles using sitemap and direct scraping.
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


class CNBCNewsScraper(BaseNewsScraper):
    """
    CNBC News Scraper implementation.
    Scrapes news articles from CNBC using sitemap and direct content extraction.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize CNBC scraper with default configuration."""
        if config is None:
            config = ScrapingConfig(
                source_name="CNBC",
                base_url="https://www.cnbc.com",
                selectors={
                    "sitemap": "https://www.cnbc.com/sitemap_news.xml",
                    "article_body": "div.ArticleBody-articleBody, section#ArticleBody, div[class*='article-body']",
                    "title": "h1",
                    "content": "div.ArticleBody-articleBody p, section#ArticleBody p",
                    "unwanted": "script, style, iframe, figure, div[class*='ad'], div[data-module='mps-slot'], span[class*='share'], aside, div.RelatedContent-collapsibleContent, div[class*='RelatedContent'], div[class*='related']"
                },
                rate_limit_delay=1,
                max_retries=3,
                timeout=25
            )
        
        super().__init__(config)
        self.sitemap_url = self.config.selectors.get("sitemap", "https://www.cnbc.com/sitemap_news.xml")

    async def _fetch_sitemap_data(self) -> bytes:
        """
        Fetch and decompress sitemap data.
        
        Returns:
            Raw sitemap XML data
            
        Raises:
            NetworkError: If sitemap cannot be fetched
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
            
            # Extract news-specific information
            news_element = url_tag.find('news:news', namespaces)
            title = ""
            date = ""
            
            if news_element is not None:
                title_element = news_element.find('news:title', namespaces)
                date_element = news_element.find('news:publication_date', namespaces)
                
                if title_element is not None and title_element.text:
                    title = title_element.text.strip()
                
                if date_element is not None and date_element.text:
                    date = date_element.text.strip()[:10]  # Extract date part only
            
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
        Extract article content from CNBC article page.
        
        Args:
            url: Article URL
            
        Returns:
            Extracted article content
        """
        try:
            content = await self._fetch_content(url)
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove unwanted elements
            unwanted_selector = self.config.selectors.get("unwanted", "")
            if unwanted_selector:
                for unwanted in soup.select(unwanted_selector):
                    unwanted.decompose()
            
            # Find article body containers
            body_selector = self.config.selectors.get("article_body", "div.ArticleBody-articleBody")
            containers = soup.select(body_selector)
            
            if not containers:
                # Fallback to entire page
                containers = [soup]
            
            # Extract text from containers
            text_parts = []
            for container in containers:
                # Remove additional unwanted elements
                for bad in container.select('script, style, iframe, figure, div[class*="ad"], div[data-module="mps-slot"], span[class*="share"], aside, div.RelatedContent-collapsibleContent, div[class*="RelatedContent"], div[class*="related"]'):
                    bad.decompose()
                
                # Extract meaningful text
                text_elements = self._extract_text_from_element(container, min_length=30)
                text_parts.extend(text_elements)
            
            # Fallback to paragraph extraction if no content found
            if not text_parts:
                for p in soup.find_all('p'):
                    text = self._clean_text(p.get_text())
                    if len(text) > 30:
                        text_parts.append(text)
            
            if not text_parts:
                return "N/A"
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            self.logger.error(f"Failed to extract content from {url}: {e}")
            return "N/A"

    async def _scrape_from_sitemap(self, keywords: List[str], start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Scrape articles from CNBC sitemap.
        
        Args:
            keywords: Keywords to filter articles
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            List of article data dictionaries
        """
        try:
            # Fetch sitemap data
            sitemap_data = await self._fetch_sitemap_data()
            
            # Parse XML
            root = ET.fromstring(sitemap_data)
            namespaces = {
                'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                'news': 'http://www.google.com/schemas/sitemap-news/0.9'
            }
            
            # Extract all articles
            all_articles = []
            for url_tag in root.findall('.//sm:url', namespaces):
                article_info = self._extract_article_info_from_sitemap(url_tag, namespaces)
                if article_info:
                    all_articles.append(article_info)
            
            self.logger.info(f"Found {len(all_articles)} articles in sitemap")
            
            # Filter by date if specified
            if start_date and end_date:
                filtered_articles = []
                for article in all_articles:
                    if article['date']:
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
        Scrape articles from CNBC source.
        
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
                    await self.handle_rate_limiting()
                    
                except Exception as e:
                    self.logger.error(f"Failed to process article {article_data['url']}: {e}")
                    continue
            
            self.logger.info(f"Successfully scraped {len(articles)} articles from CNBC")
            return articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape CNBC articles: {str(e)}", source=self.source_name)


# Azure Function wrapper
async def scrape_cnbc_news(keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
    """
    Azure Function entry point for CNBC news scraping.
    
    Args:
        keywords: Keywords to search for
        start_date: Start date for article search
        end_date: End date for article search
        **kwargs: Additional parameters
        
    Returns:
        List of scraped NewsArticle objects
    """
    async with CNBCNewsScraper() as scraper:
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)