import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# ============================== SELENIUM SETUP ==============================
def setup_driver():
    """Setup Chrome driver with options to avoid detection."""
    chrome_options = Options()
    
    # Stealth options
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Performance options
    chrome_options.add_argument('--headless')  # Run in background
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    
    # Set user agent
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    # Create driver
    driver = webdriver.Chrome(options=chrome_options)
    
    # Execute script to hide webdriver property
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

# ============================== CONTENT SCRAPER WITH SELENIUM ==============================
def fetch_article_content_selenium(driver, url):
    """Fetch full article content from Reuters URL using Selenium."""
    try:
        print(f"   Loading page...")
        driver.get(url)
        
        # Wait for article content to load (max 15 seconds)
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.article-body-module__content__bnXL1")))
        
        # Add small delay to let dynamic content load
        time.sleep(2)
        
        # Get page source and parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Find article content div
        article_body = soup.select_one("div.article-body-module__content__bnXL1")
        
        if not article_body:
            print(f"   [WARN] Could not find article content")
            return "N/A"
        
        # Remove unwanted elements
        for elem in article_body.find_all(['p', 'div']):
            # Check data-testid attributes
            test_id = elem.get('data-testid', '')
            if any(x in test_id for x in ['promo-box', 'ad', 'banner', 'CnxPlayer', 'ResponsiveAdSlot']):
                elem.decompose()
                continue
            
            # Check class names
            class_names = ' '.join(elem.get('class', []))
            if any(x in class_names for x in [
                'promo-box', 'ad-slot', 'cnx-player', 'news-assistant',
                'dianomi', 'sign-off', 'trust-badge', 'tags-'
            ]):
                elem.decompose()
                continue
            
            text = elem.get_text(strip=True)
            
            # Remove promotional content
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
        
        # Extract clean content
        content_parts = []
        for elem in article_body.find_all('div'):
            # Only get divs with data-testid="paragraph-X"
            test_id = elem.get('data-testid', '')
            if test_id.startswith('paragraph-'):
                text = elem.get_text(strip=True)
                if text and len(text) > 10:
                    content_parts.append(text)
        
        if not content_parts:
            print(f"   [WARN] No content found")
            return "N/A"
        
        content = "\n\n".join(content_parts)
        print(f"   ✓ Content fetched ({len(content)} chars)")
        return content
    
    except TimeoutException:
        print(f"   [ERROR] Timeout waiting for page to load")
        return "N/A"
    except WebDriverException as e:
        print(f"   [ERROR] WebDriver error: {e}")
        return "N/A"
    except Exception as e:
        print(f"   [ERROR] Failed to fetch content: {e}")
        return "N/A"

# ============================== SITEMAP INDEX PARSER ==============================
def get_sitemap_urls():
    """Get all sitemap URLs from sitemap index."""
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

