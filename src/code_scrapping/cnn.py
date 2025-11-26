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
    pola = [
        r'Sign up for CNN.*',
        r'Read more:.*',
        r'Watch:.*',
        r"CNN\'s\s+[\w\s,]+contributed to this report\.?",
        r'This story.*contributed to this report\.?'
    ]
    for p in pola:
        teks = re.sub(p, '', teks, flags=re.IGNORECASE | re.DOTALL)
    return re.sub(r' {2,}', ' ', teks).strip()

def is_valid_paragraph(teks, min_length=10):
    if not teks or len(teks) < min_length:
        return False
    spam = ['cookie', 'privacy policy', 'terms of service', 'subscribe', 'sign up', 'newsletter', 'follow us', 'advertisement']
    teks_lower = teks.lower()
    return not any(k in teks_lower for k in spam) and not re.match(r'^[\d\s\-:,\.]+$', teks)

def ambil_konten_cnn(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, 'html.parser')
        paragraf = []

        for selector in ['div.article__content', 'div.video-resource__description', 'main', 'article']:
            container = soup.select_one(selector)
            if container:
                for el in container.find_all(['h2', 'p', 'li']):
                    teks = el.get_text(strip=True)
                    if is_valid_paragraph(teks, min_length=8) and teks not in paragraf:
                        paragraf.append(teks)
                if len(paragraf) >= 3:
                    break

        if len(paragraf) < 2:
            for el in soup.find_all(['h2', 'p', 'li']):
                teks = el.get_text(strip=True)
                if is_valid_paragraph(teks, min_length=10) and teks not in paragraf:
                    paragraf.append(teks)

        return bersihkan_teks("\n\n".join(paragraf)) if paragraf else 'N/A'
    except Exception:
        return 'N/A'

def fetch_xml(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    content = r.content
    if url.endswith('.gz') or content[:2] == b'\x1f\x8b':
        with gzip.GzipFile(fileobj=io.BytesIO(content)) as f:
            content = f.read()
    return content

def ekstrak_info_artikel(url_tag, ns):
    loc_tag = url_tag.find('sm:loc', ns)
    if loc_tag is None or not loc_tag.text:
        return None
    link = loc_tag.text.strip()
    lastmod_tag = url_tag.find('sm:lastmod', ns)
    tanggal_raw = lastmod_tag.text.strip() if lastmod_tag is not None else ''
    news_ns = {'news': 'http://www.google.com/schemas/sitemap-news/0.9'}
    news_tag = url_tag.find('news:news', news_ns)
    title, tanggal = '', '-'
    if news_tag:
        title_tag = news_tag.find('news:title', news_ns)
        pub_tag = news_tag.find('news:publication_date', news_ns)
        title = title_tag.text.strip() if title_tag is not None else ''
        tanggal_raw = tanggal_raw or (pub_tag.text.strip() if pub_tag is not None else '')
    if tanggal_raw:
        tanggal = tanggal_raw.split('T')[0] if 'T' in tanggal_raw else tanggal_raw
    if not title:
        title = link.rstrip('/').split('/')[-1].replace('-', ' ').title()
    return {'title': title, 'link': link, 'tanggal': tanggal}

def get_cnn_news_by_keyword(keyword):
    sitemap_url = "https://www.cnn.com/sitemap/news.xml"
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    results = []
    try:
        content = fetch_xml(sitemap_url)
        root = ET.fromstring(content)
        sitemaps = (
            [s.find('sm:loc', ns).text for s in root.findall('.//sm:sitemap', ns)]
            if root.tag.endswith('sitemapindex')
            else [sitemap_url]
        )

        for sub_url in sitemaps:
            try:
                sub_content = fetch_xml(sub_url)
                sub_root = ET.fromstring(sub_content)
                for url_tag in sub_root.findall('.//sm:url', ns):
                    info = ekstrak_info_artikel(url_tag, ns)
                    if info and keyword.lower() in (info['title'] + info['link']).lower():
                        results.append(info)
                time.sleep(0.5)
            except Exception:
                continue
    except Exception:
        pass
    return results

def scrape_cnn_international(keyword, tanggal=None):
    print(f"\nMencari artikel CNN untuk keyword: {keyword}")
    artikel = get_cnn_news_by_keyword(keyword)
    if tanggal:
        tanggal_str = tanggal.strftime('%Y-%m-%d') if isinstance(tanggal, datetime) else str(tanggal)
        artikel = [a for a in artikel if a['tanggal'] == tanggal_str]

    print(f"Ditemukan {len(artikel)} artikel. Mengambil isi konten...")
    hasil_bersih = []
    for idx, a in enumerate(artikel, 1):
        print(f"  ({idx}/{len(artikel)}) {a['title'][:60]}...")
        konten = ambil_konten_cnn(a['link'])
        time.sleep(1)

        hasil_bersih.append({
            'title': a.get('title', ''),
            'date': a.get('tanggal', ''),
            'url': a.get('link', ''),
            'content': konten
        })

    return hasil_bersih
