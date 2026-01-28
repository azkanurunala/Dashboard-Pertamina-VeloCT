"""
Azure Function for The Guardian news scraping.
HTTP-triggered function that scrapes news articles from The Guardian.
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any

import azure.functions as func
import sys
import os

# Add parent directory to Python path for absolute imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


# Detailed import error logging
try:
    from scrapers.theguardian_scraper import scrape_theguardian_news
    logging.info("✓ Successfully imported scrape_theguardian_news")
except Exception as e:
    logging.error(f"✗ IMPORT ERROR - scrape_theguardian_news: {str(e)}", exc_info=True)
    raise

try:
    from shared.database_handler import DatabaseHandler
    logging.info("✓ Successfully imported DatabaseHandler")
except Exception as e:
    logging.error(f"✗ IMPORT ERROR - DatabaseHandler: {str(e)}", exc_info=True)
    raise

try:
    from shared.config import get_database_connection_string
    logging.info("✓ Successfully imported get_database_connection_string")
except Exception as e:
    logging.error(f"✗ IMPORT ERROR - get_database_connection_string: {str(e)}", exc_info=True)
    raise

try:
    from shared.utils import parse_date_parameter, validate_keywords
    logging.info("✓ Successfully imported parse_date_parameter, validate_keywords")
except Exception as e:
    logging.error(f"✗ IMPORT ERROR - utils: {str(e)}", exc_info=True)
    raise

try:
    from shared.azure_logging import AzureLoggingManager
    logging.info("✓ Successfully imported AzureLoggingManager")
except Exception as e:
    logging.error(f"✗ IMPORT ERROR - AzureLoggingManager: {str(e)}", exc_info=True)
    raise

logging.info("✓✓✓ ALL IMPORTS SUCCESSFUL FOR THE GUARDIAN SCRAPER ✓✓✓")


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function entry point for The Guardian news scraping.
    
    Expected parameters:
    - keywords: Comma-separated list of keywords to search for
    - start_date: Start date in YYYY-MM-DD format
    - end_date: End date in YYYY-MM-DD format
    - max_articles: Maximum number of articles to process (optional, default: 50)
    """
    # Initialize comprehensive logging
    correlation_id = req.headers.get('x-correlation-id')
    log_manager = AzureLoggingManager(
        function_name="theguardian_scraper_function",
        correlation_id=correlation_id
    )
    
    try:
        # Parse request parameters
        params = _parse_request_parameters(req)
        
        # Log function start
        log_manager.log_function_start(
            trigger_type="http",
            parameters={
                "keywords": params['keywords'],
                "start_date": params['start_date'].isoformat(),
                "end_date": params['end_date'].isoformat(),
                "max_articles": params['max_articles']
            }
        )
        
        # Run the scraping operation using asyncio.run()
        result = asyncio.run(_scrape_theguardian_news(params, log_manager))
        
        # Log function completion
        log_manager.log_function_end(
            status="success",
            result_summary={
                "articles_found": result['results']['articles_found'],
                "articles_saved": result['results']['articles_saved'],
                "execution_time_seconds": result['execution_time_seconds']
            }
        )
        
        # Return successful response
        return func.HttpResponse(
            json.dumps(result, indent=2, default=str),
            status_code=200,
            mimetype="application/json"
        )
        
    except ValueError as e:
        # Log parameter validation error
        log_manager.log_error(
            error=e,
            context_data={
                "error_type": "parameter_validation",
                "operation": "parse_parameters"
            }
        )
        
        log_manager.log_function_end(
            status="failed",
            result_summary={"error": "Invalid parameters", "message": str(e)}
        )
        
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
        # Log unexpected error
        log_manager.log_error(
            error=e,
            context_data={
                "error_type": "unexpected_error",
                "operation": "scraping",
                "parameters": params if 'params' in locals() else {}
            }
        )
        
        log_manager.log_function_end(
            status="failed",
            result_summary={"error": "Internal server error", "message": str(e)}
        )
        
        # Get detailed error info
        import traceback
        error_traceback = traceback.format_exc()
        
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "source": "The Guardian",
                "error": "Internal server error",
                "message": str(e),
                "error_type": type(e).__name__,
                "execution_id": log_manager.execution_id,
                "traceback": error_traceback.split('\n')[-5:],  # Last 5 lines
                "timestamp": datetime.utcnow().isoformat()
            }),
            status_code=500,
            mimetype="application/json"
        )


