"""
Error classification system for Azure Functions scraper debugging.

Classifies errors into categories:
- Import errors
- Dependency errors
- Configuration errors
- Network errors
- Database errors
- Runtime errors
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
import re


class ErrorType(Enum):
    """Error type classification."""
    IMPORT_ERROR = "import_error"
    DEPENDENCY_ERROR = "dependency_error"
    CONFIGURATION_ERROR = "configuration_error"
    NETWORK_ERROR = "network_error"
    DATABASE_ERROR = "database_error"
    RUNTIME_ERROR = "runtime_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorReport:
    """Represents a classified error from function execution."""
    
    function_name: str
    error_type: ErrorType
    error_message: str
    stack_trace: str
    timestamp: datetime
    http_status_code: int
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error report to dictionary."""
        return {
            "function_name": self.function_name,
            "error_type": self.error_type.value,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "timestamp": self.timestamp.isoformat(),
            "http_status_code": self.http_status_code,
            "request_id": self.request_id
        }
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the error."""
        return (
            f"[{self.error_type.value.upper()}] {self.function_name}\n"
            f"Time: {self.timestamp.isoformat()}\n"
            f"Status: HTTP {self.http_status_code}\n"
            f"Message: {self.error_message[:200]}..."
        )


class ErrorClassifier:
    """
    Classifies errors by type for targeted fixes.
    
    Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5
    """
    
    # Error patterns for classification
    IMPORT_PATTERNS = [
        r"ModuleNotFoundError",
        r"ImportError",
        r"cannot import name",
        r"No module named",
        r"attempted relative import"
    ]
    
    DEPENDENCY_PATTERNS = [
        r"No module named '(\w+)'",
        r"cannot find package",
        r"package not found",
        r"missing required dependency"
    ]
    
    CONFIGURATION_PATTERNS = [
        r"ConfigurationError",
        r"environment variable.*not found",
        r"missing configuration",
        r"invalid configuration",
        r"connection string.*not found",
        r"KeyVault.*not found",
        r"@Microsoft\.KeyVault"
    ]
    
    NETWORK_PATTERNS = [
        r"NetworkError",
        r"ConnectionError",
        r"TimeoutError",
        r"timeout",
        r"connection refused",
        r"connection reset",
        r"HTTP.*\d{3}",
        r"requests\.exceptions",
        r"aiohttp\.client_exceptions"
    ]
    
    DATABASE_PATTERNS = [
        r"database",
        r"sql",
        r"pyodbc",
        r"connection.*failed",
        r"login failed",
        r"authentication failed",
        r"OperationalError",
        r"DatabaseError",
        r"IntegrityError"
    ]
    
    def classify_error(self, error_message: str, stack_trace: str) -> ErrorType:
        """
        Classify an error based on its message and stack trace.
        
        Args:
            error_message: The error message
            stack_trace: The full stack trace
            
        Returns:
            ErrorType classification
        """
        combined_text = f"{error_message}\n{stack_trace}".lower()
        
        # Check import errors first (most specific)
        if self._matches_patterns(combined_text, self.IMPORT_PATTERNS):
            return ErrorType.IMPORT_ERROR
        
        # Check configuration errors
        if self._matches_patterns(combined_text, self.CONFIGURATION_PATTERNS):
            return ErrorType.CONFIGURATION_ERROR
        
        # Check network errors
        if self._matches_patterns(combined_text, self.NETWORK_PATTERNS):
            return ErrorType.NETWORK_ERROR
        
        # Check database errors
        if self._matches_patterns(combined_text, self.DATABASE_PATTERNS):
            return ErrorType.DATABASE_ERROR
        
        # Check dependency errors (broader than import)
        if self._matches_patterns(combined_text, self.DEPENDENCY_PATTERNS):
            return ErrorType.DEPENDENCY_ERROR
        
        # Default to runtime error
        return ErrorType.RUNTIME_ERROR
    
    def _matches_patterns(self, text: str, patterns: list) -> bool:
        """Check if text matches any of the given patterns."""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def extract_missing_package(self, error_message: str, stack_trace: str) -> Optional[str]:
        """
        Extract the name of a missing package from error message.
        
        Validates: Requirement 2.2
        
        Args:
            error_message: The error message
            stack_trace: The full stack trace
            
        Returns:
            Package name if found, None otherwise
        """
        combined_text = f"{error_message}\n{stack_trace}"
        
        # Try to match "No module named 'package'"
        match = re.search(r"No module named ['\"](\w+)['\"]", combined_text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Try to match "ModuleNotFoundError: package"
        match = re.search(r"ModuleNotFoundError:\s*(\w+)", combined_text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Try to match "cannot import name 'X' from 'package'"
        match = re.search(r"cannot import name .* from ['\"](\w+)['\"]", combined_text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return None
    
    def extract_missing_configuration(self, error_message: str, stack_trace: str) -> Optional[str]:
        """
        Extract the name of a missing configuration value.
        
        Validates: Requirement 2.3
        
        Args:
            error_message: The error message
            stack_trace: The full stack trace
            
        Returns:
            Configuration name if found, None otherwise
        """
        combined_text = f"{error_message}\n{stack_trace}"
        
        # Try to match "environment variable 'VAR' not found"
        match = re.search(r"environment variable ['\"](\w+)['\"] not found", combined_text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Try to match "missing configuration: VAR"
        match = re.search(r"missing configuration[:\s]+(\w+)", combined_text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Try to match "connection string not found"
        if re.search(r"connection string.*not found", combined_text, re.IGNORECASE):
            return "DatabaseConnectionString"
        
        # Try to match KeyVault reference
        if re.search(r"@Microsoft\.KeyVault", combined_text):
            return "KeyVaultReference"
        
        return None
    
    def extract_http_status_code(self, error_message: str, stack_trace: str) -> Optional[int]:
        """
        Extract HTTP status code from network error.
        
        Validates: Requirement 2.4
        
        Args:
            error_message: The error message
            stack_trace: The full stack trace
            
        Returns:
            HTTP status code if found, None otherwise
        """
        combined_text = f"{error_message}\n{stack_trace}"
        
        # Try to match "HTTP 404" or "status code: 404"
        match = re.search(r"(?:HTTP|status code)[:\s]+(\d{3})", combined_text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        # Try to match "404 Not Found"
        match = re.search(r"(\d{3})\s+(?:Not Found|Forbidden|Unauthorized|Internal Server Error)", combined_text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        return None
    
    def is_connection_error(self, error_message: str, stack_trace: str) -> bool:
        """
        Determine if a database error is a connection error vs query error.
        
        Validates: Requirement 2.5
        
        Args:
            error_message: The error message
            stack_trace: The full stack trace
            
        Returns:
            True if connection error, False if query error
        """
        combined_text = f"{error_message}\n{stack_trace}".lower()
        
        connection_keywords = [
            "connection failed",
            "cannot connect",
            "login failed",
            "authentication failed",
            "timeout",
            "connection refused",
            "connection reset",
            "unable to connect"
        ]
        
        for keyword in connection_keywords:
            if keyword in combined_text:
                return True
        
        return False
    
    def create_error_report(
        self,
        function_name: str,
        error_message: str,
        stack_trace: str,
        http_status_code: int = 500,
        request_id: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> ErrorReport:
        """
        Create a complete error report with classification.
        
        Args:
            function_name: Name of the function that failed
            error_message: The error message
            stack_trace: The full stack trace
            http_status_code: HTTP status code
            request_id: Request ID if available
            timestamp: Error timestamp (defaults to now)
            
        Returns:
            ErrorReport with classification
        """
        error_type = self.classify_error(error_message, stack_trace)
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        return ErrorReport(
            function_name=function_name,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            timestamp=timestamp,
            http_status_code=http_status_code,
            request_id=request_id
        )
    
    def get_suggested_fix(self, error_report: ErrorReport) -> str:
        """
        Get a suggested fix based on error type.
        
        Args:
            error_report: The error report
            
        Returns:
            Suggested fix description
        """
        if error_report.error_type == ErrorType.IMPORT_ERROR:
            missing_package = self.extract_missing_package(
                error_report.error_message,
                error_report.stack_trace
            )
            if missing_package:
                return f"Add '{missing_package}' to requirements.txt or fix import path"
            return "Check import statements and verify relative paths (use ..shared not shared)"
        
        elif error_report.error_type == ErrorType.CONFIGURATION_ERROR:
            missing_config = self.extract_missing_configuration(
                error_report.error_message,
                error_report.stack_trace
            )
            if missing_config:
                return f"Add '{missing_config}' to application settings or environment variables"
            return "Verify Key Vault references and environment variables are configured"
        
        elif error_report.error_type == ErrorType.NETWORK_ERROR:
            status_code = self.extract_http_status_code(
                error_report.error_message,
                error_report.stack_trace
            )
            if status_code:
                return f"Network request failed with HTTP {status_code}. Check URL, headers, and rate limiting"
            return "Check network connectivity, timeouts, and retry logic"
        
        elif error_report.error_type == ErrorType.DATABASE_ERROR:
            if self.is_connection_error(error_report.error_message, error_report.stack_trace):
                return "Database connection failed. Verify connection string, firewall rules, and authentication"
            return "Database query failed. Check SQL syntax and table schema"
        
        elif error_report.error_type == ErrorType.DEPENDENCY_ERROR:
            return "Ensure requirements.txt is in function app root and deploy with --build remote"
        
        else:
            return "Review stack trace for specific error details and fix code logic"
