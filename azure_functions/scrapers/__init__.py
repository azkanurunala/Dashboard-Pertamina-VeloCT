"""
News scraper functions for Azure Functions.
This module contains the base scraper class and individual scraper implementations.
"""

import sys
import os

# Add parent directory to Python path for absolute imports in Azure Functions
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from scrapers.base_scraper import BaseNewsScraper
from scrapers.exceptions import ScrapingError, RateLimitError, ValidationError
from scrapers.bps_scraper import BPSScraper, create_bps_scraper

__all__ = [
    'BaseNewsScraper',
    'ScrapingError', 
    'RateLimitError',
    'ValidationError',
    'BPSScraper',
    'create_bps_scraper'
]