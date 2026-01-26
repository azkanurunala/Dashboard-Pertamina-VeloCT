"""
Core interfaces and abstract base classes for the Azure Functions news scraping system.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime

from .models import (
    NewsArticle, SentimentAnalysis, ScrapingConfig, CopilotConfig,
    DatabaseConfig, ExecutionResult, ArticleFilters, DateRange
)


class INewsScraperFunction(ABC):
    """
    Interface for news scraper functions.
    Defines the contract that all news scrapers must implement.
    """
    
    @abstractmethod
    async def scrape_news(self, 
                         keywords: List[str], 
                         start_date: datetime, 
                         end_date: datetime,
                         **kwargs) -> List[NewsArticle]:
        """
        Scrape news articles from the source.
        
        Args:
            keywords: List of keywords to search for
            start_date: Start date for article search
            end_date: End date for article search
            **kwargs: Additional scraper-specific parameters
            
        Returns:
            List of scraped news articles
            
        Raises:
            ScrapingError: If scraping fails
            RateLimitError: If rate limit is exceeded
        """
        pass
    
    @abstractmethod
    async def validate_article(self, article: NewsArticle) -> bool:
        """
        Validate a scraped article.
        
        Args:
            article: Article to validate
            
        Returns:
            True if article is valid, False otherwise
        """
        pass
    
    @abstractmethod
    async def handle_rate_limiting(self) -> None:
        """
        Handle rate limiting by implementing appropriate delays.
        """
        pass
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Get the name of the news source."""
        pass
    
    @property
    @abstractmethod
    def base_url(self) -> str:
        """Get the base URL of the news source."""
        pass


