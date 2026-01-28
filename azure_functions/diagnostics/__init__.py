"""
Diagnostic utilities for Azure Functions scraper debugging.

This module provides tools for:
- Accessing Azure Function logs
- Parsing error messages and stack traces
- Classifying errors by type
- Generating diagnostic reports
"""

from .error_classifier import ErrorClassifier, ErrorType, ErrorReport
from .log_parser import LogParser, LogEntry
from .diagnostic_session import DiagnosticSession, TestResult
from .azure_log_access import AzureLogAccess

__all__ = [
    'ErrorClassifier',
    'ErrorType',
    'ErrorReport',
    'LogParser',
    'LogEntry',
    'DiagnosticSession',
    'TestResult',
    'AzureLogAccess'
]
