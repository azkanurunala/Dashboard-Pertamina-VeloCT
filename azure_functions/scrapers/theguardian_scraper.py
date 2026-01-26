"""
The Guardian News Scraper for Azure Functions.
Implements scraping functionality for The Guardian news articles using their API.
"""

import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from .base_scraper import BaseNewsScraper
from .exceptions import ScrapingError, NetworkError, ContentExtractionError
from ..shared.models import NewsArticle, ScrapingConfig


class TheGuardianNewsScraper(BaseNewsScraper):
    """
    The Guardian News Scraper implementation.
    Scrapes news articles from The Guardian using their Content API.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize The Guardian scraper with default configuration."""
        if config is None:
            config = ScrapingConfig(
                source_name="The Guardian",
                base_url="https://www.theguardian.com",
                selectors={
                    "api_base": "https://content.guardianapis.com/search",
                    "api_key": "997b85f0-96ed-452c-b509-5f62ec918b2a"  # Public test key
                },
                rate_limit_delay=0.5,
                max_retries=3,
                timeout=30
            )
        
        super().__init__(config)
        self.api_base = self.config.selectors.get("api_base", "https://content.guardianapis.com/search")
        self.api_key = self.config.selectors.get("api_key", "")

    def _clean_guardian_text(self, text: str) -> str:
        """
        Clean The Guardian-specific text patterns.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ''
        
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    async def _fetch_articles_from_api(self, keyword: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Fetch articles from The Guardian Content API.
        
        Args:
            keyword: Search keyword
            start_date: Start date for search
            end_date: End date for search
            
        Returns:
            List of article data dictionaries
        """
        try:
            # Format dates for API
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            # Prepare API parameters
            params = {
                'q': keyword,
                'api-key': self.api_key,
                'page-size': 200,  # Maximum allowed
                'show-fields': 'bodyText',
                'from-date': start_date_str,
                'to-date': end_date_str,
                'order-by': 'newest'
            }
            
            self.logger.info(f"Fetching articles for '{keyword}' from {start_date_str} to {end_date_str}")
            
            # Build URL with parameters
            url = self.api_base
            param_strings = []
            for key, value in params.items():
                param_strings.append(f"{key}={value}")
            
            if param_strings:
                url += "?" + "&".join(param_strings)
            
            # Make API request
            response = await self._make_request(url)
            data = await response.json()
            
            # Check API response status
            if data.get('response', {}).get('status') != 'ok':
                raise ScrapingError(f"API returned non-ok status: {data}", source=self.source_name)
            
            results = data['response'].get('results', [])
            self.logger.info(f"Found {len(results)} articles from API")
            
            # Process articles
            articles = []
            for article in results:
                try:
                    # Extract publication date
                    date_iso = article.get('webPublicationDate', '')
                    date_formatted = ''
                    
                    if date_iso:
                        try:
                            # Parse ISO date
                            date_obj = datetime.fromisoformat(date_iso.replace('Z', '+00:00'))
                            date_formatted = date_obj.strftime('%Y-%m-%d')
                        except Exception:
                            # Fallback to first 10 characters
                            date_formatted = date_iso[:10]
                    
                    # Extract article data
                    article_data = {
                        'title': self._clean_guardian_text(article.get('webTitle', '')),
                        'date': date_formatted,
                        'url': article.get('webUrl', ''),
                        'content': self._clean_guardian_text(article.get('fields', {}).get('bodyText', ''))
                    }
                    
                    # Only add articles with required fields
                    if article_data['title'] and article_data['url']:
                        articles.append(article_data)
                
                except Exception as e:
                    self.logger.warning(f"Failed to process article: {e}")
                    continue
            
            return articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to fetch articles from API: {str(e)}", source=self.source_name)

    async def _scrape_articles_from_source(self, keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
        """
        Scrape articles from The Guardian source.
        
        Args:
            keywords: Keywords to search for
            start_date: Start date for article search
            end_date: End date for article search
            **kwargs: Additional parameters
            
        Returns:
            List of scraped NewsArticle objects
        """
        try:
            all_articles = []
            
            # Process each keyword separately
            for keyword in keywords:
                try:
                    self.logger.info(f"Searching for keyword: {keyword}")
                    
                    # Fetch articles from API
                    api_articles = await self._fetch_articles_from_api(keyword, start_date, end_date)
                    
                    # Filter articles by date range (additional safety check)
                    filtered_articles = []
                    for article in api_articles:
                        if article['date']:
                            try:
                                article_date = datetime.strptime(article['date'], '%Y-%m-%d')
                                if start_date <= article_date <= end_date:
                                    filtered_articles.append(article)
                            except ValueError:
                                # Include articles with unparseable dates
                                filtered_articles.append(article)
                        else:
                            # Include articles without dates
                            filtered_articles.append(article)
                    
                    all_articles.extend(filtered_articles)
                    self.logger.info(f"Found {len(filtered_articles)} articles for keyword '{keyword}'")
                    
                    # Rate limiting between keywords
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    self.logger.error(f"Failed to process keyword '{keyword}': {e}")
                    continue
            
            # Remove duplicates based on URL
            unique_articles = {}
            for article in all_articles:
                unique_articles[article['url']] = article
            
            all_articles = list(unique_articles.values())
            self.logger.info(f"Total unique articles found: {len(all_articles)}")
            
            if not all_articles:
                return []
            
            # Limit articles for performance
            max_articles = kwargs.get('max_articles', 50)
            if len(all_articles) > max_articles:
                all_articles = all_articles[:max_articles]
                self.logger.info(f"Limited to {max_articles} articles for processing")
            
            # Convert to NewsArticle objects
            articles = []
            for i, article_data in enumerate(all_articles):
                try:
                    self.logger.info(f"Processing article {i+1}/{len(all_articles)}: {article_data['title'][:60]}...")
                    
                    # Parse published date
                    published_date = datetime.utcnow()
                    if article_data['date']:
                        try:
                            published_date = datetime.strptime(article_data['date'], '%Y-%m-%d')
                        except ValueError:
                            pass
                    
                    # Use API content or set as N/A if empty
                    content = article_data.get('content', '').strip()
                    if not content:
                        content = 'N/A'
                    
                    # Create article
                    article = self._create_article(
                        title=article_data['title'],
                        content=content,
                        url=article_data['url'],
                        published_date=published_date,
                        keywords=[]  # Will be populated by keyword filtering
                    )
                    
                    articles.append(article)
                    
                except Exception as e:
                    self.logger.error(f"Failed to process article {article_data['url']}: {e}")
                    continue
            
            self.logger.info(f"Successfully scraped {len(articles)} articles from The Guardian")
            return articles
            
        except Exception as e:
            raise ScrapingError(f"Failed to scrape The Guardian articles: {str(e)}", source=self.source_name)


# Azure Function wrapper
async def scrape_theguardian_news(keywords: List[str], start_date: datetime, end_date: datetime, **kwargs) -> List[NewsArticle]:
    """
    Azure Function entry point for The Guardian news scraping.
    
    Args:
        keywords: Keywords to search for
        start_date: Start date for article search
        end_date: End date for article search
        **kwargs: Additional parameters
        
    Returns:
        List of scraped NewsArticle objects
    """
    async with TheGuardianNewsScraper() as scraper:
        return await scraper.scrape_news(keywords, start_date, end_date, **kwargs)