"""
Azure Function for BPS (Statistics Indonesia) news scraper.
HTTP-triggered function that scrapes news from BPS using their official API.
"""

import azure.functions as func
import logging
import json
import os
from datetime import datetime, timedelta
from typing import List

from ..scrapers.bps_scraper import create_bps_scraper
from ..shared.database_handler import DatabaseHandler
from ..shared.config import get_config


async def main(req: func.HttpRequest) -> func.HttpResponse:
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
    logging.info('BPS scraper function triggered')
    
    try:
        # Parse query parameters
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
                return func.HttpResponse(
                    json.dumps({"error": "Invalid start_date format. Use YYYY-MM-DD"}),
                    status_code=400,
                    mimetype="application/json"
                )
        else:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            except ValueError:
                return func.HttpResponse(
                    json.dumps({"error": "Invalid end_date format. Use YYYY-MM-DD"}),
                    status_code=400,
                    mimetype="application/json"
                )
        else:
            end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Validate date range
        if start_date > end_date:
            return func.HttpResponse(
                json.dumps({"error": "start_date must be before or equal to end_date"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Parse max_pages
        max_pages = None
        if max_pages_str:
            try:
                max_pages = int(max_pages_str)
                if max_pages < 1:
                    raise ValueError()
            except ValueError:
                return func.HttpResponse(
                    json.dumps({"error": "max_pages must be a positive integer"}),
                    status_code=400,
                    mimetype="application/json"
                )
        
        # Get BPS API key from configuration
        config = get_config()
        api_key = os.getenv('BPS_API_KEY')
        
        if not api_key:
            logging.error("BPS_API_KEY not found in environment variables")
            return func.HttpResponse(
                json.dumps({"error": "BPS API key not configured"}),
                status_code=500,
                mimetype="application/json"
            )
        
        logging.info(f"Scraping BPS with keywords: {keywords}, date range: {start_date_str} to {end_date_str}")
        
        # Create scraper and scrape articles
        scraper = await create_bps_scraper(api_key=api_key)
        
        try:
            articles = await scraper.scrape_news(
                keywords=keywords,
                start_date=start_date,
                end_date=end_date,
                max_pages=max_pages
            )
            
            logging.info(f"Successfully scraped {len(articles)} articles from BPS")
            
            # Save to database if requested
            if save_to_db and articles:
                try:
                    db_handler = DatabaseHandler(config.database_connection_string)
                    await db_handler.save_articles(articles)
                    logging.info(f"Saved {len(articles)} articles to database")
                except Exception as db_error:
                    logging.error(f"Failed to save articles to database: {db_error}")
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
            
            response_data = {
                "status": "success",
                "count": len(articles),
                "articles": articles_data,
                "parameters": {
                    "keywords": keywords,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "max_pages": max_pages,
                    "saved_to_db": save_to_db
                }
            }
            
            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False, indent=2),
                status_code=200,
                mimetype="application/json"
            )
            
        finally:
            await scraper.close()
    
    except Exception as e:
        logging.error(f"Error in BPS scraper function: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }),
            status_code=500,
            mimetype="application/json"
        )
