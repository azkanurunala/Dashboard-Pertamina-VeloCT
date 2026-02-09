"""
IAEA PRIS Nuclear Data Scraper for Azure Functions.
Scrapes nuclear capacity and electrical production data from IAEA PRIS.
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd

from bs4 import BeautifulSoup

# Add parent directory to Python path
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from scrapers.base_scraper import BaseNewsScraper
from scrapers.exceptions import ScrapingError
from shared.models import ScrapingConfig


class IAEAPRISScraper(BaseNewsScraper):
    """
    IAEA PRIS Nuclear Data Scraper.
    Scrapes nuclear power statistics from IAEA PRIS database using Selenium.
    """
    
    # Countries to track
    TARGET_COUNTRIES = [
        "ARGENTINA", "BELGIUM", "BRAZIL", "BULGARIA", "CANADA", "CHINA",
        "CZECH REPUBLIC", "FINLAND", "FRANCE", "GERMANY", "HUNGARY", "INDIA",
        "IRAN", "JAPAN", "KOREA, REPUBLIC OF", "MEXICO", "NETHERLANDS",
        "PAKISTAN", "ROMANIA", "RUSSIA", "SLOVAKIA", "SLOVENIA", "SOUTH AFRICA",
        "SPAIN", "SWEDEN", "SWITZERLAND", "UKRAINE", "UNITED ARAB EMIRATES",
        "UNITED KINGDOM", "UNITED STATES OF AMERICA"
    ]
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize IAEA PRIS scraper."""
        if config is None:
            config = ScrapingConfig(
                source_name="IAEA PRIS",
                base_url="https://pris.iaea.org",
                selectors={
                    "capacity_url": "https://pris.iaea.org/PRIS/WorldStatistics/NuclearShareofElectricityGeneration.aspx",
                    "table": "table.table",
                    "table_row": "tr",
                    "table_cell": "td"
                },
                rate_limit_delay=3.0,
                max_retries=3,
                timeout=60
            )
        
        super().__init__(config)
        self.requires_selenium = True

    async def _fetch_capacity_data(self) -> List[Dict]:
        """
        Fetch nuclear capacity data from IAEA PRIS.
        
        Returns:
            List of country data dictionaries
        """
        try:
            url = self.config.selectors['capacity_url']
            content = await self._fetch_content_selenium(url)
            soup = BeautifulSoup(content, 'html.parser')
            
            data = []
            table = soup.select_one(self.config.selectors.get("table", "table.table"))
            
            if not table:
                self.logger.warning("Data table not found")
                return []
            
            rows = table.select(self.config.selectors.get("table_row", "tr"))
            headers = []
            
            for i, row in enumerate(rows):
                if i == 0:
                    # Header row
                    headers = [th.get_text(strip=True) for th in row.select('th')]
                    continue
                
                cells = row.select(self.config.selectors.get("table_cell", "td"))
                if not cells:
                    continue
                
                row_data = {}
                for j, cell in enumerate(cells):
                    if j < len(headers):
                        row_data[headers[j]] = cell.get_text(strip=True)
                
                if row_data:
                    # Filter by target countries
                    country = row_data.get('Country', '')
                    if country.upper() in self.TARGET_COUNTRIES:
                        data.append(row_data)
            
            self.logger.info(f"Fetched data for {len(data)} countries")
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to fetch capacity data: {e}")
            return []

    async def _scrape_articles_from_source(
        self, 
        keywords: List[str], 
        start_date: datetime, 
        end_date: datetime, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Main entry point for IAEA PRIS data fetching.
        Returns data dictionaries instead of NewsArticle objects.
        
        Args:
            keywords: Not used for this scraper
            start_date: Not used for this scraper  
            end_date: Not used for this scraper
            **kwargs: Additional parameters
            
        Returns:
            List of data dictionaries
        """
        try:
            self.logger.info("Fetching IAEA PRIS nuclear data")
            
            data = await self._fetch_capacity_data()
            
            if not data:
                return []
            
            # Convert to structured results
            results = [{
                'type': 'nuclear_capacity',
                'data': data,
                'fetch_date': datetime.now().isoformat(),
                'source': 'IAEA PRIS',
                'countries_count': len(data)
            }]
            
            self.logger.info(f"Successfully fetched IAEA PRIS data for {len(data)} countries")
            return results
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape IAEA PRIS: {str(e)}", source=self.source_name)


async def scrape_iaea_pris_data(**kwargs) -> List[Dict]:
    """
    Azure Function entry point for IAEA PRIS data scraping.
    
    Returns:
        List of data dictionaries with nuclear capacity information
    """
    async with IAEAPRISScraper() as scraper:
        return await scraper._scrape_articles_from_source([], datetime.now(), datetime.now(), **kwargs)
