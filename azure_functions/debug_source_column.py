
import asyncio
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
import sys
sys.path.append('azure_functions')

from shared.models import NewsArticle, DatabaseConfig
from shared.database_handler import DatabaseHandler

load_dotenv('azure_functions/.env')

async def debug_persistence():
    connection_string = os.getenv('SQL_SERVER_CONNECTION_STRING')
    if not connection_string:
        print("❌ No connection string")
        return

    config = DatabaseConfig(connection_string=connection_string)
    db = DatabaseHandler(config)
    
    article = NewsArticle(
        title="Debug Article",
        content="Testing source column issue.",
        url=f"https://debug.com/{uuid.uuid4()}",
        source="Tempo",
        published_date=datetime.utcnow()
    )
    
    print(f"📦 Attempting to save article with source='{article.source}'...")
    try:
        await db.save_articles([article])
        print("✅ SUCCESS: Article saved without error.")
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        if "source" in str(e).lower():
            print("⚠️ REPRODUCED: Found 'source' in error message.")

if __name__ == "__main__":
    asyncio.run(debug_persistence())
