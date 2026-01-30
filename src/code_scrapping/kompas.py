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

def fetch_xml(url):
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    content = r.content
    if url.endswith('.gz') or content[:2] == b'\x1f\x8b':
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(content)) as f:
                content = f.read()
        except Exception as e:
            print(f"[WARN] Failed to decompress gzip {url}: {e}")
    return content

def get_text_from_element(element):
    if element is None:
        return ""
    text = ''.join(element.itertext()).strip()
    return text if text else ""

def get_main_sitemap():
    url = "https://www.kompas.com/sitemap.xml"
    content = fetch_xml(url)
    return ET.fromstring(content)

def is_sitemap_index(root, ns):
    has_sitemap_tags = root.findall('.//sm:sitemap', ns)
    has_url_tags = root.findall('.//sm:url', ns)
    return len(has_sitemap_tags) > 0 and len(has_url_tags) == 0

def get_all_article_sitemaps(root, depth=0, max_depth=3):
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    article_sitemaps = []
    if depth > max_depth:
        print(f"[WARN] Max depth reached ({max_depth})")
        return article_sitemaps
    sitemap_tags = root.findall('.//sm:sitemap', ns)
    if not sitemap_tags:
        return []
    for sitemap_tag in sitemap_tags:
        loc = sitemap_tag.find('sm:loc', ns)
        if loc is None:
            continue
        href = get_text_from_element(loc)
        if not href:
            continue
        if 'news' not in href.lower():
            continue
        print(f"{'  ' * depth}[INFO] Checking: {href}")
        try:
            content = fetch_xml(href)
            subroot = ET.fromstring(content)
            if is_sitemap_index(subroot, ns):
                print(f"{'  ' * depth}  └─ Sitemap index, drilling down...")
                nested = get_all_article_sitemaps(subroot, depth + 1, max_depth)
                article_sitemaps.extend(nested)
            else:
                url_tags = subroot.findall('.//sm:url', ns)
                print(f"{'  ' * depth}  └─ Article sitemap! Found {len(url_tags)} URLs")
                article_sitemaps.append(href)
            time.sleep(0.1)
        except Exception as e:
            print(f"{'  ' * depth}  └─ [ERROR] {e}")
            continue
    return article_sitemaps

def extract_news_info(url_tag, ns):
    loc_tag = url_tag.find('sm:loc', ns)
    if loc_tag is None:
        return None
    link = get_text_from_element(loc_tag)
    if not link:
        return None
    news_ns = {'news': 'http://www.google.com/schemas/sitemap-news/0.9'}
    title = ""
    pubdate_raw = ""
    keywords = ""
    news_tag = url_tag.find('news:news', news_ns)
    if news_tag is not None:
        t = news_tag.find('news:title', news_ns)
        p = news_tag.find('news:publication_date', news_ns)
        k = news_tag.find('news:keywords', news_ns)
        title = get_text_from_element(t)
        pubdate_raw = get_text_from_element(p)
        keywords = get_text_from_element(k)
    date_only = pubdate_raw.split('T')[0] if 'T' in pubdate_raw else pubdate_raw or '-'
    return {
        'title': title or '(No Title)',
        'link': link,
        'pubdate': pubdate_raw,
        'date': date_only,
        'keywords': keywords
    }

def get_kompas_news_by_keyword(keyword):
    try:
        root = get_main_sitemap()
    except Exception as e:
        print(f"[ERROR] Failed to fetch main sitemap: {e}")
        return []
    print("[INFO] Crawling sitemap tree to find article sitemaps...")
    article_sitemaps = get_all_article_sitemaps(root)
    if not article_sitemaps:
        print("[WARN] No article sitemaps found.")
        return []
    print(f"\n[INFO] Found {len(article_sitemaps)} article sitemap(s).")
    print("[INFO] Starting keyword search...\n")
    
    results = []
    keyword_pattern = r'\b' + re.escape(keyword.strip().lower()) + r'\b'  # ✅ TAMBAH BARIS INI
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    
    for idx, sitemap_url in enumerate(article_sitemaps, 1):
        print(f"[INFO] ({idx}/{len(article_sitemaps)}) Processing: {sitemap_url}")
        try:
            content = fetch_xml(sitemap_url)
            subroot = ET.fromstring(content)
            urls = subroot.findall('.//sm:url', ns)
            print(f"   URLs in this sitemap: {len(urls)}")
            for url_tag in urls:
                info = extract_news_info(url_tag, ns)
                if not info or not info.get('link'):
                    continue
                title = info.get('title') or ""
                keywords = info.get('keywords') or ""
                link = info.get('link') or ""
                
                # ✅ GANTI BARIS INI
                if (re.search(keyword_pattern, title.lower()) or 
                    re.search(keyword_pattern, keywords.lower())):
                    results.append({
                        'Judul': title if title else link,
                        'Link': link,
                        'Tanggal': info.get('date') if info.get('date') else '-'
                    })
            
            print(f"   Matching articles so far: {len(results)}")
        except Exception as e:
            print(f"[ERROR] Failed to process {sitemap_url}: {e}")
            continue
        time.sleep(0.15)
    print(f"\n[INFO] Total articles with keyword '{keyword}': {len(results)}")
    return results