def _parse_request_parameters(req: func.HttpRequest) -> Dict[str, Any]:
    """Parse and validate request parameters."""
    keywords_param = req.params.get('keywords')
    start_date_param = req.params.get('start_date')
    end_date_param = req.params.get('end_date')
    max_articles_param = req.params.get('max_articles', '50')
    
    # Validate required parameters
    if not keywords_param:
        raise ValueError("Missing required parameter: keywords")
    
    if not start_date_param or not end_date_param:
        raise ValueError("Missing required parameters: start_date and end_date")
    
    # Parse and validate parameters
    keywords = validate_keywords(keywords_param)
    start_date = parse_date_parameter(start_date_param)
    end_date = parse_date_parameter(end_date_param)
    max_articles = int(max_articles_param)
    
    # Validate date range
    if start_date > end_date:
        raise ValueError("start_date must be before or equal to end_date")
    
    return {
        'keywords': keywords,
        'start_date': start_date,
        'end_date': end_date,
        'max_articles': max_articles
    }


async def _scrape_theguardian_news(params: Dict[str, Any], log_manager: AzureLoggingManager) -> Dict[str, Any]:
    """Perform The Guardian news scraping operation."""
    start_time = datetime.utcnow()
    
    # Log scraping start
    log_manager.log_scraping_start(
        source="The Guardian",
        keywords=params['keywords'],
        date_range={
            'start': params['start_date'].isoformat(),
            'end': params['end_date'].isoformat()
        }
    )
    
    try:
        # Start scraping operation
        operation_id = log_manager.log_operation_start(
            operation_name="scrape_articles",
            details={
                "source": "The Guardian",
                "keywords_count": len(params['keywords']),
                "date_range_days": (params['end_date'] - params['start_date']).days,
                "max_articles": params['max_articles']
            }
        )
        
        # Scrape articles
        articles = await scrape_theguardian_news(
            keywords=params['keywords'],
            start_date=params['start_date'],
            end_date=params['end_date'],
            max_articles=params['max_articles']
        )
        
        # Log articles found
        log_manager.log_scraping_articles_found(
            count=len(articles),
            parsing_success_rate=100.0 if articles else 0.0
        )
        
        # Save articles to database
        saved_count = 0
        if articles:
            try:
                db_start = datetime.utcnow()
                connection_string = get_database_connection_string()
                db_handler = DatabaseHandler(connection_string)
                await db_handler.save_articles(articles)
                saved_count = len(articles)
                
                db_duration = (datetime.utcnow() - db_start).total_seconds() * 1000
                
                # Log database operation
                log_manager.log_database_operation(
                    operation="INSERT",
                    table="news_articles",
                    row_count=saved_count,
                    duration_ms=db_duration
                )
                
                # Log articles saved
                log_manager.log_scraping_articles_saved(
                    saved_count=saved_count,
                    duplicate_count=len(articles) - saved_count,
                    duration_ms=db_duration
                )
                
            except Exception as e:
                # Log database error
                log_manager.log_database_error(
                    error=e,
                    query_type="INSERT",
                    table="news_articles"
                )
                # Continue without failing the entire operation
        
        # Calculate execution time
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        execution_time_ms = execution_time * 1000
        
        # Log scraping end
        log_manager.log_scraping_end(
            articles_scraped=len(articles),
            articles_saved=saved_count,
            duration_ms=execution_time_ms
        )
        
        # Log operation end
        log_manager.log_operation_end(
            operation_id=operation_id,
            status="success",
            metrics={
                "articles_found": len(articles),
                "articles_saved": saved_count,
                "execution_time_ms": execution_time_ms
            }
        )
        
        # Prepare response
        return {
            "status": "success",
            "source": "The Guardian",
            "execution_time_seconds": execution_time,
            "execution_id": log_manager.execution_id,
            "correlation_id": log_manager.correlation_id,
            "parameters": {
                "keywords": params['keywords'],
                "start_date": params['start_date'].isoformat(),
                "end_date": params['end_date'].isoformat(),
                "max_articles": params['max_articles']
            },
            "results": {
                "articles_found": len(articles),
                "articles_saved": saved_count,
                "articles": [
                    {
                        "title": article.title,
                        "url": article.url,
                        "published_date": article.published_date.isoformat() if article.published_date else None,
                        "content_length": len(article.content) if article.content else 0,
                        "keywords": article.keywords
                    }
                    for article in articles[:10]  # Return first 10 for preview
                ]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Log error
        log_manager.log_error(
            error=e,
            context_data={
                "operation": "scraping",
                "source": "The Guardian",
                "execution_time_seconds": execution_time
            }
        )
        
        # Log operation end with failure
        if 'operation_id' in locals():
            log_manager.log_operation_end(
                operation_id=operation_id,
                status="failed",
                metrics={"execution_time_seconds": execution_time}
            )
        
        raise