"""
Reuters News Scraper for Azure Functions.
Implements scraping functionality for Reuters news articles using sitemap and direct scraping.
"""

import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin
import random

from bs4 import BeautifulSoup

from .base_scraper import BaseNewsScraper
from .exceptions import ScrapingError, NetworkError, ContentExtractionError
from ..shared.models import NewsArticle, ScrapingConfig


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
        self.sitemap_index_url = self.config.selectors.get("sitemap_index", "https://www.reuters.com/arc/outboundfeeds/news-sitemap-index/?outputType=xml")

    async def _get_sitemap_urls(self, max_sitemaps: Optional[int] = 5) -> List[str]:
        """
        Get sitemap URLs from the sitemap index.
        
        Args:
            max_sitemaps: Maximum number of sitemaps to process (optional)
            
        Returns:
            List of sitemap URLs
        """
        try:
            response = await self._make_request(self.sitemap_index_url)
            content = await response.text()
            
            # Parse XML
            root = ET.fromstring(content)
            namespaces = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            sitemap_urls = []
            for sitemap in root.findall('.//sm:sitemap', namespaces):
                loc = sitemap.find('sm:loc', namespaces)
                if loc is not None and loc.text:
                    sitemap_urls.append(loc.text.strip())
                    
                    if max_sitemaps and len(sitemap_urls) >= max_sitemaps:
                        break
            
            self.logger.info(f"Found {len(sitemap_urls)} sitemap URLs")
            return sitemap_urls
            
        except Exception as e:
            self.logger.warning(f"Failed to get sitemap URLs: {e}")
            # Fallback to a default sitemap URL
            return ["https://www.reuters.com/arc/outboundfeeds/news-sitemap/?outputType=xml"]

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
            
            # Skip non-article URLs
            if not any(pattern in url for pattern in ['/article/', '/news/', '/world/', '/business/', '/technology/']):
                return None
            
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
            date = ''
            if date_raw:
                # Extract date part (before 'T' if present)
                date = date_raw.split('T')[0] if 'T' in date_raw else date_raw
            
            # Generate title from URL if not available
            if not title:
                url_parts = url.rstrip('/').split('/')
                if len(url_parts) > 0:
                    title = url_parts[-1].replace('-', ' ').title()
                else:
                    title = "Reuters Article"
            
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
        Extract article content from Reuters article page.
        
        Args:
            url: Article URL
            
        Returns:
            Extracted article content
        """
        try:
            content = await self._fetch_content(url)
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove unwanted elements first
            unwanted_selector = self.config.selectors.get("unwanted", "")
            if unwanted_selector:
                for unwanted in soup.select(unwanted_selector):
                    unwanted.decompose()
            
            # Try to find article body using various selectors
            body_selectors = [
                "div.article-body-module__content__bnXL1",
                "div[data-testid='article-body']",
                "div.StandardArticleBody_body",
                "div.ArticleBodyWrapper",
                "article"
            ]
            
            article_content = None
            for selector in body_selectors:
                article_content = soup.select_one(selector)
                if article_content:
                    break
            
            if not article_content:
                # Fallback to the entire page
                article_content = soup
            
            # Extract paragraphs
            paragraphs = []
            
            # Look for paragraph elements with various selectors
            paragraph_selectors = [
                "div[data-testid^='paragraph-']",
                "p",
                "div.text__text__1FZLe"
            ]
            
            for selector in paragraph_selectors:
                elements = article_content.select(selector)
                for element in elements:
                    text = self._clean_text(element.get_text())
                    if len(text) > 30 and text not in paragraphs:
                        paragraphs.append(text)
                
                if len(paragraphs) >= 3:
                    break
            
            # If no paragraphs found, try extracting from all text elements
            if not paragraphs:
                for element in article_content.find_all(['p', 'div', 'span']):
                    text = self._clean_text(element.get_text())
                    if len(text) > 50 and text not in paragraphs:
                        paragraphs.append(text)
            
            if not paragraphs:
                return "N/A"
            
            return "\n\n".join(paragraphs)
            
        except Exception as e:
            self.logger.error(f"Failed to extract content from {url}: {e}")
            return "N/A"

    async def _scrape_from_sitemap(self, keywords: List[str], start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Scrape articles from Reuters sitemap(s).
        
        Args:
            keywords: Keywords to filter articles
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            List of article data dictionaries
        """
        try:
            # Get sitemap URLs
            sitemap_urls = await self._get_sitemap_urls(max_sitemaps=3)  # Limit to 3 sitemaps for performance
            
            all_articles = []
            namespaces = {
                'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                'news': 'http://www.google.com/schemas/sitemap-news/0.9'
            }
            
            # Process each sitemap
            for sitemap_url in sitemap_urls:
                try:
                    response = await self._make_request(sitemap_url)
                    sitemap_data = await response.text()
                    
                    # Parse XML
                    root = ET.fromstring(sitemap_data)
                    
                    # Extract articles from this sitemap
                    for url_tag in root.findall('.//sm:url', namespaces):
                        article_info = self._extract_article_info_from_sitemap(url_tag, namespaces)
                        if article_info:
                            all_articles.append(article_info)
                    
                    # Rate limiting between sitemaps
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process sitemap {sitemap_url}: {e}")
                    continue
            
            self.logger.info(f"Found {len(all_articles)} articles across all sitemaps")
            
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
            # Get articles from sitemap
            sitemap_articles = await self._scrape_from_sitemap(keywords, start_date, end_date)
            
            # Limit the number of articles to process for performance
            max_articles = kwargs.get('max_articles', 50)
            if len(sitemap_articles) > max_articles:
                # Randomize selection to get diverse content
                import random
                sitemap_articles = random.sample(sitemap_articles, max_articles)
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
                    
                    # More conservative rate limiting for Reuters
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    self.logger.error(f"Failed to process article {article_data['url']}: {e}")
                    continue
            
            self.logger.info(f"Successfully scraped {len(articles)} articles from Reuters")
            return articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape Reuters articles: {str(e)}", source=self.source_name)


# Azure Function wrapper
async def scrape_reuters_news(keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
    """
    Azure Function entry point for Reuters news scraping.
    
    Args:
        keywords: Keywords to search for
        start_date: Start date for article search
        end_date: End date for article search
        **kwargs: Additional parameters
        
    Returns:
        List of scraped NewsArticle objects
    """
    async with ReutersNewsScraper() as scraper:
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)


# Azure Function wrapper
async def scrape_reuters_news(keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
    """
    Azure Function entry point for Reuters news scraping.
    
    Args:
        keywords: Keywords to search for
        start_date: Start date for article search
        end_date: End date for article search
        **kwargs: Additional parameters
        
    Returns:
        List of scraped NewsArticle objects
    """
    async with ReutersNewsScraper() as scraper:
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)