def bersihkan_konten(content_div):
    if not content_div:
        return "-"
    unwanted_selectors = ["aside", "script", "style", "iframe", "noscript"]
    for sel in unwanted_selectors:
        for tag in content_div.find_all(sel):
            tag.decompose()
    unwanted_classes = ["kompasidRec__wrap", "kompasidRec__subs", "kompasidRec__title", "articleRelated", "article__related", "inner__sidebar", "inject-baca-juga", "ads-on-body"]
    for kelas in unwanted_classes:
        for tag in content_div.find_all(class_=kelas):
            tag.decompose()
    for comment in content_div.find_all(string=lambda text: isinstance(text, str) and '<!--' in text):
        comment.extract()
    elements = content_div.find_all(["p", "li", "h2", "h3"])
    paragraphs = []
    for e in elements:
        text = e.get_text(strip=True)
        if not text or len(text) < 5:
            continue
        if re.search(r'^(baca\s+juga|download\s+sekarang|dalam\s+segala\s+situasi)', text, re.IGNORECASE):
            continue
        paragraphs.append(text)
    if not paragraphs:
        return "-"
    content = "\n\n".join(paragraphs)
    content = re.sub(r'\s+', ' ', content).strip()
    return content

def get_total_pages(soup):
    paging_wrap = soup.select_one("div.paging__wrap")
    if not paging_wrap:
        return 1
    paging_items = paging_wrap.select("div.paging__item")
    if not paging_items:
        return 1
    max_page = 1
    for item in paging_items:
        link = item.select_one("a.paging__link")
        if not link:
            continue
        href = link.get('href', '')
        if '?page=' in href:
            try:
                page_num = int(href.split('?page=')[-1].split('&')[0])
                if page_num > max_page:
                    max_page = page_num
            except (ValueError, IndexError):
                continue
    return max_page

def fetch_article_content(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    all_content = []
    try:
        base_url = url.split('?')[0]
        r = requests.get(base_url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        content_div = soup.select_one("div.read__content")
        if not content_div:
            print(f"[WARN] Missing content div in {base_url}")
            return "N/A"
        cleaned_content = bersihkan_konten(content_div)
        if cleaned_content and cleaned_content != "-":
            all_content.append(cleaned_content)
        total_pages = get_total_pages(soup)
        if total_pages > 1:
            print(f"   Total pages detected: {total_pages}")
            for page_num in range(2, total_pages + 1):
                page_url = f"{base_url}?page={page_num}"
                print(f"   Fetching page {page_num}: {page_url}")
                r_page = requests.get(page_url, headers=headers, timeout=15)
                r_page.raise_for_status()
                current_soup = BeautifulSoup(r_page.content, "html.parser")
                content_div = current_soup.select_one("div.read__content")
                if not content_div:
                    print(f"[WARN] Missing content div in page {page_num}")
                    continue
                cleaned_content = bersihkan_konten(content_div)
                if cleaned_content and cleaned_content != "-":
                    all_content.append(cleaned_content)
                time.sleep(0.5)
        if not all_content:
            print(f"[WARN] No valid content found in {url}")
            return "N/A"
        return "\n\n".join(all_content)
    except Exception as e:
        print(f"[ERROR] Failed to fetch content {url}: {e}")
        return "N/A"

def scrape_kompas(keyword, date=None):
    articles = get_kompas_news_by_keyword(keyword)
    if not articles:
        print("[INFO] No articles found for this keyword.")
        return []
    if date:
        if isinstance(date, datetime):
            date = date.strftime('%Y-%m-%d')
        else:
            date = str(date)
        articles = [a for a in articles if a.get('Tanggal') == date]
        print(f"[INFO] After date filter ({date}), remaining: {len(articles)} articles.")
    if not articles:
        return []
    for i, a in enumerate(articles, 1):
        print(f"[INFO] ({i}/{len(articles)}) Fetching content: {a['Link']}")
        a['Konten'] = fetch_article_content(a['Link'])
        time.sleep(1.0)
    return articles

def reformat(data):
    df = pd.DataFrame(data)
    df = df.rename(
        columns={
            'Judul' : 'title', 
            'Tanggal' : 'date', 
            'Link' : 'url', 
            'Konten' : 'content'
        }
    )
    return df

def main_kompas(keyword="MotoGP", tanggal="2025-11-16"):
    try:
        data = scrape_kompas(keyword, date=tanggal)
        if not data:
            print("No articles found.")
            return None
        df = reformat(data)
        if df.empty:
            print("No articles found after formatting.")
            return None
        print(f"Successfully scraped {len(df)} articles from Kompas")
        return df
    except Exception as e:
        print(f"Error in main_kompas: {e}")
        return None

if __name__ == '__main__':
    print(main_kompas(keyword="Ekonomi", tanggal="2026-01-28"))