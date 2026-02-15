
import asyncio
import csv
import os
import sys
from datetime import datetime
import uuid
from typing import List, Dict, Any

# Add azure_functions to path
sys.path.append(os.path.join(os.getcwd(), 'azure_functions'))

# Force UTF-8 for stdout/stderr
if sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def manual_load_env():
    env_path = os.path.join(os.getcwd(), 'azure_functions', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")
    
    # Also check local.settings.json
    settings_path = os.path.join(os.getcwd(), 'azure_functions', 'local.settings.json')
    if os.path.exists(settings_path):
        import json
        with open(settings_path, 'r') as f:
            data = json.load(f)
            values = data.get('Values', {})
            for k, v in values.items():
                if k not in os.environ:
                    os.environ[k] = str(v)

async def seed_news_data():
    print("Starting News Data Seeding...")
    manual_load_env()
    from shared.config import config_manager
    from shared.database_handler import DatabaseHandler
    from shared.models import NewsArticle
    config_manager.reload()
    try:
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
    except Exception as e:
        print(f"Failed to initialize database: {e}")
        return

    news_dir = r'azure_functions\references\news'
    if not os.path.exists(news_dir):
        print(f"Directory not found: {news_dir}")
        return

    csv_files = [f for f in os.listdir(news_dir) if f.endswith('.csv')]
    print(f"Found {len(csv_files)} CSV files in {news_dir}")

    total_saved = 0

    for filename in csv_files:
        print(f"Processing: {filename}")
        file_path = os.path.join(news_dir, filename)
        
        # Infer source from filename if not in CSV
        # Example: (News)BI Rate.csv -> BI Rate
        source_name = filename.replace("(News)", "").replace(".csv", "").strip()
        
        articles = []
        try:
            # Try multiple encodings
            content_loaded = False
            for encoding in ['utf-8-sig', 'latin-1', 'cp1252']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        reader = csv.DictReader(f)
                        rows = list(reader)
                        content_loaded = True
                        print(f"  Successfully read with {encoding}")
                        break
                except UnicodeDecodeError:
                    continue
            
            if not content_loaded:
                print(f"  ❌ Could not read {filename} with any encoding.")
                continue

            for i, row in enumerate(rows):
                    try:
                        # Map common headers
                        title = row.get('title') or row.get('Title') or row.get('headline') or "No Title"
                        content = row.get('content') or row.get('Content') or row.get('text') or row.get('Article') or ""
                        url = row.get('url') or row.get('URL') or row.get('link') or f"manual-seed-{uuid.uuid4()}"
                        
                        date_str = row.get('date') or row.get('Date') or row.get('published_at')
                        published_date = datetime.utcnow()
                        if date_str:
                            try:
                                # Try common formats
                                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"):
                                    try:
                                        published_date = datetime.strptime(date_str, fmt)
                                        break
                                    except ValueError:
                                        continue
                            except Exception:
                                pass
                        
                        source = row.get('source') or row.get('Source') or source_name
                        
                        if not content and not title:
                            continue

                        article = NewsArticle(
                            title=title,
                            content=content,
                            url=url,
                            source=source,
                            published_date=published_date,
                            scraped_date=datetime.utcnow(),
                            language=row.get('language', 'id'),
                            author=row.get('author') or row.get('Author'),
                            category=row.get('category') or row.get('Category')
                        )
                        articles.append(article)
                    except Exception as row_err:
                        print(f"  ⚠️ Skipping row {i+1} in {filename}: {row_err}")

            if articles:
                print(f"Saving {len(articles)} articles from {filename}...")
                saved_count = await db_handler.save_articles(articles)
                print(f"Saved {saved_count} new articles.")
                total_saved += saved_count
            else:
                print(f"No valid articles found in {filename}")

        except Exception as e:
            print(f"Error reading {filename}: {repr(e)}")

    print(f"Finished Seeding. Total new articles saved: {total_saved}")

if __name__ == "__main__":
    asyncio.run(seed_news_data())
