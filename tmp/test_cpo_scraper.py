"""
Test CPO scraper langsung ke GAPKI untuk cek apakah bisa scrape data terbaru.
"""
import asyncio, sys, os
sys.path.insert(0, r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions')

from scrapers.cpo_scraper import CPOPriceScraper
from datetime import datetime

async def main():
    last_date = "2026-01-13"
    print(f"Testing GAPKI CPO scraper (last_date={last_date})...")
    print("=" * 60)

    async with CPOPriceScraper() as scraper:
        # Step 1: cek pagination
        print("1. Get max pagination...")
        try:
            max_page = await scraper._get_max_pagination()
            print(f"   max_page = {max_page}")
        except Exception as e:
            print(f"   ERROR: {e}")
            return

        # Step 2: scrape halaman 1
        print("\n2. Scrape halaman 1 (list artikel)...")
        try:
            base_url = scraper.config.selectors["articles_url"]
            articles = await scraper._scrape_articles_from_page(base_url)
            print(f"   Found {len(articles)} artikel di halaman 1:")
            for a in articles[:10]:
                print(f"   [{a['upload_date']}] {a['title'][:70]}")
        except Exception as e:
            print(f"   ERROR: {e}")
            return

        # Step 3: filter yang lebih baru dari last_date
        new_articles = [a for a in articles if a['upload_date'] > last_date]
        print(f"\n3. Artikel baru setelah {last_date}: {len(new_articles)}")
        for a in new_articles:
            print(f"   [{a['upload_date']}] {a['title'][:70]}")
            print(f"   URL: {a['url']}")

        # Step 4: extract harga dari artikel pertama yang baru
        if new_articles:
            print(f"\n4. Extract harga dari artikel pertama...")
            a = new_articles[0]
            try:
                harga_list = await scraper._extract_cpo_price(a['url'], a['title'])
                print(f"   Hasil: {harga_list}")
            except Exception as e:
                print(f"   ERROR: {e}")
        else:
            # Coba ambil artikel terbaru yang ada untuk test parse
            if articles:
                print(f"\n4. Test extract harga dari artikel terbaru (untuk diagnosa)...")
                a = articles[0]
                print(f"   URL: {a['url']}")
                try:
                    harga_list = await scraper._extract_cpo_price(a['url'], a['title'])
                    print(f"   Hasil: {harga_list}")
                except Exception as e:
                    print(f"   ERROR: {e}")

asyncio.run(main())
