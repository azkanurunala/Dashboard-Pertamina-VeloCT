"""
Azure Key Vault integration for secure configuration management.
Implements secure credential retrieval and managed identity authentication.
"""

import os
import logging
from typing import Dict, Any, Optional
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential, ClientSecretCredential
from azure.core.exceptions import AzureError, ResourceNotFoundError
import asyncio
from functools import lru_cache

from .interfaces import ConfigurationError


logger = logging.getLogger(__name__)


class KeyVaultManager:
    """
    Manages Azure Key Vault operations with support for multiple authentication methods.
    Provides secure credential retrieval for different service accounts.
    """
    
    def __init__(self, key_vault_url: Optional[str] = None):
        """
        Initialize Key Vault manager.
        
        Args:
            key_vault_url: Azure Key Vault URL. If None, will use environment variable.
        """
        self.key_vault_url = key_vault_url or os.getenv("AZURE_KEY_VAULT_URL")
        if not self.key_vault_url:
            raise ConfigurationError("Azure Key Vault URL not configured")
        
        self._client: Optional[SecretClient] = None
        self._credential = None
        self._cache: Dict[str, str] = {}
        self._initialize_credential()
    
    def _initialize_credential(self) -> None:
        """Initialize Azure credential based on available authentication methods."""
        try:
            # Try managed identity first (preferred for Azure Functions)
            client_id = os.getenv("AZURE_CLIENT_ID")
            if client_id:
                logger.info("Using managed identity authentication with client ID")
                self._credential = ManagedIdentityCredential(client_id=client_id)
            else:
                logger.info("Using managed identity authentication (system-assigned)")
                self._credential = ManagedIdentityCredential()
            
            # Test the credential by creating a client
            test_client = SecretClient(vault_url=self.key_vault_url, credential=self._credential)
            
        except Exception as e:
            logger.warning(f"Managed identity authentication failed: {e}")
            
            # Fallback to service principal authentication
            client_id = os.getenv("AZURE_CLIENT_ID")
            client_secret = os.getenv("AZURE_CLIENT_SECRET")
            tenant_id = os.getenv("AZURE_TENANT_ID")
            
            if client_id and client_secret and tenant_id:
                logger.info("Using service principal authentication")
                self._credential = ClientSecretCredential(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    client_secret=client_secret
                )
            else:
                # Final fallback to default credential chain
                logger.info("Using default Azure credential chain")
                self._credential = DefaultAzureCredential()
    
    @property
    def client(self) -> SecretClient:
        """Get or create the Key Vault client."""
        if self._client is None:
            self._client = SecretClient(
                vault_url=self.key_vault_url,
                credential=self._credential
            )
        return self._client
    
    async def get_secret(self, secret_name: str, use_cache: bool = True) -> str:
        """
        Retrieve a secret from Azure Key Vault.
        
        Args:
            secret_name: Name of the secret to retrieve
            use_cache: Whether to use cached values
            
        Returns:
            Secret value
            
        Raises:
            ConfigurationError: If secret retrieval fails
        """
        # Check cache first if enabled
        if use_cache and secret_name in self._cache:
            logger.debug(f"Retrieved secret '{secret_name}' from cache")
            return self._cache[secret_name]
        
        try:
            # Run the synchronous Key Vault operation in a thread pool
            secret = await asyncio.get_event_loop().run_in_executor(
                None, self._get_secret_sync, secret_name
            )
            
            # Cache the secret if caching is enabled
            if use_cache:
                self._cache[secret_name] = secret
            
            logger.info(f"Successfully retrieved secret '{secret_name}' from Key Vault")
            return secret
            
        except ResourceNotFoundError:
            raise ConfigurationError(f"Secret '{secret_name}' not found in Key Vault")
        except AzureError as e:
            logger.error(f"Azure error retrieving secret '{secret_name}': {e}")
            raise ConfigurationError(f"Failed to retrieve secret '{secret_name}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving secret '{secret_name}': {e}")
            raise ConfigurationError(f"Failed to retrieve secret '{secret_name}': {e}")
    
    def _get_secret_sync(self, secret_name: str) -> str:
        """Synchronous helper method to get secret from Key Vault."""
        secret = self.client.get_secret(secret_name)
        return secret.value
    
    async def get_multiple_secrets(self, secret_names: list[str], use_cache: bool = True) -> Dict[str, str]:
        """
        Retrieve multiple secrets from Azure Key Vault.
        
        Args:
            secret_names: List of secret names to retrieve
            use_cache: Whether to use cached values
            
        Returns:
            Dictionary mapping secret names to values
            
        Raises:
            ConfigurationError: If any secret retrieval fails
        """
        secrets = {}
        
        for secret_name in secret_names:
            try:
                secrets[secret_name] = await self.get_secret(secret_name, use_cache)
            except ConfigurationError as e:
                logger.error(f"Failed to retrieve secret '{secret_name}': {e}")
                # Continue with other secrets, but log the failure
                secrets[secret_name] = None
        
        return secrets
    
    async def set_secret(self, secret_name: str, secret_value: str) -> None:
        """
        Set a secret in Azure Key Vault.
        
        Args:
            secret_name: Name of the secret
            secret_value: Value of the secret
            
        Raises:
            ConfigurationError: If secret setting fails
        """
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self._set_secret_sync, secret_name, secret_value
            )
            
            # Update cache
            self._cache[secret_name] = secret_value
            
            logger.info(f"Successfully set secret '{secret_name}' in Key Vault")
            
        except AzureError as e:
            logger.error(f"Azure error setting secret '{secret_name}': {e}")
            raise ConfigurationError(f"Failed to set secret '{secret_name}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error setting secret '{secret_name}': {e}")
            raise ConfigurationError(f"Failed to set secret '{secret_name}': {e}")
    
    def _set_secret_sync(self, secret_name: str, secret_value: str) -> None:
        """Synchronous helper method to set secret in Key Vault."""
        self.client.set_secret(secret_name, secret_value)
    
    async def list_secrets(self) -> list[str]:
        """
        List all secret names in the Key Vault.
        
        Returns:
            List of secret names
            
        Raises:
            ConfigurationError: If listing fails
        """
        try:
            secret_names = await asyncio.get_event_loop().run_in_executor(
                None, self._list_secrets_sync
            )
            
            logger.info(f"Successfully listed {len(secret_names)} secrets from Key Vault")
            return secret_names
            
        except AzureError as e:
            logger.error(f"Azure error listing secrets: {e}")
            raise ConfigurationError(f"Failed to list secrets: {e}")
        except Exception as e:
            logger.error(f"Unexpected error listing secrets: {e}")
            raise ConfigurationError(f"Failed to list secrets: {e}")
    
    def _list_secrets_sync(self) -> list[str]:
        """Synchronous helper method to list secrets from Key Vault."""
        secret_properties = self.client.list_properties_of_secrets()
        return [secret.name for secret in secret_properties]
    
    async def health_check(self) -> bool:
        """
        Check Key Vault connectivity and authentication.
        
        Returns:
            True if Key Vault is accessible, False otherwise
        """
        try:
            # Try to list secrets as a health check
            await asyncio.get_event_loop().run_in_executor(
                None, self._health_check_sync
            )
            return True
        except Exception as e:
            logger.error(f"Key Vault health check failed: {e}")
            return False
    
    def _health_check_sync(self) -> None:
        """Synchronous helper method for health check."""
        # Just try to access the Key Vault properties
        list(self.client.list_properties_of_secrets())
    
    def clear_cache(self) -> None:
        """Clear the secret cache."""
        self._cache.clear()
        logger.info("Key Vault secret cache cleared")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get information about the current cache state.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "cached_secrets": len(self._cache),
            "secret_names": list(self._cache.keys())
        }


