import pandas as pd
from datetime import datetime
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import xml.etree.ElementTree as ET
import requests
import gzip
import io
from bs4 import BeautifulSoup
import urllib.parse
import feedparser

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

def scrape_cnbc(url):
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

def is_valid_paragraph(teks, min_length=10):
    if not teks or len(teks) < min_length:
        return False
    spam = ['cookie', 'privacy policy', 'terms of service', 'subscribe', 'sign up', 'newsletter', 'follow us', 'advertisement']
    teks_lower = teks.lower()
    return not any(k in teks_lower for k in spam) and not re.match(r'^[\d\s\-:,\.]+$', teks)

def bersihkan_teks_cnn(teks):
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

def scrape_cnn(url):
    try:
        r = requests.get(url, headers={'User-Agent':'Mozilla/5.0'}, timeout=20)
        r.raise_for_status()
        s = BeautifulSoup(r.content, 'html.parser')

        # Hapus "top headlines" section jika ada
        top_headlines = s.find('h2', id='top-headlines')
        if top_headlines:
            next_sibling = top_headlines.find_next_sibling()
            while next_sibling:
                if next_sibling.name == 'div' and next_sibling.find('ul'):
                    next_sibling.decompose()
                    break
                next_sibling = next_sibling.find_next_sibling()
            top_headlines.decompose()

        for list_div in s.find_all('div', class_='list-elevate'):
            prev_h2 = list_div.find_previous('h2')
            if prev_h2 and 'top headlines' in prev_h2.get_text().lower():
                list_div.decompose()

        paragraf = []
        for selector in ['div.article__content', 'div.video-resource__description', 'main', 'article']:
            container = s.select_one(selector)
            if container:
                for el in container.find_all(['h2', 'p', 'li']):
                    teks = el.get_text(strip=True)
                    if is_valid_paragraph(teks, min_length=8) and teks not in paragraf:
                        paragraf.append(teks)
                if len(paragraf) >= 3:
                    break

        if len(paragraf) < 2:
            for el in s.find_all(['h2', 'p', 'li']):
                teks = el.get_text(strip=True)
                if is_valid_paragraph(teks, min_length=10) and teks not in paragraf:
                    paragraf.append(teks)

        return bersihkan_teks_cnn("\n\n".join(paragraf)) if paragraf else 'N/A'
    except Exception as e:
        print(f"Gagal ambil konten CNN: {e}")
        return 'N/A'

def scrape_google_news(keyword, language='en', country='US', filter_date=None, filter_platform=None):
    # Encode keyword untuk URL
    encoded_keyword = urllib.parse.quote(keyword)
    rss_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl={language}&gl={country}&ceid={country}:{language}"
    print(f"  [RSS URL] {rss_url}")

    # Fetch dan parse RSS feed
    try:
        feed = feedparser.parse(rss_url)
        if not feed.entries:
            print("Tidak ada berita ditemukan")
            return []
    except Exception as e:
        print(f"Error parsing RSS: {e}")
        return []

    articles = []

    # Normalize filter_date to date object if it's a string
    if filter_date:
        if isinstance(filter_date, str):
            try:
                filter_date = datetime.strptime(filter_date, '%Y-%m-%d').date()
            except:
                print(f"  [WARNING] Invalid filter_date format: {filter_date}, expected YYYY-MM-DD")
                filter_date = None
        elif isinstance(filter_date, datetime):
            filter_date = filter_date.date()

    for entry in feed.entries:
        # Parse tanggal publikasi
        published_date = entry.get('published', '')
        try:
            pub_date = datetime.strptime(published_date, '%a, %d %b %Y %H:%M:%S %Z').date()
        except:
            pub_date = None

        # Ekstrak source dari entry
        source = entry.get('source', {}).get('title', 'Unknown') if hasattr(entry.get('source', {}), 'get') else 'Unknown'

        # Filter berdasarkan tanggal
        if filter_date and pub_date != filter_date:
            continue

        # Filter berdasarkan platform (case-insensitive)
        if filter_platform and filter_platform.upper() not in source.upper():
            continue

        url = entry.get('link', '')
        print(f"  [Google News URL] {url}")

        articles.append({
            'title': entry.get('title', ''),
            'date': pub_date,
            'url': url,
            'source': source
        })

    print(f"Total {len(articles)} artikel ditemukan (setelah filter)")
    return articles

def resolve_google_news_url_selenium(google_url):
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(20)  # Increased timeout
        driver.get(google_url)

        # Wait for redirect
        max_wait = 15
        start_time = time.time()
        while time.time() - start_time < max_wait:
            current_url = driver.current_url
            if 'news.google.com' not in current_url:
                print(f"  [SELENIUM] Redirected successfully")
                return current_url
            time.sleep(0.5)

        # If still on Google News after waiting, return original URL
        print(f"  [SELENIUM] No redirect detected, returning original URL")
        return google_url
    except Exception as e:
        print(f"  [ERROR] Selenium gagal: {str(e)[:200]}")
        return google_url
    finally:
        if driver:
            driver.quit()


def cari_artikel_di_sitemap(platform, title, date_str=None):
    try:
        if platform not in PLATFORM_SITEMAPS:
            return None
        sitemap_url = PLATFORM_SITEMAPS[platform]
        data = fetch_xml(sitemap_url)
        if not data:
            return None
        root = ET.fromstring(data)
        ns = {
            'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9',
            'news': 'http://www.google.com/schemas/sitemap-news/0.9'
        }

        # Strip platform name from title (e.g., " - CNN", " - CNBC")
        title_clean = re.sub(rf'\s*-\s*{platform}$', '', title, flags=re.IGNORECASE).strip()
        title_normalized = re.sub(r'[^\w\s]', '', title_clean.lower()).strip()

        for url_tag in root.findall('.//sm:url', ns):
            info = ekstrak_info(url_tag, ns)
            if not info:
                continue
            if date_str and info['date'] != date_str:
                continue
            sitemap_title_normalized = re.sub(r'[^\w\s]', '', info['title'].lower()).strip()

            if title_normalized == sitemap_title_normalized:
                return {
                    'url': info['url'],
                    'title': info['title']
                }
        return None
    except Exception as e:
        print(f"  [ERROR] Gagal cari di sitemap {platform}: {str(e)}")
        return None
    
