"""
Azure Function for BPS (Statistics Indonesia) news scraper.
HTTP-triggered function that scrapes news from BPS using their official API.
"""

import azure.functions as func
import logging
import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sys
import os

# Add parent directory to Python path for absolute imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


# Detailed import error logging
try:
    from scrapers.bps_scraper import create_bps_scraper
    logging.info("✓ Successfully imported create_bps_scraper")
except Exception as e:
    logging.error(f"✗ IMPORT ERROR - create_bps_scraper: {str(e)}", exc_info=True)
    raise

try:
    from shared.database_handler import DatabaseHandler
    logging.info("✓ Successfully imported DatabaseHandler")
except Exception as e:
    logging.error(f"✗ IMPORT ERROR - DatabaseHandler: {str(e)}", exc_info=True)
    raise

try:
    from shared.config import get_config
    logging.info("✓ Successfully imported get_config")
except Exception as e:
    logging.error(f"✗ IMPORT ERROR - get_config: {str(e)}", exc_info=True)
    raise

try:
    from shared.azure_logging import AzureLoggingManager
    logging.info("✓ Successfully imported AzureLoggingManager")
except Exception as e:
    logging.error(f"✗ IMPORT ERROR - AzureLoggingManager: {str(e)}", exc_info=True)
    raise

logging.info("✓✓✓ ALL IMPORTS SUCCESSFUL FOR BPS SCRAPER ✓✓✓")


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function entry point for BPS scraper.
    
    Query Parameters:
        - keywords: Comma-separated list of keywords to search for
        - start_date: Start date in YYYY-MM-DD format (optional, defaults to today)
        - end_date: End date in YYYY-MM-DD format (optional, defaults to today)
        - max_pages: Maximum number of pages to scrape (optional)
        - save_to_db: Whether to save results to database (optional, defaults to true)
    
    Returns:
        JSON response with scraped articles or error message
    """
    # Initialize comprehensive logging
    correlation_id = req.headers.get('x-correlation-id')
    log_manager = AzureLoggingManager(
        function_name="bps_scraper_function",
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
                "max_pages": params['max_pages'],
                "save_to_db": params['save_to_db']
            }
        )
        
        # Run the scraping operation
        result = asyncio.run(_scrape_bps_news(params, log_manager))
        
        # Log function completion
        log_manager.log_function_end(
            status="success",
            result_summary={
                "articles_found": result['count'],
                "execution_time_seconds": result.get('execution_time_seconds', 0)
            }
        )
        
        # Return successful response
        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False, indent=2),
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
                "source": "BPS",
                "error": "Internal server error",
                "message": str(e),
                "error_type": type(e).__name__,
                "execution_id": log_manager.execution_id,
                "traceback": error_traceback.split('\n')[-5:],
                "timestamp": datetime.utcnow().isoformat()
            }),
            status_code=500,
            mimetype="application/json"
        )



def _parse_request_parameters(req: func.HttpRequest) -> Dict[str, Any]:
    """Parse and validate request parameters."""
    keywords_param = req.params.get('keywords', '')
    keywords = [k.strip() for k in keywords_param.split(',') if k.strip()] if keywords_param else []
    
    start_date_str = req.params.get('start_date')
    end_date_str = req.params.get('end_date')
    max_pages_str = req.params.get('max_pages')
    save_to_db = req.params.get('save_to_db', 'true').lower() == 'true'
    
    # Parse dates
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Invalid start_date format. Expected YYYY-MM-DD, got: {start_date_str}")
    else:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Invalid end_date format. Expected YYYY-MM-DD, got: {end_date_str}")
    else:
        end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Validate date range
    if start_date > end_date:
        raise ValueError("start_date must be before or equal to end_date")
    
    # Parse max_pages
    max_pages = None
    if max_pages_str:
        try:
            max_pages = int(max_pages_str)
            if max_pages < 1:
                raise ValueError("max_pages must be a positive integer")
        except ValueError as e:
            raise ValueError(f"Invalid max_pages: {str(e)}")
    
    return {
        'keywords': keywords,
        'start_date': start_date,
        'end_date': end_date,
        'max_pages': max_pages,
        'save_to_db': save_to_db
    }


async def _scrape_bps_news(params: Dict[str, Any], log_manager: AzureLoggingManager) -> Dict[str, Any]:
    """Perform BPS news scraping operation."""
    start_time = datetime.utcnow()
    
    # Log scraping start
    log_manager.log_scraping_start(
        source="BPS",
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
                "source": "BPS",
                "keywords_count": len(params['keywords']),
                "date_range_days": (params['end_date'] - params['start_date']).days,
                "max_pages": params['max_pages']
            }
        )
        
        # Get BPS API key from configuration
        config = get_config()
        api_key = os.getenv('BPS_API_KEY')
        
        if not api_key:
            raise ValueError("BPS_API_KEY not found in environment variables")
        
        # Create scraper and scrape articles
        scraper = await create_bps_scraper(api_key=api_key)
        
        try:
            articles = await scraper.scrape_news(
                keywords=params['keywords'],
                start_date=params['start_date'],
                end_date=params['end_date'],
                max_pages=params['max_pages']
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
                    db_handler = DatabaseHandler(config.database_connection_string)
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
                    # Continue execution, return articles even if DB save fails
            
            # Convert articles to dict for JSON response
            articles_data = [
                {
                    "title": article.title,
                    "content": article.content[:500] + "..." if len(article.content) > 500 else article.content,
                    "url": article.url,
                    "source": article.source,
                    "published_date": article.published_date.isoformat(),
                    "scraped_date": article.scraped_date.isoformat(),
                    "keywords": article.keywords,
                    "language": article.language,
                    "category": article.category
                }
                for article in articles
            ]
            
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
            
            return {
                "status": "success",
                "source": "BPS",
                "count": len(articles),
                "execution_time_seconds": execution_time,
                "execution_id": log_manager.execution_id,
                "correlation_id": log_manager.correlation_id,
                "articles": articles_data,
                "parameters": {
                    "keywords": params['keywords'],
                    "start_date": params['start_date'].isoformat(),
                    "end_date": params['end_date'].isoformat(),
                    "max_pages": params['max_pages'],
                    "saved_to_db": params['save_to_db']
                }
            }
            
        finally:
            await scraper.close()
            
    except Exception as e:
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Log error
        log_manager.log_error(
            error=e,
            context_data={
                "operation": "scraping",
                "source": "BPS",
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
