import requests

headers = {
    'Accept': 'application/json;odata=verbose',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0',
}

# SharePoint REST API - get all lists (untuk tahu nama list berita)
url = 'https://www.bi.go.id/id/publikasi/ruang-media/news-release/_api/web/lists'

try:
    print(f"Requesting: {url}")
    r = requests.get(url, headers=headers, timeout=15)
    print(f'Status: {r.status_code}')
    print(f'Content-Type: {r.headers.get("Content-Type", "")}')
    print("-" * 40)
    print(r.text[:1000])
except Exception as e:
    print(f"An error occurred: {e}")
