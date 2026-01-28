"""
Azure Functions Comprehensive Logging Module

This module provides structured logging for Azure Functions with automatic
context enrichment, sanitization, and Azure integration.
"""

import json
import logging
import traceback
import uuid
import re
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


@dataclass
class ExecutionContext:
    """
    Execution context for a function invocation.
    Contains all metadata needed for log correlation and filtering.
    """
    function_name: str
    execution_id: str
    correlation_id: str
    start_time: datetime
    custom_dimensions: Dict[str, Any] = field(default_factory=dict)
    parent_execution_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for logging."""
        return {
            "function_name": self.function_name,
            "execution_id": self.execution_id,
            "correlation_id": self.correlation_id,
            "start_time": self.start_time.isoformat(),
            "parent_execution_id": self.parent_execution_id,
            **self.custom_dimensions
        }
    
    def add_dimension(self, key: str, value: Any) -> None:
        """Add custom dimension to context."""
        self.custom_dimensions[key] = value


class LogSanitizer:
    """
    Sanitizes sensitive information from log entries.
    Prevents credentials, tokens, and PII from appearing in logs.
    """
    
    # Sensitive field patterns
    SENSITIVE_PATTERNS = [
        r'password',
        r'pwd',
        r'secret',
        r'token',
        r'api[_-]?key',
        r'access[_-]?key',
        r'auth',
        r'credential'
    ]
    
    # URL parameter patterns to redact
    URL_SENSITIVE_PARAMS = ['api_key', 'token', 'password', 'secret', 'auth']
    
    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively sanitize dictionary, redacting sensitive fields.
        
        Args:
            data: Dictionary to sanitize
            
        Returns:
            Sanitized dictionary with sensitive values redacted
        """
        if not isinstance(data, dict):
            return data
            
        sanitized = {}
        for key, value in data.items():
            if self._is_sensitive_field(key):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self.sanitize_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized
    
    def sanitize_connection_string(self, conn_str: str) -> str:
        """Sanitize database connection string."""
        if not conn_str:
            return conn_str
        # Redact password from connection string
        return re.sub(
            r'(Password|PWD)=([^;]+)',
            r'\1=***REDACTED***',
            conn_str,
            flags=re.IGNORECASE
        )
    
    def sanitize_url(self, url: str) -> str:
        """Sanitize URL by redacting sensitive query parameters."""
        if not url:
            return url
        try:
            parsed = urlparse(url)
            if parsed.query:
                params = parse_qs(parsed.query)
                sanitized_params = {
                    k: '***REDACTED***' if k.lower() in self.URL_SENSITIVE_PARAMS else v
                    for k, v in params.items()
                }
                sanitized_query = urlencode(sanitized_params, doseq=True)
                return urlunparse(parsed._replace(query=sanitized_query))
            return url
        except Exception:
            return url
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """Check if field name matches sensitive patterns."""
        field_lower = field_name.lower()
        return any(
            re.search(pattern, field_lower)
            for pattern in self.SENSITIVE_PATTERNS
        )


class AzureLogFormatter:
    """
    Formats log entries for Azure Log Stream and Application Insights.
    Ensures consistent structure and proper Azure integration.
    """
    
    def __init__(self, sanitizer: LogSanitizer):
        self.sanitizer = sanitizer
    
    def format_structured_log(
        self,
        level: str,
        message: str,
        context: ExecutionContext,
        data: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None
    ) -> str:
        """
        Format a structured log entry.
        
        Returns JSON string with all required fields for Azure.
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "message": message,
            "function_name": context.function_name,
            "execution_id": context.execution_id,
            "correlation_id": context.correlation_id,
        }
        
        # Add custom dimensions
        if context.custom_dimensions:
            log_entry["custom_dimensions"] = context.custom_dimensions
        
        # Add additional data (sanitized)
        if data:
            log_entry["data"] = self.sanitizer.sanitize_dict(data)
        
        # Add exception details
        if exception:
            log_entry["exception"] = {
                "type": type(exception).__name__,
                "message": str(exception),
                "stack_trace": traceback.format_exc()
            }
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)
    
    def format_metric_log(
        self,
        metric_name: str,
        value: float,
        context: ExecutionContext,
        dimensions: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format a metric log entry for Application Insights."""
        metric_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metric_name": metric_name,
            "value": value,
            "function_name": context.function_name,
            "execution_id": context.execution_id,
            "correlation_id": context.correlation_id,
        }
        
        if dimensions:
            metric_entry["dimensions"] = self.sanitizer.sanitize_dict(dimensions)
        
        return json.dumps(metric_entry, default=str, ensure_ascii=False)


