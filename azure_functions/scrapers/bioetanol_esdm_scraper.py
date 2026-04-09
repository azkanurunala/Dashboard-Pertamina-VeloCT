"""
Bioetanol ESDM Scraper for Azure Functions.
Scrapes HIP BBN Bioetanol data from ESDM API and PDFs.
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


class BioetanolESDMScraper(BaseNewsScraper):
    """
    Bioetanol ESDM Scraper.
    Fetches HIP BBN Bioetanol data from Indonesian Ministry of Energy API.
    """
    
    MONTHS_MAP = {
        'Januari': 1, 'Februari': 2, 'Maret': 3, 'April': 4,
        'Mei': 5, 'Juni': 6, 'Juli': 7, 'Agustus': 8,
        'September': 9, 'Oktober': 10, 'November': 11, 'Desember': 12
    }
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize Bioetanol ESDM scraper."""
        if config is None:
            config = ScrapingConfig(
                source_name="ESDM Bioetanol",
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

    def _matches_bioetanol_criteria(self, title: str) -> bool:
        """Check if title matches bioetanol criteria."""
        keywords = ["HIP", "BBN", "JENIS", "BIOETANOL", "BULAN"]
        return all(keyword in title.upper() for keyword in keywords)

    def _extract_month_from_title(self, title: str) -> Optional[str]:
        """Extract 'Bulan XXXX YYYY' string from article title."""
        m = re.search(
            r'Bulan\s+(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s+(\d{4})',
            title, re.IGNORECASE
        )
        return f"{m.group(1)} {m.group(2)}" if m else None

    def _extract_gdrive_file_id(self, html_content: str) -> Optional[str]:
        """Extract Google Drive file ID from article HTML content."""
        if not html_content:
            return None
        m = re.search(r'drive\.google\.com/file/d/([^/?\"\']+)', html_content)
        return m.group(1) if m else None

    async def _download_gdrive_pdf(self, file_id: str) -> Optional[bytes]:
        """Download PDF from Google Drive by file ID."""
        try:
            await self._ensure_session()
            url = f"https://drive.google.com/uc?export=download&id={file_id}"
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=60), allow_redirects=True) as r:
                ct = r.headers.get('content-type', '').lower()
                if 'pdf' in ct or 'octet' in ct:
                    return await r.read()
                # Virus-scan confirm page for large files
                html = await r.text()
                m = re.search(r'confirm=([^&"]+)', html)
                if m:
                    url2 = f"{url}&confirm={m.group(1)}"
                    async with self._session.get(url2, timeout=aiohttp.ClientTimeout(total=60), allow_redirects=True) as r2:
                        return await r2.read()
            return None
        except Exception as e:
            self.logger.error(f"Error downloading GDrive PDF {file_id}: {e}")
            return None

    async def _fetch_articles_from_api(self, limit: int = 200) -> List[Dict]:
        """Fetch bioetanol articles from ESDM API."""
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
                    if self._matches_bioetanol_criteria(title):
                        date_str = article.get('tanggal_publikasi') or article.get('tgl_upload', '')
                        slug = article.get('slug', '')
                        konten = article.get('konten', '')
                        gdrive_id = self._extract_gdrive_file_id(konten)

                        articles.append({
                            "title": title,
                            "url": f"https://ebtke.esdm.go.id/artikel/pengumuman/{slug}",
                            "date": date_str,
                            "hip_month": self._extract_month_from_title(title),
                            "gdrive_id": gdrive_id,
                        })

                self.logger.info(f"Found {len(articles)} bioetanol articles")
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

    def _find_hip_value_in_table(self, table: List[List]) -> Tuple[Optional[float], Optional[str], Optional[float]]:
        """Extract HIP value, month, and tetes tebu price from PDF table."""
        hip_value = None
        hip_month = None
        harga_tetes_tebu = None
        
        for row_idx, row in enumerate(table):
            if not row:
                continue
            for col_idx, cell in enumerate(row):
                text = str(cell) if cell else ""
                
                # Look for tetes tebu header
                if 'RATA-RATA TETES TEBU' in text.upper() and 'KPB' in text.upper():
                    if row_idx + 2 >= len(table):
                        continue
                    data_row = table[row_idx + 2]
                    if col_idx + 1 < len(data_row) and data_row[col_idx + 1]:
                        val = data_row[col_idx + 1]
                        # Strip thousand separators (both '.' and ',') then parse as int
                        val_clean = re.sub(r'[.,]', '', str(val).strip())
                        if val_clean.isdigit():
                            harga_tetes_tebu = float(val_clean)
                
                # Look for HIP bioetanol header
                if 'HIP BIOETANOL' in text.upper() or 'HIP BBN' in text.upper():
                    if row_idx + 2 >= len(table):
                        continue
                    data_row = table[row_idx + 2]
                    
                    # Get month
                    if col_idx < len(data_row) and data_row[col_idx]:
                        bulan_val = str(data_row[col_idx])
                        month_match = re.search(
                            r'(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s+\d{4}',
                            bulan_val
                        )
                        if month_match:
                            hip_month = month_match.group(0).strip()
                    
                    # Get value — strip thousand separators then parse as int
                    if col_idx + 1 < len(data_row) and data_row[col_idx + 1]:
                        val = data_row[col_idx + 1]
                        val_clean = re.sub(r'[.,]', '', str(val).strip())
                        if val_clean.isdigit():
                            hip_value = float(val_clean)
        
        return hip_value, hip_month, harga_tetes_tebu

    def _extract_hip_from_pdf_bytes(self, pdf_bytes: bytes) -> Tuple[Optional[float], Optional[str], Optional[float]]:
        """Extract HIP data from PDF bytes."""
        if not HAS_PDFPLUMBER:
            self.logger.warning("pdfplumber not available")
            return None, None, None
        
        try:
            import io
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        hip_value, hip_month, harga_tetes = self._find_hip_value_in_table(table)
                        if hip_value:
                            return hip_value, hip_month, harga_tetes
            return None, None, None
        except Exception as e:
            self.logger.error(f"Error parsing PDF: {e}")
            return None, None, None

    async def _scrape_articles_from_source(
        self,
        keywords: List[str],
        start_date: datetime,
        end_date: datetime,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Main entry point for Bioetanol ESDM data scraping."""
        try:
            max_articles = kwargs.get('max_articles', 50)
            existing_months = set(kwargs.get('existing_months', []))

            self.logger.info("Fetching bioetanol articles from ESDM API")
            articles = await self._fetch_articles_from_api(max_articles)

            if not articles:
                self.logger.info("No bioetanol articles found")
                return []

            all_data = []
            for article in articles:
                hip_month = article.get('hip_month')
                if not hip_month:
                    continue
                if hip_month in existing_months:
                    self.logger.info(f"Skip (already in DB): {hip_month}")
                    continue

                gdrive_id = article.get('gdrive_id')
                if not gdrive_id:
                    self.logger.warning(f"No GDrive link for {hip_month}, skipping")
                    continue

                self.logger.info(f"Downloading PDF for {hip_month}...")
                pdf_bytes = await self._download_gdrive_pdf(gdrive_id)
                if not pdf_bytes:
                    self.logger.warning(f"Failed to download PDF for {hip_month}")
                    continue

                hip_value, _, harga_tetes = self._extract_hip_from_pdf_bytes(pdf_bytes)

                if hip_value:
                    entry = {
                        'date': article.get('date') or None,
                        'bulan_hip': hip_month,
                        'hip_bioetanol_idr_l': int(hip_value),
                    }
                    if harga_tetes:
                        entry['harga_tetes_tebu'] = int(harga_tetes)
                    all_data.append(entry)
                    self.logger.info(f"Extracted HIP: {int(hip_value * 1000)} for {hip_month}")
                else:
                    self.logger.warning(f"Could not extract HIP value from PDF for {hip_month}")

                await asyncio.sleep(0.5)

            results = [{
                'type': 'data_bioetanol_hip',
                'data': all_data,
                'fetch_date': datetime.now().isoformat(),
                'articles_processed': len(articles)
            }]

            self.logger.info(f"Successfully extracted {len(all_data)} HIP bioetanol entries")
            return results

        except Exception as e:
            raise ScrapingError(f"Failed to scrape Bioetanol ESDM: {str(e)}", source=self.source_name)


    async def scrape_news(
        self, 
        keywords: List[str], 
        start_date: datetime, 
        end_date: datetime, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Override base scrape_news to bypass object validation.
        The Bioetanol scraper returns structured data, not standard articles.
        """
        return await self._scrape_articles_from_source(
            keywords, start_date, end_date, **kwargs
        )

async def scrape_bioetanol_esdm(
    max_articles: int = 50,
    **kwargs
) -> List[Dict]:
    """Azure Function entry point for Bioetanol ESDM scraping."""
    async with BioetanolESDMScraper() as scraper:
        return await scraper._scrape_articles_from_source(
            [], datetime.now(), datetime.now(),
            max_articles=max_articles, **kwargs
        )
