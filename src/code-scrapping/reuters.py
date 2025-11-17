import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import gzip
import io
import os


# =============================== Mengambil Sitemap URL ===============================
def get_sitemap_urls():
    index_url = "https://www.reuters.com/arc/outboundfeeds/news-sitemap-index/?outputType=xml"
    print(f"[INFO] Fetching sitemap index: {index_url}")
    try:
        r = requests.get(index_url, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        sitemap_urls = []
        for sitemap in root.findall('.//sm:sitemap', ns):
            loc = sitemap.find('sm:loc', ns)
            if loc is not None and loc.text:
                sitemap_urls.append(loc.text.strip())
        print(f"[INFO] Found {len(sitemap_urls)} sitemaps")
        return sitemap_urls
    except Exception as e:
        print(f"[ERROR] Failed to fetch sitemap index: {e}")
        return []

# ====== Mengambil Artikel Yang Sesuai Dengan Kata Kunci Dan Date ======
def parse_reuters_sitemap(sitemap_url, keyword=None, date_filter=None):
    try:
        r = requests.get(sitemap_url, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        ns = {
            'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9',
            'news': 'http://www.google.com/schemas/sitemap-news/0.9'
        }
        articles = []
        keyword_lower = keyword.lower() if keyword else None
        url_tags = root.findall('.//sm:url', ns)
        for url_tag in url_tags:
            loc = url_tag.find('sm:loc', ns)
            if loc is None or not loc.text:
                continue
            link = loc.text.strip()
            news_tag = url_tag.find('news:news', ns)
            if news_tag is None:
                continue
            title_tag = news_tag.find('news:title', ns)
            date_tag = news_tag.find('news:publication_date', ns)
            keywords_tag = news_tag.find('news:keywords', ns)
            title = title_tag.text.strip() if title_tag is not None and title_tag.text else "(No Title)"
            pubdate_raw = date_tag.text.strip() if date_tag is not None and date_tag.text else ""
            keywords = keywords_tag.text.strip() if keywords_tag is not None and keywords_tag.text else ""
            date_only = pubdate_raw.split('T')[0] if 'T' in pubdate_raw else pubdate_raw
            if keyword_lower:
                title_match = keyword_lower in title.lower()
                keywords_match = keyword_lower in keywords.lower()
                if not (title_match or keywords_match):
                    continue
            if date_filter:
                if isinstance(date_filter, datetime):
                    date_filter_str = date_filter.strftime('%Y-%m-%d')
                else:
                    date_filter_str = str(date_filter)
                if date_only != date_filter_str:
                    continue
            articles.append({
                'Judul': title,
                'Tanggal': date_only,
                'Link': link
            })   
        return articles
    except Exception as e:
        print(f"[ERROR] Failed to parse sitemap {sitemap_url}: {e}")
        return []

# ================= Scrapping Konten ===============
def fetch_article_content(url):
    """Fetch full article content from Reuters URL."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        )
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        for bad in soup(["script", "style", "figure", "iframe", "noscript", "aside", "nav"]):
            bad.decompose()
        article_body = soup.select_one("div.article-body-module__content__bnXL1")
        if not article_body:
            print(f"[WARN] Could not find article content in {url}")
            return "N/A"
        for elem in article_body.find_all(['p', 'div']):
            test_id = elem.get('data-testid', '')
            if any(x in test_id for x in ['promo-box', 'ad', 'banner', 'CnxPlayer', 'ResponsiveAdSlot']):
                elem.decompose()
                continue
            class_names = ' '.join(elem.get('class', []))
            if any(x in class_names for x in [
                'promo-box', 'ad-slot', 'cnx-player', 'news-assistant',
                'dianomi', 'sign-off', 'trust-badge', 'tags-'
            ]):
                elem.decompose()
                continue
            text = elem.get_text(strip=True)
            if any(phrase in text for phrase in [
                'Reuters Beacon newsletter',
                'Sign up here',
                'Discover the key points',
                'Reuters AI',
                'Advertisement',
                'Scroll to continue',
                'Reporting By',
                'Editing by',
                'Our Standards:',
                'The Thomson Reuters Trust Principles'
            ]):
                elem.decompose()
        content_parts = []
        for elem in article_body.find_all('div'):
            test_id = elem.get('data-testid', '')
            if test_id.startswith('paragraph-'):
                text = elem.get_text(strip=True)
                if text and len(text) > 10:
                    content_parts.append(text)
        if not content_parts:
            print(f"[WARN] No content found in {url}")
            return "N/A"
        content = "\n\n".join(content_parts)
        return content
    except Exception as e:
        print(f"[ERROR] Failed to fetch content {url}: {e}")
        return "N/A"

# ================= Scrapping Konten ===============
def scrape_reuters(keyword=None, date_filter=None, max_sitemaps=None):
    sitemap_urls = get_sitemap_urls()
    if not sitemap_urls:
        print("[INFO] No sitemaps found.")
        return []
    if max_sitemaps:
        sitemap_urls = sitemap_urls[:max_sitemaps]
        print(f"[INFO] Processing first {max_sitemaps} sitemaps only")
    all_articles = []
    for i, sitemap_url in enumerate(sitemap_urls, 1):
        print(f"\n[INFO] ({i}/{len(sitemap_urls)}) Processing: {sitemap_url}")
        articles = parse_reuters_sitemap(sitemap_url, keyword, date_filter)
        all_articles.extend(articles)
        print(f"   Found {len(articles)} matching articles")
        time.sleep(0.5) 
        if keyword or date_filter:
            if len(all_articles) >= 50: 
                print(f"[INFO] Found {len(all_articles)} articles, stopping early")
                break
    filter_info = []
    if keyword:
        filter_info.append(f"keyword '{keyword}'")
    if date_filter:
        filter_info.append(f"date {date_filter}")
    filter_text = " with " + " and ".join(filter_info) if filter_info else ""
    print(f"\n[INFO] Total matching articles{filter_text}: {len(all_articles)}")
    if not all_articles:
        return []
    print(f"\n[INFO] Fetching article content...")
    for i, article in enumerate(all_articles, 1):
        print(f"[INFO] ({i}/{len(all_articles)}) Fetching: {article['Link']}")
        article['Konten'] = fetch_article_content(article['Link'])
        time.sleep(1.0)
    return all_articles

# ============= Menyimpan File ===================
def save_to_excel(data, keyword=None, output_filename=None):
    if not data:
        print("[WARN] No data to save.")
        return None
    df = pd.DataFrame(data)
    column_order = ['Judul', 'Tanggal', 'Link', 'Konten']
    df = df[[col for col in column_order if col in df.columns]]
    results_folder = r"..\hasil-scrapping"
    os.makedirs(results_folder, exist_ok=True)
    if output_filename is None:
        if keyword:
            safe_keyword = keyword.replace(' ', '_').replace('/', '_')
            output_filename = f"reuters_{safe_keyword}.xlsx"
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"reuters_news_{timestamp}.xlsx"
    if not output_filename.endswith('.xlsx'):
        output_filename += '.xlsx'
    full_path = os.path.join(results_folder, output_filename)
    df.to_excel(full_path, index=False)
    print(f"\n[SUCCESS] Berhasil menyimpan {len(df)} artikel ke '{full_path}'")
    return df

# =================== Main =================
def main_reuters(keyword=None, date_filter=None, max_sitemaps=5):
    print(f"\n{'='*60}")
    print(f"Reuters News Scraper")
    print(f"{'='*60}\n")
    data = scrape_reuters(keyword, date_filter, max_sitemaps)
    if data:
        df = save_to_excel(data, keyword)
        print(f"\n{'='*60}")
        print(f"Preview (first 3 articles):")
        print(f"{'='*60}\n")
        for i, article in enumerate(data[:3], 1):
            print(f"{i}. {article['Judul']}")
            print(f"   Tanggal: {article['Tanggal']}")
            print(f"   Link: {article['Link']}")
            print()
        return df
    else:
        print("[INFO] No articles to save.")
        return None

if __name__ == '__main__':
    main_reuters(keyword="Trump", date_filter="2025-11-17")