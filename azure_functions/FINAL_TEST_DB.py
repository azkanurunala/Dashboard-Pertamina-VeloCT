import asyncio
import pyodbc
import os
import sys
from datetime import datetime
import uuid

# Add parent directory to path
parent_dir = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions'
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from shared.database_handler import DatabaseHandler
from shared.models import NewsArticle, DatabaseConfig
from shared.config import config_manager

async def diagnose_persistence():
    print("🚀 Starting Database Persistence Diagnosis...")
    
    try:
        # 1. Get Config
        db_config = await config_manager.get_database_config()
        print(f"📡 Connection String (partial): {db_config.connection_string[:50]}...")
        
        # 2. Test Connection
        handler = DatabaseHandler(db_config)
        is_healthy = await handler.health_check()
        print(f"🔌 Health Check: {'✅ SUCCESS' if is_healthy else '❌ FAILED'}")
        
        if not is_healthy:
            return

        # 3. Test Source Resolution (BankIndonesia vs Bank Indonesia)
        print("\n--- Testing Source Resolution ---")
        async with handler._get_connection() as conn:
            cursor = conn.cursor()
            
            sources_to_test = ["BankIndonesia", "Bank Indonesia"]
            for sname in sources_to_test:
                try:
                    # Try manual lookup
                    cursor.execute("SELECT id FROM news_sources WHERE name = ?", (sname,))
                    row = cursor.fetchone()
                    if row:
                        print(f"✅ Found source '{sname}' with ID: {row[0]}")
                    else:
                        print(f"❓ Source '{sname}' NOT found in DB. Attempting to create via procedure...")
                        cursor.execute("EXEC sp_GetOrCreateNewsSource @name=?, @base_url=?", (sname, "https://test.com"))
                        res = cursor.fetchone()
                        print(f"✨ Created/Retrieved source '{sname}' with ID: {res[0] if res else 'Unknown'}")
                except Exception as e:
                    print(f"❌ Error testing source '{sname}': {e}")

        # 4. Test Article Save
        print("\n--- Testing Single Article Save ---")
        test_article = NewsArticle(
            title=f"Test Article {datetime.now().isoformat()}",
            content="This is a diagnostic test article.",
            url=f"https://test.com/diag-{uuid.uuid4()}",
            source="BankIndonesia",
            published_date=datetime.now()
        )
        
        try:
            saved_count = await handler.save_articles([test_article])
            print(f"💾 Articles Saved: {saved_count}")
            if saved_count == 0:
                print("⚠ Articles returned 0. Possible duplicate or logic exit.")
        except Exception as e:
            print(f"❌ CRITICAL SAVE ERROR: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"❌ Overall Diagnosis Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(diagnose_persistence())
