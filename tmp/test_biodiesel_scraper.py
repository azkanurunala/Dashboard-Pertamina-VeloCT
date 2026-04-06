"""
Test BiodieselESDMScraper — cek API dan PDF parsing.
"""
import asyncio, sys
sys.path.insert(0, r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions')
from scrapers.biodiesel_esdm_scraper import BiodieselESDMScraper
from datetime import datetime

async def main():
    print("Testing ESDM Biodiesel scraper...")
    print("=" * 60)

    async with BiodieselESDMScraper() as scraper:
        # Step 1: fetch article list
        print("1. Fetch articles from ESDM API (limit=30)...")
        articles = await scraper._fetch_articles_from_api(limit=30)
        print(f"   Found {len(articles)} biodiesel articles:")
        for a in articles[:20]:
            print(f"   [{a['date'][:10] if a['date'] else 'no-date'}] {a['title'][:60]}")
            print(f"          pdf_url: {'YES' if a['pdf_url'] else 'NO'}")

        # Step 2: test PDF extraction dari beberapa artikel terbaru
        print("\n2. Test PDF extraction (max 5 artikel terbaru):")
        count = 0
        for a in articles:
            if not a.get('pdf_url'):
                continue
            print(f"\n   Artikel: {a['title'][:60]}")
            print(f"   PDF URL: {a['pdf_url'][:80]}")
            pdf_bytes = await scraper._download_pdf(a['pdf_url'])
            if not pdf_bytes:
                print(f"   GAGAL download PDF!")
                count += 1
                if count >= 5: break
                continue
            print(f"   PDF size: {len(pdf_bytes)} bytes")
            hip_value, hip_month = scraper._extract_hip_from_pdf_bytes(pdf_bytes)
            print(f"   HIP value: {hip_value}  month: {hip_month}")
            count += 1
            if count >= 5:
                break

asyncio.run(main())
