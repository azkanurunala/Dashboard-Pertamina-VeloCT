"""
SIPSN (Sistem Informasi Pengelolaan Sampah Nasional) Data Scraper for Azure Functions.
Fetches waste management data from Indonesia's Ministry of Environment.
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
import aiohttp

# Add parent directory to Python path
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from scrapers.base_scraper import BaseNewsScraper
from scrapers.exceptions import ScrapingError
from shared.models import ScrapingConfig
from shared.logging_config import setup_logging

logger = setup_logging(__name__)


class SIPSNDataScraper(BaseNewsScraper):
    """
    SIPSN Data Scraper.
    Fetches waste management data from Indonesia's national waste information system.
    """
    
    # Data type mapping
    DATA_TYPES = {
        'sumber': 'WTE_Sumber',       # Waste source data
        'komposisi': 'WTE_Komposisi', # Waste composition data
        'timbulan': 'WTE_Timbulan'    # Waste generation data
    }
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize SIPSN scraper."""
        if config is None:
            config = ScrapingConfig(
                source_name="SIPSN",
                base_url="https://sipsn.kemenlh.go.id",
                selectors={
                    "api_url": "https://sipsn.kemenlh.go.id/sipsn/public/home/ajax_list"
                },
                rate_limit_delay=1.0,
                max_retries=3,
                timeout=60
            )
        
        super().__init__(config)

    def _clean_column_names(self, data: List[Dict]) -> List[Dict]:
        """Clean and rename column names."""
        rename_dict = {
            'nama_dati2': 'Nama Kota/Kabupaten',
            'nama_propinsi': 'Nama Provinsi'
        }
        
        cleaned = []
        for row in data:
            cleaned_row = {}
            for key, value in row.items():
                new_key = rename_dict.get(key, key)
                cleaned_row[new_key] = value
            cleaned.append(cleaned_row)
        
        return cleaned

    async def _fetch_data(self, jenis: str, tahun: str) -> List[Dict]:
        """
        Fetch data from SIPSN API.
        
        Args:
            jenis: Data type (sumber, komposisi, timbulan)
            tahun: Year to fetch
            
        Returns:
            List of data records
        """
        try:
            await self._ensure_session()
            
            url = self.config.selectors["api_url"]
            payload = {
                'length': '-1',
                'jenis': jenis,
                'tahun': tahun
            }
            
            self.logger.info(f"Fetching {jenis} data for year {tahun}")
            
            async with self._session.post(url, data=payload,
                                          timeout=aiohttp.ClientTimeout(total=60)) as response:
                response.raise_for_status()
                data = await response.json()
                
                if 'data' in data:
                    records = data['data']
                    cleaned = self._clean_column_names(records)
                    self.logger.info(f"Got {len(cleaned)} records for {jenis}")
                    return cleaned
                    
        except Exception as e:
            self.logger.error(f"Error fetching {jenis} data: {e}")
        
        return []

    async def _scrape_articles_from_source(
        self, 
        keywords: List[str], 
        start_date: datetime, 
        end_date: datetime, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Main entry point for SIPSN data fetching.
        Returns data dictionaries instead of NewsArticle objects.
        """
        try:
            tahun = kwargs.get('year', str(datetime.now().year))
            data_types = kwargs.get('data_types', ['sumber', 'komposisi', 'timbulan'])
            
            self.logger.info(f"Fetching SIPSN data for year {tahun}")
            
            all_data = {}
            
            for jenis in data_types:
                if jenis in self.DATA_TYPES:
                    records = await self._fetch_data(jenis, tahun)
                    if records:
                        all_data[jenis] = records
                    await asyncio.sleep(1.0)  # Rate limiting
            
            if not all_data:
                self.logger.warning("No data fetched from SIPSN API")
                return []
            
            results = [{
                'type': 'sipsn_waste_data',
                'year': tahun,
                'data': all_data,
                'fetch_date': datetime.now().isoformat(),
                'data_types': list(all_data.keys())
            }]
            
            total_records = sum(len(v) for v in all_data.values())
            self.logger.info(f"Successfully fetched {total_records} total SIPSN records")
            return results
            
        except Exception as e:
            raise ScrapingError(f"Failed to fetch SIPSN data: {str(e)}", source=self.source_name)


async def scrape_sipsn_data(
    year: Optional[str] = None,
    data_types: Optional[List[str]] = None,
    **kwargs
) -> List[Dict]:
    """
    Azure Function entry point for SIPSN data scraping.
    
    Args:
        year: Year to fetch (defaults to current year)
        data_types: List of data types to fetch (sumber, komposisi, timbulan)
        
    Returns:
        List of data dictionaries
    """
    async with SIPSNDataScraper() as scraper:
        return await scraper._scrape_articles_from_source(
            [], datetime.now(), datetime.now(),
            year=year or str(datetime.now().year),
            data_types=data_types or ['sumber', 'komposisi', 'timbulan'],
            **kwargs
        )
