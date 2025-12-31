"""
Helper module untuk menggabungkan scraping dari berbagai platform dengan Google RSS fallback.
Mengatasi masalah artikel yang hilang dari indexing platform dengan backup dari Google RSS.
"""

import pandas as pd
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from code_scrapping.scrapping_google_news import scrape_with_google_rss_fallback
from code_scrapping.cnbc_id import main_cnbc
from code_scrapping.kompas import main_kompas
from code_scrapping.tempo import scrape_tempo


def scrape_cnbc_with_rss(keyword, tanggal=None, scrape_content=True):
    """
    Scrape CNBC dengan Google RSS sebagai fallback.

    Args:
        keyword: Kata kunci pencarian
        tanggal: Tanggal filter (YYYY-MM-DD atau format lain)
        scrape_content: Auto-scrape konten untuk artikel Google RSS (default: True)

    Returns:
        DataFrame hasil gabungan
    """
    return scrape_with_google_rss_fallback(
        keyword=keyword,
        date=tanggal,
        platform_scraper=main_cnbc,
        scraper_args={},
        scrape_content=scrape_content
    )


def scrape_kompas_with_rss(keyword, tanggal=None, scrape_content=True):
    """
    Scrape Kompas dengan Google RSS sebagai fallback.

    Args:
        keyword: Kata kunci pencarian
        tanggal: Tanggal filter (YYYY-MM-DD atau format lain)
        scrape_content: Auto-scrape konten untuk artikel Google RSS (default: True)

    Returns:
        DataFrame hasil gabungan
    """
    return scrape_with_google_rss_fallback(
        keyword=keyword,
        date=tanggal,
        platform_scraper=main_kompas,
        scraper_args={},
        scrape_content=scrape_content
    )


def scrape_tempo_with_rss(keyword, tanggal=None, scrape_content=True):
    """
    Scrape Tempo dengan Google RSS sebagai fallback.

    Args:
        keyword: Kata kunci pencarian
        tanggal: Tanggal filter (YYYY-MM-DD atau format lain)
        scrape_content: Auto-scrape konten untuk artikel Google RSS (default: True)

    Returns:
        DataFrame hasil gabungan
    """
    def tempo_wrapper(keyword, tanggal):
        """Wrapper untuk scrape_tempo agar compatible dengan format standar"""
        results = scrape_tempo(keyword, tanggal)
        if results:
            return pd.DataFrame(results)
        return None

    return scrape_with_google_rss_fallback(
        keyword=keyword,
        date=tanggal,
        platform_scraper=tempo_wrapper,
        scraper_args={},
        scrape_content=scrape_content
    )


