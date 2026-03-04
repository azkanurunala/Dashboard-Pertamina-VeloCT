"""
Migas ESDM ICP Scraper for Azure Functions.
Scrapes Indonesian Crude Price (ICP) data from ESDM website using PDF text extraction.
"""

import asyncio
import base64
import json
import re
import sys
import os
import tempfile
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
import aiohttp

from bs4 import BeautifulSoup

# Use pdfplumber for PDF text extraction (available in requirements.txt)
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


class MigasESDMScraper(BaseNewsScraper):
    """
    Migas ESDM ICP Scraper.
    Fetches Indonesian Crude Price data from ESDM website using PDF text extraction.
    """
    
    MONTH_TO_NUMBER = {
        'januari': 1, 'februari': 2, 'maret': 3, 'april': 4, 'mei': 5, 'juni': 6,
        'juli': 7, 'agustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'desember': 12
    }
    NUMBER_TO_MONTH = {v: k.capitalize() for k, v in MONTH_TO_NUMBER.items()}
    
    MONTH_PATTERN = r"(?:Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)"
    PRICE_PATTERN = r"US\$[\s]*([\d.,]+)"
    
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
        
        # Build date pattern for finding decree date
        self.DATE_PATTERN = rf"Ditetapkan\s+di\s+Jakarta.*?\s+(\d{{1,2}})\s+({self.MONTH_PATTERN})\s+(\d{{4}}).*?(?:MENTERI\s+ENERGI|BAHLIL|ttd)"

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

    @staticmethod
    def _parse_price(raw_price: str) -> Optional[float]:
        """
        Parse price string handling both Indonesian (80,09) and international (80.09) formats.
        
        ICP crude oil prices are typically between $15-$250 per barrel.
        """
        raw_price = raw_price.strip()
        
        try:
            has_dot = '.' in raw_price
            has_comma = ',' in raw_price
            
            if has_comma and not has_dot:
                # Indonesian format: "80,09" → 80.09
                result = float(raw_price.replace(",", "."))
            elif has_dot and not has_comma:
                # Could be decimal "80.09" or thousands "1.234"
                # Check: if single dot followed by exactly 2 digits at end → decimal
                dot_match = re.match(r'^(\d+)\.(\d{2})$', raw_price)
                if dot_match:
                    # "80.09" → 80.09 (decimal point)
                    result = float(raw_price)
                else:
                    # "1.234" → probably thousands separator
                    result = float(raw_price.replace(".", ""))
            elif has_dot and has_comma:
                # "1.234,56" → Indonesian thousands+decimal
                result = float(raw_price.replace(".", "").replace(",", "."))
            else:
                # No separators: "8009"
                result = float(raw_price)
            
            # Sanity check: ICP prices should be $15-$250/barrel
            # If > 250, likely a parsing error where decimal was removed
            if result > 250:
                # Try inserting decimal point 2 digits from end
                corrected = result / 100.0
                if 15.0 <= corrected <= 250.0:
                    return corrected
                return None  # Can't make sense of the value
            elif result < 15.0:
                return None  # Too low for crude oil
            
            return result
        except (ValueError, TypeError):
            return None

    async def _extract_icp_with_vision_ai(self, pdf_bytes: bytes) -> Tuple[Optional[str], Optional[float], Optional[str], Optional[float]]:
        """
        Fallback: Extract ICP data from scanned PDF using AI Vision API.
        Supports GEMINI, OPENAI, and COPILOT based on AI_TYPE env var.
        API key is always from AI_API_KEY.
        """
        ai_type = os.getenv('AI_TYPE', 'GEMINI').upper()
        api_key = os.getenv('AI_API_KEY')
        if not api_key:
            self.logger.warning("No AI_API_KEY available for Vision OCR fallback")
            return None, None, None, None
        
        try:
            import pypdfium2 as pdfium
            import io
            
            # Render first few pages to images
            pdf_doc = pdfium.PdfDocument(pdf_bytes)
            page_images_b64 = []
            
            for page_idx in range(min(len(pdf_doc), 5)):  # First 5 pages
                page = pdf_doc[page_idx]
                bitmap = page.render(scale=2)  # 2x scale for readability
                pil_image = bitmap.to_pil()
                
                # Convert to base64 PNG
                img_buffer = io.BytesIO()
                pil_image.save(img_buffer, format='PNG', optimize=True)
                img_b64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
                page_images_b64.append(img_b64)
            
            pdf_doc.close()
            
            if not page_images_b64:
                return None, None, None, None
            
            prompt_text = """Analyze this Indonesian government document (Keputusan Menteri ESDM) about ICP (Indonesian Crude Price).

Extract EXACTLY these values and return as JSON:
{
  "month": "the Indonesian month name (e.g. Januari, Februari, etc.)",
  "price": the ICP price as a decimal number (e.g. 80.09),
  "date": "the decree date in format 'DD MonthName' (e.g. '15 Januari')",
  "brent": the Brent/SLC crude oil price as a decimal number or null
}

IMPORTANT: The price should be in US dollars per barrel (typically $20-$200 range).
Return ONLY the JSON object, no other text."""

            # Build request based on AI_TYPE
            if ai_type == 'GEMINI':
                response_text = await self._call_gemini_vision(api_key, page_images_b64, prompt_text)
            elif ai_type in ('OPENAI', 'COPILOT'):
                # COPILOT uses Azure OpenAI (OpenAI-compatible format)
                response_text = await self._call_openai_vision(api_key, page_images_b64, prompt_text)
            else:
                # Default to Gemini
                response_text = await self._call_gemini_vision(api_key, page_images_b64, prompt_text)
            
            if not response_text:
                return None, None, None, None
            
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if not json_match:
                self.logger.warning(f"Could not parse AI Vision response: {response_text[:200]}")
                return None, None, None, None
            
            data = json.loads(json_match.group())
            
            find_month = data.get('month')
            find_price = data.get('price')
            find_date = data.get('date')
            find_brent = data.get('brent')
            
            # Validate price
            if find_price is not None:
                try:
                    find_price = float(find_price)
                    if find_price < 15 or find_price > 250:
                        self.logger.warning(f"AI Vision returned unlikely price: {find_price}")
                        find_price = None
                except (ValueError, TypeError):
                    find_price = None
            
            if find_brent is not None:
                try:
                    find_brent = float(find_brent)
                except (ValueError, TypeError):
                    find_brent = None
            
            if find_month:
                find_month = find_month.capitalize()
            
            self.logger.info(f"AI Vision ({ai_type}) extracted: month={find_month}, price={find_price}, date={find_date}, brent={find_brent}")
            return find_month, find_price, find_date, find_brent
            
        except Exception as e:
            self.logger.warning(f"AI Vision OCR fallback failed: {e}")
            return None, None, None, None

    async def _call_gemini_vision(self, api_key: str, images_b64: List[str], prompt: str) -> Optional[str]:
        """Call Gemini Vision API with images."""
        parts = []
        for img_b64 in images_b64:
            parts.append({
                "inline_data": {
                    "mime_type": "image/png",
                    "data": img_b64
                }
            })
        parts.append({"text": prompt})
        
        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "maxOutputTokens": 256,
                "temperature": 0.1
            }
        }
        
        model = os.getenv('GEMINI_VISION_MODEL', 'gemini-2.0-flash')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        await self._ensure_session()
        async with self._session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status != 200:
                error_text = await response.text()
                self.logger.warning(f"Gemini Vision API error ({response.status}): {error_text[:200]}")
                return None
            result = await response.json()
        
        if 'candidates' in result and result['candidates']:
            return result['candidates'][0].get('content', {}).get('parts', [{}])[0].get('text', '')
        return None

    async def _call_openai_vision(self, api_key: str, images_b64: List[str], prompt: str) -> Optional[str]:
        """Call OpenAI Vision API with images."""
        content = []
        for img_b64 in images_b64:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_b64}",
                    "detail": "low"
                }
            })
        content.append({"type": "text", "text": prompt})
        
        model = os.getenv('OPENAI_VISION_MODEL', 'gpt-4o-mini')
        endpoint = os.getenv('OPENAI_API_ENDPOINT', 'https://api.openai.com/v1/chat/completions')
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 256,
            "temperature": 0.1
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        await self._ensure_session()
        async with self._session.post(endpoint, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status != 200:
                error_text = await response.text()
                self.logger.warning(f"OpenAI Vision API error ({response.status}): {error_text[:200]}")
                return None
            result = await response.json()
        
        if 'choices' in result and result['choices']:
            return result['choices'][0].get('message', {}).get('content', '')
        return None

    async def _extract_icp_from_pdf_bytes(self, pdf_bytes: bytes) -> Tuple[Optional[str], Optional[float], Optional[str], Optional[float]]:
        """
        Extract ICP data from PDF using pdfplumber text extraction.
        Falls back to Gemini Vision API for scanned/image-based PDFs.
        
        Returns:
            (month_name, icp_price, decree_date, brent_price)
        """
        if not HAS_PDFPLUMBER:
            self.logger.warning("pdfplumber not available for PDF extraction")
            return await self._extract_icp_with_vision_ai(pdf_bytes)
        
        try:
            import io
            
            find_month = None
            find_price = None
            find_date = None
            find_brent = None
            
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                # Combine text from all pages for better matching
                all_text = ""
                for page in pdf.pages[:10]:  # Limit to first 10 pages
                    page_text = page.extract_text() or ""
                    all_text += page_text + "\n"
                
                if not all_text.strip():
                    self.logger.info("No text in PDF, trying AI Vision OCR...")
                    return await self._extract_icp_with_vision_ai(pdf_bytes)
                
                # 1. Find decree date (Ditetapkan di Jakarta...)
                date_match = re.search(
                    rf"(\d{{1,2}})\s+({self.MONTH_PATTERN})\s+(\d{{4}})",
                    all_text, re.IGNORECASE
                )
                if date_match:
                    day = date_match.group(1)
                    month_nama = date_match.group(2).capitalize()
                    find_date = f"{day} {month_nama}"
                
                # 2. Find ICP month and price
                # Look for "harga rata-rata minyak mentah" pattern
                keyword_pattern = r'harga\s+rata[\s\-]+rata\s+minyak\s+mentah'
                keyword_match = re.search(keyword_pattern, all_text, re.IGNORECASE)
                
                if keyword_match:
                    # Get the context around the keyword (up to 500 chars after)
                    start_pos = max(0, keyword_match.start() - 200)
                    end_pos = min(len(all_text), keyword_match.end() + 500)
                    context = all_text[start_pos:end_pos]
                    
                    # Find month in context
                    bulan_match = re.search(self.MONTH_PATTERN, context, re.IGNORECASE)
                    if bulan_match:
                        find_month = bulan_match.group(0).capitalize()
                    
                    # Find US$ price in context
                    price_match = re.search(self.PRICE_PATTERN, context)
                    if price_match:
                        find_price = self._parse_price(price_match.group(1))
                
                # 3. Find Brent/SLC price
                brent_patterns = [
                    r"(?:S\s*L\s*C|SLC)\s+.*?(\d{1,3}[.,]\d{2})",
                    r"Brent\s+.*?US\$\s*(\d{1,3}[.,]\d{2})",
                    r"Brent.*?(\d{2,3}[.,]\d{2})\s*(?:US\$|per\s+barel)",
                ]
                for pattern in brent_patterns:
                    brent_match = re.search(pattern, all_text, re.IGNORECASE)
                    if brent_match:
                        brent_str = brent_match.group(1).replace(",", ".")
                        try:
                            find_brent = float(brent_str)
                            break
                        except ValueError:
                            continue
                
                # 4. Fallback: try table extraction
                if not find_price:
                    for page in pdf.pages[:10]:
                        tables = page.extract_tables()
                        for table in tables:
                            if not table:
                                continue
                            for row in table:
                                if not row:
                                    continue
                                row_text = " ".join(str(cell) for cell in row if cell)
                                
                                if re.search(r'(?:ICP|harga.*mentah|rata.*rata)', row_text, re.IGNORECASE):
                                    price_match = re.search(r'(\d{2,3}[.,]\d{2})', row_text)
                                    if price_match:
                                        find_price = self._parse_price(price_match.group(1))
                                        
                                        if not find_month:
                                            month_m = re.search(self.MONTH_PATTERN, row_text, re.IGNORECASE)
                                            if month_m:
                                                find_month = month_m.group(0).capitalize()
                        
                        if find_price:
                            break
            
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
                    
                    find_month, find_price, find_date, find_brent = await self._extract_icp_from_pdf_bytes(pdf_bytes)

                    if find_month and find_price:
                        all_data.append({
                            'year': tahun,
                            'month': find_month,
                            'price': str(find_price),
                            'brent_price': str(find_brent) if find_brent else None,
                            'date_raw': find_date
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
