import requests
from datetime import datetime

api_key = '8199b1a60c76d284ee3d2228a51b3743'
url = f"https://webapi.bps.go.id/v1/api/list/model/news/domain/0000/page/0/key/{api_key}"

r = requests.get(url, timeout=15)
data = r.json()

items = data['data'][1]
print(f"Total items: {len(items)}")
print("\nSample items (title + rl_date):")
for item in items[:5]:
    print(f"  news_id={item.get('news_id')} | rl_date='{item.get('rl_date')}' | title={item.get('title','')[:50]}")

# Coba parse date format
print("\nCoba parse rl_date:")
for item in items[:3]:
    date_str = item.get('rl_date', '')
    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']:
        try:
            dt = datetime.strptime(date_str, fmt)
            print(f"  '{date_str}' → {fmt} → {dt.date()}")
            break
        except:
            continue
    else:
        print(f"  '{date_str}' → GAGAL PARSE")
