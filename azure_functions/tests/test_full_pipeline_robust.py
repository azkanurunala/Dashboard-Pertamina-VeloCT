
import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta
from typing import List

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.database_handler import DatabaseHandler
from shared.copilot_integration import CopilotIntegration
from shared.config import config_manager
from shared.models import NewsArticle, SentimentLabel, ArticleFilters, DateRange
from scrapers.tempo_scraper import TempoNewsScraper
from scrapers.google_news_scraper import GoogleNewsScraper
from scrapers.biodiesel_esdm_scraper import BiodieselESDMScraper
from scrapers.bioetanol_esdm_scraper import BioetanolESDMScraper
from scrapers.iaea_pris_scraper import IAEAPRISScraper

# Custom logging
def log(msg):
    full_msg = f"{datetime.now()} - {msg}"
    print(full_msg, flush=True)

# Load environment variables manually for local test
def load_env():
    log("DEBUG: Loading environment...")
    # Look for .env in the azure_functions directory (one level up from tests/)
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")
    
    # Also load from local.settings.json
    settings_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'local.settings.json'))
    if os.path.exists(settings_path):
        import json
        with open(settings_path, 'r') as f:
            try:
                data = json.load(f)
                values = data.get("Values", {})
                for k, v in values.items():
                    if k not in os.environ:
                        os.environ[k] = str(v)
            except:
                pass
    log("DEBUG: Environment loaded.")

load_env()
config_manager.reload()
    
async def test_full_pipeline():
    log("--- Starting Full Pipeline Direct Test (News + Sentiment + Data) ---")
    
    # 1. Initialize DB
    db_config = await config_manager.get_database_config()
    db_handler = DatabaseHandler(db_config)
    health = await db_handler.health_check()
    if not health:
        log("FAIL: DB Health check failed.")
        return
    log("SUCCESS: DB Connected.")

    # 2. Scrape News (Tempo + Google)
    log("\n[Step 2] Scraping News...")
    keywords = ["Pertamina", "Energi"]
    start_date = datetime.utcnow() - timedelta(days=2)
    end_date = datetime.utcnow()
    
    all_articles = []
    
    # Try Tempo
    log("Scraping Tempo...")
    try:
        tempo_scraper = TempoNewsScraper()
        tempo_articles = await tempo_scraper.scrape_news(keywords, start_date, end_date)
        if tempo_articles:
            all_articles.extend(tempo_articles)
            log(f"SUCCESS: Found {len(tempo_articles)} from Tempo.")
    except Exception as e:
        log(f"WARNING: Tempo failed: {e}")

    # Try Google News
    log("Scraping Google News...")
    try:
        google_scraper = GoogleNewsScraper()
        google_articles = await google_scraper.scrape_news(keywords, start_date, end_date, max_articles=5)
        if google_articles:
            all_articles.extend(google_articles)
            log(f"SUCCESS: Found {len(google_articles)} from Google News.")
    except Exception as e:
        log(f"WARNING: Google News failed: {e}")

    if all_articles:
        log(f"SUCCESS: Total {len(all_articles)} news articles found.")
        await db_handler.save_articles(all_articles)
        log(f"SUCCESS: Saved news articles to DB.")
    else:
        log("WARNING: No news articles found from any source.")

    # 3. Sentiment Analysis
    if all_articles:
        log("\n[Step 3] Running Sentiment Analysis...")
        copilot_config = await config_manager.get_copilot_config()
        copilot = CopilotIntegration(copilot_config)
        try:
            # Process the first batch
            async for analysis in copilot.batch_process(all_articles[:2], batch_size=2):
                analysis.id = str(uuid.uuid4())
                await db_handler.save_sentiment_analysis(analysis)
                log(f"SUCCESS: Sentiment Analysis saved for {len(all_articles[:2])} articles. ID: {analysis.id}")
                break
        finally:
            await copilot.close()

    # 4. Scrape Structured Data (Biodiesel, Bioetanol, IAEA)
    log("\n[Step 4] Scraping Structured Data...")
    
    structured_scrapers = [
        ("Biodiesel", BiodieselESDMScraper()),
        ("Bioetanol", BioetanolESDMScraper()),
        ("IAEA Nuclear", IAEAPRISScraper())
    ]
    
    for name, scraper in structured_scrapers:
        log(f"Running {name} scraper...")
        try:
            # Most data scrapers ignore keywords but we pass them for interface consistency
            results = await scraper.scrape_news(keywords, start_date, end_date)
            if results:
                # Results is usually a list of dicts with 'type' and 'data'
                for result in results:
                    table_name = result.get('type')
                    data = result.get('data', [])
                    if table_name and data:
                        log(f"Saving {len(data)} rows to {table_name}...")
                        await db_handler.save_structured_data(table_name, data[:5]) # Save top 5 for test
                        log(f"SUCCESS: Saved data to {table_name}.")
            else:
                log(f"WARNING: No data found for {name}.")
        except Exception as e:
            log(f"ERROR: {name} scraper failed: {e}")

    log("\n--- Full Pipeline Direct Test Completed ---")

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
