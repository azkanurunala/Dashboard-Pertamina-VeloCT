import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib.parse import quote

def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
        }
    )
    return driver

def get_oldest_article_date(page_source):
    soup = BeautifulSoup(page_source, "html.parser")
    dates = []
    for time_tag in soup.find_all("time"):
        dt = time_tag.get("datetime")
        if not dt:
            continue
        try:
            date_obj = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            date_obj = date_obj.replace(tzinfo=None)
            dates.append(date_obj)
        except:
            pass
    return min(dates) if dates else None

def extract_articles(page_source):
    soup = BeautifulSoup(page_source, "html.parser")
    articles = []
    article_containers = soup.find_all("div", {"data-qa": "ContentItemSearch-Container"})
    print(f"Found {len(article_containers)} article containers")
    for idx, container in enumerate(article_containers, 1):
        try:
            link_tag = container.find("a", {"data-qa": "BaseLink-renderAnchor-StyledAnchor"})
            if not link_tag or not link_tag.get("href"):
                continue
            url = f"https://www.scmp.com{link_tag['href']}"
            
            title_tag = container.find("span", {"data-qa": "ContentHeadline-Headline"})
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            summary_tag = container.find("h3", {"data-qa": "ContentSummary-ContainerWithTag"})
            summary = summary_tag.get_text(strip=True) if summary_tag else ""
            time_tag = container.find("time")
            if not time_tag or not time_tag.get("datetime"):
                continue
            date_str = time_tag['datetime']
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                date_formatted = dt.strftime("%Y-%m-%d")
            except:
                date_formatted = date_str 
            print(f" [{idx}] {title[:50]}...")
            print(f"      Date: {date_formatted}")
            if summary:
                print(f"      Summary: {summary[:60]}...")
            articles.append({
                "title": title,
                "date": date_formatted,
                "url": url,
                "content": summary
            })
        except Exception as e:
            print(f" [{idx}] Error: {e}")
            continue 
    return articles

def scroll_until_date(driver, target_date, delay=10, max_scroll=50):
    print(f"Target stop date: {target_date.date()}")
    last_height = driver.execute_script("return document.body.scrollHeight")
    for i in range(max_scroll):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(delay)
        oldest_date = get_oldest_article_date(driver.page_source)
        if oldest_date:
            print(f"[Scroll {i+1}/{max_scroll}] Oldest article: {oldest_date.date()}")
            if oldest_date <= target_date:
                print("Target date reached → STOP")
                break
        else:
            print(f"[Scroll {i+1}/{max_scroll}] No date found yet")
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print("Tidak ada konten baru, stop scrolling")
            break
        last_height = new_height
    print(f"Scrolling finished after {i+1} scrolls")

def scrape_scmp(keyword: str, tanggal: str = None):
    if tanggal is None:
        target_date = pd.Timestamp.now().normalize()
        tanggal_str = target_date.strftime("%Y-%m-%d")
    else:
        tanggal_str = tanggal
        target_date = pd.Timestamp(tanggal)
    if target_date.tz is not None:
        target_date = target_date.tz_localize(None)
    
    encoded = quote(keyword)
    search_url = f"https://www.scmp.com/search/{encoded}?q={encoded}"
    
    print("=" * 60)
    print("SCRAPING SCMP")
    print(f"Keyword: {keyword}")
    print(f"Tanggal: {tanggal_str}")
    print(f"Target date (tz-naive): {target_date}")
    print(f"URL: {search_url}")
    print("=" * 60)
    print("\nStarting Chrome driver...")
    driver = setup_driver()
    try:
        print("Loading search page...")
        driver.get(search_url)
        time.sleep(10)
        print("\nStarting scroll...\n")
        scroll_until_date(
            driver=driver,
            target_date=target_date,
            delay=10,
            max_scroll=50
        )
        print("\nExtracting articles...\n")
        articles = extract_articles(driver.page_source)
        print(f"\nTotal articles extracted: {len(articles)}")
        if not articles:
            print("Tidak ada artikel ditemukan")
            return None
        df = pd.DataFrame(articles)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        if df['date'].dt.tz is not None:
            df['date'] = df['date'].dt.tz_localize(None)
        if len(df) > 0:
            print(f"  df['date'] timezone: {df['date'].dt.tz}")
            print(f"  First date value: {df['date'].iloc[0]}")
        df = df[df['date'].dt.date == target_date.date()]
        df = df.sort_values('date', ascending=False).reset_index(drop=True)
        df['date'] = df['date'].dt.date
        print(f"\nArtikel setelah filter: {len(df)}")
        print("\nDataFrame shape:", df.shape)
        print("\nPreview:")
        print(df[['title', 'date', 'content']].head())
        return df  
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return None 
    finally:
        print("\nClosing driver...")
        driver.quit()

def main_scmp(keyword: str, tanggal: str = None):
    df = scrape_scmp(keyword, tanggal)
    if df is not None and len(df) > 0:
        print("\n" + "=" * 60)
        print(f"HASIL SCRAPING")
        print("=" * 60)
        print(f"Total artikel: {len(df)}")
        print("\nSample data:")
        print(df.head(10).to_string())
        return df
    else:
        print("\nTidak ada data untuk dikembalikan")
        return None

if __name__ == "__main__":
    df = main_scmp(
        keyword="geopolitical risks",
        tanggal="2026-01-06" 
    )
    if df is not None and len(df) > 0:
        output_file = f"scmp_scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(output_file, index=False, engine='openpyxl')
        print(f"\nData berhasil disimpan ke: {output_file}")
        print(f"Total artikel: {len(df)}")
        print("\nPreview data:")
        print(df[['title', 'date']].to_string())
    else:
        print("\nTidak ada data untuk disimpan")