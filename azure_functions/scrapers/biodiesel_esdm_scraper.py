"""
Biodiesel ESDM Scraper for Azure Functions.
Scrapes HIP BBN Biodiesel data from ESDM API and PDFs.
"""

import asyncio
import re
import sys
import os
import tempfile
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
import aiohttp

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

# Add parent directory to Python path
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from scrapers.base_scraper import BaseNewsScraper
from scrapers.exceptions import ScrapingError
from shared.models import ScrapingConfig
from shared.logging_config import setup_logging

logger = setup_logging(__name__)


class BiodieselESDMScraper(BaseNewsScraper):
    """
    Biodiesel ESDM Scraper.
    Fetches HIP BBN Biodiesel data from Indonesian Ministry of Energy API.
    """
    
    MONTHS_MAP = {
        'Januari': 1, 'Februari': 2, 'Maret': 3, 'April': 4,
        'Mei': 5, 'Juni': 6, 'Juli': 7, 'Agustus': 8,
        'September': 9, 'Oktober': 10, 'November': 11, 'Desember': 12
    }
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize Biodiesel ESDM scraper."""
        if config is None:
            config = ScrapingConfig(
                source_name="ESDM Biodiesel",
                base_url="https://ebtke.esdm.go.id",
                selectors={
                    "api_url": "https://ebtke.esdm.go.id/api/api/artikel"
                },
                rate_limit_delay=1.0,
                max_retries=3,
                timeout=30
            )
        
        super().__init__(config)
        self._temp_dir = tempfile.mkdtemp()

    def _matches_biodiesel_criteria(self, title: str) -> bool:
        """Check if title matches biodiesel criteria."""
        keywords = ["HIP", "BBN", "JENIS", "BIODIESEL", "BULAN"]
        return all(keyword in title.upper() for keyword in keywords)

    def _extract_pdf_url_from_html(self, html_content: str) -> Optional[str]:
        """Extract PDF URL from article content."""
        if not html_content:
            return None
        match = re.search(r'href=["\'](https?://[^"\']*drive\.esdm\.go\.id[^"\']*)["\']', html_content)
        return match.group(1) if match else None

    async def _fetch_articles_from_api(self, limit: int = 200) -> List[Dict]:
        """Fetch biodiesel articles from ESDM API."""
        try:
            await self._ensure_session()
            
            api_url = f"{self.config.selectors['api_url']}?kategori_slug=pengumuman&start=0&length={limit}&is_published=true"
            
            async with self._session.get(api_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                data = await response.json()
                
                if 'data' not in data or not data['data']:
                    return []
                
                articles = []
                for article in data['data']:
                    title = article.get('judul', '').strip()
                    if self._matches_biodiesel_criteria(title):
                        date_str = article.get('tanggal_publikasi') or article.get('tgl_upload', '')
                        slug = article.get('slug', '')
                        konten = article.get('konten', '')
                        pdf_url = self._extract_pdf_url_from_html(konten)
                        
                        articles.append({
                            "title": title,
                            "url": f"https://ebtke.esdm.go.id/artikel/pengumuman/{slug}",
                            "date": date_str,
                            "pdf_url": pdf_url
                        })
                
                self.logger.info(f"Found {len(articles)} biodiesel articles")
                return articles
                
        except Exception as e:
            self.logger.error(f"Error fetching articles: {e}")
            return []

    async def _download_pdf(self, url: str) -> Optional[bytes]:
        """Download PDF from URL."""
        try:
            await self._ensure_session()
            
            if not url.startswith('http'):
                url = 'https://' + url
            if 'drive.esdm.go.id' in url and 'download' not in url:
                url = url + '&mode=list&download=1' if '?' in url else url + '?download=1'
            
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                content_type = response.headers.get('content-type', '').lower()
                if 'application/pdf' not in content_type:
                    return None
                return await response.read()
                
        except Exception as e:
            self.logger.error(f"Error downloading PDF: {e}")
            return None

    def _find_hip_value_in_table(self, table: List[List]) -> Tuple[Optional[float], Optional[str]]:
        """Extract HIP value and month from PDF table."""
        hip_value = None
        hip_month = None
        
        for row_idx, row in enumerate(table):
            if not row:
                continue
            for col_idx, cell in enumerate(row):
                text = str(cell) if cell else ""
                if '(RUPIAH/LITER)' in text.upper():
                    if row_idx + 1 >= len(table):
                        continue
                    next_row = table[row_idx + 1]
                    
                    # Find price value
                    for val in reversed(next_row):
                        if val:
                            val_clean = str(val).replace(',', '.').replace(' ', '').strip()
                            match = re.match(r'^(\d+(?:\.\d+)?)$', val_clean)
                            if match:
                                hip_value = float(match.group(1))
                                break
                    
                    # Find month
                    for val in reversed(next_row):
                        if isinstance(val, str) and re.search(
                            r'(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s+\d{4}',
                            val
                        ):
                            hip_month = val.strip()
                            break
                    
                    if hip_value:
                        return hip_value, hip_month
        
        return hip_value, hip_month

    def _extract_hip_from_pdf_bytes(self, pdf_bytes: bytes) -> Tuple[Optional[float], Optional[str]]:
        """Extract HIP data from PDF bytes."""
        if not HAS_PDFPLUMBER:
            self.logger.warning("pdfplumber not available")
            return None, None
        
        try:
            import io
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        hip_value, hip_month = self._find_hip_value_in_table(table)
                        if hip_value:
                            return hip_value, hip_month
            return None, None
        except Exception as e:
            self.logger.error(f"Error parsing PDF: {e}")
            return None, None

    async def _scrape_articles_from_source(
        self, 
        keywords: List[str], 
        start_date: datetime, 
        end_date: datetime, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Main entry point for Biodiesel ESDM data scraping."""
        try:
            max_articles = kwargs.get('max_articles', 50)
            
            self.logger.info("Fetching biodiesel articles from ESDM API")
            
            articles = await self._fetch_articles_from_api(max_articles)
            
            if not articles:
                self.logger.info("No biodiesel articles found")
                return []
            
            # Filter by date range
            filtered_articles = []
            for article in articles:
                if article.get('pdf_url'):
                    filtered_articles.append(article)
            
            self.logger.info(f"Processing {len(filtered_articles)} articles with PDFs")
            
            # Extract data from PDFs
            all_data = []
            for article in filtered_articles[:max_articles]:
                if not article.get('pdf_url'):
                    continue
                
                self.logger.info(f"Processing: {article['title'][:50]}...")
                
                pdf_bytes = await self._download_pdf(article['pdf_url'])
                if not pdf_bytes:
                    continue
                
                hip_value, hip_month = self._extract_hip_from_pdf_bytes(pdf_bytes)
                
                if hip_value:
                    all_data.append({
                        'Date': article.get('date'),
                        'Bulan HIP': hip_month,
                        'HIP Biodiesel IDR/L': int(hip_value * 1000)  # Convert to actual value
                    })
                    self.logger.info(f"Extracted HIP: {hip_value} for {hip_month}")
                
                await asyncio.sleep(0.5)
            
            results = [{
                'type': 'biodiesel_hip',
                'data': all_data,
                'fetch_date': datetime.now().isoformat(),
                'articles_processed': len(filtered_articles)
            }]
            
            self.logger.info(f"Successfully extracted {len(all_data)} HIP biodiesel entries")
            return results
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape Biodiesel ESDM: {str(e)}", source=self.source_name)

    async def scrape_news(
        self, 
        keywords: List[str], 
        start_date: datetime, 
        end_date: datetime, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Override base scrape_news to bypass object validation.
        The Biodiesel scraper returns structured data, not standard articles.
        """
        return await self._scrape_articles_from_source(
            keywords, start_date, end_date, **kwargs
        )


async def scrape_biodiesel_esdm(
    max_articles: int = 50,
    **kwargs
) -> List[Dict]:
    """Azure Function entry point for Biodiesel ESDM scraping."""
    async with BiodieselESDMScraper() as scraper:
        return await scraper._scrape_articles_from_source(
            [], datetime.now(), datetime.now(),
            max_articles=max_articles, **kwargs
        )
