"""
Data processing and aggregation functions for the Azure Functions news scraping system.
"""

from .news_aggregator import NewsAggregatorFunction, NewsAggregator, AggregationResult
from .deduplication_service import DeduplicationService, DeduplicationResult, DeduplicationStats
from .data_cache import DataCacheFunction, DataCache, CachedDatabaseHandler, CacheStats

__all__ = [
    'NewsAggregatorFunction',
    'NewsAggregator',
    'AggregationResult',
    'DeduplicationService',
    'DeduplicationResult',
    'DeduplicationStats',
    'DataCacheFunction',
    'DataCache',
    'CachedDatabaseHandler',
    'CacheStats'
]