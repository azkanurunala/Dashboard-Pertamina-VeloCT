"""
Reuters News Scraper Azure Function.
HTTP-triggered function for scraping Reuters news articles with keyword filtering and date range support.
"""

import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import azure.functions as func
import sys
import os

# Add parent directory to Python path for absolute imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


# Detailed import error logging
try:
    from scrapers.reuters_scraper import ReutersNewsScraper
    logging.info("✓ Successfully imported ReutersNewsScraper")
except Exception as e:
    logging.error(f"✗ IMPORT ERROR - ReutersNewsScraper: {str(e)}", exc_info=True)
    raise

try:
    from shared.models import NewsArticle
    logging.info("✓ Successfully imported NewsArticle")
except Exception as e:
    logging.error(f"✗ IMPORT ERROR - NewsArticle: {str(e)}", exc_info=True)
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
    from shared.logging_config import setup_logging
    logging.info("✓ Successfully imported setup_logging")
except Exception as e:
    logging.error(f"✗ IMPORT ERROR - setup_logging: {str(e)}", exc_info=True)
    raise

try:
    from shared.azure_logging import AzureLoggingManager
    logging.info("✓ Successfully imported AzureLoggingManager")
except Exception as e:
    logging.error(f"✗ IMPORT ERROR - AzureLoggingManager: {str(e)}", exc_info=True)
    raise

logging.info("✓✓✓ ALL IMPORTS SUCCESSFUL FOR REUTERS SCRAPER ✓✓✓")


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main Azure Function entry point for Reuters news scraping.
    
    Expected parameters:
    - keywords: List of keywords to search for (optional)
    - start_date: Start date in YYYY-MM-DD format (optional, defaults to 7 days ago)
    - end_date: End date in YYYY-MM-DD format (optional, defaults to today)
    - save_to_db: Whether to save results to database (optional, defaults to true)
    """
    setup_logging()
    
    # Initialize comprehensive logging
    correlation_id = req.headers.get('x-correlation-id')
    log_manager = AzureLoggingManager(
        function_name="reuters_scraper_function",
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
                "save_to_db": params['save_to_db']
            }
        )
        
        # Run the scraping operation
        result = asyncio.run(_scrape_reuters_news(params, log_manager))
        
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
                "source": "Reuters",
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
    """
    Parse and validate request parameters.
    
    Args:
        req: HTTP request object
        
    Returns:
        Dictionary of parsed parameters
        
    Raises:
        ValueError: If parameters are invalid
    """
    # Get parameters from query string or JSON body
    if req.method == "GET":
        keywords_str = req.params.get('keywords', '')
        start_date_str = req.params.get('start_date', '')
        end_date_str = req.params.get('end_date', '')
        save_to_db_str = req.params.get('save_to_db', 'true')
    else:
        try:
            req_body = req.get_json()
            if not req_body:
                req_body = {}
        except ValueError:
            req_body = {}
        
        keywords_str = req_body.get('keywords', '')
        start_date_str = req_body.get('start_date', '')
        end_date_str = req_body.get('end_date', '')
        save_to_db_str = req_body.get('save_to_db', 'true')
    
    # Parse keywords
    keywords = []
    if keywords_str:
        if isinstance(keywords_str, str):
            keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
        elif isinstance(keywords_str, list):
            keywords = [str(kw).strip() for kw in keywords_str if str(kw).strip()]
    
    # Parse dates
    end_date = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=0)
    start_date = end_date - timedelta(days=7)  # Default to last 7 days
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Invalid start_date format. Expected YYYY-MM-DD, got: {start_date_str}")
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        except ValueError:
            raise ValueError(f"Invalid end_date format. Expected YYYY-MM-DD, got: {end_date_str}")
    
    # Validate date range
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")
    
    # Parse save_to_db flag
    save_to_db = save_to_db_str.lower() in ('true', '1', 'yes', 'on')
    
    return {
        'keywords': keywords,
        'start_date': start_date,
        'end_date': end_date,
        'save_to_db': save_to_db
    }


async def _scrape_reuters_news(params: Dict[str, Any], log_manager: AzureLoggingManager) -> Dict[str, Any]:
    """
    Perform Reuters news scraping operation.
    
    Args:
        params: Parsed request parameters
        log_manager: Azure logging manager instance
        
    Returns:
        Dictionary with scraping results
    """
    start_time = datetime.utcnow()
    
    # Log scraping start
    log_manager.log_scraping_start(
        source="Reuters",
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
                "source": "Reuters",
                "keywords_count": len(params['keywords']),
                "date_range_days": (params['end_date'] - params['start_date']).days
            }
        )
        
        # Initialize scraper
        async with ReutersNewsScraper() as scraper:
            # Scrape articles
            articles = await scraper.scrape_news(
                keywords=params['keywords'],
                start_date=params['start_date'],
                end_date=params['end_date']
            )
            
            # Log articles found
            log_manager.log_scraping_articles_found(
                count=len(articles),
                parsing_success_rate=100.0 if articles else 0.0
            )
            
            # Save to database if requested
            saved_count = 0
            if params['save_to_db'] and articles:
                try:
                    db_start = datetime.utcnow()
                    connection_string = get_database_connection_string()
                    
                    async with DatabaseHandler(connection_string) as db:
                        saved_count = await db.save_articles(articles)
                        
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
                "source": "Reuters",
                "execution_time_seconds": execution_time,
                "execution_id": log_manager.execution_id,
                "correlation_id": log_manager.correlation_id,
                "parameters": {
                    "keywords": params['keywords'],
                    "start_date": params['start_date'].isoformat(),
                    "end_date": params['end_date'].isoformat(),
                    "save_to_db": params['save_to_db']
                },
                "results": {
                    "articles_found": len(articles),
                    "articles_saved": saved_count,
                    "articles": [_serialize_article(article) for article in articles[:10]]  # Return first 10 for preview
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
                "source": "Reuters",
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


def _serialize_article(article: NewsArticle) -> Dict[str, Any]:
    """
    Serialize NewsArticle object for JSON response.
    
    Args:
        article: NewsArticle object
        
    Returns:
        Dictionary representation of article
    """
    return {
        "title": article.title,
        "url": article.url,
        "source": article.source,
        "published_date": article.published_date.isoformat() if article.published_date else None,
        "scraped_date": article.scraped_date.isoformat() if article.scraped_date else None,
        "keywords": article.keywords,
        "language": article.language,
        "author": article.author,
        "category": article.category,
        "content_preview": article.content[:200] + "..." if len(article.content) > 200 else article.content
    }