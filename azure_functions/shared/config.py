"""
Configuration management utilities for Azure Functions.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import asdict
import json
import logging

from .models import ScrapingConfig, CopilotConfig, DatabaseConfig
from .interfaces import IConfigurationManager, ConfigurationError

# Azure Key Vault integration
try:
    from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
    from azure.keyvault.secrets import SecretClient
    AZURE_SDK_AVAILABLE = True
except ImportError:
    AZURE_SDK_AVAILABLE = False
    logging.warning("Azure SDK not available. Key Vault integration disabled.")


class EnvironmentConfigurationManager(IConfigurationManager):
    """
    Configuration manager that reads from environment variables and local settings.
    """
    
    def __init__(self):
        """Initialize the configuration manager."""
        self._cache: Dict[str, Any] = {}
        self._load_environment_config()
    
    def _load_environment_config(self) -> None:
        """Load configuration from environment variables."""
        # Database configuration
        self._cache["database"] = {
            "connection_string": os.getenv("SQL_SERVER_CONNECTION_STRING", ""),
            "connection_pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
            "connection_timeout": int(os.getenv("DB_CONNECTION_TIMEOUT", "30")),
            "command_timeout": int(os.getenv("DB_COMMAND_TIMEOUT", "60")),
            "retry_attempts": int(os.getenv("DB_RETRY_ATTEMPTS", "3")),
            "retry_delay": int(os.getenv("DB_RETRY_DELAY", "1"))
        }
        
        # Copilot configuration
        self._cache["copilot"] = {
            "api_endpoint": os.getenv("COPILOT_API_ENDPOINT", os.getenv("GEMINI_API_ENDPOINT", "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent")),
            "model_name": os.getenv("COPILOT_MODEL_NAME", os.getenv("GEMINI_MODEL_NAME", "gemini-pro")),
            "max_tokens": int(os.getenv("COPILOT_MAX_TOKENS", "4000")),
            "temperature": float(os.getenv("COPILOT_TEMPERATURE", "0.3")),
            "rate_limit_requests_per_minute": int(os.getenv("COPILOT_RATE_LIMIT", "60")),
            "batch_size": int(os.getenv("COPILOT_BATCH_SIZE", "10")),
            "role_prompts": self._load_role_prompts()
        }
        
        # Default scraping configurations
        self._cache["scraping_defaults"] = {
            "rate_limit_delay": float(os.getenv("SCRAPER_RATE_LIMIT_DELAY", "1")),
            "max_retries": int(os.getenv("SCRAPER_MAX_RETRIES", "3")),
            "timeout": int(os.getenv("SCRAPER_TIMEOUT", "30")),
            "use_selenium": os.getenv("SCRAPER_USE_SELENIUM", "false").lower() == "true"
        }
        
        # Azure services configuration
        self._cache["azure"] = {
            "key_vault_url": os.getenv("AZURE_KEY_VAULT_URL", ""),
            "blob_storage_connection_string": os.getenv("BLOB_STORAGE_CONNECTION_STRING", ""),
            "appinsights_key": os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY", ""),
            "appinsights_connection_string": os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
        }
    
    def _load_role_prompts(self) -> Dict[str, str]:
        """Load role-specific prompts for Copilot."""
        return {
            "financial_analyst": """You are a financial analyst specializing in energy markets. 
                                   Analyze the following news articles and provide sentiment analysis 
                                   focusing on market impact, price movements, and investment implications.""",
            
            "policy_analyst": """You are a policy analyst focusing on energy and environmental policy. 
                               Analyze the following news articles and provide sentiment analysis 
                               focusing on regulatory changes, government initiatives, and policy implications.""",
            
            "market_researcher": """You are a market researcher specializing in energy sector trends. 
                                   Analyze the following news articles and provide sentiment analysis 
                                   focusing on market trends, competitive dynamics, and industry developments.""",
            
            "risk_analyst": """You are a risk analyst focusing on energy sector risks. 
                             Analyze the following news articles and provide sentiment analysis 
                             focusing on operational risks, market risks, and regulatory risks.""",
            
            "general": """Analyze the following news articles and provide a comprehensive sentiment analysis 
                        including overall sentiment, key themes, and potential market implications."""
        }
    
    async def get_scraping_config(self, source_name: str) -> ScrapingConfig:
        """Get scraping configuration for a specific source."""
        # Load source-specific configuration if available
        source_config = self._get_source_specific_config(source_name)
        
        # Merge with defaults
        defaults = self._cache["scraping_defaults"]
        config_data = {**defaults, **source_config}
        
        return ScrapingConfig(
            source_name=source_name,
            base_url=config_data.get("base_url", ""),
            selectors=config_data.get("selectors", {}),
            rate_limit_delay=config_data["rate_limit_delay"],
            max_retries=config_data["max_retries"],
            timeout=config_data["timeout"],
            headers=config_data.get("headers", {}),
            use_selenium=config_data.get("use_selenium", defaults["use_selenium"])
        )
    
    def _get_source_specific_config(self, source_name: str) -> Dict[str, Any]:
        """Get source-specific configuration."""
        # Define configurations for major news sources
        source_configs = {
            "cnbc": {
                "base_url": "https://www.cnbc.com",
                "selectors": {
                    "title": "h1.ArticleHeader-headline",
                    "content": "div.ArticleBody-articleBody",
                    "date": "time[data-module='ArticleHeader']",
                    "author": "a[data-module='ArticleHeader']"
                },
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            },
            "cnn": {
                "base_url": "https://www.cnn.com",
                "selectors": {
                    "title": "h1.headline__text",
                    "content": "section.zn-body-text",
                    "date": "p.update-time",
                    "author": "span.metadata__byline__author"
                },
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            },
            "reuters": {
                "base_url": "https://www.reuters.com",
                "selectors": {
                    "title": "h1[data-testid='Heading']",
                    "content": "div[data-testid='ArticleBodyWrapper']",
                    "date": "time[datetime]",
                    "author": "span[data-testid='AuthorName']"
                },
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            },
            "kompas": {
                "base_url": "https://www.kompas.com",
                "selectors": {
                    "title": "h1.read__title",
                    "content": "div.read__content",
                    "date": "div.read__time",
                    "author": "div.read__author"
                },
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            }
        }
        
        return source_configs.get(source_name.lower(), {})
    
    async def get_copilot_config(self) -> CopilotConfig:
        """Get Copilot API configuration."""
        config_data = self._cache["copilot"]
        
        if not config_data["api_endpoint"]:
            raise ConfigurationError("Copilot API endpoint not configured")
            
        # Add API key to config
        config_data["api_key"] = get_ai_api_key()
        
        return CopilotConfig(**config_data)
    
    async def get_database_config(self) -> DatabaseConfig:
        """Get database configuration."""
        config_data = self._cache["database"]
        
        if not config_data["connection_string"]:
            raise ConfigurationError("Database connection string not configured")
        
        return DatabaseConfig(**config_data)
    
    async def get_secret(self, secret_name: str) -> str:
        """
        Get a secret value from environment variables or Key Vault.
        
        Args:
            secret_name: Name of the secret
            
        Returns:
            Secret value
        """
        # Try direct environment variable first
        value = os.getenv(secret_name)
        
        # If not in environment, or placeholder, or KV reference, check Key Vault
        if not value or value == "PLACEHOLDER-WILL-BE-CONFIGURED-LATER" or str(value).startswith("@Microsoft.KeyVault"):
            kv_secret = _get_key_vault_secret(secret_name)
            if kv_secret:
                value = kv_secret
                
        if value is None:
            raise ConfigurationError(f"Secret '{secret_name}' not found in environment or Key Vault")
            
        return str(value)

    def reload(self) -> None:
        """Reload configuration from environment."""
        self._load_environment_config()
    
    async def update_configuration(self, key: str, value: Any) -> None:
        """Update a configuration value in cache."""
        # Parse the key to update nested configuration
        keys = key.split(".")
        current = self._cache
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def get_azure_config(self) -> Dict[str, str]:
        """Get Azure services configuration."""
        return self._cache["azure"]
    
    def get_blob_storage_config(self) -> Dict[str, str]:
        """Get blob storage configuration."""
        azure_config = self._cache["azure"]
        return {
            "connection_string": azure_config.get("blob_storage_connection_string", ""),
            "account_url": azure_config.get("blob_storage_account_url", "")
        }
    
    def get_all_source_names(self) -> list[str]:
        """Get list of all configured news sources."""
        return [
            "cnbc", "cnn", "reuters", "kompas", "bisnis_indonesia", "kontan",
            "tempo", "bloomberg", "theguardian", "scmp", "oilprice", 
            "energiesmedia", "bioenergytimes", "bank_indonesia", "bps",
            "migas_esdm", "migas_eia", "biodiesel_esdm", "bioetanol_esdm",
            "google_news", "cnbc_id"
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        return self._cache.copy()


# Global configuration instance
config_manager = EnvironmentConfigurationManager()


def _get_key_vault_secret(secret_name: str) -> Optional[str]:
    """
    Get secret from Azure Key Vault using Managed Identity.
    
    Args:
        secret_name: Name of the secret in Key Vault
        
    Returns:
        Secret value or None if not found
    """
    if not AZURE_SDK_AVAILABLE:
        return None
    
    key_vault_url = os.getenv("KEY_VAULT_URL")
    if not key_vault_url:
        return None
    
    try:
        # Use Managed Identity to authenticate
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=key_vault_url, credential=credential)
        
        # Get the secret
        secret = client.get_secret(secret_name)
        return secret.value
    except Exception as e:
        logging.warning(f"Failed to get secret '{secret_name}' from Key Vault: {e}")
        return None



def get_database_connection_string() -> str:
    """
    Get database connection string from environment variables or Key Vault.
    Supports both Azure App Settings and local development.
    
    Priority order:
    1. Direct environment variable (DatabaseConnectionString)
    2. Azure Key Vault (using Managed Identity)
    3. Fallback environment variables for local dev
    """
    # Try direct environment variable first (works if Key Vault reference is resolved)
    connection_string = os.getenv("DatabaseConnectionString")
    
    # If not found or is a Key Vault reference, try to get from Key Vault directly
    if not connection_string or connection_string.startswith("@Microsoft.KeyVault"):
        kv_secret = _get_key_vault_secret("DatabaseConnectionString")
        if kv_secret:
            connection_string = kv_secret
    
    # Fallback to SQL_SERVER_CONNECTION_STRING for local dev
    if not connection_string:
        connection_string = os.getenv("SQL_SERVER_CONNECTION_STRING")
    
    # Fallback to direct connection string for testing
    if not connection_string:
        connection_string = os.getenv("SQLAZURECONNSTR_DefaultConnection")
    
    if not connection_string:
        raise ConfigurationError(
            "Database connection string not found. "
            "Please set DatabaseConnectionString, SQL_SERVER_CONNECTION_STRING, "
            "or SQLAZURECONNSTR_DefaultConnection environment variable."
        )
    
    return connection_string


def get_database_config() -> Dict[str, Any]:
    """
    Get database configuration from environment variables.
    
    Returns:
        Dictionary with database configuration
    """
    return {
        "connection_string": get_database_connection_string(),
        "connection_pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "connection_timeout": int(os.getenv("DB_CONNECTION_TIMEOUT", "30")),
        "command_timeout": int(os.getenv("DB_COMMAND_TIMEOUT", "60")),
        "retry_attempts": int(os.getenv("DB_RETRY_ATTEMPTS", "3")),
        "retry_delay": int(os.getenv("DB_RETRY_DELAY", "1"))
    }


def get_storage_connection_string() -> str:
    """
    Get storage connection string from environment variables or Key Vault.
    
    Priority order:
    1. Direct environment variable (StorageConnectionString)
    2. Azure Key Vault (using Managed Identity)
    3. Fallback environment variables
    """
    # Try direct environment variable first
    connection_string = os.getenv("StorageConnectionString")
    
    # If not found or is a Key Vault reference, try to get from Key Vault directly
    if not connection_string or connection_string.startswith("@Microsoft.KeyVault"):
        kv_secret = _get_key_vault_secret("StorageConnectionString")
        if kv_secret:
            connection_string = kv_secret
    
    # Fallback to AzureWebJobsStorage
    if not connection_string:
        connection_string = os.getenv("AzureWebJobsStorage")
    
    if not connection_string:
        raise ConfigurationError(
            "Storage connection string not found. "
            "Please set StorageConnectionString or AzureWebJobsStorage environment variable."
        )
    
    return connection_string


def get_ai_api_key() -> str:
    """
    Get Copilot/AI API key from environment variables or Key Vault.
    
    Priority order:
    1. Direct environment variable (AI_API_KEY)
    2. Direct environment variable (CopilotApiKey - Legacy)
    3. Azure Key Vault (using Managed Identity)
    """
    # Try direct environment variables first
    api_key = os.getenv("AI_API_KEY") or os.getenv("CopilotApiKey")
    
    # If not found, or placeholder, or Key Vault reference, try to get from Key Vault directly
    if not api_key or api_key == "PLACEHOLDER-WILL-BE-CONFIGURED-LATER" or api_key.startswith("@Microsoft.KeyVault"):
        # Try both names in Key Vault
        for name in ["AI_API_KEY", "CopilotApiKey"]:
            kv_secret = _get_key_vault_secret(name)
            if kv_secret:
                api_key = kv_secret
                break
    
    if not api_key or api_key == "PLACEHOLDER-WILL-BE-CONFIGURED-LATER":
        raise ConfigurationError(
            "AI API key not configured. "
            "Please set AI_API_KEY environment variable."
        )
    
    return api_key


def get_copilot_endpoint() -> str:
    """
    Get Copilot API endpoint from environment variables or Key Vault.
    
    Priority order:
    1. Direct environment variable (CopilotEndpoint or COPILOT_API_ENDPOINT)
    2. Azure Key Vault (using Managed Identity)
    """
    # Try direct environment variables first
    endpoint = os.getenv("CopilotEndpoint") or os.getenv("COPILOT_API_ENDPOINT")
    
    # If not found, or placeholder, or Key Vault reference, try to get from Key Vault directly
    if not endpoint or endpoint == "PLACEHOLDER-WILL-BE-CONFIGURED-LATER" or endpoint.startswith("@Microsoft.KeyVault"):
        # Try both names in Key Vault
        for name in ["CopilotEndpoint", "COPILOT_API_ENDPOINT"]:
            kv_secret = _get_key_vault_secret(name)
            if kv_secret:
                endpoint = kv_secret
                break
    
    if not endpoint or endpoint == "PLACEHOLDER-WILL-BE-CONFIGURED-LATER":
        raise ConfigurationError(
            "Copilot API endpoint not configured. "
            "Please set CopilotEndpoint or COPILOT_API_ENDPOINT environment variable."
        )
    
    return endpoint
