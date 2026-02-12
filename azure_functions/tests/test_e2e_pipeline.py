
import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta
from typing import List

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Custom print that writes to file in the root directory
def log(msg):
    full_msg = f"{datetime.now()} - {msg}"
    print(full_msg, flush=True)
    try:
        # Use absolute path to the root directory for the log file
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        log_path = os.path.join(root_dir, 'e2e_log_robust.txt')
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(full_msg + "\n")
    except Exception as e:
        print(f"FAILED TO WRITE TO LOG: {e}")

log("DEBUG: Script started")

# Load environment variables manually for local test
def load_env():
    log("DEBUG: Loading environment...")
    # Look for .env in the root directory (2 levels up from azure_functions/tests/)
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")
    
    # Also load from local.settings.json (1 level up in azure_functions/)
    settings_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'local.settings.json'))
    if os.path.exists(settings_path):
        import json
        with open(settings_path, 'r') as f:
            data = json.load(f)
            values = data.get("Values", {})
            for k, v in values.items():
                if k not in os.environ:
                    os.environ[k] = str(v)
    log("DEBUG: Environment loaded.")

load_env()

# AI_TYPE will be pulled from environment variables loaded above
log("DEBUG: Checking critical environment variables...")
log(f"DEBUG: SQL_SERVER_CONNECTION_STRING set: {'Yes' if os.environ.get('SQL_SERVER_CONNECTION_STRING') else 'No'}")
log(f"DEBUG: AI_API_KEY set: {'Yes' if os.environ.get('AI_API_KEY') else 'No'}")
log(f"DEBUG: AI_TYPE: {os.environ.get('AI_TYPE', 'Default (Gemini)')}")
log(f"DEBUG: COPILOT_MODEL_NAME: {os.environ.get('COPILOT_MODEL_NAME', 'N/A')}")

from shared.database_handler import DatabaseHandler
from shared.copilot_integration import CopilotIntegration
from shared.config import config_manager
from shared.models import NewsArticle, SentimentLabel, ArticleFilters, DateRange
# Import TempoNewsScraper for better stability
from scrapers.tempo_scraper import TempoNewsScraper

