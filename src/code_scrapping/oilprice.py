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

# ======== Fungsi : Menemukan Artikel Yang Sesuai Dengan Tanggal Dan Keyword ========
def parse_oilprice_xml(keyword=None, date_filter=None):
    url = "https://oilprice.com/googlenews.xml"
    print(f"[INFO] Fetching OilPrice.com news XML: {url}")
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        ns = {
            'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9',
            'news': 'http://www.google.com/schemas/sitemap-news/0.9'
        }
        articles = []
        url_tags = root.findall('.//sm:url', ns)
        print(f"[INFO] Found {len(url_tags)} total articles in XML")
        keyword_lower = keyword.lower() if keyword else None
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
        filter_info = []
        if keyword:
            filter_info.append(f"keyword '{keyword}'")
        if date_filter:
            filter_info.append(f"date {date_filter}")
        filter_text = " with " + " and ".join(filter_info) if filter_info else ""
        print(f"[INFO] Found {len(articles)} matching articles{filter_text}")
        return articles
    except Exception as e:
        print(f"[ERROR] Failed to parse XML: {e}")
        return []
    
# ======== Fungsi : Mengambil Konten Artikel ========
def fetch_article_content(url):
    """Fetch full article content from OilPrice.com URL."""
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
        for bad in soup(["script", "style", "figure", "iframe", "noscript", "aside"]):
            bad.decompose()
        article_body = soup.select_one("div#article-content.wysiwyg.clear")
        if not article_body:
            print(f"[WARN] Could not find article content in {url}")
            return "N/A"
        found_more_top_reads = False
        elements_to_remove = []
        for elem in article_body.find_all(['p', 'ul', 'li', 'strong']):
            text = elem.get_text(strip=True)
            if 'More Top Reads' in text:
                found_more_top_reads = True
                elements_to_remove.append(elem)
                if elem.parent and elem.parent.name == 'p':
                    elements_to_remove.append(elem.parent)
                continue
            if found_more_top_reads and elem.name in ['ul', 'li']:
                elements_to_remove.append(elem)
                continue
            if any(phrase in text for phrase in [
                'Related:',
                'for Oilprice.com',
                'Download The Free Oilprice App',
                'Back to homepage'
            ]):
                elements_to_remove.append(elem)
                if elem.parent and elem.parent.name in ['p', 'ul']:
                    elements_to_remove.append(elem.parent)
        for elem in set(elements_to_remove):
            elem.decompose()
        content_parts = []
        for elem in article_body.find_all(['p', 'li']):
            text = elem.get_text(strip=True)
            if not text or len(text) < 10:
                continue
            if any(phrase in text.lower() for phrase in [
                'subscribe',
                'newsletter',
                'advertisement',
                'click here',
                'more top reads',
                'related:'
            ]):
                continue
            links = elem.find_all('a')
            if links and len(text) < 100:
                link_text_length = sum(len(link.get_text(strip=True)) for link in links)
                if link_text_length / len(text) > 0.8:
                    continue
            content_parts.append(text)
        if not content_parts:
            print(f"[WARN] No content found in {url}")
            return "N/A"
        content = "\n\n".join(content_parts)
        return content
    except Exception as e:
        print(f"[ERROR] Failed to fetch content {url}: {e}")
        return "N/A"

# ======== Fungsi : Main Scrapping ========   
def scrape_oilprice(keyword=None, date_filter=None):
    articles = parse_oilprice_xml(keyword, date_filter)
    if not articles:
        print("[INFO] No articles found.")
        return []
    for i, article in enumerate(articles, 1):
        print(f"[INFO] ({i}/{len(articles)}) Fetching content: {article['Link']}")
        article['Konten'] = fetch_article_content(article['Link'])
        time.sleep(1.0)
    return articles

# ======== Fungsi : Menyimpan Ke Excel ========    
def reformat(data):
    if not data:
        print("[WARN] No data to save.")
        return None
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

# ======== Fungsi : Main ========   
def main_oilprice(keyword=None, tanggal=None):
    print(f"\n{'='*60}")
    print(f"OilPrice.com News Scraper")
    print(f"{'='*60}\n")
    data = scrape_oilprice(keyword, tanggal)
    if not data:  
        print("[INFO] No articles to save.")
        return None
    df = reformat(data)
    return df if not df.empty else None
if __name__ == '__main__':
    main_oilprice(keyword="Oil Price", date_filter="2025-11-17")