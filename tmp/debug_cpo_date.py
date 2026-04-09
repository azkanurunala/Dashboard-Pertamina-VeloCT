"""
Debug: cek format teks artikel GAPKI untuk memahami pola tanggal harga CPO.
"""
import asyncio, sys, re
sys.path.insert(0, r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions')
from scrapers.cpo_scraper import CPOPriceScraper

URLS = [
    # Artikel terbaru (parsed_date=None)
    ("2026-04-02", "https://gapki.id/news/2026/04/06/posisi-harga-komoditas-pada-penutupan-bursa-pasar-fisik-2-april-2026/"),
    ("2026-03-31", "https://gapki.id/news/2026/04/01/posisi-harga-komoditas-pada-penutupan-bursa-pasar-fisik-31-maret-2026/"),
    # Artikel lama yang berhasil (price_date != upload_date)
    ("2026-01-12", "https://gapki.id/news/2026/01/12/posisi-harga-komoditas-pada-penutupan-bursa-pasar-fisik-9-januari-2026/"),
]

async def main():
    async with CPOPriceScraper() as scraper:
        for upload_date, url in URLS:
            print(f"\n{'='*60}")
            print(f"upload_date={upload_date}")
            print(f"URL: {url}")
            content = await scraper._fetch_content(url)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'lxml')
            paragraphs = soup.select("div.nv-content-wrap.entry-content p")
            print(f"Paragraphs: {len(paragraphs)}")
            for p in paragraphs:
                text = p.get_text().strip()
                if text and ('KPB' in text.upper() or 'CPO' in text.upper() or 'IDR' in text or 'Rp' in text):
                    print(f"\n  [KPB/CPO para]:\n  {text[:400]}")

asyncio.run(main())
