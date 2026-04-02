import sys
import os
import asyncio
import pyodbc
from datetime import datetime, timedelta
import json
import uuid
import re
import time

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from shared.models import NewsArticle
from shared.copilot_integration import copilot_integration
from shared.selenium_helper import get_selenium_helper

# Indonesian month names for date parsing
BULAN_INDONESIA = {
    'januari': '01', 'februari': '02', 'maret': '03', 'april': '04',
    'mei': '05', 'juni': '06', 'juli': '07', 'agustus': '08',
    'september': '09', 'oktober': '10', 'november': '11', 'desember': '12'
}

def parse_indonesian_date(date_str):
    if not date_str or date_str == 'N/A':
        return None
    match = re.search(r'(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})', date_str)
    if match:
        day = match.group(1).zfill(2)
        month = BULAN_INDONESIA.get(match.group(2).lower(), '01')
        year = match.group(3)
        return datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d")
    return None

def get_connection():
    settings_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\local.settings.json'
    with open(settings_path, 'r') as f:
        data = json.load(f)
        conn_str = data.get('Values', {}).get('SQL_SERVER_CONNECTION_STRING')
    
    conn_str = conn_str.replace("Encrypt=yes", "Encrypt=no").replace("TrustServerCertificate=no", "TrustServerCertificate=yes")
    return pyodbc.connect(conn_str, timeout=10)

async def fetch_article_content(url):
    helper = get_selenium_helper()
    try:
        html = await helper.fetch_page(url)
        soup = BeautifulSoup(html, 'html.parser')
        content_div = soup.select_one("#ctl00_PlaceHolderMain_ctl05__ControlWrapper_RichHtmlField")
        if not content_div:
            return "N/A"
        
        paragraphs = content_div.find_all('p')
        content_text = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) >= 30:
                if "Jakarta," in text and "Departemen Komunikasi" in text:
                    continue
                if text.startswith("No. ") and "DKom" in text:
                    continue
                content_text.append(text)
                
        if content_text:
            return "\n\n".join(content_text).strip()
        return "N/A"
    except Exception as e:
        print(f"Error extracting content from {url}: {e}")
        return "N/A"

async def fetch_historical_links(target_date):
    print(f"Loading Bank Indonesia press releases until {target_date.strftime('%Y-%m-%d')}")
    url = "https://www.bi.go.id/id/publikasi/ruang-media/news-release/Default.aspx"
    helper = get_selenium_helper()
    driver = helper._create_driver()  # We manually manage it for pagination
    
    driver.get(url)
    time.sleep(3)
    
    articles = []
    
    while True:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        items = soup.select(".media.media--pers")
        oldest_date = datetime.now()
        
        for item in reversed(items):
            subtitle_elem = item.select_one(".media__subtitle")
            if subtitle_elem:
                subtitle_text = subtitle_elem.get_text(strip=True)
                parts = subtitle_text.split("•")
                date_str = parts[0].strip() if parts else None
                art_date = parse_indonesian_date(date_str)
                if art_date:
                    oldest_date = art_date
                    break
        
        print(f"Currently loaded until: {oldest_date.strftime('%Y-%m-%d')} (found {len(items)} on page)")
        if oldest_date < target_date:
            break
            
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Try to click next
            next_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input.next[type='image'], a.next, button.next, .pagination-next"))
            )
            driver.execute_script("arguments[0].click();", next_btn)
            time.sleep(3)
        except Exception as e:
            print(f"Could not click next logically, stopping pagination: {e}")
            break
            
    # Now parse all
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    items = soup.select(".media.media--pers")
    
    for item in items:
        title_elem = item.select_one(".media__title")
        subtitle_elem = item.select_one(".media__subtitle")
        if not title_elem or not subtitle_elem:
            continue
            
        title = title_elem.get_text(strip=True)
        link = title_elem.get('href', '')
        if link and not link.startswith('http'):
            link = "https://www.bi.go.id" + link
            
        date_str = subtitle_elem.get_text(strip=True).split("•")[0].strip()
        art_date = parse_indonesian_date(date_str)
        
        if art_date and art_date >= target_date:
            articles.append({
                'title': title,
                'url': link,
                'date': art_date
            })
            
    driver.quit()
    print(f"Total articles extracted matching timeframe: {len(articles)}")
    return articles

