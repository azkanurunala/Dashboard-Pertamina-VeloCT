"""
Data processing and aggregation functions for the Azure Functions news scraping system.
"""

from .news_aggregator import NewsAggregatorFunction
from .deduplicator import DeduplicationFunction
from .data_cache import DataCacheFunction

__all__ = [
    'NewsAggregatorFunction',
    'DeduplicationFunction', 
    'DataCacheFunction'
]