import sys
import os
import asyncio
import pyodbc
from datetime import datetime, timedelta
import json
import uuid

# Add current dir to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from shared.models import NewsArticle, SentimentAnalysis, SentimentLabel
from shared.copilot_integration import copilot_integration
from scrapers.google_news_scraper import scrape_google_news

log_file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "backfill_final_attempt.log")

def log(msg):
    print(msg)
    with open(log_file_path, "a") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

def get_connection():
    settings_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\local.settings.json'
    with open(settings_path, 'r') as f:
        data = json.load(f)
        conn_str = data.get('Values', {}).get('SQL_SERVER_CONNECTION_STRING')
    
    conn_str = conn_str.replace("Encrypt=yes", "Encrypt=no").replace("TrustServerCertificate=no", "TrustServerCertificate=yes")
    return pyodbc.connect(conn_str, timeout=10)

async def run_backfill():
    # Set AI type to what the system usually uses (OpenAI/Azure)
    os.environ['AI_TYPE'] = 'OPENAI'
    
    # We will search month by month to ensure we find articles through Google News RSS
    months = []
    current = datetime(2025, 1, 1)
    end_limit = datetime(2026, 3, 14)
    
    while current <= end_limit:
        months.append(current)
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)

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

    category = 'indeks kepercayaan knsmn'
    role_context = "Idx Keyakinan Konsumen"

    for m_start in months:
        m_end = (m_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        if m_end > end_limit:
            m_end = end_limit
            
        month_str = m_start.strftime("%Y-%m")
        log(f"--- Processing Month {month_str} ---")
        
        # Build query for Google News
        # We look for BI press releases about all three indices provided by the user
        indicator_terms = [
            "Indeks Kepercayaan Konsumen", 
            "Indeks Ekspektasi Konsumen", 
            "Indeks Ekonomi Saat Ini",
            "Survei Konsumen"
        ]
        
        # We'll try to find any of these in the specific month
        search_query_base = f'site:bi.go.id after:{m_start.strftime("%Y-%m-%d")} before:{m_end.strftime("%Y-%m-%d")}'
        
        # We'll use a combined query or iterate if needed. 
        # For simplicity and effectiveness, we'll search for the main "Survei Konsumen" or the specific indices.
        query = f'{search_query_base} ("Survei Konsumen" OR "Indeks Kepercayaan Konsumen" OR "Indeks Ekspektasi Konsumen" OR "Indeks Ekonomi Saat Ini")'
        log(f"  Searching Google News: {query}")
        
        try:
            articles = await scrape_google_news(
                keywords=[query],
                start_date=m_start - timedelta(days=5), # Buffer for timezones/delays
                end_date=m_end + timedelta(days=5),
                max_articles=15
            )
            
            if not articles:
                log(f"  No articles found for {month_str}")
                continue
                
            log(f"  Found {len(articles)} articles. Processing...")
            
            monthly_news_objects = []
            for art in articles:
                # Check duplicate
                cursor.execute("SELECT id FROM news_articles WHERE url = ? AND category = ?", (art.url, category))
                existing = cursor.fetchone()
                if existing:
                    log(f"    [Skip] Already in DB: {art.title[:50]}...")
                    # Fetch from DB for sentiment grouping
                    id_val = existing[0]
                    cursor.execute("SELECT title, content, published_date FROM news_articles WHERE id = ?", (id_val,))
                    row = cursor.fetchone()
                    monthly_news_objects.append(NewsArticle(
                        title=row[0], content=row[1], url=art.url, source=source_name,
                        published_date=row[2], category=category, id=id_val
                    ))
                    continue

                if art.content == "N/A" or len(art.content) < 100:
                    log(f"    [Skip] No content for: {art.title[:50]}...")
                    continue

                art_id = str(uuid.uuid4())
                cursor.execute("""
                INSERT INTO news_articles 
                (id, title, content, url, source_id, published_date, scraped_date, language, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (art_id, art.title, art.content, art.url, source_id, art.published_date, datetime.utcnow(), "id", category))
                conn.commit()
                
                art.id = art_id
                art.category = category
                monthly_news_objects.append(art)
                log(f"    Saved: {art.title[:50]}...")

            if monthly_news_objects:
                log(f"  Generating Sentiment Analysis for {len(monthly_news_objects)} articles in {month_str}...")
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
                        datetime.utcnow(), role_context
                    ))
                    conn.commit()
                    log(f"  -> Saved Sentiment Analysis for {month_str}!")
                except Exception as se:
                    log(f"  -> Failed sentiment for {month_str}: {se}")
            
        except Exception as e:
            log(f"  Error processing month {month_str}: {e}")
        
        await asyncio.sleep(2) # Prevent Rate Limiting

    conn.close()
    print("\nBackfill via Google News Finished!")

if __name__ == "__main__":
    asyncio.run(run_backfill())