PLATFORM_SCRAPERS = {
    'CNBC': scrape_cnbc,
    'CNN': scrape_cnn,
}

PLATFORM_SITEMAPS = {
    'CNBC': 'https://www.cnbc.com/sitemap_news.xml',
    'CNN': 'https://www.cnn.com/sitemap/news.xml',
}

def scrape_google_news_with_content(keyword, language='en', country='US', filter_date=None, filter_platform=None, use_selenium_fallback=True):
    print("=" * 70)
    print("STEP 1: Mengambil metadata dari Google News")
    print("=" * 70)
    articles = scrape_google_news(keyword, language, country, filter_date, filter_platform)
    if not articles:
        return []
    print("\n" + "=" * 70)
    print("STEP 2: Mengambil konten artikel")
    print("=" * 70)
    print(f"Total artikel: {len(articles)}")
    print(f"Mode: Sitemap -> Selenium Fallback")
    print(f"Selenium Fallback: {'Enabled' if use_selenium_fallback else 'Disabled'}")
    for idx, article in enumerate(articles):
        article['content'] = 'N/A'
        print(f"\n[{idx+1}/{len(articles)}] {article['title'][:60]}...")
        print(f"  Source: {article['source']}")
        print(f"  Date: {article['date']}")
        platform = None
        for platform_key in PLATFORM_SCRAPERS.keys():
            if platform_key.upper() in article['source'].upper():
                platform = platform_key
                break
        if not platform:
            print(f"  [SKIP] Platform {article['source']} belum didukung")
            continue
        scraper_func = PLATFORM_SCRAPERS[platform]
        print(f"  [SITEMAP] Mencari di {platform} sitemap...")
        date_str = article['date'].strftime('%Y-%m-%d') if article['date'] else None
        matched = cari_artikel_di_sitemap(platform, article['title'], date_str)
        if matched:
            print(f"  [SITEMAP] FOUND")
            print(f"  [SITEMAP] Title: {matched['title'][:60]}...")
            print(f"  [SITEMAP] URL: {matched['url'][:80]}...")
            article['url'] = matched['url']
            print(f"  [CONTENT] Mengambil konten dari sitemap URL...")
            content = scraper_func(matched['url'])
            article['content'] = content
            if content != 'N/A':
                print(f"  [CONTENT] OK - {len(content)} karakter")
            else:
                print(f"  [CONTENT] FAIL - Konten kosong")
        else:
            print(f"  [SITEMAP] NOT FOUND")
            if use_selenium_fallback:
                print(f"  [SELENIUM] Fallback: Resolving Google News URL...")
                actual_url = resolve_google_news_url_selenium(article['url'])
                print(f"  [SELENIUM] Resolved to: {actual_url[:80]}...")
                print(f"  [CONTENT] Mengambil konten dengan BeautifulSoup...")
                content = scraper_func(actual_url)
                article['content'] = content
                if content != 'N/A':
                    print(f"  [CONTENT] OK - {len(content)} karakter")
                else:
                    print(f"  [CONTENT] FAIL")
            else:
                print(f"  [SKIP] Selenium fallback disabled")

        time.sleep(0.5)
    return articles


if __name__ == "__main__":
    print("=" * 70)
    print("Google News Scraper - Multi Platform (CNBC & CNN)")
    print("=" * 70)
    keyword = "oil"
    platform = input("Pilih platform (CNBC/CNN/ALL): ").strip().upper() or "ALL"

    if platform not in ["CNBC", "CNN", "ALL"]:
        print("Platform tidak valid, menggunakan ALL")
        platform = "ALL"

    print(f"\nKeyword: '{keyword}'")
    print(f"Filter: {platform}")
    print(f"Strategy: Sitemap -> Selenium Fallback")

    if platform == "ALL":
        articles = scrape_google_news_with_content(
            keyword=keyword,
            filter_platform=None,
            use_selenium_fallback=True
        )
    else:
        articles = scrape_google_news_with_content(
            keyword=keyword,
            filter_platform=platform,
            use_selenium_fallback=True
        )

    if articles:
        total = len(articles)
        success = len([a for a in articles if a['content'] != 'N/A'])
        fail = total - success
        print("\n" + "=" * 70)
        print("HASIL SCRAPING")
        print("=" * 70)
        print(f"Total artikel: {total}")
        print(f"Berhasil: {success} ({success/total*100:.1f}%)")
        print(f"Gagal: {fail} ({fail/total*100:.1f}%)")
        print("\n" + "=" * 70)
        print("PREVIEW ARTIKEL")
        print("=" * 70)
        for idx, article in enumerate(articles):
            print(f"\n{idx+1}. {article['title']}")
            print(f"   Date: {article['date']}")
            print(f"   Source: {article['source']}")
            print(f"   URL: {article['url'][:80]}...")
            print(f"   Content: {len(article['content'])} chars")
            if article['content'] != 'N/A':
                print(f"   Preview: {article['content'][:150]}...")
        df = pd.DataFrame(articles)
        df.to_excel("google_news.xlsx", index=False)
        print("\n" + "=" * 70)
        print("SAVED to google_news.xlsx")
        print("=" * 70)
    else:
        print("\nTidak ada artikel ditemukan")