def scrape_all_platforms_with_rss(keyword, tanggal=None, platforms=None, scrape_content=True):
    """
    Scrape dari semua platform dengan Google RSS fallback, lalu gabungkan hasilnya.

    Args:
        keyword: Kata kunci pencarian
        tanggal: Tanggal filter (YYYY-MM-DD atau format lain)
        platforms: List platform yang ingin di-scrape (default: ['cnbc', 'kompas', 'tempo'])
        scrape_content: Auto-scrape konten untuk artikel Google RSS (default: True)

    Returns:
        DataFrame gabungan dari semua platform (sudah deduplicate)
    """
    if platforms is None:
        platforms = ['cnbc', 'kompas', 'tempo']

    all_results = []

    platform_scrapers = {
        'cnbc': scrape_cnbc_with_rss,
        'kompas': scrape_kompas_with_rss,
        'tempo': scrape_tempo_with_rss,
    }

    print(f"\n{'='*70}")
    print(f"SCRAPING FROM MULTIPLE PLATFORMS WITH GOOGLE RSS FALLBACK")
    print(f"Keyword: {keyword}")
    print(f"Date: {tanggal}")
    print(f"Platforms: {', '.join(platforms)}")
    print(f"{'='*70}\n")

    for platform in platforms:
        if platform not in platform_scrapers:
            print(f"[WARNING] Platform '{platform}' tidak dikenali, skip...")
            continue

        print(f"\n{'─'*70}")
        print(f"SCRAPING PLATFORM: {platform.upper()}")
        print(f"{'─'*70}")

        try:
            scraper = platform_scrapers[platform]
            df = scraper(keyword, tanggal, scrape_content=scrape_content)

            if df is not None and not df.empty:
                # Add source column to track which platform
                df['platform'] = platform
                all_results.append(df)
                print(f"✓ {platform.upper()}: {len(df)} articles")
            else:
                print(f"⚠ {platform.upper()}: No results")

        except Exception as e:
            print(f"✗ {platform.upper()}: Error - {e}")
            continue

    if not all_results:
        print("\n[FINAL] Tidak ada hasil dari semua platform")
        return None

    # Combine all results
    print(f"\n{'='*70}")
    print(f"COMBINING RESULTS FROM ALL PLATFORMS")
    print(f"{'='*70}")

    df_combined = pd.concat(all_results, ignore_index=True)

    print(f"\nTotal before deduplication: {len(df_combined)} articles")

    # Deduplicate based on URL (across all platforms)
    # Keep first occurrence (platform with higher priority)
    df_combined['url_normalized'] = df_combined['url'].apply(
        lambda x: x.lower().replace('www.', '').split('?')[0].rstrip('/')
    )

    initial_count = len(df_combined)
    df_combined = df_combined.drop_duplicates(subset=['url_normalized'], keep='first')
    df_combined = df_combined.drop(columns=['url_normalized'])

    duplicates_removed = initial_count - len(df_combined)

    print(f"Duplicates removed: {duplicates_removed}")
    print(f"Total after deduplication: {len(df_combined)} articles")

    # Sort by date (newest first)
    if 'date' in df_combined.columns:
        df_combined['date'] = pd.to_datetime(df_combined['date'], errors='coerce')
        df_combined = df_combined.sort_values('date', ascending=False)

    # Reorder columns
    standard_cols = ['title', 'date', 'url', 'content', 'platform']
    other_cols = [col for col in df_combined.columns if col not in standard_cols]
    df_combined = df_combined[standard_cols + other_cols]

    print(f"\n{'='*70}")
    print(f"SCRAPING COMPLETED")
    print(f"Total unique articles: {len(df_combined)}")
    print(f"{'='*70}\n")

    return df_combined


def save_to_excel(df, filename=None, keyword=None):
    """
    Save DataFrame to Excel dengan penamaan yang informatif.

    Args:
        df: DataFrame hasil scraping
        filename: Custom filename (optional)
        keyword: Keyword yang digunakan untuk scraping

    Returns:
        Filename yang digunakan
    """
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        keyword_str = f"_{keyword}" if keyword else ""
        filename = f"news_scraping{keyword_str}_{timestamp}.xlsx"

    df.to_excel(filename, index=False, engine='openpyxl')
    print(f"\n✓ Data berhasil disimpan ke: {filename}")

    return filename


# Example usage
if __name__ == '__main__':
    # Test scraping dengan kombinasi platform + Google RSS
    keyword = "pertamina"
    tanggal = "2025-12-30"  # Optional, bisa None untuk semua tanggal

    # Contoh 1: Scrape CNBC saja dengan Google RSS fallback
    print("=" * 80)
    print("CONTOH 1: CNBC + Google RSS")
    print("=" * 80)
    df_cnbc = scrape_cnbc_with_rss(keyword, tanggal)
    if df_cnbc is not None and not df_cnbc.empty:
        print(f"\nHasil: {len(df_cnbc)} artikel")
        print(df_cnbc[['title', 'date', 'url']].head())

    # Contoh 2: Scrape semua platform dengan Google RSS fallback
    print("\n\n" + "=" * 80)
    print("CONTOH 2: ALL PLATFORMS + Google RSS")
    print("=" * 80)
    df_all = scrape_all_platforms_with_rss(
        keyword=keyword,
        tanggal=tanggal,
        platforms=['cnbc', 'kompas', 'tempo']
    )

    if df_all is not None and not df_all.empty:
        print(f"\nHasil gabungan: {len(df_all)} artikel unik")
        print("\nBreakdown per platform:")
        print(df_all['platform'].value_counts())

        print("\nPreview data:")
        print(df_all[['title', 'date', 'platform']].head(10))

        # Save to Excel
        save_to_excel(df_all, keyword=keyword)
