import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

try:
    import undetected_chromedriver as uc
    HAS_UC = True
except ImportError:
    HAS_UC = False
    print("[WARN] undetected-chromedriver not found. Install: pip install undetected-chromedriver")

# ============================== SELENIUM SETUP ==============================
def setup_driver(use_undetected=True, headless=False):
    print(f"[INFO] Setting up Chrome driver (undetected={use_undetected and HAS_UC}, headless={headless})...")
    if use_undetected and HAS_UC:
        options = uc.ChromeOptions()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-notifications')
        prefs = {
            'profile.managed_default_content_settings.images': 2,
            'profile.default_content_setting_values.notifications': 2,
            'profile.managed_default_content_settings.stylesheets': 2,
        }
        options.add_experimental_option('prefs', prefs)
        if headless:
            options.add_argument('--headless=new')
        try:
            driver = uc.Chrome(options=options, version_main=None)
            print("[SUCCESS] Undetected ChromeDriver ready!")
            return driver
        except Exception as e:
            print(f"[WARN] Failed to create undetected driver: {e}")
            use_undetected = False
    if not use_undetected or not HAS_UC:
        chrome_options = Options()
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        prefs = {'profile.managed_default_content_settings.images': 2}
        chrome_options.add_experimental_option('prefs', prefs)
        if headless:
            chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        ]
        chrome_options.add_argument(f'user-agent={random.choice(user_agents)}')
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print("[SUCCESS] Regular ChromeDriver ready!")
        return driver

# ============================== DRIVER HEALTH CHECK ==============================
def is_driver_alive(driver):
    """Check if driver is still responsive."""
    try:
        _ = driver.current_url
        return True
    except:
        return False

# ============================== CONTENT SCRAPER WITH SCROLLING ==============================
def fetch_article_content_selenium(driver, url, max_retries=2, wait_time=60, enable_scrolling=True):
    """Fetch full article content with scrolling and extended wait."""
    for attempt in range(1, max_retries + 1):
        try:
            if not is_driver_alive(driver):
                print(f"   [ERROR] Driver is not responsive")
                return "N/A"
            
            print(f"   Loading page (attempt {attempt}/{max_retries})...")
            driver.get(url)
            
            print(f"Waiting for initial content...")
            
            selectors = [
                "div.article-body-module__content__bnXL1",
                "div[data-testid='article-body']",
                "article div.article-body__content",
            ]
            
            wait = WebDriverWait(driver, 15)
            content_found = False
            
            for selector in selectors:
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    print(f"Initial content found: {selector}")
                    content_found = True
                    break
                except TimeoutException:
                    continue
            if not content_found:
                print(f"Content not found")
                if attempt < max_retries:
                    time.sleep(3)
                    continue
                return "N/A"
            if enable_scrolling:
                print(f"Scrolling page...")
                last_height = driver.execute_script("return document.body.scrollHeight")
                scroll_pause = 2
                for i in range(10):
                    scroll_amount = last_height // 10
                    current_position = i * scroll_amount
                    driver.execute_script(f"window.scrollTo({{top: {current_position}, behavior: 'smooth'}});")
                    time.sleep(scroll_pause)
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height > last_height:
                        last_height = new_height
                        print(f"      ↓ Scroll {i+1}/10 (expanded)")
                    else:
                        print(f"      ↓ Scroll {i+1}/10")
                driver.execute_script("window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});")
                print(f"   ✓ Reached bottom")
            print(f"Waiting {wait_time}s for full load...")
            intervals = 6
            interval_time = wait_time / intervals
            for i in range(intervals):
                time.sleep(interval_time)
                progress = int((i + 1) / intervals * 100)
                print(f"{progress}% ({int((i + 1) * interval_time)}s / {wait_time}s)")
            print(f"Wait complete, extracting...")
            driver.execute_script("window.scrollTo({top: 0, behavior: 'smooth'});")
            time.sleep(1)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            article_body = soup.select_one("div.article-body-module__content__bnXL1")
            if not article_body:
                for selector in ["div[data-testid='article-body']", "article"]:
                    article_body = soup.select_one(selector)
                    if article_body:
                        print(f"   ℹ Using alternative: {selector}")
                        break
            if not article_body:
                print(f"   [WARN] Could not find article container")
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print(f"   [DEBUG] Saved debug_page.html")
                if attempt < max_retries:
                    time.sleep(3)
                    continue
                return "N/A"
            for elem in article_body.find_all(['p', 'div', 'aside', 'section']):
                try:
                    test_id = elem.get('data-testid', '')
                    if any(x in test_id for x in ['promo-box', 'ad', 'banner', 'CnxPlayer']):
                        elem.decompose()
                        continue
                    
                    text = elem.get_text(strip=True)
                    if any(phrase in text for phrase in [
                        'Reuters Beacon', 'Sign up', 'Advertisement',
                        'Reporting By', 'Editing by', 'Our Standards'
                    ]):
                        elem.decompose()
                except Exception:
                    continue
            content_parts = []
            try:
                for elem in article_body.find_all('div', attrs={'data-testid': lambda x: x and x.startswith('paragraph-')}):
                    try:
                        text = elem.get_text(strip=True)
                        if text and len(text) > 10:
                            content_parts.append(text)
                    except Exception:
                        continue
            except Exception as e:
                print(f"   ℹ Strategy 1 failed: {str(e)[:50]}")
            if not content_parts:
                print(f"   ℹ Fallback to <p> tags...")
                try:
                    for p in article_body.find_all('p'):
                        try:
                            text = p.get_text(strip=True)
                            if text and len(text) > 20:
                                content_parts.append(text)
                        except Exception:
                            continue
                except Exception as e:
                    print(f"   ℹ Strategy 2 failed: {str(e)[:50]}")
            if not content_parts:
                print(f"   ℹ Fallback to direct text...")
                try:
                    text = article_body.get_text(separator='\n\n', strip=True)
                    if text and len(text) > 50:
                        content_parts.append(text)
                except Exception as e:
                    print(f"   ℹ Strategy 3 failed: {str(e)[:50]}")
            if not content_parts:
                print(f"   [WARN] No content extracted")
                if attempt < max_retries:
                    time.sleep(3)
                    continue
                return "N/A"
            content = "\n\n".join(content_parts)
            print(f"Content fetched ({len(content)} chars, {len(content_parts)} paragraphs)")
            return content
        except TimeoutException:
            print(f"[ERROR] Timeout")
            if attempt < max_retries:
                time.sleep(5)
            else:
                return "N/A"
        
        except WebDriverException as e:
            error_msg = str(e)
            if "target window already closed" in error_msg:
                print(f"   [ERROR] Browser crashed")
                return "N/A"
            elif attempt < max_retries:
                print(f"   [RETRY] WebDriver error, retrying...")
                time.sleep(5)
            else:
                return "N/A"
        
        except Exception as e:
            print(f"   [ERROR] {str(e)[:100]}")
            if attempt < max_retries:
                time.sleep(5)
            else:
                return "N/A"
    
    return "N/A"

