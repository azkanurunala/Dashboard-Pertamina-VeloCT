"""
OilPrice News Scraper for Azure Functions.
Implements scraping functionality for OilPrice news articles using sitemap and direct scraping.
"""

import asyncio
import re
import sys
import os
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

# Add parent directory to Python path for absolute imports in Azure Functions
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from scrapers.base_scraper import BaseNewsScraper
from scrapers.exceptions import ScrapingError, NetworkError, ContentExtractionError
from shared.models import NewsArticle, ScrapingConfig


class OilPriceNewsScraper(BaseNewsScraper):
    """
    OilPrice.com News Scraper implementation.
    Scrapes news articles from OilPrice.com using sitemap and JSON-LD extraction.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize OilPrice scraper with default configuration."""
        if config is None:
            config = ScrapingConfig(
                source_name="OilPrice",
                base_url="https://oilprice.com",
                selectors={
                    "sitemap": "https://oilprice.com/googlenews.xml",
                    "article_content": "div#article-content.wysiwyg.clear",
                    "json_ld": "script[type='application/ld+json']"
                },
                rate_limit_delay=1.0,
                max_retries=3,
                timeout=25
            )
        
        super().__init__(config)
        self.sitemap_url = self.config.selectors.get("sitemap", "https://oilprice.com/googlenews.xml")

    def _clean_oilprice_text(self, text: str) -> str:
        """
        Clean OilPrice-specific text patterns.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        if not text or text == 'N/A':
            return text
        
        # Replace HTML entities
        replacements = {
            '&nbsp;': ' ',
            '&rsquo;': "'",
            '&ldquo;': '"',
            '&rdquo;': '"',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>'
        }
        
        for entity, replacement in replacements.items():
            text = text.replace(entity, replacement)
        
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
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
                    date = date_raw.split('T')[0] if 'T' in date_raw else date_raw
                
                if keywords_element is not None and keywords_element.text:
                    keywords = keywords_element.text.strip()
            
            # Generate title from URL if not available
            if not title:
                title = url.rstrip('/').split('/')[-1].replace('-', ' ').title()
            
            return {
                'title': title or "(No Title)",
                'url': url,
                'date': date,
                'keywords': keywords
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to extract article info: {e}")
            return None

    async def _extract_article_content_json_ld(self, url: str) -> str:
        """
        Extract article content using JSON-LD structured data.
        
        Args:
            url: Article URL
            
        Returns:
            Extracted article content
        """
        try:
            content = await self._fetch_content(url)
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for JSON-LD scripts
            json_ld_scripts = soup.find_all('script', {'type': 'application/ld+json'})
            
            for script in json_ld_scripts:
                try:
                    if not script.string:
                        continue
                    
                    data = json.loads(script.string)
                    
                    # Check if this is a NewsArticle
                    if isinstance(data, dict) and data.get('@type') == 'NewsArticle':
                        article_body = data.get('articleBody', '')
                        
                        if article_body:
                            cleaned_content = self._clean_oilprice_text(article_body)
                            self.logger.debug(f"Extracted {len(cleaned_content)} characters from JSON-LD")
                            return cleaned_content
                
                except json.JSONDecodeError:
                    continue
            
            # Fallback to HTML parsing
            self.logger.debug("No JSON-LD found, trying HTML parsing")
            return await self._extract_article_content_html(soup)
            
        except Exception as e:
            self.logger.error(f"Failed to extract content from {url}: {e}")
            return "N/A"

    async def _extract_article_content_html(self, soup: BeautifulSoup) -> str:
        """
        Extract article content from HTML as fallback.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Extracted article content
        """
        try:
            # Find article content container
            article_body = soup.select_one(self.config.selectors.get("article_content", "div#article-content.wysiwyg.clear"))
            
            if not article_body:
                self.logger.warning("No article content container found")
                return "N/A"
            
            # Extract paragraphs
            content_parts = []
            for elem in article_body.find_all(['p']):
                text = elem.get_text(strip=True)
                if text and len(text) > 10:
                    content_parts.append(text)
            
            if content_parts:
                content = "\n\n".join(content_parts)
                cleaned_content = self._clean_oilprice_text(content)
                self.logger.debug(f"Extracted {len(cleaned_content)} characters from HTML")
                return cleaned_content
            
            return "N/A"
            
        except Exception as e:
            self.logger.error(f"Failed to extract HTML content: {e}")
            return "N/A"

    async def _scrape_from_sitemap(self, keywords: List[str], start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Scrape articles from OilPrice sitemap.
        
        Args:
            keywords: Keywords to filter articles
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            List of article data dictionaries
        """
        content = None
        
        # Try aiohttp first
        try:
            response = await self._make_request(self.sitemap_url)
            content = await response.read()
        except Exception as e:
            self.logger.info(f"aiohttp failed for sitemap, trying Selenium fallback: {e}")
            try:
                content_str = await self._fetch_sitemap_selenium(self.sitemap_url)
                content = content_str.encode('utf-8')
            except Exception as selenium_error:
                self.logger.error(f"Selenium sitemap fallback also failed: {selenium_error}")
                raise ScrapingError(f"Failed to fetch sitemap: {str(e)}", source=self.source_name)
        
        try:
            # Parse XML
            root = ET.fromstring(content)
            namespaces = {
                'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                'news': 'http://www.google.com/schemas/sitemap-news/0.9'
            }
            
            # Extract all articles
            all_articles = []
            url_tags = root.findall('.//sm:url', namespaces)
            self.logger.info(f"Found {len(url_tags)} total articles in sitemap")
            
            for url_tag in url_tags:
                article_info = self._extract_article_info_from_sitemap(url_tag, namespaces)
                if article_info:
                    all_articles.append(article_info)
            
            # Filter by keywords if provided
            if keywords:
                filtered_articles = []
                for article in all_articles:
                    title = article.get('title', '').lower()
                    keywords_text = article.get('keywords', '').lower()
                    
                    # Check if any keyword matches
                    for keyword in keywords:
                        keyword_lower = keyword.lower()
                        if keyword_lower in title or keyword_lower in keywords_text:
                            filtered_articles.append(article)
                            break
                
                all_articles = filtered_articles
                self.logger.info(f"Keyword filtering resulted in {len(all_articles)} articles")
            
            # Filter by date if specified
            if start_date and end_date:
                date_filtered_articles = []
                for article in all_articles:
                    if article['date']:
                        try:
                            article_date = datetime.strptime(article['date'], '%Y-%m-%d')
                            if start_date <= article_date <= end_date:
                                date_filtered_articles.append(article)
                        except ValueError:
                            # Include articles with unparseable dates
                            date_filtered_articles.append(article)
                    else:
                        # Include articles without dates
                        date_filtered_articles.append(article)
                
                all_articles = date_filtered_articles
                self.logger.info(f"Date filtering resulted in {len(all_articles)} articles")
            
            return all_articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape from sitemap: {str(e)}", source=self.source_name)

    async def _scrape_articles_from_source(self, keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
        """
        Scrape articles from OilPrice source.
        
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
            
            if not sitemap_articles:
                return []
            
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
                    
                    # Extract content using JSON-LD method
                    content = await self._extract_article_content_json_ld(article_data['url'])
                    
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
                        keywords=article_data.get('keywords', '').split(',') if article_data.get('keywords') else []
                    )
                    
                    articles.append(article)
                    
                    # Rate limiting
                    await asyncio.sleep(1.0)
                    
                except Exception as e:
                    self.logger.error(f"Failed to process article {article_data['url']}: {e}")
                    continue
            
            self.logger.info(f"Successfully scraped {len(articles)} articles from OilPrice")
            return articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape OilPrice articles: {str(e)}", source=self.source_name)


# Azure Function wrapper
async def scrape_oilprice_news(keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
    """
    Azure Function entry point for OilPrice news scraping.
    
    Args:
        keywords: Keywords to search for
        start_date: Start date for article search
        end_date: End date for article search
        **kwargs: Additional parameters
        
    Returns:
        List of scraped NewsArticle objects
    """
    async with OilPriceNewsScraper() as scraper:
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)