"""
CPO (Crude Palm Oil) Price Scraper for Azure Functions.
Scrapes CPO prices from GAPKI (Indonesian Palm Oil Association).
"""

import asyncio
import re
import sys
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

from bs4 import BeautifulSoup

# Add parent directory to Python path
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from scrapers.base_scraper import BaseNewsScraper
from scrapers.exceptions import ScrapingError
from shared.models import ScrapingConfig
from shared.logging_config import setup_logging

logger = setup_logging(__name__)


class CPOPriceScraper(BaseNewsScraper):
    """
    GAPKI CPO Price Scraper.
    Scrapes crude palm oil prices from Indonesian Palm Oil Association.
    """
    
    # Indonesian month mapping
    BULAN_ID = {
        "Januari": 1, "Februari": 2, "Maret": 3, "April": 4,
        "Mei": 5, "Juni": 6, "Juli": 7, "Agustus": 8,
        "September": 9, "Oktober": 10, "November": 11, "Desember": 12
    }
    
    BULAN_ABBR = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
        "Mei": 5, "Jun": 6, "Jul": 7, "Agt": 8, "Agu": 8,
        "Sep": 9, "Okt": 10, "Nov": 11, "Des": 12
    }
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize CPO price scraper."""
        if config is None:
            config = ScrapingConfig(
                source_name="GAPKI CPO",
                base_url="https://gapki.id",
                selectors={
                    "articles_url": "https://gapki.id/posisi-harga-komoditas/",
                    "main_article": "div.bdp-left-block",
                    "article_list": "div.bdp-s-medium-9.bdp-columns",
                    "article_title": "h2.bdp-post-title a, h4.bdp-post-title a",
                    "content": "div.nv-content-wrap.entry-content"
                },
                rate_limit_delay=2.0,
                max_retries=3,
                timeout=30
            )
        
        super().__init__(config)

    def _parse_date_from_title(self, title: str) -> Optional[str]:
        """Parse date from article title."""
        pattern = r'(\d{1,2})\s+(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s+(\d{4})'
        match = re.search(pattern, title)
        
        if match:
            day = int(match.group(1))
            month = self.BULAN_ID[match.group(2)]
            year = int(match.group(3))
            try:
                return f"{year:04d}-{month:02d}-{day:02d}"
            except:
                return None
        return None

    def _parse_date_in_parentheses(self, date_str: str, full_text: str, article_title: str = None) -> Optional[str]:
        """Parse date from parenthetical notation in content."""
        match = re.search(r"(\d{1,2})\s*(\w+)", date_str)
        if not match:
            return None
        
        day = int(match.group(1))
        month_str = match.group(2)
        month = None
        
        for abbr, num in self.BULAN_ABBR.items():
            if month_str.startswith(abbr):
                month = num
                break
        
        if not month:
            return None
        
        # Try to get year from article title first
        year = None
        if article_title:
            year_match = re.search(r'20\d{2}', article_title)
            if year_match:
                year = int(year_match.group(0))
        
        if not year:
            year_match = re.search(r'20\d{2}', full_text)
            if year_match:
                year = int(year_match.group(0))
        
        if not year:
            year = datetime.now().year
        
        try:
            return f"{year:04d}-{month:02d}-{day:02d}"
        except:
            return None

    async def _get_max_pagination(self) -> int:
        """Get maximum pagination count from website."""
        try:
            url = self.config.selectors["articles_url"]
            content = await self._fetch_content(url)
            soup = BeautifulSoup(content, 'lxml')
            
            pagination = soup.select_one("div.bdp-post-pagination")
            if not pagination:
                return 1
            
            page_links = pagination.select("a.page-numbers")
            max_page = 1
            
            for link in page_links:
                text = link.get_text(strip=True)
                if text.isdigit():
                    max_page = max(max_page, int(text))
            
            return max_page
            
        except Exception as e:
            self.logger.error(f"Failed to get pagination: {e}")
            return 1

    async def _scrape_articles_from_page(self, page_url: str) -> List[Dict]:
        """Scrape article list from a page."""
        try:
            content = await self._fetch_content(page_url)
            soup = BeautifulSoup(content, 'lxml')
            
            articles = []
            
            # Main article
            main_article = soup.select_one(self.config.selectors.get("main_article", "div.bdp-left-block"))
            if main_article:
                title_tag = main_article.select_one("h2.bdp-post-title a")
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    link = title_tag.get("href", "")
                    if "Posisi Harga Komoditas" in title:
                        article_date = self._parse_date_from_title(title)
                        if article_date:
                            articles.append({
                                "title": title,
                                "url": link,
                                "upload_date": article_date
                            })
            
            # Other articles
            article_containers = soup.select(self.config.selectors.get("article_list", "div.bdp-s-medium-9"))
            for container in article_containers:
                title_tag = container.select_one("h4.bdp-post-title a")
                if not title_tag:
                    continue
                
                title = title_tag.get_text(strip=True)
                link = title_tag.get("href", "")
                
                if "Posisi Harga Komoditas" not in title:
                    continue
                
                article_date = self._parse_date_from_title(title)
                if article_date:
                    articles.append({
                        "title": title,
                        "url": link,
                        "upload_date": article_date
                    })
            
            return articles
            
        except Exception as e:
            self.logger.error(f"Error scraping page: {e}")
            return []

    async def _extract_cpo_price(self, url: str, article_title: str = None) -> List[Dict]:
        """Extract CPO price from article page."""
        try:
            content = await self._fetch_content(url)
            soup = BeautifulSoup(content, 'lxml')
            
            paragraphs = soup.select("div.nv-content-wrap.entry-content p")
            harga_list = []
            
            for p in paragraphs:
                text = p.get_text()
                lines = text.split('\n')
                
                for line in lines:
                    line = line.strip()
                    
                    if "KPB" in line.upper() and "CPO" in line.upper():
                        # Pattern with date in parentheses
                        pattern_with_date = r"([\d\.]+)\s*\((\d{1,2})\s*(\w+)['']?\)"
                        matches = list(re.finditer(pattern_with_date, line))
                        
                        if matches:
                            for match in matches:
                                val = re.sub(r"[^\d]", "", match.group(1))
                                try:
                                    harga = int(val)
                                    day = match.group(2)
                                    month_abbr = match.group(3)
                                    date_str = f"{day} {month_abbr}"
                                    parsed_date = self._parse_date_in_parentheses(
                                        date_str, line, article_title
                                    )
                                    
                                    harga_list.append({
                                        "harga": harga,
                                        "parsed_date": parsed_date
                                    })
                                except:
                                    continue
                            
                            return harga_list
                        else:
                            # Try IDR pattern
                            match = re.search(r"IDR\s*([\d\.,]+)", line)
                            if match:
                                val = re.sub(r"[^\d]", "", match.group(1))
                                try:
                                    harga = int(val)
                                    harga_list.append({
                                        "harga": harga,
                                        "parsed_date": None
                                    })
                                    return harga_list
                                except:
                                    continue
            
            return harga_list
            
        except Exception as e:
            self.logger.error(f"Failed to extract CPO price: {e}")
            return []

    async def _scrape_articles_from_source(
        self, 
        keywords: List[str], 
        start_date: datetime, 
        end_date: datetime, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Main entry point for CPO price scraping.
        Returns data dictionaries instead of NewsArticle objects.
        """
        try:
            last_date = kwargs.get('last_date')
            if last_date and isinstance(last_date, str):
                last_date_str = last_date
            else:
                last_date_str = start_date.strftime("%Y-%m-%d")
            
            self.logger.info(f"Scraping GAPKI CPO prices after {last_date_str}")
            
            base_url = self.config.selectors["articles_url"]
            max_page = await self._get_max_pagination()
            
            new_articles = []
            should_stop = False
            
            for page_num in range(1, max_page + 1):
                if should_stop:
                    break
                
                if page_num == 1:
                    page_url = base_url
                else:
                    page_url = f"{base_url}page/{page_num}/"
                
                self.logger.info(f"Scraping page {page_num}...")
                articles = await self._scrape_articles_from_page(page_url)
                
                for article in articles:
                    article_date = article["upload_date"]
                    if article_date > last_date_str:
                        new_articles.append(article)
                    else:
                        should_stop = True
                        break
                
                await asyncio.sleep(2.0)
            
            self.logger.info(f"Found {len(new_articles)} new articles")
            
            if not new_articles:
                return []
            
            # Extract prices
            all_data = []
            for idx, article in enumerate(new_articles):
                self.logger.info(f"[{idx+1}/{len(new_articles)}] {article['title'][:60]}...")
                harga_list = await self._extract_cpo_price(article['url'], article['title'])
                
                for harga_data in harga_list:
                    dates = harga_data["parsed_date"] or article["upload_date"]
                    all_data.append({
                        "upload_date": article["upload_date"],
                        "price_date": dates,
                        "px_last": harga_data["harga"]
                    })
                
                await asyncio.sleep(1.0)
            
            results = [{
                'type': 'data_cpo_prices',
                'data': all_data,
                'fetch_date': datetime.now().isoformat(),
                'articles_count': len(new_articles)
            }]
            
            self.logger.info(f"Successfully scraped {len(all_data)} CPO price entries")
            return results
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape GAPKI CPO: {str(e)}", source=self.source_name)

    async def scrape_news(
        self, 
        keywords: List[str], 
        start_date: datetime, 
        end_date: datetime, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Override base scrape_news to bypass object validation.
        The CPO scraper returns structured data, not standard articles.
        """
        return await self._scrape_articles_from_source(
            keywords, start_date, end_date, **kwargs
        )


async def scrape_cpo_prices(
    last_date: Optional[str] = None,
    **kwargs
) -> List[Dict]:
    """
    Azure Function entry point for GAPKI CPO price scraping.
    
    Args:
        last_date: Last scraped date in YYYY-MM-DD format
        
    Returns:
        List of price data dictionaries
    """
    start = datetime.strptime(last_date, "%Y-%m-%d") if last_date else datetime(2020, 1, 1)
    
    async with CPOPriceScraper() as scraper:
        return await scraper._scrape_articles_from_source(
            [], start, datetime.now(), last_date=last_date, **kwargs
        )