# ============================== SITEMAP PARSER ==============================
def get_sitemap_urls(max_sitemaps=None):
    """Get sitemap URLs from index."""
    index_url = "https://www.reuters.com/arc/outboundfeeds/news-sitemap-index/?outputType=xml"
    print(f"[INFO] Fetching sitemap index...")
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
        
        if max_sitemaps and len(sitemap_urls) > max_sitemaps:
            sitemap_urls = sitemap_urls[:max_sitemaps]
            print(f"[INFO] Limited to {max_sitemaps} most recent")
        
        return sitemap_urls
    except Exception as e:
        print(f"[ERROR] Failed to fetch sitemap: {e}")
        return []

def parse_reuters_sitemap(sitemap_url, keyword=None, date_filter=None, search_keywords=True):
    """Parse single sitemap with filtering."""
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
        
        for url_tag in root.findall('.//sm:url', ns):
            loc = url_tag.find('sm:loc', ns)
            if loc is None or not loc.text:
                continue
            
            link = loc.text.strip()
            if any(path in link for path in ['/fr/', '/it/', '/es/', '/pt/', '/de/']):
                continue
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
            
            # Keyword filter
            if keyword_lower:
                title_match = keyword_lower in title.lower()
                keywords_match = search_keywords and keyword_lower in keywords.lower()
                if not (title_match or keywords_match):
                    continue
            
            # Date filter
            if date_filter:
                date_filter_str = date_filter.strftime('%Y-%m-%d') if isinstance(date_filter, datetime) else str(date_filter)
                if date_only != date_filter_str:
                    continue
            
            articles.append({
                'Judul': title,
                'Tanggal': date_only,
                'Link': link,
                'Keywords': keywords
            })
        
        return articles
    except Exception as e:
        print(f"[ERROR] Failed to parse sitemap: {e}")
        return []

