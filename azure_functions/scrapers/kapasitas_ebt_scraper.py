"""
Kapasitas EBT Scraper for Azure Functions.
Fetches current EBT (Energi Baru Terbarukan) generator capacity data
from the EBTKE ESDM API.

API only returns data for the current month — run this monthly.
"""

import sys
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

import aiohttp

_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from scrapers.base_scraper import BaseNewsScraper
from scrapers.exceptions import ScrapingError
from shared.models import ScrapingConfig
from shared.logging_config import setup_logging

logger = setup_logging(__name__)

MONTH_MAP = {
    'January': 1, 'February': 2, 'March': 3, 'April': 4,
    'May': 5, 'June': 6, 'July': 7, 'August': 8,
    'September': 9, 'October': 10, 'November': 11, 'December': 12
}


class KapasitasEBTScraper(BaseNewsScraper):
    """
    EBT Capacity Scraper.
    Fetches monthly generator capacity data from EBTKE ESDM API.
    Returns data for `data_ebt_capacity` table.
    """

    API_URL = "https://ebtke.esdm.go.id/api/api/konten/data-angka"

    CAPACITY_FIELDS = [
        'plta', 'pltm', 'pltmh', 'pltp', 'plts', 'plts_atap',
        'pltb', 'pltbm', 'pltbg', 'pltsa', 'pltbn', 'plt_hybrid', 'total'
    ]

    def __init__(self, config: Optional[ScrapingConfig] = None):
        if config is None:
            config = ScrapingConfig(
                source_name="EBTKE ESDM Kapasitas",
                base_url="https://ebtke.esdm.go.id",
                selectors={},
                rate_limit_delay=1.0,
                max_retries=3,
                timeout=30
            )
        super().__init__(config)

    def _parse_float(self, value) -> Optional[float]:
        """Safely convert a value to float."""
        if value is None:
            return None
        try:
            return float(str(value).replace(',', '.'))
        except (ValueError, TypeError):
            return None

    async def _fetch_api(self) -> Optional[Dict]:
        """Fetch raw data from EBTKE API."""
        try:
            await self._ensure_session()
            async with self._session.get(
                self.API_URL,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            self.logger.error(f"Failed to fetch EBTKE API: {e}")
            return None

    async def _scrape_articles_from_source(
        self,
        keywords: List[str],
        start_date: datetime,
        end_date: datetime,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch EBT capacity data from EBTKE ESDM API.
        Returns structured data for `data_ebt_capacity` table.
        """
        try:
            raw = await self._fetch_api()
            if not raw:
                self.logger.warning("No data returned from EBTKE API")
                return []

            kapasitas = raw.get('data', {}).get('dataAngkaKapasitasPembangkit', {})
            if not kapasitas:
                self.logger.warning("dataAngkaKapasitasPembangkit not found in API response")
                return []

            bulan_nama = kapasitas.get('bulan')
            tahun = kapasitas.get('tahun')

            bulan = MONTH_MAP.get(bulan_nama)
            if not bulan:
                self.logger.warning(f"Unknown month name from API: {bulan_nama}")
                return []

            if not tahun:
                self.logger.warning("tahun not found in API response")
                return []

            row = {
                'tahun': int(tahun),
                'bulan': bulan,
            }
            for field in self.CAPACITY_FIELDS:
                row[field] = self._parse_float(kapasitas.get(field))

            self.logger.info(
                f"Fetched EBT capacity: tahun={tahun}, bulan={bulan} ({bulan_nama}), "
                f"total={row.get('total')} MW"
            )

            return [{
                'type': 'data_ebt_capacity',
                'data': [row],
                'fetch_date': datetime.now().isoformat()
            }]

        except Exception as e:
            raise ScrapingError(
                f"Failed to fetch EBT capacity data: {str(e)}",
                source=self.source_name
            )

    async def scrape_news(
        self,
        keywords: List[str],
        start_date: datetime,
        end_date: datetime,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Override to return structured data instead of news articles."""
        return await self._scrape_articles_from_source(
            keywords, start_date, end_date, **kwargs
        )
