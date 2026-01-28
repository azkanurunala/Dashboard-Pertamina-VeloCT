"""
Utility functions for Azure Functions news scraping system.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
import json
import hashlib
from functools import wraps
import time

T = TypeVar('T')


def generate_execution_id() -> str:
    """Generate a unique execution ID for function runs."""
    return str(uuid.uuid4())


def generate_correlation_id() -> str:
    """Generate a correlation ID for tracking across functions."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def parse_date_parameter(date_str: str) -> datetime:
    """
    Parse a date string parameter into a datetime object.
    
    Args:
        date_str: Date string in YYYY-MM-DD format or ISO format
        
    Returns:
        Parsed datetime object
        
    Raises:
        ValueError: If date string is invalid or in wrong format
    """
    if not date_str:
        raise ValueError("Date string cannot be empty")
    
    # Try YYYY-MM-DD format first
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d")
    except ValueError:
        pass
    
    # Try ISO format
    try:
        return datetime.fromisoformat(date_str.strip().replace('Z', '+00:00'))
    except ValueError:
        pass
    
    # Try common alternative formats
    for fmt in ["%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%m-%d-%Y", "%m/%d/%Y"]:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD format.")


def validate_keywords(keywords_param: str) -> List[str]:
    """
    Validate and parse keywords parameter.
    
    Args:
        keywords_param: Comma-separated string of keywords
        
    Returns:
        List of validated keyword strings
        
    Raises:
        ValueError: If keywords are invalid or empty
    """
    if not keywords_param:
        raise ValueError("Keywords parameter cannot be empty")
    
    # Split by comma and clean each keyword
    keywords = [kw.strip() for kw in keywords_param.split(',')]
    
    # Filter out empty keywords
    keywords = [kw for kw in keywords if kw]
    
    if not keywords:
        raise ValueError("At least one valid keyword is required")
    
    # Validate each keyword
    for kw in keywords:
        if len(kw) < 2:
            raise ValueError(f"Keyword '{kw}' is too short (minimum 2 characters)")
        if len(kw) > 100:
            raise ValueError(f"Keyword '{kw}' is too long (maximum 100 characters)")
    
    return keywords


def safe_json_serialize(obj: Any) -> str:
    """
    Safely serialize an object to JSON, handling datetime and other non-serializable types.
    
    Args:
        obj: Object to serialize
        
    Returns:
        JSON string representation
    """
    def json_serializer(o):
        if isinstance(o, datetime):
            return o.isoformat()
        elif hasattr(o, '__dict__'):
            return o.__dict__
        elif hasattr(o, 'to_dict'):
            return o.to_dict()
        else:
            return str(o)
    
    return json.dumps(obj, default=json_serializer, ensure_ascii=False, indent=2)


def safe_json_deserialize(json_str: str, default: Any = None) -> Any:
    """
    Safely deserialize JSON string, returning default on error.
    
    Args:
        json_str: JSON string to deserialize
        default: Default value to return on error
        
    Returns:
        Deserialized object or default value
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def calculate_hash(content: str) -> str:
    """
    Calculate SHA-256 hash of content for deduplication.
    
    Args:
        content: Content to hash
        
    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def normalize_url(url: str) -> str:
    """
    Normalize URL for consistent comparison and deduplication.
    
    Args:
        url: URL to normalize
        
    Returns:
        Normalized URL
    """
    # Remove common tracking parameters and fragments
    url = url.split('#')[0]  # Remove fragment
    url = url.split('?')[0]  # Remove query parameters for now (could be more sophisticated)
    
    # Ensure consistent protocol
    if url.startswith('http://'):
        url = url.replace('http://', 'https://', 1)
    
    # Remove trailing slash
    if url.endswith('/'):
        url = url[:-1]
    
    return url.lower()


