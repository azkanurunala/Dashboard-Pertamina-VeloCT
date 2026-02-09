import os

FUNCTION_JSON = """{
  "scriptFile": "__init__.py",
  "bindings": [
    {
      "authLevel": "function",
      "type": "httpTrigger",
      "direction": "in",
      "name": "req",
      "methods": [
        "get",
        "post"
      ]
    },
    {
      "type": "http",
      "direction": "out",
      "name": "$return"
    }
  ]
}"""

SCRAPERS = [
    # (scraper_file_name without .py, class_name, source_display_name)
    ("bank_indonesia_scraper", "BankIndonesiaScraper", "Bank Indonesia"),
    ("biodiesel_esdm_scraper", "BiodieselESDMScraper", "ESDM Biodiesel"),
    ("bioenergytimes_scraper", "BioenergyTimesScraper", "Bioenergy Times"),
    ("bioetanol_esdm_scraper", "BioetanolESDMScraper", "ESDM Bioetanol"),
    ("bisnis_indonesia_scraper", "BisnisIndonesiaNewsScraper", "Bisnis Indonesia"),
    ("bloomberg_technoz_scraper", "BloombergTechnozScraper", "Bloomberg Technoz"),
    ("bps_scraper", "BPSScraper", "BPS"),
    ("cnbc_indonesia_scraper", "CNBCIndonesiaNewsScraper", "CNBC Indonesia"),
    ("cnbc_scraper", "CNBCNewsScraper", "CNBC"),
    ("cnn_scraper", "CNNNewsScraper", "CNN"),
    ("cpo_scraper", "CPOPriceScraper", "CPO Price"),
    ("energiesmedia_scraper", "EnergiesMediaScraper", "Energies Media"),
    ("google_news_scraper", "GoogleNewsScraper", "Google News"),
    ("iaea_pris_scraper", "IAEAPRISScraper", "IAEA PRIS"),
    ("kompas_scraper", "KompasNewsScraper", "Kompas"),
    ("kontan_bbm_scraper", "KontanBBMScraper", "Kontan BBM"),
    ("kontan_biodiesel_scraper", "KontanBiodieselScraper", "Kontan Biodiesel"),
    ("kontan_scraper", "KontanNewsScraper", "Kontan"),
    ("migas_eia_scraper", "MigasEIAScraper", "Migas EIA"),
    ("migas_esdm_scraper", "MigasESDMScraper", "Migas ESDM"),
    ("oilprice_scraper", "OilPriceNewsScraper", "Oil Price"),
    ("reuters_scraper", "ReutersNewsScraper", "Reuters"),
    ("sandp_data_scraper", "SAndPDataScraper", "S&P Data"),
    ("sandp_news_scraper", "SAndPNewsScraper", "S&P News"),
    ("scmp_scraper", "SCMPScraper", "SCMP"),
    ("sipsn_scraper", "SIPSNDataScraper", "SIPSN"),
    ("tempo_scraper", "TempoNewsScraper", "Tempo"),
    ("theguardian_scraper", "TheGuardianNewsScraper", "The Guardian")
]

def generate_init_py(scraper_file, class_name, source_name):
    """Generate __init__.py for a scraper function."""
    
    # Handle specific constructor requirements
    if class_name == "BPSScraper":
        scraper_init = f"{class_name}(api_key=os.getenv('BPS_API_KEY', ''))"
    else:
        scraper_init = f"{class_name}()"
    
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

# Ensure parent directory is in path for imports
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
        
        # Run the async scraper
        result = asyncio.run(_scrape_data(params, log_manager))
        
        log_manager.log_function_end(status="success", result_summary={{"count": result.get("results", {{}}).get("articles_found", 0)}})
        
        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            status_code=200,
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
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        else:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        else:
            end_date = datetime.now()
    except Exception as e:
         raise ValueError(f"Invalid date format. Use YYYY-MM-DD. Error: {{str(e)}}")
    
    return {{
        'keywords': keywords,
        'start_date': start_date,
        'end_date': end_date,
        'save_to_db': save_to_db
    }}

async def _scrape_data(params: Dict[str, Any], log_manager: AzureLoggingManager) -> Dict[str, Any]:
    """Perform scraping operation and persist to database."""
    start_time = datetime.utcnow()
    
    # Initialize scraper
    scraper = {scraper_init}
    
    try:
        # Perform scraping
        articles = await scraper.scrape_news(
            keywords=params.get('keywords', []),
            start_date=params.get('start_date'),
            end_date=params.get('end_date')
        )
        
        # Convert to NewsArticle model
        news_articles = []
        for a in (articles if articles else []):
            # Handle both dict and object types
            title = getattr(a, 'title', '') or (a.get('title', '') if isinstance(a, dict) else '')
            content = getattr(a, 'content', '') or (a.get('content', '') if isinstance(a, dict) else '')
            url = getattr(a, 'url', '') or (a.get('url', '') if isinstance(a, dict) else '')
            pub_date = getattr(a, 'published_date', None) or (a.get('published_date', None) if isinstance(a, dict) else None)
            
            # Fallback for data-type scrapers that might nest data
            if not title and isinstance(a, dict) and 'type' in a:
                title = f"{{SOURCE_NAME}} {{a.get('type')}} Data"
                if not content:
                    content = json.dumps(a.get('data', a))
            
            # Robust defaults
            if not pub_date:
                pub_date = datetime.utcnow()
            elif not isinstance(pub_date, datetime):
                try:
                    pub_date = datetime.fromisoformat(str(pub_date))
                except:
                    pub_date = datetime.utcnow()
            
            if not title:
                title = f"{{SOURCE_NAME}} Data Entry - {{pub_date.strftime('%Y-%m-%d')}}"
            
            if not url:
                url = f"https://local.internal/{{SOURCE_NAME.lower().replace(' ', '_')}}/{{pub_date.timestamp()}}"

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
        persistence_error = None
        if params.get('save_to_db') and news_articles:
            try:
                db_config = await config_manager.get_database_config()
                db_handler = DatabaseHandler(db_config)
                await db_handler.save_articles(news_articles)
                articles_saved = len(news_articles)
                log_manager.info(f"Successfully saved {{articles_saved}} articles to database")
            except Exception as db_error:
                persistence_error = str(db_error)
                log_manager.log_error(error=db_error, context_data={{"operation": "database_persistence"}})
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {{
            "status": "success",
            "source": SOURCE_NAME,
            "execution_time_seconds": execution_time,
            "execution_id": log_manager.execution_id,
            "results": {{
                "articles_found": len(news_articles),
                "articles_saved": articles_saved,
                "persistence_error": persistence_error,
                "articles": [a.to_dict() for a in news_articles[:5]]
            }},
            "parameters": {{
                "keywords": params.get('keywords', []),
                "start_date": params['start_date'].isoformat(),
                "end_date": params['end_date'].isoformat()
            }}
        }}
        
    finally:
        if hasattr(scraper, 'close'):
            try:
                await scraper.close()
            except:
                pass
'''

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
        
        print(f"Created/Updated {{scraper_file}}_function/")
        created += 1
    
    print(f"\\nGenerated/Updated {{created}} function directories!")

if __name__ == "__main__":
    main()
