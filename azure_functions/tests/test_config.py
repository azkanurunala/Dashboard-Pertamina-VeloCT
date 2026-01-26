"""
Test configuration for Azure Functions database tests.
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.models import DatabaseConfig


def get_test_database_config() -> DatabaseConfig:
    """
    Get database configuration for testing.
    Uses Azure SQL Database pei-dashboard if available, otherwise falls back to mock.
    """
    # Try to use Azure SQL Database first
    azure_connection_string = os.getenv('AZURE_SQL_CONNECTION_STRING')
    
    if not azure_connection_string:
        # Default Azure SQL connection string for pei-dashboard
        # User should set AZURE_SQL_CONNECTION_STRING environment variable with actual password
        azure_connection_string = (
            "Driver={ODBC Driver 18 for SQL Server};"
            "Server=tcp:pei-dashboard.database.windows.net,1433;"
            "Database=pei-dashboard;"
            "Uid=CloudSAa33fbc7c;"
            "Pwd={your_password_here};"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=30;"
        )
    
    return DatabaseConfig(
        connection_string=azure_connection_string,
        connection_pool_size=5,
        connection_timeout=30,
        command_timeout=60,
        retry_attempts=3,
        retry_delay=2
    )


def should_use_mock_database() -> bool:
    """
    Determine if we should use mock database for testing.
    Returns True if Azure SQL connection is not available or password not set.
    """
    connection_string = os.getenv('AZURE_SQL_CONNECTION_STRING', '')
    return not connection_string or '{your_password_here}' in connection_string


def get_mock_database_config() -> DatabaseConfig:
    """Get mock database configuration for testing without real database."""
    return DatabaseConfig(
        connection_string="mock://test",
        connection_pool_size=5,
        connection_timeout=10,
        command_timeout=30,
        retry_attempts=2,
        retry_delay=1
    )