def clean_text(text: str) -> str:
    """
    Clean and normalize text content.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove common HTML entities that might have been missed
    html_entities = {
        '&nbsp;': ' ',
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
        '&hellip;': '...',
        '&mdash;': '—',
        '&ndash;': '–'
    }
    
    for entity, replacement in html_entities.items():
        text = text.replace(entity, replacement)
    
    return text.strip()


def retry_async(max_attempts: int = 3, 
                delay: float = 1.0, 
                backoff: float = 2.0,
                exceptions: tuple = (Exception,)):
    """
    Decorator for async functions to implement retry logic with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for delay
        exceptions: Tuple of exceptions to catch and retry on
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        break
                    
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        
        return wrapper
    return decorator


def rate_limit(calls_per_second: float):
    """
    Decorator to rate limit function calls.
    
    Args:
        calls_per_second: Maximum number of calls per second
    """
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            
            if left_to_wait > 0:
                await asyncio.sleep(left_to_wait)
            
            last_called[0] = time.time()
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def batch_items(items: List[T], batch_size: int) -> List[List[T]]:
    """
    Split a list into batches of specified size.
    
    Args:
        items: List of items to batch
        batch_size: Size of each batch
        
    Returns:
        List of batches
    """
    if batch_size <= 0:
        raise ValueError("Batch size must be positive")
    
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge multiple dictionaries, with later dictionaries taking precedence.
    
    Args:
        *dicts: Dictionaries to merge
        
    Returns:
        Merged dictionary
    """
    result = {}
    for d in dicts:
        if d:
            result.update(d)
    return result


def validate_date_range(start_date: datetime, end_date: datetime) -> None:
    """
    Validate that a date range is valid.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Raises:
        ValueError: If date range is invalid
    """
    if start_date >= end_date:
        raise ValueError("Start date must be before end date")
    
    if end_date > utc_now():
        raise ValueError("End date cannot be in the future")


def format_duration(duration_ms: int) -> str:
    """
    Format duration in milliseconds to human-readable string.
    
    Args:
        duration_ms: Duration in milliseconds
        
    Returns:
        Formatted duration string
    """
    if duration_ms < 1000:
        return f"{duration_ms}ms"
    elif duration_ms < 60000:
        return f"{duration_ms / 1000:.1f}s"
    elif duration_ms < 3600000:
        return f"{duration_ms / 60000:.1f}m"
    else:
        return f"{duration_ms / 3600000:.1f}h"


def extract_domain(url: str) -> str:
    """
    Extract domain from URL.
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Domain name
    """
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return ""


def is_valid_url(url: str) -> bool:
    """
    Check if a URL is valid.
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL is valid, False otherwise
    """
    try:
        from urllib.parse import urlparse
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with optional suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters.
    
    Args:
        filename: Filename to sanitize
        
    Returns:
        Sanitized filename
    """
    import re
    # Remove invalid characters for Windows/Unix filesystems
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove control characters
    sanitized = re.sub(r'[\x00-\x1f\x7f]', '', sanitized)
    # Limit length
    return truncate_text(sanitized, 255)


class CircuitBreaker:
    """
    Circuit breaker implementation for handling external service failures.
    """
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: float = 60.0,
                 expected_exception: type = Exception):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open
    
    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Call function through circuit breaker.
        
        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == 'open':
            if self._should_attempt_reset():
                self.state = 'half-open'
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (time.time() - self.last_failure_time) >= self.recovery_timeout
    
    def _on_success(self) -> None:
        """Handle successful call."""
        self.failure_count = 0
        self.state = 'closed'
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'open'


async def create_blob_storage_manager(connection_string: Optional[str] = None, 
                                    account_url: Optional[str] = None) -> 'BlobStorageManager':
    """
    Factory function to create and initialize a BlobStorageManager instance.
    
    Args:
        connection_string: Azure Storage connection string
        account_url: Azure Storage account URL (for managed identity auth)
        
    Returns:
        Initialized BlobStorageManager instance
        
    Raises:
        ConfigurationError: If initialization fails
    """
    from .blob_storage import BlobStorageManager
    
    manager = BlobStorageManager(connection_string=connection_string, account_url=account_url)
    await manager.initialize()
    return manager