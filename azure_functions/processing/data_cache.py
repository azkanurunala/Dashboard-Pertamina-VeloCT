"""
Data caching module for frequent database queries.
Implements in-memory caching with TTL and cache invalidation logic.
"""

import asyncio
import logging
from typing import Any, Optional, Dict, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import hashlib
import json

try:
    from ..shared.logging_config import get_logger
except ImportError:
    from shared.logging_config import get_logger


@dataclass
class CacheEntry:
    """Represents a single cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    last_accessed: Optional[datetime] = None


@dataclass
class CacheStats:
    """Statistics about cache performance."""
    total_entries: int
    total_hits: int
    total_misses: int
    hit_rate: float
    total_size_bytes: int
    oldest_entry: Optional[datetime] = None
    newest_entry: Optional[datetime] = None


class DataCache:
    """
    In-memory data cache with TTL and invalidation support.
    
    Features:
    - Time-to-live (TTL) for automatic expiration
    - Cache invalidation by key or pattern
    - Cache statistics and monitoring
    - Thread-safe operations
    - Memory-efficient storage
    """
    
    def __init__(self, default_ttl_seconds: int = 300, max_size: int = 1000):
        """
        Initialize the data cache.
        
        Args:
            default_ttl_seconds: Default time-to-live in seconds (default: 300 = 5 minutes)
            max_size: Maximum number of cache entries (default: 1000)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._default_ttl = timedelta(seconds=default_ttl_seconds)
        self._max_size = max_size
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0
        self.logger = get_logger(__name__)
        
        self.logger.info(f"DataCache initialized with TTL={default_ttl_seconds}s, max_size={max_size}")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        async with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._misses += 1
                self.logger.debug(f"Cache miss for key: {key}")
                return None
            
            # Check if expired
            if datetime.utcnow() > entry.expires_at:
                self.logger.debug(f"Cache entry expired for key: {key}")
                del self._cache[key]
                self._misses += 1
                return None
            
            # Update access statistics
            entry.hit_count += 1
            entry.last_accessed = datetime.utcnow()
            self._hits += 1
            
            self.logger.debug(f"Cache hit for key: {key}")
            return entry.value
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Optional custom TTL in seconds (uses default if not provided)
        """
        async with self._lock:
            # Check if we need to evict entries
            if len(self._cache) >= self._max_size and key not in self._cache:
                await self._evict_oldest()
            
            ttl = timedelta(seconds=ttl_seconds) if ttl_seconds else self._default_ttl
            now = datetime.utcnow()
            
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                expires_at=now + ttl
            )
            
            self._cache[key] = entry
            self.logger.debug(f"Cache set for key: {key}, TTL: {ttl.total_seconds()}s")
    
    async def delete(self, key: str) -> bool:
        """
        Delete a specific key from the cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False if key didn't exist
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self.logger.debug(f"Cache entry deleted: {key}")
                return True
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match (simple substring match)
            
        Returns:
            Number of entries invalidated
        """
        async with self._lock:
            keys_to_delete = [key for key in self._cache.keys() if pattern in key]
            
            for key in keys_to_delete:
                del self._cache[key]
            
            count = len(keys_to_delete)
            self.logger.info(f"Invalidated {count} cache entries matching pattern: {pattern}")
            return count
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self.logger.info(f"Cache cleared: {count} entries removed")
    
    async def cleanup_expired(self) -> int:
        """
        Remove all expired entries from the cache.
        
        Returns:
            Number of expired entries removed
        """
        async with self._lock:
            now = datetime.utcnow()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now > entry.expires_at
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            count = len(expired_keys)
            if count > 0:
                self.logger.info(f"Cleaned up {count} expired cache entries")
            return count
    
    async def get_stats(self) -> CacheStats:
        """
        Get cache statistics.
        
        Returns:
            CacheStats with performance metrics
        """
        async with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            # Calculate approximate size
            total_size = sum(
                len(str(entry.value).encode('utf-8'))
                for entry in self._cache.values()
            )
            
            # Find oldest and newest entries
            if self._cache:
                oldest = min(entry.created_at for entry in self._cache.values())
                newest = max(entry.created_at for entry in self._cache.values())
            else:
                oldest = None
                newest = None
            
            return CacheStats(
                total_entries=len(self._cache),
                total_hits=self._hits,
                total_misses=self._misses,
                hit_rate=round(hit_rate, 2),
                total_size_bytes=total_size,
                oldest_entry=oldest,
                newest_entry=newest
            )
    
    async def _evict_oldest(self) -> None:
        """Evict the oldest cache entry to make room for new entries."""
        if not self._cache:
            return
        
        # Find the oldest entry
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].created_at
        )
        
        del self._cache[oldest_key]
        self.logger.debug(f"Evicted oldest cache entry: {oldest_key}")
    
    def generate_key(self, *args, **kwargs) -> str:
        """
        Generate a cache key from arguments.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Generated cache key
        """
        # Create a deterministic string from arguments
        key_parts = [str(arg) for arg in args]
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key_string = ":".join(key_parts)
        
        # Hash for consistent length
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return key_hash



class CachedDatabaseHandler:
    """
    Wrapper for DatabaseHandler that adds caching capabilities.
    
    Automatically caches frequent database queries with configurable TTL.
    """
    
    def __init__(self, db_handler, cache: Optional[DataCache] = None):
        """
        Initialize the cached database handler.
        
        Args:
            db_handler: DatabaseHandler instance to wrap
            cache: Optional DataCache instance (creates new one if not provided)
        """
        self.db_handler = db_handler
        self.cache = cache or DataCache()
        self.logger = get_logger(__name__)
    
    async def get_articles_cached(
        self,
        filters,
        ttl_seconds: int = 300
    ):
        """
        Get articles with caching.
        
        Args:
            filters: ArticleFilters object
            ttl_seconds: Cache TTL in seconds
            
        Returns:
            List of articles
        """
        # Generate cache key from filters
        cache_key = self.cache.generate_key(
            "articles",
            source=filters.source,
            keywords=filters.keywords,
            start_date=filters.start_date,
            end_date=filters.end_date
        )
        
        # Try to get from cache
        cached_result = await self.cache.get(cache_key)
        if cached_result is not None:
            self.logger.debug("Returning cached articles")
            return cached_result
        
        # Cache miss - fetch from database
        self.logger.debug("Cache miss - fetching articles from database")
        articles = await self.db_handler.get_articles(filters)
        
        # Store in cache
        await self.cache.set(cache_key, articles, ttl_seconds)
        
        return articles
    
    async def get_sentiment_analyses_cached(
        self,
        date_range=None,
        ttl_seconds: int = 600
    ):
        """
        Get sentiment analyses with caching.
        
        Args:
            date_range: Optional DateRange object
            ttl_seconds: Cache TTL in seconds
            
        Returns:
            List of sentiment analyses
        """
        # Generate cache key
        cache_key = self.cache.generate_key(
            "sentiment",
            start=date_range.start_date if date_range else None,
            end=date_range.end_date if date_range else None
        )
        
        # Try to get from cache
        cached_result = await self.cache.get(cache_key)
        if cached_result is not None:
            self.logger.debug("Returning cached sentiment analyses")
            return cached_result
        
        # Cache miss - fetch from database
        self.logger.debug("Cache miss - fetching sentiment analyses from database")
        analyses = await self.db_handler.get_sentiment_analyses(date_range)
        
        # Store in cache
        await self.cache.set(cache_key, analyses, ttl_seconds)
        
        return analyses
    
    async def invalidate_articles_cache(self) -> int:
        """
        Invalidate all cached article queries.
        
        Returns:
            Number of cache entries invalidated
        """
        return await self.cache.invalidate_pattern("articles")
    
    async def invalidate_sentiment_cache(self) -> int:
        """
        Invalidate all cached sentiment analysis queries.
        
        Returns:
            Number of cache entries invalidated
        """
        return await self.cache.invalidate_pattern("sentiment")
    
    async def save_articles(self, articles):
        """
        Save articles and invalidate related cache entries.
        
        Args:
            articles: List of articles to save
        """
        # Save to database
        await self.db_handler.save_articles(articles)
        
        # Invalidate article cache since data changed
        await self.invalidate_articles_cache()
        self.logger.info("Articles saved and cache invalidated")
    
    async def save_sentiment_analysis(self, analysis):
        """
        Save sentiment analysis and invalidate related cache entries.
        
        Args:
            analysis: SentimentAnalysis object to save
        """
        # Save to database
        await self.db_handler.save_sentiment_analysis(analysis)
        
        # Invalidate sentiment cache since data changed
        await self.invalidate_sentiment_cache()
        self.logger.info("Sentiment analysis saved and cache invalidated")


class DataCacheFunction:
    """
    Azure Function for cache management operations.
    
    Provides HTTP endpoints for cache statistics, cleanup, and invalidation.
    """
    
    def __init__(self, cache: DataCache):
        """
        Initialize the cache function.
        
        Args:
            cache: DataCache instance to manage
        """
        self.cache = cache
        self.logger = get_logger(__name__)
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        stats = await self.cache.get_stats()
        
        return {
            'total_entries': stats.total_entries,
            'total_hits': stats.total_hits,
            'total_misses': stats.total_misses,
            'hit_rate_percent': stats.hit_rate,
            'total_size_bytes': stats.total_size_bytes,
            'oldest_entry': stats.oldest_entry.isoformat() if stats.oldest_entry else None,
            'newest_entry': stats.newest_entry.isoformat() if stats.newest_entry else None
        }
    
    async def cleanup_cache(self) -> Dict[str, Any]:
        """
        Clean up expired cache entries.
        
        Returns:
            Dictionary with cleanup results
        """
        expired_count = await self.cache.cleanup_expired()
        
        return {
            'expired_entries_removed': expired_count,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def clear_cache(self) -> Dict[str, Any]:
        """
        Clear all cache entries.
        
        Returns:
            Dictionary with clear results
        """
        stats_before = await self.cache.get_stats()
        await self.cache.clear()
        
        return {
            'entries_cleared': stats_before.total_entries,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def invalidate_pattern(self, pattern: str) -> Dict[str, Any]:
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match
            
        Returns:
            Dictionary with invalidation results
        """
        count = await self.cache.invalidate_pattern(pattern)
        
        return {
            'pattern': pattern,
            'entries_invalidated': count,
            'timestamp': datetime.utcnow().isoformat()
        }
