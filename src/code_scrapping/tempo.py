import requests
import xml.etree.ElementTree as ET
import pandas as pd
import re
import time
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse

TEMPO_SITEMAPS = [
    "https://www.tempo.co/politik-sitemap.xml",
    "https://www.tempo.co/hukum-sitemap.xml",
    "https://www.tempo.co/ekonomi-sitemap.xml",
    "https://www.tempo.co/lingkungan-sitemap.xml",
    "https://www.tempo.co/wawancara-sitemap.xml",
    "https://www.tempo.co/sains-sitemap.xml",
    "https://www.tempo.co/investigasi-sitemap.xml",
    "https://www.tempo.co/cekfakta-sitemap.xml",
    "https://www.tempo.co/kolom-sitemap.xml",
    "https://www.tempo.co/hiburan-sitemap.xml",
    "https://www.tempo.co/internasional-sitemap.xml",
    "https://www.tempo.co/otomotif-sitemap.xml",
    "https://www.tempo.co/olahraga-sitemap.xml",
    "https://www.tempo.co/sepakbola-sitemap.xml",
    "https://www.tempo.co/digital-sitemap.xml",
    "https://www.tempo.co/gaya-hidup-sitemap.xml",
]

def fetch_xml(url):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        r.raise_for_status()
        return r.content
    except:
        return b""

def ekstrak_keywords_dari_url(url):
    path = urlparse(url).path
    parts = path.strip('/').split('/')
    if len(parts) < 2:
        return []
    slug = parts[-1]
    slug = re.sub(r'-\d{8,}$', '', slug)
    return [k.lower() for k in slug.split('-') if len(k) >= 3]

def cek_keyword_match(url_keywords, search_keyword):
    s = search_keyword.lower()
    return any(s in kw for kw in url_keywords)

def ekstrak_info_tempo(url_tag, ns):
    loc = url_tag.find('sm:loc', ns)
    lastmod = url_tag.find('sm:lastmod', ns)
    if loc is None or not loc.text:
        return None
    url = loc.text.strip()
    tanggal = lastmod.text.strip()[:10] if lastmod is not None and lastmod.text else ''
    keywords = ekstrak_keywords_dari_url(url)
    title = ' '.join([k.capitalize() for k in keywords])
    return {'title': title, 'link': url, 'tanggal': tanggal, 'url_keywords': keywords}

def ambil_konten_artikel_tempo(url):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=25)
        s = BeautifulSoup(r.text, 'html.parser')
        teks_final = []

        kontainer = s.select_one('div#isi, div.detail-content, article, div.detail-area')
        if not kontainer:
            kontainer = s

        for tag in kontainer.select('script, style, iframe, figure, aside, nav, '
                                    'div[class*="ad"], div[class*="iklan"], '
                                    'div[class*="share"], div[class*="related"], '
                                    'div[class*="author"], div[class*="penulis"], '
                                    'div.text-neutral-900'):
            tag.decompose()

        for p in kontainer.find_all('p'):
            teks = re.sub(r'\s+', ' ', p.get_text(" ", strip=True))
            if len(teks) > 30:
                teks_final.append(teks)

        teks_bersih = "\n\n".join(teks_final)
        pola_bersih = [
            r'Baca berita.*?klik di sini',
            r'Scroll ke bawah.*',
            r'Lulus dari Jurusan.*?(hak asasi manusia)?',
            r'This is breaking news.*'
        ]
        for pola in pola_bersih:
            teks_bersih = re.sub(pola, '', teks_bersih, flags=re.I)
        teks_bersih = re.sub(r'\s+', ' ', teks_bersih).strip()

        return teks_bersih if teks_bersih else "N/A"
    except:
        return "N/A"

def scrape_tempo(keyword, tanggal=None):
    hasil = []
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

    for sitemap_url in TEMPO_SITEMAPS:
        data = fetch_xml(sitemap_url)
        if not data:
            continue
        try:
            root = ET.fromstring(data)
        except:
            continue
        for url_tag in root.findall('.//sm:url', ns):
            info = ekstrak_info_tempo(url_tag, ns)
            if not info:
                continue
            if cek_keyword_match(info['url_keywords'], keyword):
                if tanggal and info['tanggal'] != tanggal:
                    continue
                hasil.append(info)

    for item in hasil:
        del item['url_keywords']

    print(f"Ditemukan {len(hasil)} artikel dari Tempo. Mengambil konten...")

    hasil_bersih = []
    for idx, a in enumerate(hasil, 1):
        print(f"  ({idx}/{len(hasil)}) {a['title'][:60]}...")
        konten = ambil_konten_artikel_tempo(a['link'])
        time.sleep(0.5)

        hasil_bersih.append({
            'title': a.get('title', ''),
            'date': a.get('tanggal', ''),
            'url': a.get('link', ''),
            'content': konten
        })

    return hasil_bersih