"""
News scraper functions for Azure Functions.
This module contains the base scraper class and individual scraper implementations.
"""

from .base_scraper import BaseNewsScraper
from .exceptions import ScrapingError, RateLimitError, ValidationError
from .bps_scraper import BPSScraper, create_bps_scraper

__all__ = [
    'BaseNewsScraper',
    'ScrapingError', 
    'RateLimitError',
    'ValidationError',
    'BPSScraper',
    'create_bps_scraper'
]