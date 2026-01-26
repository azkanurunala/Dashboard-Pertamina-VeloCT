"""
Custom exceptions for news scraping operations.
"""


class ScrapingError(Exception):
    """Base exception for scraping operations."""
    
    def __init__(self, message: str, source: str = None, url: str = None):
        super().__init__(message)
        self.source = source
        self.url = url
        self.message = message

    def __str__(self):
        parts = [self.message]
        if self.source:
            parts.append(f"Source: {self.source}")
        if self.url:
            parts.append(f"URL: {self.url}")
        return " | ".join(parts)


class RateLimitError(ScrapingError):
    """Exception raised when rate limits are exceeded."""
    
    def __init__(self, message: str, retry_after: int = None, source: str = None):
        super().__init__(message, source)
        self.retry_after = retry_after

    def __str__(self):
        base = super().__str__()
        if self.retry_after:
            return f"{base} | Retry after: {self.retry_after}s"
        return base


class ValidationError(ScrapingError):
    """Exception raised when article validation fails."""
    
    def __init__(self, message: str, field: str = None, value: str = None):
        super().__init__(message)
        self.field = field
        self.value = value

    def __str__(self):
        parts = [self.message]
        if self.field:
            parts.append(f"Field: {self.field}")
        if self.value:
            parts.append(f"Value: {self.value}")
        return " | ".join(parts)


class NetworkError(ScrapingError):
    """Exception raised for network-related errors."""
    
    def __init__(self, message: str, status_code: int = None, source: str = None, url: str = None):
        super().__init__(message, source, url)
        self.status_code = status_code

    def __str__(self):
        base = super().__str__()
        if self.status_code:
            return f"{base} | Status: {self.status_code}"
        return base


class ContentExtractionError(ScrapingError):
    """Exception raised when content extraction fails."""
    
    def __init__(self, message: str, selector: str = None, source: str = None, url: str = None):
        super().__init__(message, source, url)
        self.selector = selector

    def __str__(self):
        base = super().__str__()
        if self.selector:
            return f"{base} | Selector: {self.selector}"
        return base