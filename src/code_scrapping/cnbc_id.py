import requests, xml.etree.ElementTree as ET, pandas as pd, gzip, io, re, time
from bs4 import BeautifulSoup
from datetime import datetime

def fetch_xml(url):
    try:
        r = requests.get(url, headers={'User-Agent':'Mozilla/5.0'}, timeout=20)
        r.raise_for_status()
        c = r.content
        if url.endswith('.gz') or c[:2] == b'\x1f\x8b':
            with gzip.GzipFile(fileobj=io.BytesIO(c)) as f: c = f.read()
        return c
    except Exception as e:
        print(f"Gagal ambil {url}: {e}")
        return b""

def ekstrak_info(url_tag, ns):
    news_ns = {'news': 'http://www.google.com/schemas/sitemap-news/0.9'}
    loc = url_tag.find('sm:loc', ns)
    if loc is None: return None
    news = url_tag.find('news:news', news_ns)
    title = tanggal = keywords = ''
    if news:
        t = news.find('news:title', news_ns); title = t.text.strip() if t is not None else ''
        d = news.find('news:publication_date', news_ns); tanggal = d.text.strip()[:10] if d is not None else ''
        k = news.find('news:keywords', news_ns); keywords = k.text.strip() if k is not None else ''
    return {'title': title or loc.text.split('/')[-1], 'link': loc.text.strip(), 'tanggal': tanggal, 'keywords': keywords}

def ambil_konten(url):
    try:
        s = BeautifulSoup(requests.get(url, headers={'User-Agent':'Mozilla/5.0'}, timeout=20).text, 'html.parser')
        c = s.select_one('div.detail-text, div.detail_text, article, section')
        if not c: return "N/A"
        for x in c.select('script, style, iframe, figure, div[class*="sisip"], div[class*="ads"], a[href*="baca"]'): x.decompose()
        p = [re.sub(r'\s+', ' ', e.get_text(" ", strip=True)) for e in c.find_all(['p','li']) if len(e.get_text(strip=True))>30]
        return "\n\n".join(p) if p else "N/A"
    except: return "N/A"

def ambil_semua_sitemap(url_awal):
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    hasil = []
    data = fetch_xml(url_awal)
    if not data: return hasil
    root = ET.fromstring(data)
    sitemap_tags = root.findall('.//sm:sitemap', ns)
    if sitemap_tags:  
        for sm in sitemap_tags:
            loc = sm.find('sm:loc', ns)
            if loc is not None and 'sitemap_news' in loc.text:
                hasil += ambil_semua_sitemap(loc.text)  
    else:
        if 'sitemap_news' in url_awal:
            hasil.append(url_awal)
    return list(set(hasil))

def scrape_cnbc_id(keyword, tanggal=None):
    #print("Mengambil daftar semua sitemap CNBC...")
    semua_sitemap = ambil_semua_sitemap("https://www.cnbcindonesia.com/sitemap.xml")
    #print(f"Total sitemap_news ditemukan: {len(semua_sitemap)}\n")

    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    hasil = []

    for sm_url in semua_sitemap:
        #print(f"Cek: {sm_url}")
        data = fetch_xml(sm_url)
        if not data: continue
        try:
            root = ET.fromstring(data)
        except ET.ParseError:
            continue
        for url_tag in root.findall('.//sm:url', ns):
            info = ekstrak_info(url_tag, ns)
            if not info: continue
            gabung = f"{info['title']} {info['link']} {info['keywords']}".lower()
            if keyword.lower() in gabung:
                if not tanggal or info['tanggal'] == tanggal:
                    hasil.append({
                        'title': info['title'],
                        'date': info['tanggal'],
                        'url': info['link']
                    })
        time.sleep(0.1)

    for i,a in enumerate(hasil,1):
        print(f"{i}. {a['title']}")
        a['content'] = ambil_konten(a['url'])
        time.sleep(0.3)
    return hasil