# ============================== XML PARSER ==============================
def parse_reuters_sitemap(sitemap_url, keyword=None, date_filter=None):
    """Parse a single Reuters sitemap and filter by keyword and/or date."""
    try:
        r = requests.get(sitemap_url, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        
        # Define namespaces
        ns = {
            'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9',
            'news': 'http://www.google.com/schemas/sitemap-news/0.9'
        }
        
        articles = []
        keyword_lower = keyword.lower() if keyword else None
        
        url_tags = root.findall('.//sm:url', ns)
        
        for url_tag in url_tags:
            # Extract location (article URL)
            loc = url_tag.find('sm:loc', ns)
            if loc is None or not loc.text:
                continue
            
            link = loc.text.strip()
            
            # Skip languages that are disallowed in robots.txt
            # fr (French), it (Italian), es (Spanish), pt (Portuguese), de (German)
            disallowed_paths = ['/fr/', '/it/', '/es/', '/pt/', '/de/']
            if any(path in link for path in disallowed_paths):
                continue
            
            # Extract news information
            news_tag = url_tag.find('news:news', ns)
            if news_tag is None:
                continue
            
            title_tag = news_tag.find('news:title', ns)
            date_tag = news_tag.find('news:publication_date', ns)
            keywords_tag = news_tag.find('news:keywords', ns)
            
            title = title_tag.text.strip() if title_tag is not None and title_tag.text else "(No Title)"
            pubdate_raw = date_tag.text.strip() if date_tag is not None and date_tag.text else ""
            keywords = keywords_tag.text.strip() if keywords_tag is not None and keywords_tag.text else ""
            
            # Extract date only (YYYY-MM-DD)
            date_only = pubdate_raw.split('T')[0] if 'T' in pubdate_raw else pubdate_raw
            
            # Apply keyword filter if specified (only check title for Reuters)
            if keyword_lower:
                title_match = keyword_lower in title.lower()
                
                if not title_match:
                    continue
            
            # Apply date filter if specified
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

# ============================== SCRAPE ALL SITEMAPS ==============================
def scrape_reuters(keyword=None, date_filter=None, max_sitemaps=5, max_articles=20):
    """Scrape articles from Reuters with optional keyword and date filter."""
    sitemap_urls = get_sitemap_urls()
    
    if not sitemap_urls:
        print("[INFO] No sitemaps found.")
        return []
    
    # Limit number of sitemaps if specified
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
        
        # Stop early if we have enough articles
        if len(all_articles) >= max_articles:
            print(f"[INFO] Found {len(all_articles)} articles, stopping early")
            all_articles = all_articles[:max_articles]
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
    
    # Setup Selenium driver
    print(f"\n[INFO] Setting up Chrome driver...")
    try:
        driver = setup_driver()
        print(f"[INFO] Chrome driver ready!")
    except Exception as e:
        print(f"[ERROR] Failed to setup Chrome driver: {e}")
        print("[INFO] Make sure you have Chrome and chromedriver installed!")
        return all_articles  # Return without content
    
    # Fetch content for each article using Selenium
    print(f"\n[INFO] Fetching article content with Selenium...")
    try:
        for i, article in enumerate(all_articles, 1):
            print(f"[INFO] ({i}/{len(all_articles)}) Fetching: {article['Link']}")
            article['Konten'] = fetch_article_content_selenium(driver, article['Link'])
            time.sleep(3)  # Delay between articles
    finally:
        # Always close driver
        driver.quit()
        print(f"[INFO] Chrome driver closed")
    
    return all_articles

# ============================== SAVE TO EXCEL ==============================
def save_to_excel(data, keyword=None, output_filename=None):
    """Save scraped data to Excel file."""
    if not data:
        print("[WARN] No data to save.")
        return None
    
    df = pd.DataFrame(data)
    
    # Reorder columns
    column_order = ['Judul', 'Tanggal', 'Link', 'Konten']
    df = df[[col for col in column_order if col in df.columns]]
    
    # Create results folder
    results_folder = r"..\hasil-scrapping"
    os.makedirs(results_folder, exist_ok=True)
    
    # Generate filename
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
    
    # Save to Excel
    df.to_excel(full_path, index=False)
    print(f"\n[SUCCESS] Berhasil menyimpan {len(df)} artikel ke '{full_path}'")
    
    return df

# ============================== MAIN EXECUTION ==============================
def main_reuters(keyword=None, date_filter=None, max_sitemaps=5, max_articles=10):
    """
    Main function to scrape Reuters news using Selenium.
    
    Args:
        keyword: Keyword to search in title (case-insensitive)
        date_filter: Date string in format 'YYYY-MM-DD' or datetime object
        max_sitemaps: Maximum number of sitemaps to process (default: 5)
        max_articles: Maximum number of articles to scrape (default: 10)
    
    Examples:
        # Scrape 10 articles with keyword "Trump"
        main_reuters(keyword="Trump", max_articles=10)
        
        # Scrape articles from specific date
        main_reuters(keyword="election", date_filter="2025-11-17", max_articles=5)
    
    Requirements:
        pip install selenium
        Download ChromeDriver: https://chromedriver.chromium.org/
    """
    print(f"\n{'='*60}")
    print(f"Reuters News Scraper (Selenium)")
    print(f"{'='*60}\n")
    
    data = scrape_reuters(keyword, date_filter, max_sitemaps, max_articles)
    
    if data:
        df = save_to_excel(data, keyword)
        
        # Display preview
        print(f"\n{'='*60}")
        print(f"Preview (first 3 articles):")
        print(f"{'='*60}\n")
        for i, article in enumerate(data[:3], 1):
            print(f"{i}. {article['Judul']}")
            print(f"   Tanggal: {article['Tanggal']}")
            print(f"   Link: {article['Link']}")
            konten = article.get('Konten', 'N/A')
            preview = konten[:100] + "..." if len(konten) > 100 else konten
            print(f"   Konten: {preview}")
            print()
        
        return df
    else:
        print("[INFO] No articles to save.")
        return None


if __name__ == '__main__':
    # Example usage:
    # Scrape 5 articles with keyword "Trump"
    main_reuters(keyword="Trump", max_articles=1)