class IDatabaseHandler(ABC):
    """
    Interface for database operations.
    Defines the contract for SQL Server database interactions.
    """
    
    @abstractmethod
    async def save_articles(self, articles: List[NewsArticle]) -> None:
        """
        Save news articles to the database.
        
        Args:
            articles: List of articles to save
            
        Raises:
            DatabaseError: If save operation fails
        """
        pass
    
    @abstractmethod
    async def get_articles(self, filters: ArticleFilters) -> List[NewsArticle]:
        """
        Retrieve articles from the database based on filters.
        
        Args:
            filters: Filters to apply to the query
            
        Returns:
            List of matching articles
            
        Raises:
            DatabaseError: If query fails
        """
        pass
    
    @abstractmethod
    async def save_sentiment_analysis(self, analysis: SentimentAnalysis) -> None:
        """
        Save sentiment analysis results to the database.
        
        Args:
            analysis: Sentiment analysis to save
            
        Raises:
            DatabaseError: If save operation fails
        """
        pass
    
    @abstractmethod
    async def get_sentiment_analyses(self, 
                                   date_range: Optional[DateRange] = None) -> List[SentimentAnalysis]:
        """
        Retrieve sentiment analyses from the database.
        
        Args:
            date_range: Optional date range filter
            
        Returns:
            List of sentiment analyses
            
        Raises:
            DatabaseError: If query fails
        """
        pass
    
    @abstractmethod
    async def deduplicate_articles(self) -> int:
        """
        Remove duplicate articles based on URL.
        
        Returns:
            Number of duplicates removed
            
        Raises:
            DatabaseError: If deduplication fails
        """
        pass
    
    @abstractmethod
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a raw SQL query.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            Query results
            
        Raises:
            DatabaseError: If query execution fails
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check database connectivity and health.
        
        Returns:
            True if database is healthy, False otherwise
        """
        pass


class ICopilotIntegration(ABC):
    """
    Interface for Microsoft Copilot API integration.
    Defines the contract for AI-powered sentiment analysis and summarization.
    """
    
    @abstractmethod
    async def analyze_sentiment(self, articles: List[NewsArticle]) -> SentimentAnalysis:
        """
        Analyze sentiment of news articles using Copilot.
        
        Args:
            articles: List of articles to analyze
            
        Returns:
            Sentiment analysis results
            
        Raises:
            CopilotError: If analysis fails
            RateLimitError: If rate limit is exceeded
        """
        pass
    
    @abstractmethod
    async def generate_summary(self, 
                             articles: List[NewsArticle], 
                             role_prompt: str) -> str:
        """
        Generate a summary of articles using role-specific prompts.
        
        Args:
            articles: List of articles to summarize
            role_prompt: Role-specific prompt template
            
        Returns:
            Generated summary
            
        Raises:
            CopilotError: If summary generation fails
        """
        pass
    
    @abstractmethod
    async def batch_process(self, 
                          articles: List[NewsArticle], 
                          batch_size: Optional[int] = None) -> AsyncGenerator[SentimentAnalysis, None]:
        """
        Process articles in batches for large volumes.
        
        Args:
            articles: List of articles to process
            batch_size: Size of each batch (optional)
            
        Yields:
            Sentiment analysis results for each batch
            
        Raises:
            CopilotError: If batch processing fails
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check Copilot API connectivity and health.
        
        Returns:
            True if API is healthy, False otherwise
        """
        pass


class ISchedulerFunction(ABC):
    """
    Interface for scheduler functions.
    Defines the contract for timer-triggered Azure Functions.
    """
    
    @abstractmethod
    async def daily_morning_routine(self) -> ExecutionResult:
        """
        Execute the daily morning routine.
        
        Returns:
            Execution result
        """
        pass
    
    @abstractmethod
    async def daily_afternoon_routine(self) -> ExecutionResult:
        """
        Execute the daily afternoon routine.
        
        Returns:
            Execution result
        """
        pass
    
    @abstractmethod
    async def weekly_summary_routine(self) -> ExecutionResult:
        """
        Execute the weekly summary routine.
        
        Returns:
            Execution result
        """
        pass
    
    @abstractmethod
    async def monthly_aggregation_routine(self) -> ExecutionResult:
        """
        Execute the monthly aggregation routine.
        
        Returns:
            Execution result
        """
        pass


class IOrchestratorFunction(ABC):
    """
    Interface for orchestrator functions.
    Defines the contract for workflow orchestration.
    """
    
    @abstractmethod
    async def orchestrate_scraping(self, 
                                 sources: List[str], 
                                 keywords: List[str],
                                 date_range: DateRange) -> ExecutionResult:
        """
        Orchestrate scraping across multiple sources.
        
        Args:
            sources: List of news sources to scrape
            keywords: Keywords to search for
            date_range: Date range for scraping
            
        Returns:
            Orchestration execution result
        """
        pass
    
    @abstractmethod
    async def orchestrate_analysis(self, date_range: DateRange) -> ExecutionResult:
        """
        Orchestrate sentiment analysis for a date range.
        
        Args:
            date_range: Date range for analysis
            
        Returns:
            Analysis execution result
        """
        pass
    
    @abstractmethod
    async def orchestrate_full_pipeline(self, 
                                       sources: List[str], 
                                       keywords: List[str],
                                       date_range: DateRange) -> ExecutionResult:
        """
        Orchestrate the complete pipeline from scraping to analysis.
        
        Args:
            sources: List of news sources to scrape
            keywords: Keywords to search for
            date_range: Date range for processing
            
        Returns:
            Pipeline execution result
        """
        pass


class IConfigurationManager(ABC):
    """
    Interface for configuration management.
    Defines the contract for managing application configuration.
    """
    
    @abstractmethod
    async def get_scraping_config(self, source_name: str) -> ScrapingConfig:
        """
        Get scraping configuration for a specific source.
        
        Args:
            source_name: Name of the news source
            
        Returns:
            Scraping configuration
            
        Raises:
            ConfigurationError: If configuration not found
        """
        pass
    
    @abstractmethod
    async def get_copilot_config(self) -> CopilotConfig:
        """
        Get Copilot API configuration.
        
        Returns:
            Copilot configuration
            
        Raises:
            ConfigurationError: If configuration not found
        """
        pass
    
    @abstractmethod
    async def get_database_config(self) -> DatabaseConfig:
        """
        Get database configuration.
        
        Returns:
            Database configuration
            
        Raises:
            ConfigurationError: If configuration not found
        """
        pass
    
    @abstractmethod
    async def get_secret(self, secret_name: str) -> str:
        """
        Get a secret value from secure storage.
        
        Args:
            secret_name: Name of the secret
            
        Returns:
            Secret value
            
        Raises:
            ConfigurationError: If secret not found
        """
        pass
    
    @abstractmethod
    async def update_configuration(self, key: str, value: Any) -> None:
        """
        Update a configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
            
        Raises:
            ConfigurationError: If update fails
        """
        pass


class IDataProcessor(ABC):
    """
    Interface for data processing operations.
    Defines the contract for data aggregation and transformation.
    """
    
    @abstractmethod
    async def aggregate_articles(self, articles: List[NewsArticle]) -> Dict[str, Any]:
        """
        Aggregate articles by various dimensions.
        
        Args:
            articles: List of articles to aggregate
            
        Returns:
            Aggregation results
        """
        pass
    
    @abstractmethod
    async def standardize_data(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """
        Standardize article data format and content.
        
        Args:
            articles: List of articles to standardize
            
        Returns:
            Standardized articles
        """
        pass
    
    @abstractmethod
    async def clean_content(self, content: str) -> str:
        """
        Clean and normalize article content.
        
        Args:
            content: Raw article content
            
        Returns:
            Cleaned content
        """
        pass
    
    @abstractmethod
    async def extract_keywords(self, content: str) -> List[str]:
        """
        Extract keywords from article content.
        
        Args:
            content: Article content
            
        Returns:
            Extracted keywords
        """
        pass


class IBlobStorageManager(ABC):
    """
    Interface for Azure Blob Storage operations.
    Defines the contract for temporary file operations and large file handling.
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the blob service client and ensure containers exist.
        
        Raises:
            ConfigurationError: If initialization fails
        """
        pass
    
    @abstractmethod
    async def upload_temp_file(self, 
                              file_content: Any, 
                              filename: Optional[str] = None,
                              content_type: Optional[str] = None,
                              metadata: Optional[Dict[str, str]] = None) -> str:
        """
        Upload a temporary file to blob storage.
        
        Args:
            file_content: File content (string, bytes, or file-like object)
            filename: Optional filename (auto-generated if not provided)
            content_type: MIME type of the content
            metadata: Optional metadata dictionary
            
        Returns:
            Blob name/path of the uploaded file
            
        Raises:
            Exception: If upload fails
        """
        pass
    
    @abstractmethod
    async def upload_processing_file(self, 
                                   file_content: Any,
                                   filename: str,
                                   content_type: Optional[str] = None,
                                   metadata: Optional[Dict[str, str]] = None) -> str:
        """
        Upload a file for processing operations.
        
        Args:
            file_content: File content
            filename: Filename
            content_type: MIME type of the content
            metadata: Optional metadata dictionary
            
        Returns:
            Blob name/path of the uploaded file
        """
        pass
    
    @abstractmethod
    async def download_file(self, blob_name: str, container_name: Optional[str] = None) -> bytes:
        """
        Download a file from blob storage.
        
        Args:
            blob_name: Name/path of the blob
            container_name: Container name (defaults to temp_container)
            
        Returns:
            File content as bytes
            
        Raises:
            ResourceNotFoundError: If file not found
        """
        pass
    
    @abstractmethod
    async def stream_download(self, 
                            blob_name: str, 
                            container_name: Optional[str] = None,
                            chunk_size: int = 8192) -> AsyncGenerator[bytes, None]:
        """
        Stream download a large file from blob storage.
        
        Args:
            blob_name: Name/path of the blob
            container_name: Container name (defaults to temp_container)
            chunk_size: Size of each chunk in bytes
            
        Yields:
            File content chunks as bytes
        """
        pass
    
    @abstractmethod
    async def stream_upload(self, 
                          data_stream: AsyncGenerator[bytes, None],
                          blob_name: str,
                          container_name: Optional[str] = None,
                          content_type: Optional[str] = None,
                          metadata: Optional[Dict[str, str]] = None) -> str:
        """
        Stream upload large file content to blob storage.
        
        Args:
            data_stream: Async generator yielding file chunks
            blob_name: Name/path for the blob
            container_name: Container name (defaults to processing_container)
            content_type: MIME type of the content
            metadata: Optional metadata dictionary
            
        Returns:
            Blob name/path of the uploaded file
        """
        pass
    
    @abstractmethod
    async def delete_file(self, blob_name: str, container_name: Optional[str] = None) -> bool:
        """
        Delete a file from blob storage.
        
        Args:
            blob_name: Name/path of the blob to delete
            container_name: Container name (defaults to temp_container)
            
        Returns:
            True if deleted successfully, False if file didn't exist
        """
        pass
    
    @abstractmethod
    async def cleanup_expired_files(self, container_name: Optional[str] = None) -> ExecutionResult:
        """
        Clean up expired temporary and processing files.
        
        Args:
            container_name: Container to clean (defaults to all containers)
            
        Returns:
            Execution result with cleanup statistics
        """
        pass
    
    @abstractmethod
    async def archive_file(self, blob_name: str, container_name: Optional[str] = None) -> bool:
        """
        Archive a file by moving it to the archive container.
        
        Args:
            blob_name: Name/path of the blob to archive
            container_name: Source container (defaults to temp_container)
            
        Returns:
            True if archival was successful
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the blob service client and clean up resources."""
        pass


# Custom exceptions for the interfaces
class ScrapingError(Exception):
    """Exception raised when scraping operations fail."""
    pass


class DatabaseError(Exception):
    """Exception raised when database operations fail."""
    pass


class CopilotError(Exception):
    """Exception raised when Copilot API operations fail."""
    pass


class RateLimitError(Exception):
    """Exception raised when rate limits are exceeded."""
    pass


class ConfigurationError(Exception):
    """Exception raised when configuration operations fail."""
    pass


class ProcessingError(Exception):
    """Exception raised when data processing operations fail."""
    pass