class AzureLoggingManager:
    """
    Central logging manager for Azure Functions.
    Provides structured logging with automatic context enrichment.
    """
    
    def __init__(self, function_name: str, correlation_id: Optional[str] = None):
        """
        Initialize logging manager for a function execution.
        
        Args:
            function_name: Name of the Azure Function
            correlation_id: Optional correlation ID for cross-function tracing
        """
        self.function_name = function_name
        self.execution_id = self._generate_execution_id()
        self.correlation_id = correlation_id or self.execution_id
        self.start_time = datetime.utcnow()
        
        # Initialize components
        self.sanitizer = LogSanitizer()
        self.formatter = AzureLogFormatter(self.sanitizer)
        self.logger = self._setup_logger()
        
        # Create execution context
        self.context = ExecutionContext(
            function_name=function_name,
            execution_id=self.execution_id,
            correlation_id=self.correlation_id,
            start_time=self.start_time
        )
        
        # Track operations
        self.operations = {}
    
    def _generate_execution_id(self) -> str:
        """Generate unique execution ID."""
        return str(uuid.uuid4())
    
    def _setup_logger(self) -> logging.Logger:
        """Setup Python logger for Azure Functions."""
        logger = logging.getLogger(self.function_name)
        logger.setLevel(logging.INFO)
        
        # Ensure we have a handler
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            logger.addHandler(handler)
        
        return logger
    
    def _log(self, level: str, message: str, data: Optional[Dict[str, Any]] = None, 
             exception: Optional[Exception] = None) -> None:
        """Internal logging method."""
        formatted_log = self.formatter.format_structured_log(
            level=level,
            message=message,
            context=self.context,
            data=data,
            exception=exception
        )
        
        # Map to Python logging levels
        log_method = {
            "DEBUG": self.logger.debug,
            "INFO": self.logger.info,
            "WARNING": self.logger.warning,
            "ERROR": self.logger.error,
            "CRITICAL": self.logger.critical
        }.get(level, self.logger.info)
        
        log_method(formatted_log)
    
    # Function Lifecycle Logging
    
    def log_function_start(self, trigger_type: str, parameters: Dict[str, Any]) -> None:
        """Log function execution start with trigger and parameters."""
        self.context.add_dimension("trigger_type", trigger_type)
        self._log(
            "INFO",
            f"🚀 FUNCTION_START: {self.function_name}",
            data={
                "trigger_type": trigger_type,
                "parameters": parameters,
                "execution_id": self.execution_id,
                "correlation_id": self.correlation_id
            }
        )
    
    def log_function_end(self, status: str, result_summary: Dict[str, Any]) -> None:
        """Log function execution completion with results."""
        duration_ms = (datetime.utcnow() - self.start_time).total_seconds() * 1000
        self._log(
            "INFO" if status == "success" else "ERROR",
            f"✅ FUNCTION_END: {self.function_name} - {status.upper()}",
            data={
                "status": status,
                "duration_ms": duration_ms,
                "result_summary": result_summary
            }
        )
    
    def log_operation_start(self, operation_name: str, details: Dict[str, Any]) -> str:
        """Log start of a major operation, returns operation_id for tracking."""
        operation_id = str(uuid.uuid4())
        self.operations[operation_id] = {
            "name": operation_name,
            "start_time": datetime.utcnow(),
            "details": details
        }
        
        self._log(
            "INFO",
            f"▶️ OPERATION_START: {operation_name}",
            data={
                "operation_id": operation_id,
                "operation_name": operation_name,
                **details
            }
        )
        return operation_id
    
    def log_operation_end(self, operation_id: str, status: str, metrics: Dict[str, Any]) -> None:
        """Log completion of a major operation with metrics."""
        if operation_id in self.operations:
            operation = self.operations[operation_id]
            duration_ms = (datetime.utcnow() - operation["start_time"]).total_seconds() * 1000
            
            self._log(
                "INFO" if status == "success" else "ERROR",
                f"⏹️ OPERATION_END: {operation['name']} - {status.upper()}",
                data={
                    "operation_id": operation_id,
                    "operation_name": operation["name"],
                    "status": status,
                    "duration_ms": duration_ms,
                    "metrics": metrics
                }
            )
            
            del self.operations[operation_id]
    
    def log_error(self, error: Exception, context_data: Dict[str, Any]) -> None:
        """Log error with full context and stack trace."""
        self._log(
            "ERROR",
            f"❌ ERROR: {type(error).__name__} - {str(error)}",
            data=context_data,
            exception=error
        )
    
    # Scraper-Specific Logging
    
    def log_scraping_start(self, source: str, keywords: List[str], date_range: Dict) -> None:
        """Log scraping operation start."""
        self.context.add_dimension("source", source)
        self._log(
            "INFO",
            f"🔍 SCRAPING_START: {source}",
            data={
                "source": source,
                "keywords": keywords,
                "date_range": date_range
            }
        )
    
    def log_scraping_page_fetch(self, url: str, status_code: int, response_time_ms: float) -> None:
        """Log individual page fetch during scraping."""
        sanitized_url = self.sanitizer.sanitize_url(url)
        self._log(
            "DEBUG",
            f"📄 PAGE_FETCH: {status_code}",
            data={
                "url": sanitized_url,
                "status_code": status_code,
                "response_time_ms": response_time_ms
            }
        )
    
    def log_scraping_articles_found(self, count: int, parsing_success_rate: float) -> None:
        """Log articles found and parsing success rate."""
        self._log(
            "INFO",
            f"📰 ARTICLES_FOUND: {count} articles",
            data={
                "articles_count": count,
                "parsing_success_rate": parsing_success_rate
            }
        )
    
    def log_scraping_articles_parsed(self, parsed_count: int, failed_count: int, 
                                     parsing_errors: List[str]) -> None:
        """Log article parsing results."""
        self._log(
            "INFO",
            f"📝 ARTICLES_PARSED: {parsed_count} success, {failed_count} failed",
            data={
                "parsed_count": parsed_count,
                "failed_count": failed_count,
                "parsing_errors": parsing_errors[:5]  # Limit to first 5 errors
            }
        )
    
    def log_scraping_articles_saved(self, saved_count: int, duplicate_count: int, 
                                    duration_ms: float) -> None:
        """Log articles saved to database."""
        self._log(
            "INFO",
            f"💾 ARTICLES_SAVED: {saved_count} saved, {duplicate_count} duplicates",
            data={
                "saved_count": saved_count,
                "duplicate_count": duplicate_count,
                "duration_ms": duration_ms
            }
        )
    
    def log_scraping_end(self, articles_scraped: int, articles_saved: int, 
                        duration_ms: float) -> None:
        """Log scraping operation completion."""
        self._log(
            "INFO",
            f"✅ SCRAPING_END: {articles_scraped} scraped, {articles_saved} saved",
            data={
                "articles_scraped": articles_scraped,
                "articles_saved": articles_saved,
                "duration_ms": duration_ms,
                "throughput_articles_per_second": articles_scraped / (duration_ms / 1000) if duration_ms > 0 else 0
            }
        )
    
    # Database Operation Logging
    
    def log_database_connection(self, connection_time_ms: float, success: bool) -> None:
        """Log database connection attempt."""
        self._log(
            "INFO" if success else "ERROR",
            f"🔌 DB_CONNECTION: {'SUCCESS' if success else 'FAILED'}",
            data={
                "connection_time_ms": connection_time_ms,
                "success": success
            }
        )
    
    def log_database_operation(self, operation: str, table: str, row_count: int, 
                              duration_ms: float) -> None:
        """Log database operation with metrics."""
        self._log(
            "INFO",
            f"💽 DB_OPERATION: {operation} on {table}",
            data={
                "operation": operation,
                "table": table,
                "row_count": row_count,
                "duration_ms": duration_ms
            }
        )
    
    def log_database_error(self, error: Exception, query_type: str, table: str) -> None:
        """Log database error with context."""
        self._log(
            "ERROR",
            f"❌ DB_ERROR: {query_type} on {table}",
            data={
                "query_type": query_type,
                "table": table
            },
            exception=error
        )
    
    def log_database_transaction(self, transaction_id: str, operation_count: int, 
                                 status: str) -> None:
        """Log database transaction."""
        self._log(
            "INFO",
            f"🔄 DB_TRANSACTION: {status}",
            data={
                "transaction_id": transaction_id,
                "operation_count": operation_count,
                "status": status
            }
        )
    
    # Scheduler Logging
    
    def log_scheduler_trigger(self, schedule_name: str, trigger_time: datetime, 
                             workflow_params: Dict) -> None:
        """Log scheduler function trigger."""
        self.context.add_dimension("schedule_name", schedule_name)
        self._log(
            "INFO",
            f"⏰ SCHEDULER_TRIGGER: {schedule_name}",
            data={
                "schedule_name": schedule_name,
                "trigger_time": trigger_time.isoformat(),
                "workflow_params": workflow_params
            }
        )
    
    def log_scheduler_orchestration(self, scrapers: List[str], parallel_count: int) -> None:
        """Log scheduler orchestration details."""
        self._log(
            "INFO",
            f"🎭 SCHEDULER_ORCHESTRATION: {len(scrapers)} scrapers, {parallel_count} parallel",
            data={
                "scrapers": scrapers,
                "parallel_count": parallel_count,
                "total_scrapers": len(scrapers)
            }
        )
    
    def log_scheduler_wait(self, pending_scrapers: List[str], completed_scrapers: List[str], 
                          timeout_seconds: int) -> None:
        """Log scheduler waiting for scraper completion."""
        self._log(
            "INFO",
            f"⏳ SCHEDULER_WAIT: {len(completed_scrapers)}/{len(pending_scrapers) + len(completed_scrapers)} complete",
            data={
                "pending_scrapers": pending_scrapers,
                "completed_scrapers": completed_scrapers,
                "timeout_seconds": timeout_seconds
            }
        )
    
    def log_scheduler_aggregation(self, total_articles: int, success_rate: float, 
                                  metrics: Dict[str, Any]) -> None:
        """Log scheduler aggregation results."""
        self._log(
            "INFO",
            f"📊 SCHEDULER_AGGREGATION: {total_articles} articles, {success_rate:.1f}% success",
            data={
                "total_articles": total_articles,
                "success_rate": success_rate,
                "metrics": metrics
            }
        )
    
    def log_scheduler_complete(self, workflow_summary: Dict[str, Any], 
                              next_run: Optional[datetime] = None) -> None:
        """Log scheduler completion."""
        duration_ms = (datetime.utcnow() - self.start_time).total_seconds() * 1000
        self._log(
            "INFO",
            f"✅ SCHEDULER_COMPLETE: Workflow finished",
            data={
                "workflow_summary": workflow_summary,
                "duration_ms": duration_ms,
                "next_run": next_run.isoformat() if next_run else None
            }
        )
    
    # Performance Metrics
    
    def log_performance_metrics(self, metrics: Dict[str, Any]) -> None:
        """Log performance metrics."""
        self._log(
            "INFO",
            f"📈 PERFORMANCE_METRICS",
            data=metrics
        )
