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
        """Transform raw API data to structured format matching data_eia_market table."""
        rows = []
        
        for series_id, records in all_data.items():
            # Get human readable name
            series_name = self.SERIES_IDS.get(series_id, series_id)
            
            for record in records:
                period = record.get('period')
                value = record.get('value')
                
                if period and value and value != 'w':
                    try:
                        # Parse date from period "YYYY-MM"
                        year, month = map(int, period.split('-'))
                        report_date = datetime(year, month, 1).strftime('%Y-%m-%d')
                        
                        float_value = round(float(value), 2)
                        
                        row = {
                            'report_date': report_date,
                            'series_id': series_name,
                            'value': float_value,
                            'uom': 'million barrels/day' # Standard unit for these EIA series
                        }
                        rows.append(row)
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"Skipping record due to error: {e}")
                        continue
        
        return rows

    def pivot_data(self, rows: List[Dict]) -> List[Dict]:
        """Pivot the long-format data into wide-format for the database."""
        import pandas as pd
        
        if not rows:
            return []
            
        df = pd.DataFrame(rows)
        
        # Pivot
        # index: report_date
        # columns: series_id
        # values: value
        
        df_pivoted = df.pivot_table(
            index='report_date', 
            columns='series_id', 
            values='value', 
            aggfunc='first'
        ).reset_index()
        
        # Parse date to bulan/tahun
        df_pivoted['date_obj'] = pd.to_datetime(df_pivoted['report_date'])
        df_pivoted['tahun'] = df_pivoted['date_obj'].dt.year
        df_pivoted['bulan'] = df_pivoted['date_obj'].dt.month.map(self.NUMBER_TO_MONTH)
        
        # Map column names to DB schema
        # Schema: world_total_production, opec, non_opec, crude_oil, other_liquids, world_total_consumption, oecd, non_oecd
        
        column_mapping = {
            'World Total Production': 'world_total_production',
            'OPEC Production': 'opec',
            'Non-OPEC Production': 'non_opec',
            'Crude Oil': 'crude_oil',
            'World Total Consumption': 'world_total_consumption',
            'OECD Consumption': 'oecd',
            # Add missing ones if they exist in source or calculate them
        }
        
        # Calculate 'non_oecd' and 'other_liquids' if possible or missing
        # 'other_liquids' = World Total Production - Crude Oil? Or provided by API?
        # 'Non-OECD' = World Consumption - OECD
        
        if 'World Total Production' in df_pivoted.columns and 'Crude Oil' in df_pivoted.columns:
            df_pivoted['other_liquids'] = df_pivoted['World Total Production'] - df_pivoted['Crude Oil']
            
        if 'World Total Consumption' in df_pivoted.columns and 'OECD Consumption' in df_pivoted.columns:
            df_pivoted['non_oecd'] = df_pivoted['World Total Consumption'] - df_pivoted['OECD Consumption']
            
        # Apply renaming
        df_pivoted = df_pivoted.rename(columns=column_mapping)
        
        # Keep only valid columns
        valid_cols = [
            'bulan', 'tahun', 'world_total_production', 'opec', 'non_opec', 
            'crude_oil', 'other_liquids', 'world_total_consumption', 
            'oecd', 'non_oecd', 'next_release_date'
        ]
        
        # Fill missing with None
        for col in valid_cols:
            if col not in df_pivoted.columns:
                df_pivoted[col] = None
        
        # Return dicts
        # drop helper cols
        return df_pivoted[valid_cols].to_dict('records')

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
            long_format = self.transform_data(all_data, next_release_str)
            transformed = self.pivot_data(long_format)
            
            # Map column names if needed to match database exactly
            # Database columns: bulan, tahun, world_total_production, opec, non_opec, crude_oil, ...
            
            results = [{
                'type': 'data_eia_market',
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
