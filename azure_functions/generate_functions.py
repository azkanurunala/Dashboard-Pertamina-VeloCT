"""Generate Azure Function HTTP trigger directories for ALL scrapers with CORRECT class names."""

import os

FUNCTION_JSON = """{
  "scriptFile": "__init__.py",
  "bindings": [
    {
      "authLevel": "function",
      "type": "httpTrigger",
      "direction": "in",
      "name": "req",
      "methods": ["get", "post"]
    },
    {
      "type": "http",
      "direction": "out",
      "name": "$return"
    }
  ]
}
"""

def generate_init_py(scraper_file, class_name, source_name, has_keywords=True):
    """Generate __init__.py for a scraper function."""
    
    return f'''"""
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

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from scrapers.{scraper_file} import {class_name}
from shared.azure_logging import AzureLoggingManager
from shared.database_handler import DatabaseHandler
from shared.config import config_manager
from shared.models import NewsArticle

SOURCE_NAME = "{source_name}"


def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Function entry point."""
    correlation_id = req.headers.get('x-correlation-id')
    log_manager = AzureLoggingManager(
        function_name="{scraper_file}_function",
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


# ALL scrapers with CORRECT class names (from grep search)
SCRAPERS = [
    # (scraper_file_name without .py, class_name, source_display_name)
    ("bank_indonesia_scraper", "BankIndonesiaScraper", "BankIndonesia"),
    ("biodiesel_esdm_scraper", "BiodieselESDMScraper", "BiodieselESDM"),
    ("bioetanol_esdm_scraper", "BioetanolESDMScraper", "BioetanolESDM"),
    ("bioenergytimes_scraper", "BioenergyTimesScraper", "BioenergyTimes"),
    ("bisnis_indonesia_scraper", "BisnisIndonesiaNewsScraper", "BisnisIndonesia"),
    ("bloomberg_technoz_scraper", "BloombergTechnozScraper", "BloombergTechnoz"),
    ("bps_scraper", "BPSScraper", "BPS"),
    ("cnbc_indonesia_scraper", "CNBCIndonesiaNewsScraper", "CNBCIndonesia"),
    ("cnbc_scraper", "CNBCNewsScraper", "CNBC"),
    ("cnn_scraper", "CNNNewsScraper", "CNN"),
    ("cpo_scraper", "CPOPriceScraper", "CPOPrice"),
    ("energiesmedia_scraper", "EnergiesMediaScraper", "EnergiesMedia"),
    ("google_news_scraper", "GoogleNewsScraper", "GoogleNews"),
    ("iaea_pris_scraper", "IAEAPRISScraper", "IAEA_PRIS"),
    ("kompas_scraper", "KompasNewsScraper", "Kompas"),
    ("kontan_bbm_scraper", "KontanBBMScraper", "KontanBBM"),
    ("kontan_biodiesel_scraper", "KontanBiodieselScraper", "KontanBiodiesel"),
    ("kontan_scraper", "KontanNewsScraper", "Kontan"),
    ("migas_eia_scraper", "MigasEIAScraper", "MigasEIA"),
    ("migas_esdm_scraper", "MigasESDMScraper", "MigasESDM"),
    ("oilprice_scraper", "OilPriceNewsScraper", "OilPrice"),
    ("reuters_scraper", "ReutersNewsScraper", "Reuters"),
    ("sandp_data_scraper", "SAndPDataScraper", "SAndPData"),
    ("sandp_news_scraper", "SAndPNewsScraper", "SAndPNews"),
    ("scmp_scraper", "SCMPScraper", "SCMP"),
    ("sipsn_scraper", "SIPSNDataScraper", "SIPSN"),
    ("tempo_scraper", "TempoNewsScraper", "Tempo"),
    ("theguardian_scraper", "TheGuardianNewsScraper", "TheGuardian"),
]

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    created = 0
    for scraper_file, class_name, source_name in SCRAPERS:
        func_dir = os.path.join(base_dir, f"{scraper_file}_function")
        os.makedirs(func_dir, exist_ok=True)
        
        # Write function.json
        with open(os.path.join(func_dir, "function.json"), "w") as f:
            f.write(FUNCTION_JSON)
        
        # Write __init__.py
        with open(os.path.join(func_dir, "__init__.py"), "w") as f:
            f.write(generate_init_py(scraper_file, class_name, source_name))
        
        print(f"Created/Updated {scraper_file}_function/")
        created += 1
    
    print(f"\nGenerated/Updated {created} function directories!")
    print("Now run: func azure functionapp publish pei-dashboard --python")


if __name__ == "__main__":
    main()
