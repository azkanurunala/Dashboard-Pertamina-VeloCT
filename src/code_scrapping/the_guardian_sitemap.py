import requests
import xml.etree.ElementTree as ET
import pandas as pd
import gzip
import io
import re
import time
from datetime import datetime

from bs4 import BeautifulSoup

def fetch_xml(url):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        r.raise_for_status()
        c = r.content
        if url.endswith('.gz') or c[:2] == b'\x1f\x8b':
            with gzip.GzipFile(fileobj=io.BytesIO(c)) as f:
                c = f.read()
        return c
    except Exception as e:
        print(f"[ERROR] Failed to fetch {url}: {e}")
        return b""

def extract_news_info(url_tag, ns):
    loc_tag = url_tag.find('sm:loc', ns)
    if loc_tag is None or not loc_tag.text:
        return None
    link = loc_tag.text.strip()
    news_ns = {'news': 'http://www.google.com/schemas/sitemap-news/0.9'}
    title = ""
    pubdate_raw = ""
    keywords = ""
    news_tag = url_tag.find('news:news', news_ns)
    if news_tag is not None:
        t = news_tag.find('news:title', news_ns)
        p = news_tag.find('news:publication_date', news_ns)
        k = news_tag.find('news:keywords', news_ns)
        if t is not None and t.text:
            title = t.text.strip()
        if p is not None and p.text:
            pubdate_raw = p.text.strip()
        if k is not None and k.text:
            keywords = k.text.strip()
    if not pubdate_raw:
        lastmod = url_tag.find('sm:lastmod', ns)
        if lastmod is not None and lastmod.text:
            pubdate_raw = lastmod.text.strip()
    date_only = pubdate_raw.split('T')[0] if 'T' in pubdate_raw else pubdate_raw or '-'
    return {
        'title': title or '(No Title)',
        'link': link,
        'pubdate': pubdate_raw,
        'date': date_only,
        'keywords': keywords
    }

def get_the_guardian_news_by_keyword(keyword):
    sitemap_url = "http://www.theguardian.com/sitemaps/news.xml"
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    print(f"[INFO] Fetching sitemap: {sitemap_url}")
    content = fetch_xml(sitemap_url)
    if not content:
        print("[ERROR] Failed to fetch sitemap")
        return []
    try:
        root = ET.fromstring(content)
    except Exception as e:
        print(f"[ERROR] Failed to parse sitemap: {e}")
        return []
    urls = root.findall('.//sm:url', ns)
    print(f"[INFO] Found {len(urls)} URLs in sitemap")
    results = []
    keyword_lower = keyword.lower()
    for url_tag in urls:
        info = extract_news_info(url_tag, ns)
        if not info or not info.get('link'):
            continue
        title = info.get('title') or ""
        keywords_text = info.get('keywords') or ""
        link = info.get('link') or ""
        if (keyword_lower in title.lower()) or \
           (keyword_lower in keywords_text.lower()) or \
           (keyword_lower in link.lower()):
            results.append({
                'Judul': title if title else link,
                'Link': link,
                'Tanggal': info.get('date', '-')
            })
    print(f"[INFO] Total articles with keyword '{keyword}': {len(results)}")
    return results

def is_valid_paragraph(text, min_length=15):
    if not text or len(text) < min_length:
        return False
    spam_keywords = [
        'cookie', 'privacy policy', 'terms of service',
        'subscribe', 'sign up', 'newsletter', 'follow us',
        'advertisement', 'share on', 'view image in fullscreen',
        'photograph:', 'marketing preferences', 'enter your email',
        'skip past newsletter', 'after newsletter promotion',
        'privacy notice:', 'get updates about', 'sign up to'
    ]
    text_lower = text.lower()
    return not any(keyword in text_lower for keyword in spam_keywords)

def clean_text(text):
    if not text:
        return ''
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def fetch_article_content(url):
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
        for tag in soup(["script", "style", "figure", "iframe", "noscript", 
                         "aside", "form", "button", "svg", "gu-island"]):
            tag.decompose()
        containers = [
            soup.select_one("div.article-body-commercial-selector")
        ]
        content_div = None
        for container in containers:
            if container:
                content_div = container
                break
        if not content_div:
            print(f"[WARN] No article body found in {url}")
            return "N/A"
        paragraphs = []
        for element in content_div.find_all(['p', 'h2', 'h3', 'li']):
            text = element.get_text(strip=True)
            if is_valid_paragraph(text) and text not in paragraphs:
                paragraphs.append(text)
        if not paragraphs:
            print(f"[WARN] No valid paragraphs found in {url}")
            return "N/A"
        content = "\n\n".join(paragraphs)
        return clean_text(content)
    except Exception as e:
        print(f"[ERROR] Failed to fetch content from {url}: {e}")
        return "N/A"

def scrape_the_guardian(keyword, date=None, fetch_content=True):
    keyword = keyword.strip()
    print("=" * 70)
    print(f"Scraping The Guardian for keyword: '{keyword}'")
    if fetch_content:
        print("Mode: Fetch FULL CONTENT")
    else:
        print("Mode: Metadata only (no content)")
    print("=" * 70)
    articles = get_the_guardian_news_by_keyword(keyword)
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
        print("[INFO] No articles found after filtering.")
        return []
    if fetch_content:
        print(f"\n[INFO] Fetching content for {len(articles)} articles...")
        for idx, article in enumerate(articles, 1):
            print(f"  ({idx}/{len(articles)}) Fetching: {article['Judul'][:60]}...")
            content = fetch_article_content(article['Link'])
            article['Konten'] = content
            time.sleep(1.5)
        print("[INFO] Content fetch complete!")
    else:
        for article in articles:
            article['Konten'] = ''
    return articles

if __name__ == "__main__":
    keyword = "oil"
    tanggal = "2026-01-19"  
    print(f"\nScraping The Guardian - keyword: {keyword}\n")
    hasil = scrape_the_guardian(keyword, tanggal, fetch_content=True)
    print(f"\nTotal: {len(hasil)} berita")
    if hasil:
        df = pd.DataFrame(hasil)
        filename = f"guardian_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"Saved: {filename}")
        print("\nPreview:")
        for i, row in enumerate(hasil[:3], 1):
            print(f"\n{i}. {row['Judul']}")
            print(f"   Date: {row['Tanggal']}")
            print(f"   URL: {row['Link']}")
            if row.get('Konten'):
                print(f"   Content: {row['Konten'][:200]}...")