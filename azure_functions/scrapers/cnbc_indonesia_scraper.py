"""
CNBC Indonesia News Scraper for Azure Functions.
Implements scraping functionality for CNBC Indonesia news articles using search-based scraping.
"""

import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, quote

from bs4 import BeautifulSoup

from .base_scraper import BaseNewsScraper
from .exceptions import ScrapingError, NetworkError, ContentExtractionError
from ..shared.models import NewsArticle, ScrapingConfig


class CNBCIndonesiaNewsScraper(BaseNewsScraper):
    """
    CNBC Indonesia News Scraper implementation.
    Scrapes news articles from CNBC Indonesia using search functionality.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize CNBC Indonesia scraper with default configuration."""
        if config is None:
            config = ScrapingConfig(
                source_name="CNBC Indonesia",
                base_url="https://www.cnbcindonesia.com",
                selectors={
                    "search_url": "https://www.cnbcindonesia.com/search?query={keyword}",
                    "article_item": "article",
                    "article_link": "a.group",
                    "article_title": "h2",
                    "article_date": "span.text-xs.text-gray",
                    "article_content": "div.detail-text, div.detail_text",
                    "pagination": "div.flex.gap-1.items-center.justify-center.m-0",
                    "unwanted": "script, style, iframe, figure, table, div[class*='ads'], div[class*='related'], div[class*='sisip'], div[class*='baca'], div[class*='lihatjg'], div[class*='linksisip']"
                },
                rate_limit_delay=1.0,
                max_retries=3,
                timeout=20
            )
        
        super().__init__(config)

    def _clean_date_cnbc(self, raw_date: str) -> str:
        """
        Convert relative date format to absolute date format.
        
        Args:
            raw_date: Raw date string from CNBC Indonesia
            
        Returns:
            Formatted date string in 'DD MMM YYYY' format
        """
        if not raw_date:
            return ""
        
        now = datetime.now()
        raw_date_lower = raw_date.strip().lower()
        
        # Handle years ago
        if match_tahun := re.search(r"(\d+)\s*tahun", raw_date_lower):
            years_ago = int(match_tahun.group(1))
            target_date = now - timedelta(days=years_ago * 365)
            return target_date.strftime("%d %b %Y")
        
        # Handle months ago
        if match_bulan := re.search(r"(\d+)\s*bulan", raw_date_lower):
            months_ago = int(match_bulan.group(1))
            target_date = now - timedelta(days=months_ago * 30)
            return target_date.strftime("%d %b %Y")
        
        # Handle weeks ago
        if match_minggu := re.search(r"(\d+)\s*minggu", raw_date_lower):
            weeks_ago = int(match_minggu.group(1))
            target_date = now - timedelta(weeks=weeks_ago)
            return target_date.strftime("%d %b %Y")
        
        # Handle days ago
        if match_hari := re.search(r"(\d+)\s*hari", raw_date_lower):
            days_ago = int(match_hari.group(1))
            target_date = now - timedelta(days=days_ago)
            return target_date.strftime("%d %b %Y")
        
        # Handle hours/minutes ago
        if "yang lalu" in raw_date_lower:
            match_jam = re.search(r"(\d+)\s*jam", raw_date_lower)
            hours_ago = int(match_jam.group(1)) if match_jam else 0
            match_menit = re.search(r"(\d+)\s*menit", raw_date_lower)
            minutes_ago = int(match_menit.group(1)) if match_menit else 0
            delta = timedelta(hours=hours_ago, minutes=minutes_ago)
            target_datetime = now - delta
            return target_datetime.strftime("%d %b %Y")
        
        # Handle Indonesian month names
        bulan_id_to_en = {
            'januari': 'Jan', 'februari': 'Feb', 'maret': 'Mar', 'april': 'Apr',
            'mei': 'May', 'juni': 'Jun', 'juli': 'Jul', 'agustus': 'Aug',
            'september': 'Sep', 'oktober': 'Oct', 'november': 'Nov', 'desember': 'Dec'
        }
        
        for id_month, en_month in bulan_id_to_en.items():
            if id_month in raw_date_lower:
                raw_date_lower = raw_date_lower.replace(id_month, en_month)
                break
        
        # Handle absolute date format
        if match_tanggal := re.match(r"(\d{1,2}\s+\w+\s+\d{4})", raw_date_lower):
            return match_tanggal.group(1).strip()
        
        return raw_date

    def _clean_cnbc_indonesia_text(self, text: str) -> str:
        """
        Clean CNBC Indonesia-specific text patterns.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        if not text or text == 'N/A':
            return text
        
        # Remove Jakarta prefix
        if text.startswith("Jakarta, CNBC Indonesia"):
            text = re.sub(r"^Jakarta, CNBC Indonesia\s*[-–]\s*", "", text)
        
        # Remove parenthetical short text
        if text.startswith("(") and text.endswith(")") and len(text) < 20:
            return ""
        
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    async def _get_total_pages(self, soup) -> int:
        """
        Get total number of pages from pagination.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Total number of pages
        """
        try:
            # Look for pagination container
            pagination = soup.find("div", class_="flex gap-1 items-center justify-center m-0")
            if not pagination:
                # Fallback: look for any links with page parameter
                all_links = soup.find_all("a", href=re.compile(r"[?&]page=\d+"))
                if not all_links:
                    return 1
                page_links = all_links
            else:
                page_links = pagination.find_all("a", href=True)
            
            page_numbers = []
            for link in page_links:
                href = link.get("href", "")
                match = re.search(r"[?&]page=(\d+)", href)
                if match:
                    page_numbers.append(int(match.group(1)))
                
                text = link.get_text(strip=True)
                if text.isdigit():
                    page_numbers.append(int(text))
            
            return max(page_numbers) if page_numbers else 1
            
        except Exception:
            return 1

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
        
        try:
            response = await self._make_request(search_url)
            content = await response.text()
            soup = BeautifulSoup(content, 'html.parser')
            
            articles = []
            article_items = soup.select(self.config.selectors.get("article_item", "article"))
            
            for idx, item in enumerate(article_items, 1):
                try:
                    # Extract link
                    link_tag = item.select_one(self.config.selectors.get("article_link", "a.group"))
                    if not link_tag or not link_tag.get('href'):
                        continue
                    
                    link = link_tag['href']
                    if link.startswith("/"):
                        link = self.base_url + link
                    
                    # Extract title
                    title_tag = link_tag.select_one(self.config.selectors.get("article_title", "h2"))
                    if not title_tag:
                        continue
                    title = title_tag.get_text(strip=True)
                    
                    # Extract date
                    date_tag = link_tag.select_one(self.config.selectors.get("article_date", "span.text-xs.text-gray"))
                    if not date_tag:
                        continue
                    
                    raw_date = date_tag.get_text(strip=True)
                    formatted_date = self._clean_date_cnbc(raw_date)
                    
                    self.logger.debug(f"Article {idx}: {title[:50]}... Date: {formatted_date}")
                    
                    articles.append({
                        'title': title,
                        'url': link,
                        'date': formatted_date,
                        'raw_date': raw_date
                    })
                
                except Exception as e:
                    self.logger.warning(f"Failed to parse article item {idx}: {e}")
                    continue
            
            return articles, soup
            
        except Exception as e:
            self.logger.error(f"Failed to scrape search page {page}: {e}")
            return [], None

    async def _extract_article_content(self, url: str) -> str:
        """
        Extract article content from CNBC Indonesia article page.
        
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
            content_div = None
            
            for selector in content_selectors:
                content_div = soup.select_one(selector.strip())
                if content_div:
                    break
            
            if not content_div:
                self.logger.warning(f"No content container found for {url}")
                return 'N/A'
            
            # Remove unwanted elements
            unwanted_selector = self.config.selectors.get("unwanted", "")
            if unwanted_selector:
                for unwanted in content_div.select(unwanted_selector):
                    unwanted.decompose()
            
            # Remove unwanted divs by class patterns
            for div in content_div.find_all("div"):
                class_str = " ".join(div.get("class", []))
                if any(x in class_str for x in ["ads", "related", "sisip", "baca", "lihatjg", "linksisip"]):
                    div.decompose()
            
            # Extract text from paragraphs
            all_text_lines = []
            
            for p in content_div.find_all("p"):
                text = p.get_text(strip=True)
                if text and len(text) > 15:
                    cleaned_text = self._clean_cnbc_indonesia_text(text)
                    if cleaned_text:
                        all_text_lines.append(cleaned_text)
            
            # Extract text from lists
            for ol in content_div.find_all(["ol", "ul"]):
                for li in ol.find_all("li", recursive=False):
                    text = li.get_text(strip=True)
                    if text and len(text) > 15:
                        all_text_lines.append(text)
            
            if not all_text_lines:
                return 'N/A'
            
            content_text = '\n\n'.join(all_text_lines)
            return content_text
            
        except Exception as e:
            self.logger.error(f"Failed to extract content from {url}: {e}")
            return 'N/A'

    async def _scrape_articles_from_source(self, keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
        """
        Scrape articles from CNBC Indonesia source.
        
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
                        article_date = datetime.strptime(article['date'], "%d %b %Y")
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
                                article_date = datetime.strptime(article['date'], "%d %b %Y")
                                if article_date < start_date:
                                    should_stop = True
                                    break
                                elif start_date <= article_date <= end_date:
                                    keyword_articles.append(article)
                            except ValueError:
                                keyword_articles.append(article)  # Include articles with unparseable dates
                        
                        if should_stop:
                            break
                        
                        await asyncio.sleep(1.0)  # Rate limiting
                
                # Filter articles by date range
                filtered_articles = []
                for article in keyword_articles:
                    try:
                        article_date = datetime.strptime(article['date'], "%d %b %Y")
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
                        published_date = datetime.strptime(article_data['date'], '%d %b %Y')
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
            
            self.logger.info(f"Successfully scraped {len(articles)} articles from CNBC Indonesia")
            return articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape CNBC Indonesia articles: {str(e)}", source=self.source_name)


# Azure Function wrapper
async def scrape_cnbc_indonesia_news(keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
    """
    Azure Function entry point for CNBC Indonesia news scraping.
    
    Args:
        keywords: Keywords to search for
        start_date: Start date for article search
        end_date: End date for article search
        **kwargs: Additional parameters
        
    Returns:
        List of scraped NewsArticle objects
    """
    async with CNBCIndonesiaNewsScraper() as scraper:
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)