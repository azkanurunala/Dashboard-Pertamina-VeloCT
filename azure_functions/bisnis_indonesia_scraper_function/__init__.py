"""
Azure Function for Bisnis Indonesia news scraping.
HTTP-triggered function that scrapes news articles from Bisnis Indonesia.
"""

import json
import logging
from datetime import datetime
from typing import List

import azure.functions as func

from ..scrapers.bisnis_indonesia_scraper import scrape_bisnis_indonesia_news
from ..shared.database_handler import DatabaseHandler
from ..shared.config import get_database_connection_string
from ..shared.utils import parse_date_parameter, validate_keywords


async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function entry point for Bisnis Indonesia news scraping.
    
    Expected parameters:
    - keywords: Comma-separated list of keywords to search for
    - start_date: Start date in YYYY-MM-DD format
    - end_date: End date in YYYY-MM-DD format
    - max_articles: Maximum number of articles to process (optional, default: 20)
    """
    logging.info('Bisnis Indonesia scraper function triggered')
    
    try:
        # Parse request parameters
        keywords_param = req.params.get('keywords')
        start_date_param = req.params.get('start_date')
        end_date_param = req.params.get('end_date')
        max_articles_param = req.params.get('max_articles', '20')
        
        # Validate required parameters
        if not keywords_param:
            return func.HttpResponse(
                json.dumps({"error": "Missing required parameter: keywords"}),
                status_code=400,
                mimetype="application/json"
            )
        
        if not start_date_param or not end_date_param:
            return func.HttpResponse(
                json.dumps({"error": "Missing required parameters: start_date and end_date"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Parse and validate parameters
        try:
            keywords = validate_keywords(keywords_param)
            start_date = parse_date_parameter(start_date_param)
            end_date = parse_date_parameter(end_date_param)
            max_articles = int(max_articles_param)
        except ValueError as e:
            return func.HttpResponse(
                json.dumps({"error": f"Invalid parameter: {str(e)}"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Validate date range
        if start_date > end_date:
            return func.HttpResponse(
                json.dumps({"error": "start_date must be before or equal to end_date"}),
                status_code=400,
                mimetype="application/json"
            )
        
        logging.info(f'Scraping Bisnis Indonesia articles for keywords: {keywords}, date range: {start_date} to {end_date}')
        
        # Scrape articles
        articles = await scrape_bisnis_indonesia_news(
            keywords=keywords,
            start_date=start_date,
            end_date=end_date,
            max_articles=max_articles
        )
        
        # Save articles to database
        if articles:
            try:
                connection_string = get_database_connection_string()
                db_handler = DatabaseHandler(connection_string)
                await db_handler.save_articles(articles)
                logging.info(f'Saved {len(articles)} articles to database')
            except Exception as e:
                logging.error(f'Failed to save articles to database: {e}')
                # Continue execution - don't fail the function if DB save fails
        
        # Prepare response
        response_data = {
            "status": "success",
            "source": "Bisnis Indonesia",
            "articles_found": len(articles),
            "keywords": keywords,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "articles": [
                {
                    "title": article.title,
                    "url": article.url,
                    "published_date": article.published_date.isoformat(),
                    "content_length": len(article.content) if article.content else 0,
                    "keywords": article.keywords
                }
                for article in articles
            ]
        }
        
        logging.info(f'Successfully scraped {len(articles)} articles from Bisnis Indonesia')
        
        return func.HttpResponse(
            json.dumps(response_data, ensure_ascii=False, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f'Error in Bisnis Indonesia scraper function: {str(e)}', exc_info=True)
        
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "source": "Bisnis Indonesia",
                "error": str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )