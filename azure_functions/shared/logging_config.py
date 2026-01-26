"""
Logging configuration and Application Insights integration for Azure Functions.
"""

import logging
import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime
import json

# Application Insights integration
try:
    from applicationinsights import TelemetryClient
    from applicationinsights.logging import LoggingHandler
    APPINSIGHTS_AVAILABLE = True
except ImportError:
    APPINSIGHTS_AVAILABLE = False
    TelemetryClient = None
    LoggingHandler = None


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured logging with JSON output.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "function_name": getattr(record, 'function_name', None),
            "execution_id": getattr(record, 'execution_id', None),
            "correlation_id": getattr(record, 'correlation_id', None)
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from the record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info', 'function_name', 'execution_id',
                          'correlation_id']:
                extra_fields[key] = value
        
        if extra_fields:
            log_entry["extra"] = extra_fields
        
        return json.dumps(log_entry, default=str)


class AzureFunctionsLogger:
    """
    Centralized logging configuration for Azure Functions.
    """
    
    def __init__(self, 
                 function_name: str,
                 log_level: str = "INFO",
                 enable_appinsights: bool = True):
        """
        Initialize the logger for an Azure Function.
        
        Args:
            function_name: Name of the Azure Function
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            enable_appinsights: Whether to enable Application Insights integration
        """
        self.function_name = function_name
        self.log_level = getattr(logging, log_level.upper())
        self.enable_appinsights = enable_appinsights and APPINSIGHTS_AVAILABLE
        
        # Get Application Insights configuration
        self.appinsights_key = os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY")
        self.appinsights_connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
        
        # Initialize logger
        self.logger = self._setup_logger()
        
        # Initialize Application Insights client if available
        self.telemetry_client = self._setup_appinsights() if self.enable_appinsights else None
    
    def _setup_logger(self) -> logging.Logger:
        """Set up the main logger with appropriate handlers and formatters."""
        logger = logging.getLogger(self.function_name)
        logger.setLevel(self.log_level)
        
        # Remove existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Console handler with structured formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(StructuredFormatter())
        logger.addHandler(console_handler)
        
        # Application Insights handler if available
        if self.enable_appinsights and (self.appinsights_key or self.appinsights_connection_string):
            try:
                if self.appinsights_connection_string:
                    appinsights_handler = LoggingHandler(self.appinsights_connection_string)
                else:
                    appinsights_handler = LoggingHandler(self.appinsights_key)
                appinsights_handler.setLevel(logging.WARNING)  # Only send warnings and errors to AppInsights
                logger.addHandler(appinsights_handler)
            except Exception as e:
                logger.warning(f"Failed to initialize Application Insights logging: {e}")
        
        return logger
    
    def _setup_appinsights(self) -> Optional[TelemetryClient]:
        """Set up Application Insights telemetry client."""
        if not (self.appinsights_key or self.appinsights_connection_string):
            return None
        
        try:
            if self.appinsights_connection_string:
                client = TelemetryClient(self.appinsights_connection_string)
            else:
                client = TelemetryClient(self.appinsights_key)
            
            # Set default properties
            client.context.application.ver = "1.0.0"
            client.context.cloud.role = "azure-functions-news-scraper"
            client.context.cloud.roleInstance = self.function_name
            
            return client
        except Exception as e:
            self.logger.warning(f"Failed to initialize Application Insights client: {e}")
            return None
    
    def get_logger(self, execution_id: Optional[str] = None, 
                   correlation_id: Optional[str] = None) -> logging.LoggerAdapter:
        """
        Get a logger adapter with execution context.
        
        Args:
            execution_id: Unique identifier for the function execution
            correlation_id: Correlation ID for tracking across functions
            
        Returns:
            LoggerAdapter with context information
        """
        extra = {
            "function_name": self.function_name,
            "execution_id": execution_id,
            "correlation_id": correlation_id
        }
        return logging.LoggerAdapter(self.logger, extra)
    
    def track_event(self, name: str, properties: Optional[Dict[str, Any]] = None,
                   measurements: Optional[Dict[str, float]] = None) -> None:
        """
        Track a custom event in Application Insights.
        
        Args:
            name: Event name
            properties: Event properties
            measurements: Event measurements
        """
        if self.telemetry_client:
            try:
                self.telemetry_client.track_event(name, properties, measurements)
                self.telemetry_client.flush()
            except Exception as e:
                self.logger.warning(f"Failed to track event '{name}': {e}")
    
    def track_metric(self, name: str, value: float, 
                    properties: Optional[Dict[str, Any]] = None) -> None:
        """
        Track a custom metric in Application Insights.
        
        Args:
            name: Metric name
            value: Metric value
            properties: Metric properties
        """
        if self.telemetry_client:
            try:
                self.telemetry_client.track_metric(name, value, properties=properties)
                self.telemetry_client.flush()
            except Exception as e:
                self.logger.warning(f"Failed to track metric '{name}': {e}")
    
    def track_exception(self, exception: Exception, 
                       properties: Optional[Dict[str, Any]] = None) -> None:
        """
        Track an exception in Application Insights.
        
        Args:
            exception: Exception to track
            properties: Exception properties
        """
        if self.telemetry_client:
            try:
                self.telemetry_client.track_exception(type(exception), exception, 
                                                    exception.__traceback__, properties)
                self.telemetry_client.flush()
            except Exception as e:
                self.logger.warning(f"Failed to track exception: {e}")
    
    def track_dependency(self, name: str, data: str, type_name: str = "HTTP",
                        target: Optional[str] = None, duration: Optional[int] = None,
                        success: bool = True, result_code: Optional[str] = None,
                        properties: Optional[Dict[str, Any]] = None) -> None:
        """
        Track a dependency call in Application Insights.
        
        Args:
            name: Dependency name
            data: Dependency data (e.g., URL, SQL query)
            type_name: Dependency type (HTTP, SQL, etc.)
            target: Dependency target
            duration: Duration in milliseconds
            success: Whether the call was successful
            result_code: Result code
            properties: Additional properties
        """
        if self.telemetry_client:
            try:
                self.telemetry_client.track_dependency(name, data, type_name, target,
                                                     duration, success, result_code, properties)
                self.telemetry_client.flush()
            except Exception as e:
                self.logger.warning(f"Failed to track dependency '{name}': {e}")


def get_function_logger(function_name: str, 
                       execution_id: Optional[str] = None,
                       correlation_id: Optional[str] = None,
                       log_level: str = "INFO") -> tuple[logging.LoggerAdapter, AzureFunctionsLogger]:
    """
    Convenience function to get a configured logger for an Azure Function.
    
    Args:
        function_name: Name of the Azure Function
        execution_id: Unique identifier for the function execution
        correlation_id: Correlation ID for tracking across functions
        log_level: Logging level
        
    Returns:
        Tuple of (LoggerAdapter, AzureFunctionsLogger)
    """
    azure_logger = AzureFunctionsLogger(function_name, log_level)
    logger_adapter = azure_logger.get_logger(execution_id, correlation_id)
    
    return logger_adapter, azure_logger


# Global configuration
def configure_root_logging():
    """Configure root logging for the entire application."""
    # Set root logger level
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Suppress noisy third-party loggers
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("selenium").setLevel(logging.WARNING)
    
    # Configure Azure Functions specific logging
    azure_functions_logger = logging.getLogger("azure.functions")
    azure_functions_logger.setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Simple function to get a logger by name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Initialize root logging when module is imported
configure_root_logging()