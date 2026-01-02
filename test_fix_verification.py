import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'code_scrapping'))

from google_news import scrape_google_news

# Test the fixed function
keyword = "oil"
tanggal = "2025-12-31"  # String format
platform = "CNN"

print(f"Testing scrape_google_news:")
print(f"  Keyword: {keyword}")
print(f"  Filter Date: {tanggal} (type: {type(tanggal).__name__})")
print(f"  Filter Platform: {platform}")
print("=" * 70)

articles = scrape_google_news(
    keyword=keyword,
    filter_date=tanggal,
    filter_platform=platform
)

print("\n" + "=" * 70)
print(f"HASIL: {len(articles)} artikel CNN pada {tanggal}")
print("=" * 70)

for idx, article in enumerate(articles[:10]):  # Show first 10
    print(f"\n{idx+1}. {article['title']}")
    print(f"   Source: {article['source']}")
    print(f"   Date: {article['date']}")
    print(f"   URL: {article['url'][:80]}...")
