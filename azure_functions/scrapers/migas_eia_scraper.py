"""
EIA STEO (Short-Term Energy Outlook) Data Scraper for Azure Functions.
Fetches energy production and consumption data from U.S. EIA API.
"""

import asyncio
import re
import sys
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
import aiohttp

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


class MigasEIAScraper(BaseNewsScraper):
    """
    EIA STEO Data Scraper.
    Fetches energy production/consumption data from U.S. Energy Information Administration API.
    """
    
    # Series IDs for oil production and consumption
    SERIES_IDS = {
        'PAPR_WORLD': 'World Total Production',
        'PAPR_OPEC': 'OPEC Production',
        'PAPR_NONOPEC': 'Non-OPEC Production',
        'COPR_WORLD': 'Crude Oil',
        'PATC_WORLD': 'World Total Consumption',
        'PATC_OECD': 'OECD Consumption'
    }
    
    # Indonesian month names
    NUMBER_TO_MONTH = {
        1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
        5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
        9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
    }
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize EIA scraper."""
        if config is None:
            config = ScrapingConfig(
                source_name="EIA STEO",
                base_url="https://api.eia.gov/v2/steo/data/",
                selectors={
                    "steo_url": "https://www.eia.gov/outlooks/steo/data/browser/"
                },
                rate_limit_delay=1.0,
                max_retries=3,
                timeout=30
            )
        
        super().__init__(config)
        self._api_key = os.getenv("EIA_API_KEY", "kODFA7mKVrNKWrGyFiIk5fIdlC1AKGXzba5lJxzY")

    async def get_release_dates(self) -> Dict[str, Any]:
        """Get current and next release dates from EIA website."""
        try:
            url = self.config.selectors["steo_url"]
            content = await self._fetch_content(url)
            soup = BeautifulSoup(content, 'html.parser')
            
            pub_title_div = soup.find('div', class_='pub_title')
            if not pub_title_div:
                return {'success': False, 'error': 'Could not find pub_title div'}
            
            p_tag = pub_title_div.find('p')
            if not p_tag:
                return {'success': False, 'error': 'Could not find paragraph tag'}
            
            text = p_tag.get_text()
            
            # Parse release date
            release_match = re.search(r'Release Date:\s*(\w+)\s+(\d+),\s+(\d+)', text)
            next_match = re.search(r'Next Release Date:\s*(\w+)\s+(\d+),\s+(\d+)', text)
            
            month_map = {
                'January': 1, 'February': 2, 'March': 3, 'April': 4,
                'May': 5, 'June': 6, 'July': 7, 'August': 8,
                'September': 9, 'October': 10, 'November': 11, 'December': 12
            }
            
            result = {'success': True}
            
            if release_match:
                month = month_map.get(release_match.group(1))
                if month:
                    result['release_date'] = datetime(
                        int(release_match.group(3)), month, int(release_match.group(2))
                    )
            
            if next_match:
                month = month_map.get(next_match.group(1))
                if month:
                    result['next_release_date'] = datetime(
                        int(next_match.group(3)), month, int(next_match.group(2))
                    )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get release dates: {e}")
            return {'success': False, 'error': str(e)}

    async def fetch_series_data(
        self, 
        series_id: str, 
        start: str, 
        end: str
    ) -> List[Dict]:
        """
        Fetch data for a specific series from EIA API.
        
        Args:
            series_id: EIA series identifier
            start: Start date (YYYY-MM format)
            end: End date (YYYY-MM format)
            
        Returns:
            List of data records
        """
        try:
            await self._ensure_session()
            
            params = {
                "api_key": self._api_key,
                "frequency": "monthly",
                "data[0]": "value",
                "facets[seriesId][]": series_id,
                "start": start,
                "end": end
            }
            
            async with self._session.get(self.config.base_url, params=params,
                                         timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                data = await response.json()
                
                if "response" in data and "data" in data["response"]:
                    records = data["response"]["data"]
                    self.logger.info(f"Got {len(records)} records for {series_id}")
                    return records
                else:
                    return []
                    
        except Exception as e:
            self.logger.error(f"Error fetching {series_id}: {e}")
            return []

    def transform_data(
        self, 
        all_data: Dict[str, List], 
        next_release_str: Optional[str] = None
    ) -> List[Dict]:
        """Transform raw API data to structured format."""
        period_data = {}
        
        for series_id, records in all_data.items():
            for record in records:
                period = record.get('period')
                value = record.get('value')
                
                if period and value and value != 'w':
                    if period not in period_data:
                        period_data[period] = {}
                    try:
                        period_data[period][series_id] = round(float(value), 2)
                    except (ValueError, TypeError):
                        period_data[period][series_id] = None
        
        rows = []
        for period in sorted(period_data.keys()):
            year, month = period.split('-')
            year = int(year)
            month = int(month)
            
            world_total_prod = period_data[period].get('PAPR_WORLD')
            opec = period_data[period].get('PAPR_OPEC')
            non_opec = period_data[period].get('PAPR_NONOPEC')
            crude_oil = period_data[period].get('COPR_WORLD')
            world_total_cons = period_data[period].get('PATC_WORLD')
            oecd = period_data[period].get('PATC_OECD')
            
            # Calculate derived fields
            other_liquids = None
            if world_total_prod is not None and crude_oil is not None:
                other_liquids = round(world_total_prod - crude_oil, 2)
            
            non_oecd = None
            if world_total_cons is not None and oecd is not None:
                non_oecd = round(world_total_cons - oecd, 2)
            
            row = {
                'Bulan': self.NUMBER_TO_MONTH.get(month, f'Month-{month}'),
                'Tahun': year,
                'Next Release Date': next_release_str,
                'World Total Production': world_total_prod,
                'OPEC': opec,
                'Non-OPEC': non_opec,
                'Crude Oil': crude_oil,
                'Other Liquids': other_liquids,
                'World Total Consumption': world_total_cons,
                'OECD': oecd,
                'Non-OECD': non_oecd
            }
            rows.append(row)
        
        return rows

    async def _scrape_articles_from_source(
        self, 
        keywords: List[str], 
        start_date: datetime, 
        end_date: datetime, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Main entry point for EIA data fetching.
        Returns data dictionaries instead of NewsArticle objects.
        """
        try:
            # Determine date range
            start_str = kwargs.get('start_period')
            end_str = kwargs.get('end_period')
            
            if not start_str:
                start_str = "2015-01"
            if not end_str:
                end_month = end_date.month - 1
                end_year = end_date.year
                if end_month == 0:
                    end_month = 12
                    end_year -= 1
                end_str = f"{end_year}-{end_month:02d}"
            
            self.logger.info(f"Fetching EIA data from {start_str} to {end_str}")
            
            # Get release dates
            release_info = await self.get_release_dates()
            next_release_str = None
            if release_info.get('success') and 'next_release_date' in release_info:
                next_release_str = release_info['next_release_date'].strftime('%B %d, %Y')
            
            # Fetch all series
            all_data = {}
            for series_id in self.SERIES_IDS.keys():
                records = await self.fetch_series_data(series_id, start_str, end_str)
                if records:
                    all_data[series_id] = records
                await asyncio.sleep(0.5)  # Rate limiting
            
            if not all_data:
                self.logger.warning("No data fetched from EIA API")
                return []
            
            # Transform data
            transformed = self.transform_data(all_data, next_release_str)
            
            results = [{
                'type': 'eia_steo',
                'data': transformed,
                'period': f"{start_str} to {end_str}",
                'fetch_date': datetime.now().isoformat(),
                'next_release': next_release_str
            }]
            
            self.logger.info(f"Successfully fetched {len(transformed)} months of EIA data")
            return results
            
        except Exception as e:
            raise ScrapingError(f"Failed to fetch EIA data: {str(e)}", source=self.source_name)

    async def scrape_news(
        self, 
        keywords: List[str], 
        start_date: datetime, 
        end_date: datetime, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Override base scrape_news to bypass article object validation.
        EIA STEO Returns structured data rather than news articles.
        """
        return await self._scrape_articles_from_source(
            keywords, start_date, end_date, **kwargs
        )


async def scrape_migas_eia_data(
    start_period: Optional[str] = None,
    end_period: Optional[str] = None,
    **kwargs
) -> List[Dict]:
    """
    Azure Function entry point for EIA STEO data scraping.
    
    Args:
        start_period: Start period in YYYY-MM format (optional, defaults to 2015-01)
        end_period: End period in YYYY-MM format (optional, defaults to last month)
        
    Returns:
        List of data dictionaries
    """
    async with MigasEIAScraper() as scraper:
        return await scraper._scrape_articles_from_source(
            [], datetime.now(), datetime.now(),
            start_period=start_period, end_period=end_period, **kwargs
        )
