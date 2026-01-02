import feedparser
import urllib.parse
from datetime import datetime

keyword = "oil"
encoded_keyword = urllib.parse.quote(keyword)
rss_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=en&gl=US&ceid=US:en"

print(f"RSS URL: {rss_url}\n")

feed = feedparser.parse(rss_url)

print(f"Total entries: {len(feed.entries)}\n")

# Cari entry CNN yang spesifik
for idx, entry in enumerate(feed.entries[:20]):  # Check first 20 entries
    source = entry.get('source', {}).get('title', 'Unknown') if hasattr(entry.get('source', {}), 'get') else 'Unknown'

    if 'CNN' in source or 'cnn' in source.lower():
        print(f"Entry #{idx + 1}:")
        print(f"  Title: {entry.get('title', '')}")
        print(f"  Source: {source}")
        print(f"  Published: {entry.get('published', '')}")
        print(f"  Link: {entry.get('link', '')}")

        # Test date parsing
        published_date = entry.get('published', '')
        try:
            pub_date = datetime.strptime(published_date, '%a, %d %b %Y %H:%M:%S %Z').date()
            print(f"  Parsed Date: {pub_date}")
        except Exception as e:
            print(f"  Date Parse Error: {e}")

        # Test filter
        filter_platform = 'CNN'
        if filter_platform in source:
            print(f"  [OK] PASS platform filter ('{filter_platform}' in '{source}')")
        else:
            print(f"  [FAIL] FAIL platform filter ('{filter_platform}' NOT in '{source}')")

        # Test date filter
        filter_date = datetime(2025, 12, 31).date()
        try:
            pub_date = datetime.strptime(published_date, '%a, %d %b %Y %H:%M:%S %Z').date()
            if pub_date == filter_date:
                print(f"  [OK] PASS date filter ({pub_date} == {filter_date})")
            else:
                print(f"  [FAIL] FAIL date filter ({pub_date} != {filter_date})")
        except:
            print(f"  [FAIL] FAIL date parsing")

        print()
