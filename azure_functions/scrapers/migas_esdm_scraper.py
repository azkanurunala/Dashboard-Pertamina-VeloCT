"""
Migas ESDM ICP Scraper for Azure Functions.
Scrapes Indonesian Crude Price (ICP) data from ESDM website using OCR.
"""

import asyncio
import re
import sys
import os
import tempfile
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
import aiohttp

from bs4 import BeautifulSoup

# Optional imports for OCR
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import easyocr
    import numpy as np
    from PIL import Image
    import io as bytesio
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

# Add parent directory to Python path
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from scrapers.base_scraper import BaseNewsScraper
from scrapers.exceptions import ScrapingError
from shared.models import ScrapingConfig
from shared.logging_config import setup_logging

logger = setup_logging(__name__)


class MigasESDMScraper(BaseNewsScraper):
    """
    Migas ESDM ICP Scraper.
    Fetches Indonesian Crude Price data from ESDM website using PDF OCR.
    """
    
    MONTH_TO_NUMBER = {
        'januari': 1, 'februari': 2, 'maret': 3, 'april': 4, 'mei': 5, 'juni': 6,
        'juli': 7, 'agustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'desember': 12
    }
    NUMBER_TO_MONTH = {v: k.capitalize() for k, v in MONTH_TO_NUMBER.items()}
    
    MONTH_PATTERN = r"(?:Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)"
    PRICE_PATTERN = r"US\$[\s]*([\d.,]+)"
    DATE_PATTERN = None  # Built dynamically
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize Migas ESDM scraper."""
        if config is None:
            config = ScrapingConfig(
                source_name="Migas ESDM ICP",
                base_url="https://www.migas.esdm.go.id",
                selectors={
                    "icp_url": "https://www.migas.esdm.go.id/post/read/harga-minyak-mentah"
                },
                rate_limit_delay=2.0,
                max_retries=3,
                timeout=60
            )
        
        super().__init__(config)
        self._temp_dir = tempfile.mkdtemp()
        self._reader = None
        
        # Build date pattern
        self.DATE_PATTERN = rf"Ditetapkan\s+di\s+Jakarta.*?\s+(\d{{1,2}})\s+({self.MONTH_PATTERN})\s+(\d{{4}}).*?(?:MENTERI\s+ENERGI|BAHLIL|ttd)"

    def _get_ocr_reader(self):
        """Initialize OCR reader lazily."""
        if not HAS_OCR:
            return None
        if self._reader is None:
            self._reader = easyocr.Reader(['id', 'en'], gpu=False, verbose=False)
        return self._reader

    async def _fetch_icp_page(self) -> Optional[str]:
        """Fetch ICP page HTML."""
        try:
            url = self.config.selectors["icp_url"]
            content = await self._fetch_content(url)
            return content
        except Exception as e:
            self.logger.error(f"Error fetching ICP page: {e}")
            return None

    def _extract_pdf_links(self, html_content: str, last_year: Optional[int], last_month: Optional[int]) -> Dict:
        """Extract relevant PDF links from HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        pdf_links = {}
        
        tahun_pattern = re.compile(r"20\d{2}")
        rows = soup.find_all("tr")
        
        # Find year row and data row
        tahun_row = None
        data_row = None
        for i, row in enumerate(rows[:-1]):
            tds = row.find_all("td")
            for td in tds:
                b = td.find("b")
                if b and tahun_pattern.search(b.get_text()):
                    tahun_row = row
                    data_row = rows[i + 1] if i + 1 < len(rows) else None
                    break
            if tahun_row:
                break
        
        if not tahun_row or not data_row:
            return {}
        
        # Extract years
        tahun_list = []
        for td in tahun_row.find_all("td"):
            match = tahun_pattern.search(td.get_text())
            if match:
                tahun_list.append(int(match.group()))
        
        if not tahun_list:
            return {}
        
        tahun_mulai = last_year or min(tahun_list)
        
        # Extract PDF links
        data_tds = data_row.find_all("td")
        for tahun, td in zip(tahun_list, data_tds):
            if tahun < tahun_mulai:
                continue
            
            for a in td.find_all("a", href=True):
                bulan_text = a.text.strip().lower()
                bulan_angka = self.MONTH_TO_NUMBER.get(bulan_text)
                
                if not bulan_angka:
                    continue
                
                if tahun == tahun_mulai and last_month and bulan_angka <= last_month:
                    continue
                
                href = a["href"]
                if not href.startswith("http"):
                    href = f"https://migas.esdm.go.id{href}"
                
                if tahun not in pdf_links:
                    pdf_links[tahun] = []
                
                pdf_links[tahun].append({
                    "Bulan": bulan_text.capitalize(),
                    "Bulan_Angka": bulan_angka,
                    "url": href
                })
        
        return pdf_links

    async def _download_pdf(self, url: str) -> Optional[bytes]:
        """Download PDF from URL."""
        try:
            await self._ensure_session()
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                response.raise_for_status()
                return await response.read()
        except Exception as e:
            self.logger.error(f"Error downloading PDF: {e}")
            return None

    def _clean_ocr_text(self, text: str) -> str:
        """Clean OCR text for better parsing."""
        text = re.sub(r'\bUSS(\d)', r'US$\1', text)
        text = re.sub(r'\bUS8(\d{2,3}[.,]\d{2})', r'US$\1', text)
        text = re.sub(r'\bU\s*[Ss]\s*[8S\$]?\s*(?=\d)', 'US$', text)
        return text

    def _extract_icp_from_pdf_bytes(self, pdf_bytes: bytes) -> Tuple[Optional[str], Optional[float], Optional[str], Optional[float]]:
        """Extract ICP data from PDF using OCR."""
        if not HAS_PYMUPDF or not HAS_OCR:
            self.logger.warning("PyMuPDF or EasyOCR not available")
            return None, None, None, None
        
        try:
            reader = self._get_ocr_reader()
            if not reader:
                return None, None, None, None
            
            pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
            keyword_pattern = r'harga\s+rata[\s-]+rata\s+minyak\s+mentah'
            
            find_month = None
            find_price = None
            find_date = None
            find_brent = None
            
            # Process pages 2-7
            start_idx = 1  # 0-indexed, page 2
            end_idx = min(7, len(pdf))
            
            for i in range(start_idx, end_idx):
                page = pdf[i]
                pix = page.get_pixmap(dpi=300)
                img = Image.open(bytesio.BytesIO(pix.tobytes()))
                
                results = reader.readtext(np.array(img), detail=0)
                text = " ".join(results)
                text = self._clean_ocr_text(text)
                
                # Find date
                if not find_date:
                    tanggal_match = re.search(self.DATE_PATTERN, text, re.IGNORECASE | re.DOTALL)
                    if tanggal_match:
                        day = tanggal_match.group(1)
                        month_nama = tanggal_match.group(2).capitalize()
                        find_date = f"{day} {month_nama}"
                
                # Find Brent price
                if not find_brent:
                    text_upper = text.upper()
                    pattern_slc = r"(?:S\s*L\s*C|SLC)\s+(\d{1,3}[.,]\d{2})"
                    match_brent = re.search(pattern_slc, text_upper)
                    if match_brent:
                        brent_str = match_brent.group(1).replace(",", ".")
                        find_brent = float(brent_str)
                
                # Find ICP price and month
                if (not find_price or not find_month) and re.search(keyword_pattern, text, re.IGNORECASE):
                    sentences = re.split(r'[.!?]\s+', text)
                    for sentence in sentences:
                        if not re.search(keyword_pattern, sentence, re.IGNORECASE):
                            continue
                        
                        bulan_match = re.search(self.MONTH_PATTERN, sentence, re.IGNORECASE)
                        harga_match = re.search(self.PRICE_PATTERN, sentence)
                        
                        if bulan_match and harga_match:
                            find_month = bulan_match.group(0).capitalize()
                            clean_price = (
                                harga_match.group(1)
                                .replace(".", "")
                                .replace(",", ".")
                                .strip()
                            )
                            find_price = float(clean_price)
                            break
                
                if find_month and find_price and find_date and find_brent:
                    break
            
            pdf.close()
            return find_month, find_price, find_date, find_brent
            
        except Exception as e:
            self.logger.error(f"Error extracting ICP from PDF: {e}")
            return None, None, None, None

    async def _scrape_articles_from_source(
        self, 
        keywords: List[str], 
        start_date: datetime, 
        end_date: datetime, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Main entry point for Migas ESDM ICP scraping."""
        try:
            last_year = kwargs.get('last_year')
            last_month = kwargs.get('last_month')
            
            self.logger.info("Fetching ICP page from Migas ESDM")
            
            html = await self._fetch_icp_page()
            if not html:
                return []
            
            pdf_links = self._extract_pdf_links(html, last_year, last_month)
            
            if not pdf_links:
                self.logger.info("No new PDFs found")
                return []
            
            total_pdfs = sum(len(v) for v in pdf_links.values())
            self.logger.info(f"Found {total_pdfs} PDFs to process")
            
            # Process PDFs
            all_data = []
            for tahun, items in pdf_links.items():
                for item in items:
                    bulan = item["Bulan"]
                    url = item["url"]
                    
                    self.logger.info(f"Processing {tahun} {bulan}...")
                    
                    pdf_bytes = await self._download_pdf(url)
                    if not pdf_bytes:
                        continue
                    
                    find_month, find_price, find_date, find_brent = self._extract_icp_from_pdf_bytes(pdf_bytes)
                    
                    if find_month and find_price:
                        all_data.append({
                            'Tahun': tahun,
                            'Bulan': find_month,
                            'Harga': str(find_price),
                            'Harga_Brent': str(find_brent) if find_brent else None,
                            'Tanggal': find_date
                        })
                        self.logger.info(f"Extracted ICP: US${find_price} for {find_month}")
                    
                    await asyncio.sleep(1.0)
            
            results = [{
                'type': 'data_oil_prices',
                'data': all_data,
                'fetch_date': datetime.now().isoformat(),
                'pdfs_processed': total_pdfs
            }]
            
            self.logger.info(f"Successfully extracted {len(all_data)} ICP entries")
            return results
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape Migas ESDM: {str(e)}", source=self.source_name)


    async def scrape_news(
        self, 
        keywords: List[str], 
        start_date: datetime, 
        end_date: datetime, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Override base scrape_news to bypass object validation.
        The Migas ESDM scraper returns structured data, not standard articles.
        """
        return await self._scrape_articles_from_source(
            keywords, start_date, end_date, **kwargs
        )


async def scrape_migas_esdm_icp(
    last_year: Optional[int] = None,
    last_month: Optional[int] = None,
    **kwargs
) -> List[Dict]:
    """Azure Function entry point for Migas ESDM ICP scraping."""
    async with MigasESDMScraper() as scraper:
        return await scraper._scrape_articles_from_source(
            [], datetime.now(), datetime.now(),
            last_year=last_year, last_month=last_month, **kwargs
        )
