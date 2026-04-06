import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'id-ID,id;q=0.9,en;q=0.8',
}

url = 'https://www.bi.go.id/id/publikasi/ruang-media/news-release/Default.aspx'
try:
    print(f"Requesting: {url}")
    r = requests.get(url, headers=headers, timeout=15)
    print(f'Status: {r.status_code}')

    soup = BeautifulSoup(r.text, 'html.parser')
    # Cek apakah ada artikel di HTML langsung
    items = soup.select('.media.media--pers')
    print(f'Artikel ditemukan di HTML: {len(items)}')
    if items:
        print('Contoh:', items[0].get_text(strip=True)[:100])
    else:
        print('Tidak ada artikel — kemungkinan dirender via JavaScript')
        # Cek apakah ada script yang load data
        scripts = [s.get('src','') for s in soup.find_all('script') if s.get('src')]
        print('Scripts (first 5):', scripts[:5])
        
        # Check for possible OData or API endpoints in scripts
        for s in soup.find_all('script'):
            content = s.string if s.string else ""
            if "_api/web" in content or "ListName" in content:
                print("Found potential API call in script content.")
except Exception as e:
    print(f"An error occurred: {e}")
