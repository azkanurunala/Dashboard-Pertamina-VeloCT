import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'code_scrapping'))

from cnn import main_google_news_cnn
from datetime import datetime

# Test dengan parameter yang sama seperti di main
keyword = "oil"
tanggal = "2025-12-31"

print(f"Testing main_google_news_cnn(keyword='{keyword}', tanggal='{tanggal}')")
print("=" * 70)

hasil = main_google_news_cnn(keyword=keyword, tanggal=tanggal)

print("\n" + "=" * 70)
print(f"HASIL AKHIR: {len(hasil)} artikel")
print("=" * 70)

for idx, h in enumerate(hasil[:5]):  # Show first 5
    print(f"\n{idx+1}. {h['title']}")
    print(f"   Date: {h['date']}")
    print(f"   URL: {h['url'][:80]}...")
    print(f"   Content: {len(h['content'])} chars")
