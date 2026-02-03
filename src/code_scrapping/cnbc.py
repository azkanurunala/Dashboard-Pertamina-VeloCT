import requests, xml.etree.ElementTree as ET, pandas as pd, gzip, io, re, time, sys, os
from bs4 import BeautifulSoup
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from google_news import scrape_google_news_with_content
from helpers.scraping_helper import fetch_xml
    
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
        containers = s.select('div.ArticleBody-articleBody, section#ArticleBody, div[class*="article-body"]')
        if not containers:
            containers = [s] 
        teks_final = []
        for c in containers:
            for bad in c.select('script, style, iframe, figure, div[class*="ad"], div[data-module="mps-slot"], span[class*="share"], aside, div.RelatedContent-collapsibleContent, div[class*="RelatedContent"], div[class*="related"]'):
                bad.decompose() 
            for e in c.find_all(['p', 'li', 'h2']):
                teks = re.sub(r'\s+', ' ', e.get_text(" ", strip=True))
                if len(teks) > 30:
                    teks_final.append(teks)
        if not teks_final:
            for e in s.find_all('p'):
                teks = re.sub(r'\s+', ' ', e.get_text(" ", strip=True))
                if len(teks) > 30:
                    teks_final.append(teks)
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
    semua_berita = []
    for url_tag in root.findall('.//sm:url', ns):
        info = ekstrak_info(url_tag, ns)
        if not info:
            continue
        if tanggal and info['date'] != tanggal:
            continue
        semua_berita.append({
            'title': info['title'],
            'date': info['date'],
            'url': info['url']
        })
    hasil = []
    keyword_pattern = r'\b' + re.escape(keyword.strip().lower()) + r'\b'
    
    for berita in semua_berita:
        if ambil_konten:
            berita['content'] = ambil_konten_artikel(berita['url'])
            time.sleep(0.5)
        else:
            berita['content'] = 'N/A'
        if (re.search(keyword_pattern, berita['title'].lower()) or
            re.search(keyword_pattern, berita['url'].lower()) or
            (ambil_konten and re.search(keyword_pattern, berita['content'].lower()))):
            hasil.append(berita)
    return hasil

def main_google_news_cnbc(keyword, tanggal=None):
    print("=" * 70)
    print("STEP 1: Ambil dari Google News (CNBC only) + Konten")
    print("=" * 70)
    google_articles = scrape_google_news_with_content(keyword, filter_date=tanggal, filter_platform='CNBC', use_selenium_fallback=True)
    print(f"Google News: {len(google_articles)} artikel CNBC")
    print("\n" + "=" * 70)
    print("STEP 2: Ambil dari CNBC Sitemap + Konten")
    print("=" * 70)
    cnbc_articles = scrape_cnbc_international(keyword, tanggal, ambil_konten=True)
    print(f"CNBC Sitemap: {len(cnbc_articles)} artikel")
    print("\n" + "=" * 70)
    print("STEP 3: Gabungkan + Drop Duplicate")
    print("=" * 70)
    all_articles = google_articles + cnbc_articles
    print(f"Total sebelum deduplicate: {len(all_articles)}")
    seen_urls = set()
    unique_articles = []
    for article in all_articles:
        url = article['url']
        if url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)
    print(f"Total setelah deduplicate: {len(unique_articles)}")
    return unique_articles

if __name__ == '__main__':
    keyword = "geopolitical risks"
    print(f"Scraping CNBC (Google News + Sitemap) - keyword: {keyword}\n")
    hasil = main_google_news_cnbc(keyword=keyword, tanggal="2026-01-28")
    print(f"\nTotal: {len(hasil)} berita")
    if hasil:
        df = pd.DataFrame(hasil)
        filename = f"cnbc_combined_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        print(df)
        # df.to_excel(filename, index=False, engine='openpyxl')
        print(f"Saved: {filename}")
    else:
        print("Tidak ada berita")
