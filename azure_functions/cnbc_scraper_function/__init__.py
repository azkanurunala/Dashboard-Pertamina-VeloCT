"""
CNBC News Scraper Azure Function.
HTTP-triggered function for scraping CNBC news articles with keyword filtering and date range support.
"""

import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import azure.functions as func

from ..scrapers.cnbc_scraper import CNBCNewsScraper
from ..shared.models import NewsArticle
from ..shared.database_handler import DatabaseHandler
from ..shared.config import get_database_connection_string
from ..shared.logging_config import setup_logging


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main Azure Function entry point for CNBC news scraping.
    
    Expected parameters:
    - keywords: List of keywords to search for (optional)
    - start_date: Start date in YYYY-MM-DD format (optional, defaults to 7 days ago)
    - end_date: End date in YYYY-MM-DD format (optional, defaults to today)
    - save_to_db: Whether to save results to database (optional, defaults to true)
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info('CNBC scraper function triggered')
    
    try:
        # Parse request parameters
        params = _parse_request_parameters(req)
        logger.info(f"Scraping CNBC with parameters: {params}")
        
        # Run the scraping operation
        result = asyncio.run(_scrape_cnbc_news(params))
        
        # Return successful response
        return func.HttpResponse(
            json.dumps(result, indent=2, default=str),
            status_code=200,
            mimetype="application/json"
        )
        
    except ValueError as e:
        logger.error(f"Parameter validation error: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "error": "Invalid parameters",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }),
            status_code=400,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"CNBC scraper function error: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "error": "Internal server error",
                "message": str(e),
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


async def _scrape_cnbc_news(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform CNBC news scraping operation.
    
    Args:
        params: Parsed request parameters
        
    Returns:
        Dictionary with scraping results
    """
    logger = logging.getLogger(__name__)
    start_time = datetime.utcnow()
    
    try:
        # Initialize scraper
        async with CNBCNewsScraper() as scraper:
            # Scrape articles
            articles = await scraper.scrape_news(
                keywords=params['keywords'],
                start_date=params['start_date'],
                end_date=params['end_date']
            )
            
            logger.info(f"Successfully scraped {len(articles)} articles from CNBC")
            
            # Save to database if requested
            saved_count = 0
            if params['save_to_db'] and articles:
                try:
                    connection_string = get_database_connection_string()
                    async with DatabaseHandler(connection_string) as db:
                        saved_count = await db.save_articles(articles)
                        logger.info(f"Saved {saved_count} articles to database")
                except Exception as e:
                    logger.error(f"Failed to save articles to database: {e}")
                    # Continue without failing the entire operation
            
            # Prepare response
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "status": "success",
                "source": "CNBC",
                "execution_time_seconds": execution_time,
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
        logger.error(f"CNBC scraping failed after {execution_time}s: {e}")
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