import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'code_scrapping'))

from google_news import scrape_google_news_with_content

keyword = "oil"
tanggal = "2025-12-31"
platform = "CNN"

print(f"Testing Full Flow:")
print(f"  Keyword: {keyword}")
print(f"  Date: {tanggal}")
print(f"  Platform: {platform}")
print("=" * 70)

# Test only Google News scraping with content
google_articles = scrape_google_news_with_content(
    keyword=keyword,
    filter_date=tanggal,
    filter_platform=platform,
    use_selenium_fallback=False  # Disable Selenium untuk test cepat
)

print("\n" + "=" * 70)
print(f"HASIL: {len(google_articles)} artikel")
print("=" * 70)

for idx, article in enumerate(google_articles):
    print(f"\n{idx+1}. {article['title']}")
    print(f"   Source: {article['source']}")
    print(f"   Date: {article['date']}")
    print(f"   URL: {article['url'][:80]}...")
    print(f"   Content: {len(article['content'])} chars")
    if article['content'] != 'N/A':
        print(f"   Preview: {article['content'][:200]}...")
