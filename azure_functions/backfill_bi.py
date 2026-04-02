import sys
import os
import asyncio
import pyodbc
from datetime import datetime, timedelta
import json
import uuid

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from scrapers.bank_indonesia_scraper import scrape_bank_indonesia_news
from orchestration.orchestrator_function import CATEGORY_KEYWORDS

def classify(title, content):
    text = f"{title} {content}".lower()
    matched = []
    for cat, kws in CATEGORY_KEYWORDS.items():
        for kw in kws:
            if kw.lower() in text:
                matched.append(cat)
                break
    return matched if matched else ['Harga Minyak']

def get_connection():
    settings_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\local.settings.json'
    with open(settings_path, 'r') as f:
        data = json.load(f)
        conn_str = data.get('Values', {}).get('SQL_SERVER_CONNECTION_STRING')
    
    conn_str = conn_str.replace("Encrypt=yes", "Encrypt=no").replace("TrustServerCertificate=no", "TrustServerCertificate=yes")
    return pyodbc.connect(conn_str, timeout=10)

async def backfill():
    keywords = [
        "indeks", "konsumen", "bi rate", "suku bunga", "ritel", "manufaktur",
        "neraca perdagangan", "inflasi", "ihsg", "indonia", "jasa"
    ]
    
    print("Connecting to DB using pyodbc...")
    conn = get_connection()
    cursor = conn.cursor()
    
    print("Starting backfill for the last 30 days...")
    total_saved = 0
    t_now = datetime.now()
    
    for i in range(30):
        target_date = t_now - timedelta(days=i)
        print(f"Scraping {target_date.strftime('%Y-%m-%d')}...")
        
        try:
            articles = await scrape_bank_indonesia_news(
                keywords=keywords,
                start_date=target_date,
                end_date=target_date
            )
            
            if articles:
                saved = 0
                for a in articles:
                    cats = classify(a.title, a.content)
                    cat = cats[0] if cats else 'Harga Minyak'
                    
                    # Get or create source
                    source_name = a.source
                    cursor.execute("SELECT id FROM news_sources WHERE name = ?", (source_name,))
                    result = cursor.fetchone()
                    
                    if result:
                        source_id = result[0]
                    else:
                        cursor.execute("INSERT INTO news_sources (name, base_url) OUTPUT INSERTED.id VALUES (?, ?)", 
                                       (source_name, f"https://www.{source_name.lower().replace(' ', '')}.com"))
                        source_id = cursor.fetchone()[0]
                    
                    # Check duplicate
                    cursor.execute("SELECT 1 FROM news_articles WHERE url = ? AND category = ?", (a.url, cat))
                    if cursor.fetchone():
                        continue
                        
                    insert_query = """
                    INSERT INTO news_articles 
                    (id, title, content, url, source_id, published_date, scraped_date, 
                     language, author, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    
                    cursor.execute(insert_query, (
                        a.id or str(uuid.uuid4()),
                        a.title,
                        a.content,
                        a.url,
                        source_id,
                        a.published_date,
                        a.scraped_date,
                        a.language,
                        a.author,
                        cat
                    ))
                    saved += 1
                
                conn.commit()
                print(f"  -> Found {len(articles)} articles, Saved {saved} new to DB.")
                total_saved += saved
            else:
                print("  -> No articles found.")
                
        except Exception as e:
            conn.rollback()
            print(f"  -> Error: {e}")
            
        await asyncio.sleep(1)
        
    conn.close()
    print(f"\nBackfill Complete. Total new articles saved: {total_saved}")

if __name__ == "__main__":
    asyncio.run(backfill())
