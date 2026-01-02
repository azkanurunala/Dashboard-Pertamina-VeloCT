import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'code_scrapping'))

from google_news import cari_artikel_di_sitemap
import re

# Title from Google News
google_news_title = "Oil tanker pursued by US now has a Russian flag painted on its side - CNN"
platform = "CNN"
date_str = "2025-12-31"

print(f"Original title: {google_news_title}")

# Strip platform name
title_clean = re.sub(rf'\s*-\s*{platform}$', '', google_news_title, flags=re.IGNORECASE).strip()
print(f"Cleaned title: {title_clean}")

# Normalize
title_normalized = re.sub(r'[^\w\s]', '', title_clean.lower()).strip()
print(f"Normalized: {title_normalized}")

print("\n" + "=" * 70)
print("Searching in CNN sitemap...")
print("=" * 70)

result = cari_artikel_di_sitemap(platform, google_news_title, date_str)

if result:
    print(f"\n[FOUND]")
    print(f"Title: {result['title']}")
    print(f"URL: {result['url']}")
else:
    print("\n[NOT FOUND] - Artikel tidak ditemukan di sitemap")
