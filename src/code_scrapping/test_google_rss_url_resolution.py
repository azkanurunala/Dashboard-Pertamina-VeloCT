"""
Test script untuk memverifikasi URL resolution dari Google News redirect.

Author: VeloCT Development Team
Date: 2025-12-31
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from code_scrapping.scrapping_google_news import (
    fetch_google_news_rss,
    clean_google_news_url
)


def test_url_resolution():
    """
    Test URL resolution untuk Google News redirect URLs.
    """
    print("\n" + "="*80)
    print("TEST: GOOGLE NEWS URL RESOLUTION")
    print("="*80)

    # Test dengan keyword sederhana
    keyword = "pertamina"
    print(f"\nFetching Google News RSS for keyword: {keyword}")
    print(f"{'─'*80}\n")

    articles = fetch_google_news_rss(keyword)

    if not articles:
        print("\n❌ No articles found")
        return

    print(f"\n{'='*80}")
    print(f"RESULTS: {len(articles)} articles")
    print(f"{'='*80}\n")

    # Analyze URL resolution success rate
    google_urls = 0
    resolved_urls = 0
    domains = {}

    for idx, article in enumerate(articles, 1):
        url = article['url']
        title = article['title']
        source = article.get('source', 'Unknown')

        print(f"\n[{idx}] {title[:60]}...")
        print(f"    Source: {source}")

        if 'news.google.com' in url:
            google_urls += 1
            print(f"    URL: ⚠️  GOOGLE REDIRECT (not resolved)")
            print(f"         {url[:80]}...")
        else:
            resolved_urls += 1
            print(f"    URL: ✓ RESOLVED")
            print(f"         {url[:80]}...")

            # Track domains
            domain = url.split('/')[2] if len(url.split('/')) > 2 else 'unknown'
            domains[domain] = domains.get(domain, 0) + 1

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total articles: {len(articles)}")
    print(f"✓ Resolved URLs: {resolved_urls} ({resolved_urls/len(articles)*100:.1f}%)")
    print(f"⚠ Google redirects: {google_urls} ({google_urls/len(articles)*100:.1f}%)")

    if domains:
        print(f"\nDomains found:")
        for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {domain}: {count} articles")

    # Recommendations
    print(f"\n{'='*80}")
    print("RECOMMENDATIONS")
    print(f"{'='*80}")

    if resolved_urls > 0:
        print("✓ URL resolution is working!")
        print("  Articles with resolved URLs can be scraped for content.")
    else:
        print("⚠ No URLs were resolved successfully.")
        print("  Possible issues:")
        print("  1. Network/firewall blocking redirects")
        print("  2. Google News changed redirect mechanism")
        print("  3. Timeout too short (increase timeout in clean_google_news_url)")

    if google_urls > 0:
        print(f"\n⚠ {google_urls} articles still have Google redirect URLs")
        print("  These will be skipped during content scraping.")
        print("  Consider:")
        print("  1. Increasing timeout in clean_google_news_url()")
        print("  2. Using alternative methods to resolve URLs")


def test_single_url_resolution():
    """
    Test resolving a single Google News URL.
    """
    print("\n" + "="*80)
    print("TEST: SINGLE URL RESOLUTION")
    print("="*80)

    # Example Google News URL (replace with actual URL from RSS feed)
    google_url = "https://news.google.com/rss/articles/CBMiWkFVX3lxTE5VdlJwTWNIYU5HZ01vdUdtY09UeVFhQzV2Ml9zOUhOMUJ5cVIwOFY0RjFzUHV6U2JzMFUxTGxBUlF2cjduVmoyb3R1ankzMi1DMWVmZTdPWVFwd9IBX0FVX3lxTE1zNFU3WnJBZFpEU3oxRzJrNWNuVWZaRHZWQWhCa01JcU01NS1MMm1ic21YY3Atd19aMl9RTkV3S0RhNmpRNGFIYUJoMUY1MUpDRS1CZnpLcTVUdW5RMVJB"

    print(f"\nOriginal URL:")
    print(f"  {google_url[:100]}...\n")

    print("Attempting to resolve URL...")
    resolved_url = clean_google_news_url(google_url, follow_redirect=True, timeout=10)

    print(f"\nResolved URL:")
    print(f"  {resolved_url}\n")

    if 'news.google.com' not in resolved_url:
        print("✓ SUCCESS: URL was resolved to actual article URL")
    else:
        print("⚠ FAILED: URL still points to Google News redirect")


if __name__ == '__main__':
    # Run URL resolution test
    test_url_resolution()

    # Uncomment to test single URL resolution
    # test_single_url_resolution()

    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80 + "\n")
