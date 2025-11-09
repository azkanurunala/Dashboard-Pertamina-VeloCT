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

# ============================== TEXT CLEANING ==============================
def clean_text(text):
    """Remove irrelevant lines from article content."""
    if not text or text == 'N/A':
        return text

    lines = []
    for line in text.splitlines():
        # Skip lines containing unwanted phrases
        if re.search(r'(Baca\s+Juga|Selanjutnya|Menarik\s+Dibaca|Cek\s+Berita|INDEKS\s+BERITA)', line, flags=re.IGNORECASE):
            continue
        # Skip lines containing only URLs
        if re.match(r'^\s*https?://', line.strip()):
            continue
        lines.append(line.strip())

    # Clean multiple blank lines
    cleaned = "\n".join(line for line in lines if line)
    cleaned = re.sub(r'\n{2,}', '\n\n', cleaned).strip()

    return cleaned

# ============================== CONTENT SCRAPER ==============================
def fetch_article_content(url):
    """Scrape main article content from Kontan page."""
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

        # Remove unnecessary tags
        for bad in soup(["script", "style", "figure", "iframe", "noscript"]):
            bad.decompose()

        div = soup.select_one("div.tmpt-desk-kon")
        if not div:
            print(f"[WARN] Missing div.tmpt-desk-kon in {url}")
            return "N/A"

        # Collect text only from <p> and <li>
        elements = div.find_all(["p", "li"])
        paragraphs = []
        for e in elements:
            text = e.get_text(strip=True)
            if text and not re.search(r'Baca\s+Juga', text, re.IGNORECASE):
                paragraphs.append(text)

        if not paragraphs:
            print(f"[WARN] No paragraph text found in {url}")
            return "N/A"

        content = "\n\n".join(paragraphs)
        return clean_text(content)

    except Exception as e:
        print(f"[ERROR] Failed to fetch content {url}: {e}")
        return "N/A"

# ============================== XML FETCHER ==============================
def fetch_xml(url):
    """Fetch and decompress XML or GZ sitemap file."""
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

# ============================== SITEMAP HANDLING ==============================
def get_main_sitemap():
    """Retrieve main sitemap root."""
    url = "https://www.kontan.co.id/sitemap.xml"
    print(f"[INFO] Fetching main sitemap: {url}")
    content = fetch_xml(url)
    return ET.fromstring(content)

def get_news_sitemaps(root):
    """Get sub-sitemaps that contain 'news' and 'investasi' or 'industri'."""
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    links = []
    for loc in root.findall('.//sm:loc', ns):
        if loc.text:
            href = loc.text.strip().lower()
            if (
                ('news' in href)
                and (('investasi' in href) or ('industri' in href))
                and (href.endswith('.xml') or href.endswith('.xml.gz'))
                and ('sitemap' in href or '/sitemaps/' in href)
            ):
                links.append(href)

    unique_links = list(dict.fromkeys(links))  # remove duplicates
    print(f"[INFO] Found {len(unique_links)} news sub-sitemaps for investasi/industri.")
    for i, link in enumerate(unique_links, 1):
        print(f"   {i}. {link}")
    return unique_links

# ============================== EXTRACT NEWS INFO ==============================
def extract_news_info(url_tag, ns):
    """Extract title, link, and publication date from a <url> tag."""
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

# ============================== FILTER NEWS BY KEYWORD ==============================
def get_kontan_news_by_keyword(keyword):
    """Find all Kontan articles that match a given keyword."""
    try:
        root = get_main_sitemap()
    except Exception as e:
        print(f"[ERROR] Failed to fetch main sitemap: {e}")
        return []

    subs = get_news_sitemaps(root)
    if not subs:
        print("[WARN] No sub-sitemaps found containing 'news'.")
        return []

    results = []
    keyword_lower = keyword.lower()
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

    for idx, sub in enumerate(subs, 1):
        print(f"[INFO] ({idx}/{len(subs)}) Processing: {sub}")
        try:
            content = fetch_xml(sub)
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

                # Match by title, keywords, or link text
                if (keyword_lower in title.lower()) or (keyword_lower in keywords.lower()) or (keyword_lower in link.lower()):
                    results.append({
                        'Judul': title if title else link,
                        'Link': link,
                        'Tanggal': info.get('date') if info.get('date') else '-'
                    })
            print(f"   Matching articles so far: {len(results)}")
        except Exception as e:
            print(f"[ERROR] Failed to process {sub}: {e}")
            continue
        time.sleep(0.15)

    print(f"[INFO] Total articles with keyword '{keyword}': {len(results)}")
    return results

# ============================== SCRAPE AND SAVE ==============================
def scrape_kontan(keyword, date=None):
    """Scrape articles from Kontan that match keyword and optional date."""
    articles = get_kontan_news_by_keyword(keyword)
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

def save_to_excel(data, query, output_filename=None):
    # Pastikan data berupa DataFrame
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data

    # Ubah nama kolom jika perlu
    df.columns = ["Judul", "Tanggal", "Link", "Konten"]

    # Tentukan folder hasil
    results_folder = r"..\hasil-scrapping"
    os.makedirs(results_folder, exist_ok=True)

    # Buat nama file
    if output_filename is None:
        output_filename = f"hasil_scraping_kontan_{query.replace(' ', '_')}.xlsx"
    if not output_filename.endswith('.xlsx'):
        output_filename += '.xlsx'

    full_path = os.path.join(results_folder, output_filename)
    df.to_excel(full_path, index=False)

    print(f"\n✅ Berhasil menyimpan {len(df)} data ke '{full_path}'")
    return df

# ============================== MAIN EXECUTION ==============================
if __name__ == '__main__':
    keyword = "Pembukaan Toko"
    date_filter = "2025-11-09"
    data = scrape_kontan(keyword, date=date_filter)
    if data:
        save_to_excel(data, keyword)
        for d in data[:3]:
            print(d['Judul'], d['Tanggal'], d['Link'])
    else:
        print("No articles found.")