# ============================== SCRAPE ALL ==============================
def scrape_reuters(keyword=None, date_filter=None, max_sitemaps=5, max_articles=20,
                   search_keywords=True, fetch_content=True, restart_interval=3,
                   wait_time=60, enable_scrolling=True):
    """Main scraping function."""
    print(f"\n{'='*80}")
    print(f"Reuters Scraper - Complete Version")
    print(f"{'='*80}\n")
    
    sitemap_urls = get_sitemap_urls(max_sitemaps)
    if not sitemap_urls:
        return []
    
    all_articles = []
    
    # Parse sitemaps
    for i, sitemap_url in enumerate(sitemap_urls, 1):
        print(f"\n[INFO] ({i}/{len(sitemap_urls)}) Processing sitemap...")
        articles = parse_reuters_sitemap(sitemap_url, keyword, date_filter, search_keywords)
        all_articles.extend(articles)
        print(f"   Found {len(articles)} matching articles")
        time.sleep(0.5)
        
        if len(all_articles) >= max_articles:
            all_articles = all_articles[:max_articles]
            break
    
    print(f"\n[INFO] Total articles: {len(all_articles)}")
    
    if not all_articles or not fetch_content:
        return all_articles
    
    # Fetch content
    print(f"\n[INFO] Fetching content (restart every {restart_interval} articles)...\n")
    driver = None
    
    try:
        driver = setup_driver(use_undetected=True, headless=False)
        
        for i, article in enumerate(all_articles, 1):
            print(f"[{i}/{len(all_articles)}] {article['Judul'][:60]}...")
            
            # Restart driver
            if i > 1 and (i - 1) % restart_interval == 0:
                print(f"   [INFO] Restarting driver...")
                try:
                    driver.quit()
                except:
                    pass
                time.sleep(3)
                driver = setup_driver(use_undetected=True, headless=False)
            
            # Fetch content
            try:
                article['Konten'] = fetch_article_content_selenium(
                    driver,
                    article['Link'],
                    max_retries=2,
                    wait_time=wait_time,
                    enable_scrolling=enable_scrolling
                )
            except Exception as e:
                print(f"   [ERROR] {str(e)[:80]}")
                article['Konten'] = "N/A"
            
            # Delay
            if i < len(all_articles):
                time.sleep(random.uniform(4, 7))
    
    finally:
        if driver:
            try:
                driver.quit()
                print(f"\n[INFO] Driver closed")
            except:
                pass
    
    return all_articles

# ============================== SAVE TO EXCEL ==============================
def save_to_excel(data, keyword=None):
    """Save to Excel."""
    if not data:
        return None
    
    df = pd.DataFrame(data)
    
    column_order = ['Judul', 'Tanggal', 'Link', 'Konten']
    df = df[[col for col in column_order if col in df.columns]]
    
    results_folder = r"..\hasil-scrapping"
    os.makedirs(results_folder, exist_ok=True)
    
    if keyword:
        safe_keyword = keyword.replace(' ', '_').replace('/', '_')
        output_filename = f"reuters_{safe_keyword}.xlsx"
    else:
        output_filename = f"reuters_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    full_path = os.path.join(results_folder, output_filename)
    df.to_excel(full_path, index=False)
    
    print(f"\n{'='*80}")
    print(f"SUCCESS!")
    print(f"{'='*80}")
    print(f"Saved: {len(df)} articles")
    print(f"File: {full_path}")
    print(f"Size: {os.path.getsize(full_path) / 1024:.1f} KB")
    print(f"{'='*80}\n")
    
    return df

# ============================== MAIN ==============================
def main_reuters(keyword=None, date_filter=None, max_sitemaps=5, max_articles=10,
                 search_keywords=True, fetch_content=True, restart_interval=3,
                 wait_time=60, enable_scrolling=True):
    data = scrape_reuters(keyword, date_filter, max_sitemaps, max_articles,
                         search_keywords, fetch_content, restart_interval,
                         wait_time, enable_scrolling)
    
    if data:
        df = save_to_excel(data, keyword)
        
        print(f"Preview (first 3):")
        print(f"{'='*80}\n")
        for i, article in enumerate(data[:3], 1):
            print(f"{i}. {article['Judul']}")
            print(f"   Date: {article['Tanggal']}")
            print(f"   Link: {article['Link']}")
            if 'Konten' in article:
                preview = article['Konten'][:100] + "..." if len(article['Konten']) > 100 else article['Konten']
                print(f"   Content: {preview}")
            print()
        
        return df
    else:
        print("[INFO] No articles to save.")
        return None


if __name__ == '__main__':
    main_reuters(keyword="Trump", date_filter="2025-11-18", restart_interval=5,
                 wait_time=60, enable_scrolling=True, max_articles=
                 1)