async def run_backfill():
    os.environ['AI_TYPE'] = 'OPENAI'
    target_start = datetime(2025, 1, 1)
    target_end = datetime(2026, 3, 14)
    keywords = ["indeks", "konsumen", "bi rate", "suku bunga", "ritel", "manufaktur", "neraca perdagangan", "inflasi", "ihsg", "indonia", "jasa", "ikk", "ike", "iek"]
    
    try:
        articles_metadata = await fetch_historical_links(target_start)
    except Exception as e:
        print(f"Failed to fetch metadata: {e}")
        return

    # Filter with keywords initially to save content fetching
    matched_metadata = []
    for am in articles_metadata:
        title_lower = am['title'].lower()
        if any(kw.lower() in title_lower for kw in keywords):
            matched_metadata.append(am)
            
    print(f"Articles matching keywords in title: {len(matched_metadata)}")

    # Group by month
    articles_by_month = {}
    for m in matched_metadata:
        month_key = m['date'].strftime('%Y-%m')
        if month_key not in articles_by_month:
            articles_by_month[month_key] = []
        articles_by_month[month_key].append(m)

    conn = get_connection()
    cursor = conn.cursor()

    source_name = "Bank Indonesia"
    cursor.execute("SELECT id FROM news_sources WHERE name = ?", (source_name,))
    result = cursor.fetchone()
    if result:
        source_id = result[0]
    else:
        cursor.execute("INSERT INTO news_sources (name, base_url) OUTPUT INSERTED.id VALUES (?, ?)", 
                       (source_name, "https://www.bi.go.id"))
        source_id = cursor.fetchone()[0]
        conn.commit()

    for month_key in sorted(articles_by_month.keys()):
        print(f"--- Processing Month {month_key} ---")
        monthly_meta = articles_by_month[month_key]
        monthly_news_objects = []
        
        for am in monthly_meta:
            # Check if exists in db
            cursor.execute("SELECT id FROM news_articles WHERE url = ? AND category = 'indeks kepercayaan knsmn'", (am['url'],))
            row = cursor.fetchone()
            if row:
                print(f"  [Skip] Already in DB: {am['title']}")
                cursor.execute("SELECT title, content, published_date FROM news_articles WHERE id = ?", (row[0],))
                db_art = cursor.fetchone()
                monthly_news_objects.append(NewsArticle(
                    title=db_art[0], content=db_art[1], url=am['url'], source=source_name, 
                    published_date=db_art[2], category='indeks kepercayaan knsmn', id=row[0]
                ))
                continue
            
            print(f"  Fetching content: {am['title']}")
            content = await fetch_article_content(am['url'])
            if content == "N/A":
                continue
                
            art_id = str(uuid.uuid4())
            cat = 'indeks kepercayaan knsmn'
            
            cursor.execute("""
            INSERT INTO news_articles 
            (id, title, content, url, source_id, published_date, scraped_date, language, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (art_id, am['title'], content, am['url'], source_id, am['date'], datetime.utcnow(), "id", cat))
            conn.commit()
            
            monthly_news_objects.append(NewsArticle(
                title=am['title'], content=content, url=am['url'], source=source_name,
                published_date=am['date'], category=cat, id=art_id
            ))
            
        # Run Sentiment Analysis for this month
        if monthly_news_objects:
            print(f"  Generating Sentiment Analysis for {len(monthly_news_objects)} articles in {month_key}...")
            dt = datetime.strptime(month_key, '%Y-%m')
            m_start = dt
            if m_start.month == 12:
                m_end = datetime(m_start.year + 1, 1, 1) - timedelta(seconds=1)
            else:
                m_end = datetime(m_start.year, m_start.month + 1, 1) - timedelta(seconds=1)
                
            try:
                analysis = await copilot_integration.analyze_sentiment(monthly_news_objects)
                analysis_id = str(uuid.uuid4())
                
                cursor.execute("""
                INSERT INTO sentiment_analyses 
                (id, date_range_start, date_range_end, sentiment_score, sentiment_label, 
                 confidence, summary, summary_data, model_version, analysis_date, role_context)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    analysis_id, m_start, m_end, analysis.sentiment_score, analysis.sentiment_label.value,
                    analysis.confidence, analysis.summary, json.dumps({}), analysis.model_version,
                    datetime.utcnow(), "Idx Keyakinan Konsumen"
                ))
                conn.commit()
                print("  -> Saved Sentiment Analysis!")
            except Exception as e:
                print(f"  -> Failed to generate sentiment: {e}")

    conn.close()
    
    # ensure selenium helper cleans up properly
    helper = get_selenium_helper()
    helper.close()
    
    print("Backfill Sentiment Complete!")

if __name__ == "__main__":
    asyncio.run(run_backfill())
