"""
Bisnis Indonesia News Scraper for Azure Functions.
Implements scraping functionality for Bisnis Indonesia news articles using search-based scraping.
"""

import asyncio
import re
import sys
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, quote

from bs4 import BeautifulSoup

# Add parent directory to Python path for absolute imports in Azure Functions
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from scrapers.base_scraper import BaseNewsScraper
from scrapers.exceptions import ScrapingError, NetworkError, ContentExtractionError
from shared.models import NewsArticle, ScrapingConfig


class BisnisIndonesiaNewsScraper(BaseNewsScraper):
    """
    Bisnis Indonesia News Scraper implementation.
    Scrapes news articles from Bisnis Indonesia using search functionality.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize Bisnis Indonesia scraper with default configuration."""
        if config is None:
            config = ScrapingConfig(
                source_name="Bisnis Indonesia",
                base_url="https://bisnis.com",
                selectors={
                    "search_url": "https://search.bisnis.com/?q={keyword}",
                    "article_item": "div.artItem",
                    "article_title": "h4.artTitle",
                    "article_link": "a.artLink",
                    "article_date": "div.artDate",
                    "article_content": "article.detailsContent, div.col--main",
                    "pagination": "ol.pagingList",
                    "unwanted": "div.billboard, div.baca-juga-box, div.baca-juga-inline"
                },
                rate_limit_delay=1.5,
                max_retries=3,
                timeout=20
            )
        
        super().__init__(config)

    def _change_format_date(self, text: str) -> Optional[str]:
        """
        Convert date format from 'DD MonthName YYYY' to 'YYYY-MM-DD'.
        
        Args:
            text: Date text to convert
            
        Returns:
            Formatted date string or None if parsing fails
        """
        if not text:
            return None
        
        # Month mapping
        months = {
            'january': '01', 'february': '02', 'march': '03', 'april': '04',
            'may': '05', 'june': '06', 'july': '07', 'august': '08',
            'september': '09', 'october': '10', 'november': '11', 'december': '12',
            'januari': '01', 'februari': '02', 'maret': '03', 'april': '04',
            'mei': '05', 'juni': '06', 'juli': '07', 'agustus': '08',
            'september': '09', 'oktober': '10', 'november': '11', 'desember': '12'
        }
        
        # Find date pattern DD MonthName YYYY
        match = re.search(r'(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})', text)
        if match:
            day = match.group(1).zfill(2)
            month = months.get(match.group(2).lower(), '01')
            year = match.group(3)
            return f"{year}-{month}-{day}"
        
        return None

    def _clean_bisnis_text(self, text: str) -> str:
        """
        Clean Bisnis Indonesia-specific text patterns.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        if not text or text == 'N/A':
            return text
        
        # Bisnis Indonesia-specific patterns to remove
        patterns = [
            r'Baca Juga.*',
            r'Cek Berita dan Artikel.*'
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Clean up extra whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    async def _get_total_pages(self, soup) -> int:
        """
        Get total number of pages from pagination.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Total number of pages
        """
        pagination_list = soup.find("ol", class_="pagingList")
        if not pagination_list:
            return 1
        
        page_links = pagination_list.find_all("a", href=True)
        if not page_links:
            return 1
        
        page_numbers = []
        for link in page_links:
            page_text = link.get_text(strip=True)
            if page_text.isdigit():
                page_numbers.append(int(page_text))
        
        return max(page_numbers) if page_numbers else 1

    async def _scrape_search_page(self, keyword: str, page: int = 1) -> tuple[List[Dict[str, Any]], BeautifulSoup]:
        """
        Scrape articles from a search results page.
        
        Args:
            keyword: Search keyword
            page: Page number
            
        Returns:
            Tuple of (article list, soup object)
        """
        search_url = self.config.selectors.get("search_url", "").format(keyword=quote(keyword))
        if page > 1:
            search_url += f"&page={page}"
        
        content = None
        
        # Try aiohttp first
        try:
            response = await self._make_request(search_url)
            content = await response.text()
        except Exception as e:
            # Try Selenium fallback
            self.logger.info(f"aiohttp failed for search page {page}, trying Selenium fallback: {e}")
            try:
                content = await self._fetch_content_selenium(search_url)
            except Exception as selenium_error:
                self.logger.error(f"Selenium fallback also failed: {selenium_error}")
                return [], None
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            articles = []
            article_items = soup.select(self.config.selectors.get("article_item", "div.artItem"))
            
            for item in article_items:
                try:
                    # Extract title
                    title_tag = item.select_one(self.config.selectors.get("article_title", "h4.artTitle"))
                    if not title_tag:
                        continue
                    title = title_tag.get_text(strip=True)
                    
                    # Extract link
                    link_tag = item.select_one(self.config.selectors.get("article_link", "a.artLink"))
                    if not link_tag or not link_tag.get('href'):
                        continue
                    link = link_tag['href']
                    
                    # Extract date
                    date_tag = item.select_one(self.config.selectors.get("article_date", "div.artDate"))
                    if not date_tag:
                        continue
                    
                    date_text = date_tag.get_text(strip=True)
                    formatted_date = self._change_format_date(date_text)
                    
                    if formatted_date:
                        articles.append({
                            'title': title,
                            'url': link,
                            'date': formatted_date,
                            'date_text': date_text
                        })
                
                except Exception as e:
                    self.logger.warning(f"Failed to parse article item: {e}")
                    continue
            
            return articles, soup
            
        except Exception as e:
            self.logger.error(f"Failed to scrape search page {page}: {e}")
            return [], None

    async def _extract_article_content(self, url: str) -> str:
        """
        Extract article content from Bisnis Indonesia article page.
        
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
            main_container = None
            
            for selector in content_selectors:
                main_container = soup.select_one(selector.strip())
                if main_container:
                    break
            
            if not main_container:
                self.logger.warning(f"No content container found for {url}")
                return 'N/A'
            
            # Remove unwanted elements
            unwanted_selector = self.config.selectors.get("unwanted", "")
            if unwanted_selector:
                for unwanted in main_container.select(unwanted_selector):
                    unwanted.decompose()
            
            # Extract text from paragraphs and list items
            elements = main_container.find_all(['p', 'li'])
            text_lines = []
            
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) > 10:
                    text_lines.append(text)
            
            if not text_lines:
                return 'N/A'
            
            content_text = '\n\n'.join(text_lines)
            return self._clean_bisnis_text(content_text)
            
        except Exception as e:
            self.logger.error(f"Failed to extract content from {url}: {e}")
            return 'N/A'

    async def _scrape_articles_from_source(self, keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
        """
        Scrape articles from Bisnis Indonesia source.
        
        Args:
            keywords: Keywords to search for
            start_date: Start date for article search
            end_date: End date for article search
            **kwargs: Additional parameters
            
        Returns:
            List of scraped NewsArticle objects
        """
        try:
            all_articles = []
            
            # Process each keyword separately
            for keyword in keywords:
                self.logger.info(f"Searching for keyword: {keyword}")
                
                # Get first page to check pagination
                page_articles, soup = await self._scrape_search_page(keyword, 1)
                if not soup:
                    continue
                
                total_pages = await self._get_total_pages(soup)
                self.logger.info(f"Found {total_pages} pages for keyword '{keyword}'")
                
                keyword_articles = page_articles.copy()
                should_stop = False
                
                # Check if we should stop based on date
                for article in page_articles:
                    try:
                        article_date = datetime.strptime(article['date'], "%Y-%m-%d")
                        if article_date < start_date:
                            should_stop = True
                            break
                    except ValueError:
                        continue
                
                # Scrape additional pages if needed
                if not should_stop and total_pages > 1:
                    for page in range(2, min(total_pages + 1, 6)):  # Limit to 5 pages max
                        self.logger.info(f"Scraping page {page}/{total_pages} for keyword '{keyword}'")
                        
                        page_articles, _ = await self._scrape_search_page(keyword, page)
                        if not page_articles:
                            break
                        
                        # Check dates and add articles
                        for article in page_articles:
                            try:
                                article_date = datetime.strptime(article['date'], "%Y-%m-%d")
                                if article_date < start_date:
                                    should_stop = True
                                    break
                                elif start_date <= article_date <= end_date:
                                    keyword_articles.append(article)
                            except ValueError:
                                keyword_articles.append(article)  # Include articles with unparseable dates
                        
                        if should_stop:
                            break
                        
                        await asyncio.sleep(1.5)  # Rate limiting
                
                # Filter articles by date range
                filtered_articles = []
                for article in keyword_articles:
                    try:
                        article_date = datetime.strptime(article['date'], "%Y-%m-%d")
                        if start_date <= article_date <= end_date:
                            filtered_articles.append(article)
                    except ValueError:
                        # Include articles with unparseable dates
                        filtered_articles.append(article)
                
                all_articles.extend(filtered_articles)
                self.logger.info(f"Found {len(filtered_articles)} articles for keyword '{keyword}'")
                
                # Rate limiting between keywords
                await asyncio.sleep(1.0)
            
            # Remove duplicates based on URL
            unique_articles = {}
            for article in all_articles:
                unique_articles[article['url']] = article
            
            all_articles = list(unique_articles.values())
            self.logger.info(f"Total unique articles found: {len(all_articles)}")
            
            if not all_articles:
                return []
            
            # Limit articles for performance
            max_articles = kwargs.get('max_articles', 20)
            if len(all_articles) > max_articles:
                all_articles = all_articles[:max_articles]
                self.logger.info(f"Limited to {max_articles} articles for processing")
            
            # Extract content for each article
            articles = []
            for i, article_data in enumerate(all_articles):
                try:
                    self.logger.info(f"Processing article {i+1}/{len(all_articles)}: {article_data['title'][:50]}...")
                    
                    # Extract content
                    content = await self._extract_article_content(article_data['url'])
                    
                    # Parse published date
                    published_date = datetime.utcnow()
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
                    await asyncio.sleep(1.5)
                    
                except Exception as e:
                    self.logger.error(f"Failed to process article {article_data['url']}: {e}")
                    continue
            
            self.logger.info(f"Successfully scraped {len(articles)} articles from Bisnis Indonesia")
            return articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape Bisnis Indonesia articles: {str(e)}", source=self.source_name)


# Azure Function wrapper
async def scrape_bisnis_indonesia_news(keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
    """
    Azure Function entry point for Bisnis Indonesia news scraping.
    
    Args:
        keywords: Keywords to search for
        start_date: Start date for article search
        end_date: End date for article search
        **kwargs: Additional parameters
        
    Returns:
        List of scraped NewsArticle objects
    """
    async with BisnisIndonesiaNewsScraper() as scraper:
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)