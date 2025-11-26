import requests, xml.etree.ElementTree as ET, pandas as pd, gzip, io, re, time
from bs4 import BeautifulSoup
from datetime import datetime

def fetch_xml(url):
    try:
        r = requests.get(url, headers={'User-Agent':'Mozilla/5.0'}, timeout=20)
        r.raise_for_status()
        c = r.content
        if url.endswith('.gz') or c[:2] == b'\x1f\x8b':
            with gzip.GzipFile(fileobj=io.BytesIO(c)) as f:
                c = f.read()
        return c
    except:
        return b""

def ekstrak_info(url_tag, ns):
    loc = url_tag.find('sm:loc', ns)
    if loc is None or not loc.text:
        return None
    news = url_tag.find('news:news', ns)
    title = tanggal = ''
    if news is not None:
        t = news.find('news:title', ns)
        d = news.find('news:publication_date', ns)
        title = t.text.strip() if t is not None and t.text else ''
        tanggal = d.text.strip()[:10] if d is not None and d.text else ''
    if not title:
        title = loc.text.rstrip('/').split('/')[-1].replace('-', ' ').title()
    return {'title': title, 'url': loc.text.strip(), 'date': tanggal}

def ambil_konten_artikel(url):
    try:
        r = requests.get(url, headers={'User-Agent':'Mozilla/5.0'}, timeout=25)
        s = BeautifulSoup(r.text, 'html.parser')

        # Ambil semua kontainer utama artikel
        containers = s.select('div.ArticleBody-articleBody, section#ArticleBody, div[class*="article-body"]')
        if not containers:
            containers = [s]  # fallback

        teks_final = []
        for c in containers:
            # Hapus elemen nonteks (iklan, script, box inline, dll)
            for bad in c.select('script, style, iframe, figure, div[class*="ad"], div[data-module="mps-slot"], span[class*="share"], aside'):
                bad.decompose()

            # Ambil semua paragraf, list, dan heading di seluruh depth
            for e in c.find_all(['p', 'li', 'h2']):
                teks = re.sub(r'\s+', ' ', e.get_text(" ", strip=True))
                if len(teks) > 30:
                    teks_final.append(teks)

        # Jika masih kosong, ambil seluruh <p> di halaman
        if not teks_final:
            for e in s.find_all('p'):
                teks = re.sub(r'\s+', ' ', e.get_text(" ", strip=True))
                if len(teks) > 30:
                    teks_final.append(teks)

        # Gabungkan hasil
        return "\n\n".join(teks_final) if teks_final else "N/A"
    except Exception as e:
        print("Gagal ambil konten:", e)
        return "N/A"

def scrape_cnbc_international(keyword, tanggal=None, ambil_konten=True):
    sitemap_url = "https://www.cnbc.com/sitemap_news.xml"
    data = fetch_xml(sitemap_url)
    if not data:
        return []
    try:
        root = ET.fromstring(data)
    except:
        return []
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9', 'news': 'http://www.google.com/schemas/sitemap-news/0.9'}
    hasil = []
    for url_tag in root.findall('.//sm:url', ns):
        info = ekstrak_info(url_tag, ns)
        if not info:
            continue
        if keyword.lower() in info['title'].lower() or keyword.lower() in info['url'].lower():
            if tanggal and info['date'] != tanggal:
                continue
            hasil.append({
                'title': info['title'],
                'date': info['date'],
                'url': info['url']
            })

    if ambil_konten:
        for a in hasil:
            a['content'] = ambil_konten_artikel(a['url'])
            time.sleep(0.5)
    else:
        for a in hasil:
            a['content'] = 'N/A'

    return hasil