"""
Contoh penggunaan sistem scraping dengan Google RSS fallback dan auto-content scraping.

Author: VeloCT Development Team
Date: 2025-12-31
"""

from datetime import datetime
from news_scraper_helper import (
    scrape_cnbc_with_rss,
    scrape_kompas_with_rss,
    scrape_tempo_with_rss,
    scrape_all_platforms_with_rss,
    save_to_excel
)


def example_1_single_platform_with_content():
    """
    Contoh 1: Scraping single platform (CNBC) dengan auto-scraping konten.
    """
    print("\n" + "="*80)
    print("CONTOH 1: SCRAPING CNBC + GOOGLE RSS (WITH AUTO-CONTENT SCRAPING)")
    print("="*80)

    df = scrape_cnbc_with_rss(
        keyword="pertamina",
        tanggal="2025-12-30",
        scrape_content=True  # Default, akan scrape konten artikel Google RSS
    )

    if df is not None and not df.empty:
        print(f"\n✓ Total artikel: {len(df)}")
        print(f"✓ Artikel dengan konten: {df['content'].notna().sum()}")
        print(f"✓ Artikel tanpa konten: {(df['content'] == '').sum()}")

        # Preview
        print("\nPreview:")
        for idx, row in df.head(5).iterrows():
            content_len = len(row['content']) if row['content'] else 0
            print(f"  - {row['title'][:50]}... ({content_len} chars)")

        # Save to Excel
        save_to_excel(df, keyword="pertamina_cnbc")
    else:
        print("\n✗ Tidak ada hasil")


def example_2_single_platform_without_content():
    """
    Contoh 2: Scraping tanpa auto-content (lebih cepat).
    """
    print("\n" + "="*80)
    print("CONTOH 2: SCRAPING CNBC + GOOGLE RSS (WITHOUT CONTENT SCRAPING)")
    print("="*80)

    df = scrape_cnbc_with_rss(
        keyword="biodiesel",
        tanggal="2025-12-30",
        scrape_content=False  # Skip content scraping untuk kecepatan
    )

    if df is not None and not df.empty:
        print(f"\n✓ Total artikel: {len(df)}")
        print("⚠ Artikel dari Google RSS tidak punya konten (scrape_content=False)")

        # Save to Excel
        save_to_excel(df, keyword="biodiesel_cnbc_no_content")
    else:
        print("\n✗ Tidak ada hasil")


def example_3_all_platforms():
    """
    Contoh 3: Scraping dari semua platform dengan auto-content.
    """
    print("\n" + "="*80)
    print("CONTOH 3: SCRAPING ALL PLATFORMS + GOOGLE RSS (WITH AUTO-CONTENT)")
    print("="*80)

    df = scrape_all_platforms_with_rss(
        keyword="migas",
        tanggal="2025-12-30",
        platforms=['cnbc', 'kompas', 'tempo'],
        scrape_content=True
    )

    if df is not None and not df.empty:
        print(f"\n✓ Total artikel unik: {len(df)}")

        # Breakdown per platform
        print("\nBreakdown per platform:")
        platform_counts = df['platform'].value_counts()
        for platform, count in platform_counts.items():
            print(f"  - {platform}: {count} artikel")

        # Content statistics
        has_content = df['content'].notna() & (df['content'] != '')
        print(f"\n✓ Artikel dengan konten: {has_content.sum()}")
        print(f"✗ Artikel tanpa konten: {(~has_content).sum()}")

        # Save to Excel
        save_to_excel(df, keyword="migas_all_platforms")
    else:
        print("\n✗ Tidak ada hasil")


def example_4_compare_platform_vs_google():
    """
    Contoh 4: Membandingkan hasil dari platform vs Google RSS.
    """
    print("\n" + "="*80)
    print("CONTOH 4: COMPARE PLATFORM VS GOOGLE RSS")
    print("="*80)

    from code_scrapping.cnbc_id import main_cnbc
    from code_scrapping.scrapping_google_news import main_google_news

    keyword = "kurs"
    tanggal = "2025-12-30"

    # Scrape dari CNBC saja
    print("\n[1] Scraping dari CNBC...")
    df_cnbc = main_cnbc(keyword=keyword, tanggal=tanggal)

    # Scrape dari Google RSS saja
    print("\n[2] Scraping dari Google RSS...")
    df_google = main_google_news(keyword=keyword, tanggal=tanggal)

    # Compare
    cnbc_count = len(df_cnbc) if df_cnbc is not None else 0
    google_count = len(df_google) if df_google is not None else 0

    print(f"\n{'─'*70}")
    print("COMPARISON RESULTS")
    print(f"{'─'*70}")
    print(f"CNBC: {cnbc_count} artikel")
    print(f"Google RSS: {google_count} artikel")

    if df_cnbc is not None and df_google is not None and not df_cnbc.empty and not df_google.empty:
        # Normalize URLs for comparison
        cnbc_urls = set(df_cnbc['url'].str.lower().str.replace('www.', '').str.split('?').str[0])
        google_urls = set(df_google['url'].str.lower().str.replace('www.', '').str.split('?').str[0])

        only_cnbc = len(cnbc_urls - google_urls)
        only_google = len(google_urls - cnbc_urls)
        both = len(cnbc_urls & google_urls)

        print(f"\nHanya di CNBC: {only_cnbc}")
        print(f"Hanya di Google: {only_google}")
        print(f"Di kedua-duanya: {both}")

        print(f"\n💡 Insight: Google RSS menemukan {only_google} artikel tambahan yang tidak ada di CNBC!")