class MultiAccountKeyVaultManager:
    """
    Manages multiple Key Vault instances for different service accounts.
    Provides isolation between AI, Functions, and SQL Server accounts.

    Note: currently only referenced by tests; production uses the single-vault
    KeyVaultManager wired via config_manager.get_secret().
    """

    def __init__(self):
        """Initialize multi-account Key Vault manager."""
        self._vault_managers: Dict[str, KeyVaultManager] = {}
        self._initialize_vault_managers()

    def _initialize_vault_managers(self) -> None:
        """Initialize Key Vault managers for different accounts."""
        # AI provider account Key Vault
        ai_vault_url = os.getenv("AI_KEY_VAULT_URL")
        if ai_vault_url:
            self._vault_managers["ai"] = KeyVaultManager(ai_vault_url)

        # Azure Functions account Key Vault
        functions_vault_url = os.getenv("FUNCTIONS_KEY_VAULT_URL")
        if functions_vault_url:
            self._vault_managers["functions"] = KeyVaultManager(functions_vault_url)

        # SQL Server account Key Vault
        sql_vault_url = os.getenv("SQL_KEY_VAULT_URL")
        if sql_vault_url:
            self._vault_managers["sql"] = KeyVaultManager(sql_vault_url)

        # Default Key Vault (fallback)
        default_vault_url = os.getenv("AZURE_KEY_VAULT_URL")
        if default_vault_url:
            self._vault_managers["default"] = KeyVaultManager(default_vault_url)
    
    async def get_copilot_credentials(self) -> Dict[str, str]:
        """
        Get Copilot API credentials from dedicated Key Vault.
        
        Returns:
            Dictionary with Copilot credentials
            
        Raises:
            ConfigurationError: If credentials retrieval fails
        """
        vault_manager = self._get_vault_manager("copilot")
        
        credential_names = [
            "copilot-api-key",
            "copilot-api-endpoint",
            "copilot-subscription-key"
        ]
        
        credentials = await vault_manager.get_multiple_secrets(credential_names)
        
        # Validate required credentials
        if not credentials.get("copilot-api-key"):
            raise ConfigurationError("Copilot API key not found in Key Vault")
        if not credentials.get("copilot-api-endpoint"):
            raise ConfigurationError("Copilot API endpoint not found in Key Vault")
        
        return credentials
    
    async def get_sql_credentials(self) -> Dict[str, str]:
        """
        Get SQL Server credentials from dedicated Key Vault.
        
        Returns:
            Dictionary with SQL Server credentials
            
        Raises:
            ConfigurationError: If credentials retrieval fails
        """
        vault_manager = self._get_vault_manager("sql")
        
        credential_names = [
            "sql-server-connection-string",
            "sql-server-username",
            "sql-server-password",
            "sql-database-name"
        ]
        
        credentials = await vault_manager.get_multiple_secrets(credential_names)
        
        # Validate required credentials
        if not credentials.get("sql-server-connection-string"):
            raise ConfigurationError("SQL Server connection string not found in Key Vault")
        
        return credentials
    
    async def get_functions_credentials(self) -> Dict[str, str]:
        """
        Get Azure Functions credentials from dedicated Key Vault.
        
        Returns:
            Dictionary with Functions credentials
            
        Raises:
            ConfigurationError: If credentials retrieval fails
        """
        vault_manager = self._get_vault_manager("functions")
        
        credential_names = [
            "functions-storage-connection-string",
            "functions-appinsights-key",
            "functions-subscription-id",
            "blob-storage-connection-string"
        ]
        
        credentials = await vault_manager.get_multiple_secrets(credential_names)
        
        return credentials
    
    async def get_secret_from_account(self, account: str, secret_name: str) -> str:
        """
        Get a specific secret from a specific account's Key Vault.
        
        Args:
            account: Account name (copilot, functions, sql, default)
            secret_name: Name of the secret
            
        Returns:
            Secret value
            
        Raises:
            ConfigurationError: If secret retrieval fails
        """
        vault_manager = self._get_vault_manager(account)
        return await vault_manager.get_secret(secret_name)
    
    def _get_vault_manager(self, account: str) -> KeyVaultManager:
        """
        Get Key Vault manager for specific account.
        
        Args:
            account: Account name
            
        Returns:
            KeyVaultManager instance
            
        Raises:
            ConfigurationError: If account not configured
        """
        if account not in self._vault_managers:
            # Try default vault as fallback
            if "default" in self._vault_managers:
                logger.warning(f"Account '{account}' Key Vault not configured, using default")
                return self._vault_managers["default"]
            else:
                raise ConfigurationError(f"Key Vault for account '{account}' not configured")
        
        return self._vault_managers[account]
    
    async def health_check_all(self) -> Dict[str, bool]:
        """
        Check health of all configured Key Vaults.
        
        Returns:
            Dictionary mapping account names to health status
        """
        health_status = {}
        
        for account, vault_manager in self._vault_managers.items():
            health_status[account] = await vault_manager.health_check()
        
        return health_status
    
    def get_configured_accounts(self) -> list[str]:
        """
        Get list of configured account names.
        
        Returns:
            List of account names
        """
        return list(self._vault_managers.keys())


# Global instances for easy access
key_vault_manager = None
multi_account_manager = None


def get_key_vault_manager() -> KeyVaultManager:
    """Get the global Key Vault manager instance."""
    global key_vault_manager
    if key_vault_manager is None:
        key_vault_manager = KeyVaultManager()
    return key_vault_manager


def get_multi_account_manager() -> MultiAccountKeyVaultManager:
    """Get the global multi-account Key Vault manager instance."""
    global multi_account_manager
    if multi_account_manager is None:
        multi_account_manager = MultiAccountKeyVaultManager()
    return multi_account_manager