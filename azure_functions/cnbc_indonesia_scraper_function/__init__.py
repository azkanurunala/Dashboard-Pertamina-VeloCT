"""
Azure Function for CNBCIndonesia scraper.
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

from scrapers.cnbc_indonesia_scraper import CNBCIndonesiaNewsScraper
from shared.azure_logging import AzureLoggingManager

SOURCE_NAME = "CNBCIndonesia"


def main(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Function entry point."""
    correlation_id = req.headers.get('x-correlation-id')
    log_manager = AzureLoggingManager(
        function_name="cnbc_indonesia_scraper_function",
        correlation_id=correlation_id
    )
    
    try:
        params = _parse_request_parameters(req)
        log_manager.log_function_start(trigger_type="http", parameters={k: str(v) for k, v in params.items()})
        
        result = asyncio.run(_scrape_data(params, log_manager))
        
        log_manager.log_function_end(status="success", result_summary={"count": result.get("results", {}).get("articles_found", 0)})
        
        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            status_code=200,
            mimetype="application/json"
        )
        
    except ValueError as e:
        log_manager.log_function_end(status="failed", result_summary={"error": str(e)})
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "error": "Invalid parameters",
                "message": str(e),
                "error_type": "ValueError",
                "execution_id": log_manager.execution_id,
                "timestamp": datetime.utcnow().isoformat()
            }),
            status_code=400,
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
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    else:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    else:
        end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return {
        'keywords': keywords,
        'start_date': start_date,
        'end_date': end_date,
        'save_to_db': save_to_db
    }


async def _scrape_data(params: Dict[str, Any], log_manager: AzureLoggingManager) -> Dict[str, Any]:
    """Perform scraping operation."""
    start_time = datetime.utcnow()
    
    scraper = CNBCIndonesiaNewsScraper()
    
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
        
        # Convert articles to serializable format
        articles_data = []
        for a in (articles if articles else []):
            article = {
                "title": getattr(a, 'title', str(a)) if hasattr(a, 'title') else str(a),
                "url": getattr(a, 'url', '') if hasattr(a, 'url') else '',
                "source": getattr(a, 'source', SOURCE_NAME) if hasattr(a, 'source') else SOURCE_NAME
            }
            if hasattr(a, 'published_date') and a.published_date:
                article["published_date"] = a.published_date.isoformat() if hasattr(a.published_date, 'isoformat') else str(a.published_date)
            articles_data.append(article)
        
        return {
            "status": "success",
            "source": SOURCE_NAME,
            "execution_time_seconds": execution_time,
            "execution_id": log_manager.execution_id,
            "results": {
                "articles_found": len(articles_data),
                "articles_saved": len(articles_data) if params.get('save_to_db') else 0,
                "articles": articles_data[:10]  # Limit to 10 in response
            },
            "parameters": {
                "keywords": params.get('keywords', []),
                "start_date": params['start_date'].isoformat() if params.get('start_date') else None,
                "end_date": params['end_date'].isoformat() if params.get('end_date') else None
            }
        }
        
    finally:
        if hasattr(scraper, 'close'):
            try:
                await scraper.close()
            except:
                pass
