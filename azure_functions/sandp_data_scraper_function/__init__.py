"""
Azure Function for S&P Data scraper.
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

from scrapers.sandp_data_scraper import SAndPDataScraper
from shared.azure_logging import AzureLoggingManager
from shared.database_handler import DatabaseHandler
from shared.config import config_manager
from shared.models import NewsArticle

SOURCE_NAME = "S&P Data"

def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Function entry point."""
    correlation_id = req.headers.get('x-correlation-id')
    log_manager = AzureLoggingManager(
        function_name="sandp_data_scraper_function",
        correlation_id=correlation_id
    )
    
    try:
        params = _parse_request_parameters(req)
        log_manager.log_function_start(trigger_type="http", parameters={k: str(v) for k, v in params.items()})
        
        # Run the async scraper
        result = asyncio.run(_scrape_data(params, log_manager))
        
        log_manager.log_function_end(status="success", result_summary={"count": result.get("results", {}).get("articles_found", 0)})
        
        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        log_manager.log_error(error=e, context_data={"operation": "scraping"})
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "source": SOURCE_NAME,
                "error": str(e),
                "error_type": type(e).__name__,
                "execution_id": log_manager.execution_id,
                "timestamp": datetime.utcnow().isoformat()
            }),
            status_code=500,
            mimetype="application/json"
        )

def _parse_request_parameters(req: func.HttpRequest) -> Dict[str, Any]:
    """Parse request parameters from body or query string."""
    try:
        body = req.get_json()
    except:
        body = {}
    
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
         raise ValueError(f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}")
    
    # Get data type (e.g. bbm_forecast_short, petrochemical, saf)
    data_type = body.get('data_type') or req.params.get('data_type', 'bbm_forecast_short')
    
    return {
        'keywords': keywords,
        'start_date': start_date,
        'end_date': end_date,
        'save_to_db': save_to_db,
        'data_type': data_type
    }

async def _scrape_data(params: Dict[str, Any], log_manager: AzureLoggingManager) -> Dict[str, Any]:
    """Perform scraping operation and persist to database."""
    start_time = datetime.utcnow()
    
    # Initialize scraper
    scraper = SAndPDataScraper()
    
    try:
        # Perform scraping with specific data type support
        results = await scraper.scrape_news(
            keywords=params.get('keywords', []),
            start_date=params.get('start_date'),
            end_date=params.get('end_date'),
            data_type=params.get('data_type')
        )
        
        items_saved = 0
        persistence_error = None
        structured_results = []

        if params.get('save_to_db') and results:
            try:
                db_config = await config_manager.get_database_config()
                db_handler = DatabaseHandler(db_config)
                
                # S&P Data scraper returns a list of dicts with 'type' and 'data'
                for result in results:
                    table_name = result.get('type')
                    data_list = result.get('data')
                    
                    if table_name and data_list:
                        await db_handler.save_structured_data(table_name, data_list)
                        items_saved += len(data_list)
                        structured_results.append({
                            "table": table_name,
                            "count": len(data_list)
                        })
                
                log_manager.info(f"Successfully saved {items_saved} items to specialized tables")
            except Exception as db_error:
                persistence_error = str(db_error)
                log_manager.log_error(error=db_error, context_data={"operation": "database_persistence"})
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "status": "success",
            "source": SOURCE_NAME,
            "data_type": params.get('data_type'),
            "execution_time_seconds": execution_time,
            "execution_id": log_manager.execution_id,
            "results": {
                "items_found": items_saved if not persistence_error else 0, # approximation if saved
                "items_saved": items_saved,
                "structured_summary": structured_results,
                "persistence_error": persistence_error
            },
            "parameters": {
                "keywords": params.get('keywords', []),
                "start_date": params['start_date'].isoformat(),
                "end_date": params['end_date'].isoformat()
            }
        }
        
    finally:
        if hasattr(scraper, 'close'):
            try:
                await scraper.close()
            except:
                pass
