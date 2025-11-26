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

def ambil_konten_kontan(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        r = requests.get(url, headers=headers, timeout=15)
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
    except Exception:
        return 'N/A'

def fetch_xml(url):
    r = requests.get(url, timeout=15)
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
    # ambil semua <loc> yang kemungkinan sub-sitemap
    for loc in root.findall('.//sm:loc', ns):
        if loc.text:
            href = loc.text.strip()
            # biasanya sub-sitemap berakhiran .xml atau .xml.gz — tambahkan semua yang relevan
            if href.endswith('.xml') or href.endswith('.xml.gz') or 'sitemap' in href or '/sitemaps/' in href:
                links.append(href)
    # deduplicate sambil pertahankan urutan
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
    # ambil tanggal bagian sebelum 'T' bila ada
    tanggal = pubdate_raw.split('T')[0].strip() if 'T' in pubdate_raw else (pubdate_raw.strip() if pubdate_raw else '-')
    return {'title': title, 'link': link, 'pubdate': pubdate_raw, 'tanggal': tanggal, 'keywords': keywords}

def get_kontan_news_by_keyword(keyword):
    try:
        root = ambil_sitemap_utama()
    except Exception as e:
        print(f"Gagal ambil sitemap utama: {e}")
        return []

    subs = ambil_daftar_subsitemap(root)
    results = []
    keyword_lower = keyword.lower()
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

    for idx, sub in enumerate(subs, 1):
        try:
            content = fetch_xml(sub)
            subroot = ET.fromstring(content)
            for url_tag in subroot.findall('.//sm:url', ns):
                info = ekstrak_info_news(url_tag, ns)
                if not info or not info.get('link'):
                    continue
                title = info.get('title') or ""
                keywords = info.get('keywords') or ""
                link = info.get('link') or ""
                # filter: title, keywords, or link
                if (keyword_lower in title.lower()) or (keyword_lower in keywords.lower()) or (keyword_lower in link.lower()):
                    results.append({
                        'judul': title if title else link,
                        'link': link,
                        'tanggal': info.get('tanggal') if info.get('tanggal') else '-',
                        'keywords': keywords
                    })
        except Exception:
            # lanjutkan ke subsitemap berikutnya jika ada error
            continue
        time.sleep(0.15)
    return results

def scrape_kontan(keyword, tanggal=None):
    artikel = get_kontan_news_by_keyword(keyword)
    if not artikel:
        return []
    if tanggal:
        if isinstance(tanggal, datetime):
            tanggal = tanggal.strftime('%Y-%m-%d')
        else:
            tanggal = str(tanggal)
        artikel = [a for a in artikel if a.get('tanggal') == tanggal]
    if not artikel:
        return []
    hasil = []
    for i, a in enumerate(artikel, 1):
        content = ambil_konten_kontan(a['link'])
        hasil.append({
            "title": a.get("judul", "-"),
            "date": a.get("tanggal", "-"),
            "url": a.get("link", "-"),
            "content": content
        })
        time.sleep(1.0)
    return hasil


def simpan_excel(data, keyword):
    if not data:
        print("Tidak ada data untuk disimpan.")
        return
    nama = f"kontan_{keyword.replace(' ', '_')}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    df = pd.DataFrame(data)
    kolom = ['title', 'date', 'url', 'content']
    cols = [c for c in kolom if c in df.columns]
    df = df[cols]
    df.to_excel(nama, index=False, engine='openpyxl')
    print(f"Disimpan: {nama}")