async def run_e2e_test():
    log("DEBUG: Entering run_e2e_test")
    log("--- Starting End-to-End Pipeline Test ---")
    
    # 1. Initialize Database
    log("\n[Step 1] Initializing Database Handler...")
    db_config = await config_manager.get_database_config()
    db_handler = DatabaseHandler(db_config)
    health = await db_handler.health_check()
    if not health:
        log("FAIL: Database health check failed. Check connection string.")
        return
    log("SUCCESS: Database connected.")

    # 2. Scrape News
    log("\n[Step 2] Scraping News (Tempo)...")
    scraper = TempoNewsScraper()
    # Broaden keywords to ensure real articles are found today
    keywords = ["Pertamina", "Indonesia", "Energi", "Ekonomi", "Bisnis", "Market", "Pemerintah"]
    
    # User requested range: 1 Jan 2024 - 9 Feb 2026
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2026, 2, 9, 23, 59, 59)
    
    log(f"Scraping for keywords: {keywords}")
    log(f"Date range: {start_date.date()} to {end_date.date()}")
    
    articles = []
    try:
        articles = await scraper.scrape_news(keywords, start_date, end_date)
        if articles:
            log(f"SUCCESS: Found {len(articles)} real articles from Tempo matching keywords.")
        else:
            log("WARNING: No articles matched keywords. Attempting broad discovery for pipeline verification...")
            # Fallback: Just grab the latest articles from the first category sitemap to test the pipeline
            all_articles = await scraper._scrape_from_sitemap(scraper.sitemap_urls[0], [], start_date, end_date)
            if all_articles:
                log(f"DEBUG: Found {len(all_articles)} general articles from sitemap. Picking top 2 for pipeline test.")
                # Limit to 2 for the test
                test_articles_data = all_articles[:2]
                for data in test_articles_data:
                    content = await scraper._extract_article_content(data['url'])
                    article = scraper._create_article(
                        title=data['title'],
                        content=content,
                        url=data['url'],
                        published_date=datetime.utcnow(),
                        keywords=["Test-Fallback"]
                    )
                    articles.append(article)
                log(f"SUCCESS: Proceeding with {len(articles)} general articles to test AI and Database.")
    except Exception as e:
        log(f"ERROR: Scraping logic failed: {str(e)}")
    
    if not articles:
        log("\n[!] Scraping found 0 articles. No real data available for subsequent steps.")
        return

    # 3. Save to Database
    log("\n[Step 3] Saving Articles to Database...")
    # Add unique ID if missing
    for art in articles:
        if not art.id:
            art.id = str(uuid.uuid4())
    
    await db_handler.save_articles(articles)
    log(f"SUCCESS: Saved {len(articles)} articles to DB.")

    # 4. Fetch from Database for Analysis
    log("\n[Step 4] Fetching Articles for Analysis...")
    filters = ArticleFilters(
        limit=20 
    )
    db_articles = await db_handler.get_articles(filters)
    
    # Match by URL to find the ones we just saved
    target_urls = {a.url for a in articles}
    found_articles = [a for a in db_articles if a.url in target_urls]
    
    log(f"SUCCESS: Retrieved {len(found_articles)} target articles from DB.")

    if not found_articles:
        log("FAIL: Could not retrieve articles just saved.")
        return

    # 5. Run Sentiment Analysis
    ai_type = os.getenv("AI_TYPE", "OPENAI")
    log(f"\n[Step 5] Running Sentiment Analysis ({ai_type})...")
    copilot_config = await config_manager.get_copilot_config()
    copilot = CopilotIntegration(copilot_config)
    
    try:
        # Process targeted articles
        batch_iterator = copilot.batch_process(found_articles, batch_size=len(found_articles))
        async for analysis in batch_iterator:
            log(f"SUCCESS: Analysis completed for batch. Label: {analysis.sentiment_label}, Score: {analysis.sentiment_score}")
            
            # 6. Save Sentiment Analysis
            log("\n[Step 6] Saving Sentiment Analysis to Database...")
            analysis.id = str(uuid.uuid4())
            await db_handler.save_sentiment_analysis(analysis)
            log(f"SUCCESS: Sentiment Analysis saved. ID: {analysis.id}")
            
            # 7. Verification Query
            log("\n[Step 7] Final Verification Query...")
            # Query without DateRange because articles might be historical (2024), 
            # causing date_range_start to be outside the "now +/- 1 day" window.
            analyses = await db_handler.get_sentiment_analyses(None)
            found = any(a.id == analysis.id for a in analyses)
            
            if found:
                log(f"VERIFIED: Sentiment analysis record FOUND in sentiment_analyses table.")
                
                # Check mapping table
                query = "SELECT COUNT(*) FROM sentiment_analysis_articles WHERE sentiment_analysis_id = ?"
                result = await db_handler.execute_query(query, params=[analysis.id])
                if result and result[0][0] > 0:
                    log(f"VERIFIED: {result[0][0]} articles LINKED in sentiment_analysis_articles table.")
                    log("\n[!!!] ALL TEST STEPS PASSED SUCCESSFULLY [!!!]")
                else:
                    log(f"FAIL: Linked articles NOT found in mapping table.")
            else:
                log(f"FAIL: Sentiment analysis record NOT found in sentiment_analyses table.")
            
            break # Only test one batch
    except Exception as e:
        log(f"FAIL: Sentiment analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if 'copilot' in locals():
            await copilot.close()
            log("DEBUG: Closed AI provider session.")

    log("\n--- End-to-End Pipeline Test Completed ---")

if __name__ == "__main__":
    asyncio.run(run_e2e_test())
