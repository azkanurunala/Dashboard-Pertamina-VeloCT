import os

# List of all scraper function directories
SCRAPER_FUNCS = [
    "bank_indonesia_scraper_function", "biodiesel_esdm_scraper_function",
    "bioetanol_esdm_scraper_function", "bioenergytimes_scraper_function",
    "bisnis_indonesia_scraper_function", "bloomberg_technoz_scraper_function",
    "bps_scraper_function", "cnbc_indonesia_scraper_function",
    "cnbc_scraper_function", "cnn_scraper_function", "cpo_scraper_function",
    "energiesmedia_scraper_function", "google_news_scraper_function",
    "iaea_pris_scraper_function", "kompas_scraper_function",
    "kontan_bbm_scraper_function", "kontan_biodiesel_scraper_function",
    "kontan_scraper_function", "migas_eia_scraper_function",
    "migas_esdm_scraper_function", "oilprice_scraper_function",
    "reuters_scraper_function", "sandp_data_scraper_function",
    "sandp_news_scraper_function", "scmp_scraper_function",
    "sipsn_scraper_function", "tempo_scraper_function",
    "theguardian_scraper_function"
]

def update_scraper(func_name):
    # Path to __init__.py
    init_path = os.path.join("azure_functions", func_name, "__init__.py")
    if not os.path.exists(init_path):
        print(f"Skipping {func_name}: __init__.py not found")
        return False
    
    with open(init_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Check if already updated
    content = "".join(lines)
    if "from shared.database_handler import DatabaseHandler" in content:
        print(f"{func_name} is already updated")
        return True

    # Find where to add imports
    import_idx = -1
    for i, line in enumerate(lines):
        if "from shared.azure_logging import AzureLoggingManager" in line:
            import_idx = i
            break
    
    if import_idx != -1:
        new_imports = [
            "from shared.database_handler import DatabaseHandler\n",
            "from shared.config import config_manager\n",
            "from shared.models import NewsArticle\n"
        ]
        for item in reversed(new_imports):
            lines.insert(import_idx + 1, item)
    
    # Update _scrape_data logic
    # We'll replace the return block and the article loop roughly
    # Actually, it's easier to just rewrite the whole file for each one based on a template
    # but with the specific Scraper class name.
    
    # Extract the scraper class name from the file
    class_name = ""
    for line in lines:
        if "scraper =" in line and "()" in line:
            class_name = line.split("=")[1].split("(")[0].strip()
            break
    
    if not class_name:
        print(f"Could not find scraper class in {func_name}")
        return False

    source_name = func_name.replace("_scraper_function", "").title()
    if "Cnbc" in source_name: source_name = "CNBC"
    if "Cnn" in source_name: source_name = "CNN"
    if "Bps" in source_name: source_name = "BPS"
    
    # Find Scraper Class in imports
    scraper_import_line = ""
    for line in lines:
        if "from scrapers." in line:
            scraper_import_line = line
            break
            
    new_content = f'''"""
Azure Function for {source_name} scraper.
HTTP-triggered function.
"""

import azure.functions as func
import logging
import json
import os
import asyncio
from datetime import datetime
from typing import Dict, Any
import sys

# Add parent directory to Python path for absolute imports in Azure Functions
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

{scraper_import_line}from shared.azure_logging import AzureLoggingManager
from shared.database_handler import DatabaseHandler
from shared.config import config_manager
from shared.models import NewsArticle

SOURCE_NAME = "{source_name}"


def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Function entry point."""
    correlation_id = req.headers.get('x-correlation-id')
    log_manager = AzureLoggingManager(
        function_name="{func_name}",
        correlation_id=correlation_id
    )
    
    try:
        params = _parse_request_parameters(req)
        log_manager.log_function_start(trigger_type="http", parameters={{k: str(v) for k, v in params.items()}})
        
        result = asyncio.run(_scrape_data(params, log_manager))
        
        log_manager.log_function_end(status="success", result_summary={{"count": result.get("results", {{}}).get("articles_found", 0)}})
        
        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            status_code=200,
            mimetype="application/json"
        )
        
    except ValueError as e:
        log_manager.log_function_end(status="failed", result_summary={{"error": str(e)}})
        return func.HttpResponse(
            json.dumps({{
                "status": "error",
                "error": "Invalid parameters",
                "message": str(e),
                "error_type": "ValueError",
                "execution_id": log_manager.execution_id,
                "timestamp": datetime.utcnow().isoformat()
            }}),
            status_code=400,
            mimetype="application/json"
        )
        
    except Exception as e:
        log_manager.log_error(error=e, context_data={{"operation": "scraping"}})
        return func.HttpResponse(
            json.dumps({{
                "status": "error",
                "source": SOURCE_NAME,
                "error": str(e),
                "error_type": type(e).__name__,
                "execution_id": log_manager.execution_id,
                "timestamp": datetime.utcnow().isoformat()
            }}),
            status_code=500,
            mimetype="application/json"
        )


def _parse_request_parameters(req: func.HttpRequest) -> Dict[str, Any]:
    """Parse request parameters from body or query string."""
    try:
        body = req.get_json()
    except:
        body = {{}}
    
    # Get keywords from body or query params
    keywords_param = body.get('keywords') or req.params.get('keywords', '')
    if isinstance(keywords_param, list):
        keywords = keywords_param
    else:
        keywords = [k.strip() for k in keywords_param.split(',') if k.strip()] if keywords_param else []
    
    # Get dates
    start_date_str = body.get('start_date') or req.params.get('start_date')
    end_date_str = body.get('end_date') or req.params.get('end_date')
    save_to_db = str(body.get('save_to_db', req.params.get('save_to_db', 'true'))).lower() == 'true'
    
    # Parse dates
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    else:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    else:
        end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return {{
        'keywords': keywords,
        'start_date': start_date,
        'end_date': end_date,
        'save_to_db': save_to_db
    }}


async def _scrape_data(params: Dict[str, Any], log_manager: AzureLoggingManager) -> Dict[str, Any]:
    """Perform scraping operation."""
    start_time = datetime.utcnow()
    
    scraper = {class_name}()
    
    try:
        # Try different scraping methods based on what the scraper supports
        articles = []
        
        if hasattr(scraper, 'scrape_news'):
            articles = await scraper.scrape_news(
                keywords=params.get('keywords', []),
                start_date=params.get('start_date'),
                end_date=params.get('end_date')
            )
        elif hasattr(scraper, 'scrape'):
            articles = await scraper.scrape(
                keywords=params.get('keywords', []),
                start_date=params.get('start_date'),
                end_date=params.get('end_date')
            )
        elif hasattr(scraper, 'scrape_data'):
            articles = await scraper.scrape_data()
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Convert articles to serializable format and prepare for DB
        articles_data = []
        news_articles = []
        
        for a in (articles if articles else []):
            # Extract data safely
            title = getattr(a, 'title', str(a)) if hasattr(a, 'title') else str(a)
            url = getattr(a, 'url', '') if hasattr(a, 'url') else ''
            content = getattr(a, 'content', '') if hasattr(a, 'content') else ''
            pub_date = getattr(a, 'published_date', None) if hasattr(a, 'published_date') else None
            
            if not pub_date:
                pub_date = datetime.now()
            
            # For JSON response
            article_snippet = {{
                "title": title,
                "url": url,
                "source": getattr(a, 'source', SOURCE_NAME) if hasattr(a, 'source') else SOURCE_NAME,
                "published_date": pub_date.isoformat() if hasattr(pub_date, 'isoformat') else str(pub_date)
            }}
            articles_data.append(article_snippet)
            
            # For Database persistence
            news_articles.append(NewsArticle(
                title=title,
                content=content or "No content available",
                url=url,
                source=SOURCE_NAME,
                published_date=pub_date,
                keywords=params.get('keywords', [])
            ))
        
        # Save to database if requested
        articles_saved = 0
        if params.get('save_to_db') and news_articles:
            try:
                db_config = await config_manager.get_database_config()
                db_handler = DatabaseHandler(db_config)
                await db_handler.save_articles(news_articles)
                articles_saved = len(news_articles)
                log_manager.log_info(f"Successfully saved {{articles_saved}} articles to database")
            except Exception as db_error:
                log_manager.log_error(error=db_error, context_data={{"operation": "database_persistence"}})
        
        return {{
            "status": "success",
            "source": SOURCE_NAME,
            "execution_time_seconds": execution_time,
            "execution_id": log_manager.execution_id,
            "results": {{
                "articles_found": len(articles_data),
                "articles_saved": articles_saved,
                "articles": articles_data[:10]  # Limit to 10 in response
            }},
            "parameters": {{
                "keywords": params.get('keywords', []),
                "start_date": params['start_date'].isoformat() if params.get('start_date') else None,
                "end_date": params['end_date'].isoformat() if params.get('end_date') else None
            }}
        }}
        
    finally:
        if hasattr(scraper, 'close'):
            try:
                await scraper.close()
            except:
                pass
'''
    
    with open(init_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    
    print(f"Updated {func_name} successfully")
    return True

if __name__ == "__main__":
    count = 0
    for func in SCRAPER_FUNCS:
        if update_scraper(func):
            count += 1
    print(f"Finished. Updated {count} functions.")
