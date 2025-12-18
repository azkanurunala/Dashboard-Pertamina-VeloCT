import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import gzip
import io

def bersihkan_teks(teks):
    if not teks or teks == 'N/A':
        return teks
    teks = re.sub(r'Baca Juga.*', '', teks, flags=re.IGNORECASE | re.DOTALL)
    teks = re.sub(r'Cek Berita dan Artikel.*', '', teks, flags=re.IGNORECASE | re.DOTALL)
    teks = re.sub(r'\n{3,}', '\n\n', teks)
    return teks.strip()

def get_headers():
    """Headers yang lebih lengkap untuk bypass detection"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }

def ambil_konten_kontan(url):
    try:
        session = requests.Session()
        headers = get_headers()
        
        r = session.get(url, headers=headers, timeout=20, allow_redirects=True)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, 'html.parser')

        kandidat = [
            'div.article-detail-content',
            'div.detail-content',
            'div.content-article',
            'div.article-content',
            'div#article-content',
            'article div.content',
            'div.post-content',
            'div.read__content'
        ]

        konten = None
        for selector in kandidat:
            div = soup.select_one(selector)
            if div:
                paragraf = [p.get_text(strip=True) for p in div.find_all('p') if p.get_text(strip=True)]
                if paragraf:
                    konten = '\n\n'.join(paragraf)
                    break

        if not konten:
            paragraf = [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)]
            if len(paragraf) > 3:
                konten = '\n\n'.join(paragraf)

        if not konten:
            konten = 'N/A'

        return bersihkan_teks(konten)
            
    except Exception as e:
        print(f"❌ Error pada {url}: {e}")
        return 'N/A'

def fetch_xml(url):
    headers = get_headers()
    time.sleep(1.5)
    
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    content = r.content
    
    if url.endswith('.gz') or content[:2] == b'\x1f\x8b':
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(content)) as f:
                content = f.read()
        except Exception:
            pass
    return content

def ambil_sitemap_utama():
    url = "https://www.kontan.co.id/sitemap.xml"
    content = fetch_xml(url)
    return ET.fromstring(content)

def ambil_daftar_subsitemap(root):
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    links = []
    for loc in root.findall('.//sm:loc', ns):
        if loc.text:
            href = loc.text.strip()
            if href.endswith('.xml') or href.endswith('.xml.gz') or 'sitemap' in href or '/sitemaps/' in href:
                links.append(href)
    seen = set()
    out = []
    for u in links:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out

def ekstrak_info_news(url_tag, ns):
    loc_tag = url_tag.find('sm:loc', ns)
    if loc_tag is None or not loc_tag.text:
        return None
    link = loc_tag.text.strip()
    news_tag = url_tag.find('news:news', {'news': 'http://www.google.com/schemas/sitemap-news/0.9'})
    title = ""
    pubdate_raw = ""
    keywords = ""
    if news_tag is not None:
        t = news_tag.find('news:title', {'news': 'http://www.google.com/schemas/sitemap-news/0.9'})
        p = news_tag.find('news:publication_date', {'news': 'http://www.google.com/schemas/sitemap-news/0.9'})
        k = news_tag.find('news:keywords', {'news': 'http://www.google.com/schemas/sitemap-news/0.9'})
        if t is not None and t.text:
            title = t.text.strip()
        if p is not None and p.text:
            pubdate_raw = p.text.strip()
        if k is not None and k.text:
            keywords = k.text.strip()
    tanggal = pubdate_raw.split('T')[0].strip() if 'T' in pubdate_raw else (pubdate_raw.strip() if pubdate_raw else '-')
    return {'title': title, 'link': link, 'pubdate': pubdate_raw, 'tanggal': tanggal, 'keywords': keywords}

def get_kontan_news_by_keyword(keyword):
    try:
        print("📥 Mengambil sitemap utama...")
        root = ambil_sitemap_utama()
    except Exception as e:
        print(f"❌ Gagal ambil sitemap utama: {e}")
        return []

    subs = ambil_daftar_subsitemap(root)
    print(f"✅ Ditemukan {len(subs)} sub-sitemap")
    
    results = []
    keyword_lower = keyword.lower()
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

    for idx, sub in enumerate(subs, 1):
        try:
            print(f"📄 Memproses sub-sitemap {idx}/{len(subs)}")
            content = fetch_xml(sub)
            subroot = ET.fromstring(content)
            
            count = 0
            for url_tag in subroot.findall('.//sm:url', ns):
                info = ekstrak_info_news(url_tag, ns)
                if not info or not info.get('link'):
                    continue
                title = info.get('title') or ""
                keywords = info.get('keywords') or ""
                link = info.get('link') or ""
                
                if (keyword_lower in title.lower()) or (keyword_lower in keywords.lower()) or (keyword_lower in link.lower()):
                    results.append({
                        'judul': title if title else link,
                        'link': link,
                        'tanggal': info.get('tanggal') if info.get('tanggal') else '-',
                        'keywords': keywords
                    })
                    count += 1
            
            if count > 0:
                print(f"   ✅ Ditemukan {count} artikel matching")
                
        except Exception as e:
            print(f"   ⚠️  Error pada sub-sitemap: {e}")
            continue
        
        time.sleep(1.0)
    
    print(f"\n✅ Total artikel ditemukan: {len(results)}")
    return results

def scrape_kontan(keyword, tanggal=None):
    print(f"🔍 Mencari artikel dengan keyword: '{keyword}'")
    artikel = get_kontan_news_by_keyword(keyword)
    
    if not artikel:
        print("❌ Tidak ada artikel ditemukan")
        return []
    
    if tanggal:
        if isinstance(tanggal, datetime):
            tanggal = tanggal.strftime('%Y-%m-%d')
        else:
            tanggal = str(tanggal)
        artikel = [a for a in artikel if a.get('tanggal') == tanggal]
        print(f"📅 Filter tanggal {tanggal}: {len(artikel)} artikel")
    
    if not artikel:
        print("❌ Tidak ada artikel setelah filtering")
        return []
    
    hasil = []
    print(f"\n📰 Mulai scraping {len(artikel)} artikel...")
    
    for i, a in enumerate(artikel, 1):
        print(f"\n[{i}/{len(artikel)}] {a.get('judul', 'No title')[:80]}...")
        content = ambil_konten_kontan(a['link'])
        
        hasil.append({
            "title": a.get("judul", "-"),
            "date": a.get("tanggal", "-"),
            "url": a.get("link", "-"),
            "content": content
        })
        
        if content != 'N/A':
            print(f"   ✅ Berhasil ({len(content)} karakter)")
        else:
            print(f"   ⚠️  Gagal mengambil konten")
        
        # Delay 3 detik antar artikel
        time.sleep(3.0)
    
    return hasil

def simpan_excel(data, keyword):
    if not data:
        print("❌ Tidak ada data untuk disimpan.")
        return
    
    nama = f"kontan_{keyword.replace(' ', '_')}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    df = pd.DataFrame(data)
    kolom = ['title', 'date', 'url', 'content']
    cols = [c for c in kolom if c in df.columns]
    df = df[cols]
    df.to_excel(nama, index=False, engine='openpyxl')
    print(f"✅ Disimpan: {nama}")

# Contoh penggunaan
if __name__ == "__main__":
    hasil = scrape_kontan("ekonomi")
    if hasil:
        simpan_excel(hasil, "ekonomi")