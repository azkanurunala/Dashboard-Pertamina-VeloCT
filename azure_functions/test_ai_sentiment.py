import asyncio
import os
import json
from datetime import datetime
import sys

# Add azure_functions directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.copilot_integration import CopilotIntegration
from shared.models import NewsArticle, SentimentAnalysis
from shared.config import config_manager
from shared.database_handler import DatabaseHandler

async def test_sentiment():
    print("=" * 70)
    print("Testing AI Sentiment Analysis")
    print("=" * 70)
    
    try:
        # Load environment from .env and local.settings.json
        print("Loading environment configuration...")
        env_vars = {}
        
        # 1. Load from .env in parent
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        os.environ[key] = value
                        env_vars[key] = value
        
        # 2. Load from local.settings.json
        settings_path = os.path.join(os.path.dirname(__file__), "local.settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, "r") as f:
                settings = json.load(f)
                values = settings.get("Values", {})
                for k, v in values.items():
                    os.environ[k] = str(v)
                    env_vars[k] = str(v)
        
        # Use AI_TYPE from environment/config
        if not os.environ.get("AI_TYPE"):
            os.environ["AI_TYPE"] = "OPENAI"
        
        # IMPORTANT: Reload config manager to pick up new env vars
        from shared.config import config_manager
        config_manager.reload()
        
        print(f"Environment loaded. AI_TYPE: {os.environ.get('AI_TYPE')}")
        print(f"GEMINI_API_KEY found: {'Yes' if os.environ.get('GEMINI_API_KEY') else 'No'}")
        print(f"COPILOT_API_KEY found: {'Yes' if os.environ.get('COPILOT_API_KEY') else 'No'}")

        # 1. Initialize Integration
        print("\nInitializing CopilotIntegration...")
        copilot = CopilotIntegration()
        
        # 3. Create dummy articles for test
        print("Creating dummy articles for testing...")
        articles = [
            NewsArticle(
                title="Oil Prices Surge Amid Geopolitical Tensions",
                content="Global oil prices have surged today as tensions rise in the Middle East. Analysts suggest further increases if supply is disrupted.",
                url="https://example.com/oil-surge",
                source="Reuters",
                published_date=datetime.utcnow()
            ),
            NewsArticle(
                title="Renewable Energy Investment Hits Record High",
                content="Investment in solar and wind power reached new heights last year, signaling a shift away from fossil fuels.",
                url="https://example.com/solar-high",
                source="Bloomberg",
                published_date=datetime.utcnow()
            )
        ]
        
        # 4. Perform Analysis
        print("Calling analyze_sentiment...")
        analysis = await copilot.analyze_sentiment(articles)
        
        print("\nAnalysis Result:")
        print(f"  Score: {analysis.sentiment_score}")
        print(f"  Label: {analysis.sentiment_label}")
        print(f"  Confidence: {analysis.confidence}")
        print(f"  Summary: {analysis.summary}")
        
        # 5. Check if it can save to DB
        print("\nChecking database saving...")
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
        
        # Since these are dummy articles, we need to save them first or skip relationship save
        # For test, we'll just check if the method executes without error
        # Note: save_sentiment_analysis tries to calculate date range from DB, so this might fail if IDs don't exist
        print("Skipping DB save for dummy articles (IDs not in DB).")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'copilot' in locals():
            await copilot.close()
            print("\nClosed AI provider session.")

if __name__ == "__main__":
    asyncio.run(test_sentiment())