def example_5_batch_scraping():
    """
    Contoh 5: Batch scraping untuk multiple keywords.
    """
    print("\n" + "="*80)
    print("CONTOH 5: BATCH SCRAPING MULTIPLE KEYWORDS")
    print("="*80)

    keywords = ["pertamina", "biodiesel", "migas", "kurs"]
    tanggal = datetime.now().strftime('%Y-%m-%d')

    results = {}

    for keyword in keywords:
        print(f"\n{'─'*70}")
        print(f"Scraping keyword: {keyword}")
        print(f"{'─'*70}")

        df = scrape_all_platforms_with_rss(
            keyword=keyword,
            tanggal=tanggal,
            platforms=['cnbc', 'kompas'],  # Pilih 2 platform untuk kecepatan
            scrape_content=True
        )

        if df is not None and not df.empty:
            filename = save_to_excel(df, keyword=keyword)
            results[keyword] = {
                'total': len(df),
                'filename': filename,
                'platforms': df['platform'].value_counts().to_dict()
            }
        else:
            results[keyword] = None

    # Summary
    print("\n" + "="*80)
    print("BATCH SCRAPING SUMMARY")
    print("="*80)

    for keyword, result in results.items():
        if result:
            print(f"\n{keyword.upper()}:")
            print(f"  ✓ Total: {result['total']} artikel")
            print(f"  ✓ File: {result['filename']}")
            print(f"  ✓ Platforms: {result['platforms']}")
        else:
            print(f"\n{keyword.upper()}:")
            print(f"  ✗ No results")


def example_6_manual_content_scraping():
    """
    Contoh 6: Manual scraping konten untuk artikel tertentu.
    """
    print("\n" + "="*80)
    print("CONTOH 6: MANUAL CONTENT SCRAPING")
    print("="*80)

    from helpers.content_scraper_helper import scrape_article_content

    # Scrape tanpa konten dulu (cepat)
    df = scrape_cnbc_with_rss(
        keyword="pertamina",
        tanggal="2025-12-30",
        scrape_content=False  # Skip auto-scraping
    )

    if df is not None and not df.empty:
        print(f"\n✓ Total artikel: {len(df)}")

        # Manual scrape konten untuk 5 artikel pertama saja
        print("\nManual scraping konten untuk 5 artikel pertama...")

        for idx in range(min(5, len(df))):
            row = df.iloc[idx]
            url = row['url']

            if 'news.google.com' not in url:  # Skip Google redirect URLs
                print(f"\n  [{idx+1}] Scraping: {url[:60]}...")
                content = scrape_article_content(url)

                if content:
                    df.at[idx, 'content'] = content
                    print(f"    ✓ Success ({len(content)} chars)")
                else:
                    print(f"    ✗ Failed")

        # Save
        save_to_excel(df, keyword="pertamina_manual_scraping")


# Run examples
if __name__ == '__main__':
    import sys

    print("\n" + "="*80)
    print("SISTEM SCRAPING NEWS DENGAN GOOGLE RSS FALLBACK")
    print("Auto-Content Scraping Feature")
    print("="*80)

    if len(sys.argv) > 1:
        example_num = sys.argv[1]
        examples = {
            '1': example_1_single_platform_with_content,
            '2': example_2_single_platform_without_content,
            '3': example_3_all_platforms,
            '4': example_4_compare_platform_vs_google,
            '5': example_5_batch_scraping,
            '6': example_6_manual_content_scraping,
        }

        if example_num in examples:
            examples[example_num]()
        else:
            print(f"\nContoh {example_num} tidak ditemukan!")
            print("Available examples: 1, 2, 3, 4, 5, 6")
    else:
        # Run semua contoh
        print("\nRunning all examples...\n")

        # Run contoh 1 saja untuk demo
        example_1_single_platform_with_content()

        print("\n" + "="*80)
        print("UNTUK RUN CONTOH LAINNYA:")
        print("  python example_usage.py 1  # Contoh 1")
        print("  python example_usage.py 2  # Contoh 2")
        print("  python example_usage.py 3  # Contoh 3")
        print("  python example_usage.py 4  # Contoh 4")
        print("  python example_usage.py 5  # Contoh 5")
        print("  python example_usage.py 6  # Contoh 6")
        print("="*80)
