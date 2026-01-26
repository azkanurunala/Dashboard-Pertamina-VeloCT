"""
Core data models and interfaces for the Azure Functions news scraping system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid


class SentimentLabel(Enum):
    """Enumeration for sentiment analysis labels."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class FunctionStatus(Enum):
    """Enumeration for function execution status."""
    SUCCESS = "success"
    FAILED = "failed"
    RUNNING = "running"
    QUEUED = "queued"


@dataclass
class NewsArticle:
    """
    Data model for news articles.
    Represents a single news article with all required metadata.
    """
    title: str
    content: str
    url: str
    source: str
    published_date: datetime
    scraped_date: datetime = field(default_factory=datetime.utcnow)
    keywords: List[str] = field(default_factory=list)
    language: str = "en"
    author: Optional[str] = None
    category: Optional[str] = None
    id: Optional[str] = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        """Validate article data after initialization."""
        if not self.title.strip():
            raise ValueError("Article title cannot be empty")
        if not self.content.strip():
            raise ValueError("Article content cannot be empty")
        if not self.url.strip():
            raise ValueError("Article URL cannot be empty")
        if not self.source.strip():
            raise ValueError("Article source cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Convert article to dictionary format."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "source": self.source,
            "published_date": self.published_date.isoformat(),
            "scraped_date": self.scraped_date.isoformat(),
            "keywords": self.keywords,
            "language": self.language,
            "author": self.author,
            "category": self.category
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NewsArticle':
        """Create article from dictionary format."""
        return cls(
            id=data.get("id"),
            title=data["title"],
            content=data["content"],
            url=data["url"],
            source=data["source"],
            published_date=datetime.fromisoformat(data["published_date"]),
            scraped_date=datetime.fromisoformat(data.get("scraped_date", datetime.utcnow().isoformat())),
            keywords=data.get("keywords", []),
            language=data.get("language", "en"),
            author=data.get("author"),
            category=data.get("category")
        )


@dataclass
class SentimentAnalysis:
    """
    Data model for sentiment analysis results.
    Represents the output of sentiment analysis on one or more articles.
    """
    sentiment_score: float
    sentiment_label: SentimentLabel
    confidence: float
    summary: str
    analysis_date: datetime = field(default_factory=datetime.utcnow)
    model_version: str = "copilot-1.0"
    role_context: Optional[str] = None
    article_ids: List[str] = field(default_factory=list)
    id: Optional[str] = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        """Validate sentiment analysis data after initialization."""
        if not -1.0 <= self.sentiment_score <= 1.0:
            raise ValueError("Sentiment score must be between -1.0 and 1.0")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if not self.summary.strip():
            raise ValueError("Summary cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Convert sentiment analysis to dictionary format."""
        return {
            "id": self.id,
            "sentiment_score": self.sentiment_score,
            "sentiment_label": self.sentiment_label.value,
            "confidence": self.confidence,
            "summary": self.summary,
            "analysis_date": self.analysis_date.isoformat(),
            "model_version": self.model_version,
            "role_context": self.role_context,
            "article_ids": self.article_ids
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SentimentAnalysis':
        """Create sentiment analysis from dictionary format."""
        return cls(
            id=data.get("id"),
            sentiment_score=data["sentiment_score"],
            sentiment_label=SentimentLabel(data["sentiment_label"]),
            confidence=data["confidence"],
            summary=data["summary"],
            analysis_date=datetime.fromisoformat(data["analysis_date"]),
            model_version=data.get("model_version", "copilot-1.0"),
            role_context=data.get("role_context"),
            article_ids=data.get("article_ids", [])
        )


@dataclass
class ScrapingConfig:
    """
    Configuration model for news scraping operations.
    """
    source_name: str
    base_url: str
    selectors: Dict[str, str]
    rate_limit_delay: int = 1
    max_retries: int = 3
    timeout: int = 30
    headers: Dict[str, str] = field(default_factory=dict)
    use_selenium: bool = False

    def __post_init__(self):
        """Validate scraping configuration after initialization."""
        if not self.source_name.strip():
            raise ValueError("Source name cannot be empty")
        if not self.base_url.strip():
            raise ValueError("Base URL cannot be empty")
        if self.rate_limit_delay < 0:
            raise ValueError("Rate limit delay must be non-negative")
        if self.max_retries < 0:
            raise ValueError("Max retries must be non-negative")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")


@dataclass
class CopilotConfig:
    """
    Configuration model for Microsoft Copilot API integration.
    """
    api_endpoint: str
    model_name: str = "gpt-4"
    max_tokens: int = 4000
    temperature: float = 0.3
    role_prompts: Dict[str, str] = field(default_factory=dict)
    rate_limit_requests_per_minute: int = 60
    batch_size: int = 10

    def __post_init__(self):
        """Validate Copilot configuration after initialization."""
        if not self.api_endpoint.strip():
            raise ValueError("API endpoint cannot be empty")
        if not self.model_name.strip():
            raise ValueError("Model name cannot be empty")
        if self.max_tokens <= 0:
            raise ValueError("Max tokens must be positive")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        if self.rate_limit_requests_per_minute <= 0:
            raise ValueError("Rate limit must be positive")
        if self.batch_size <= 0:
            raise ValueError("Batch size must be positive")


@dataclass
class DatabaseConfig:
    """
    Configuration model for SQL Server database operations.
    """
    connection_string: str
    connection_pool_size: int = 10
    connection_timeout: int = 30
    command_timeout: int = 60
    retry_attempts: int = 3
    retry_delay: int = 1

    def __post_init__(self):
        """Validate database configuration after initialization."""
        if not self.connection_string.strip():
            raise ValueError("Connection string cannot be empty")
        if self.connection_pool_size <= 0:
            raise ValueError("Connection pool size must be positive")
        if self.connection_timeout <= 0:
            raise ValueError("Connection timeout must be positive")
        if self.command_timeout <= 0:
            raise ValueError("Command timeout must be positive")
        if self.retry_attempts < 0:
            raise ValueError("Retry attempts must be non-negative")
        if self.retry_delay < 0:
            raise ValueError("Retry delay must be non-negative")


@dataclass
class ExecutionResult:
    """
    Model for function execution results.
    """
    function_name: str
    execution_id: str
    status: FunctionStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    input_parameters: Optional[Dict[str, Any]] = None
    output_summary: Optional[Dict[str, Any]] = None
    duration_ms: Optional[int] = None

    def __post_init__(self):
        """Calculate duration if end_time is provided."""
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            self.duration_ms = int(delta.total_seconds() * 1000)

    def to_dict(self) -> Dict[str, Any]:
        """Convert execution result to dictionary format."""
        return {
            "function_name": self.function_name,
            "execution_id": self.execution_id,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "error_message": self.error_message,
            "input_parameters": self.input_parameters,
            "output_summary": self.output_summary,
            "duration_ms": self.duration_ms
        }


@dataclass
class ArticleFilters:
    """
    Model for filtering articles in database queries.
    """
    source: Optional[str] = None
    keywords: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    language: Optional[str] = None
    category: Optional[str] = None
    limit: Optional[int] = None
    offset: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert filters to dictionary format."""
        return {
            "source": self.source,
            "keywords": self.keywords,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "language": self.language,
            "category": self.category,
            "limit": self.limit,
            "offset": self.offset
        }


@dataclass
class DateRange:
    """
    Model for date range specifications.
    """
    start_date: datetime
    end_date: datetime

    def __post_init__(self):
        """Validate date range after initialization."""
        if self.start_date >= self.end_date:
            raise ValueError("Start date must be before end date")

    def to_dict(self) -> Dict[str, Any]:
        """Convert date range to dictionary format."""
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DateRange':
        """Create date range from dictionary format."""
        return cls(
            start_date=datetime.fromisoformat(data["start_date"]),
            end_date=datetime.fromisoformat(data["end_date"])
        )