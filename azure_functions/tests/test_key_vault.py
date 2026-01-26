"""
Tests for Azure Key Vault integration.
Includes both unit tests and property-based tests for secure configuration management.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock
from hypothesis import given, strategies as st, settings
from azure.core.exceptions import ResourceNotFoundError, AzureError
from azure.keyvault.secrets import KeyVaultSecret

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.key_vault import (
    KeyVaultManager, 
    MultiAccountKeyVaultManager,
    get_key_vault_manager,
    get_multi_account_manager
)
from shared.interfaces import ConfigurationError


class TestKeyVaultManager:
    """Unit tests for KeyVaultManager class."""
    
    @pytest.fixture
    def mock_credential(self):
        """Mock Azure credential."""
        with patch('shared.key_vault.ManagedIdentityCredential') as mock:
            yield mock.return_value
    
    @pytest.fixture
    def mock_secret_client(self):
        """Mock SecretClient."""
        with patch('shared.key_vault.SecretClient') as mock:
            yield mock.return_value
    
    @pytest.fixture
    def key_vault_manager(self, mock_credential, mock_secret_client):
        """Create KeyVaultManager instance with mocked dependencies."""
        with patch.dict(os.environ, {'AZURE_KEY_VAULT_URL': 'https://test-vault.vault.azure.net/'}):
            manager = KeyVaultManager()
            manager._client = mock_secret_client
            return manager
    
    def test_initialization_with_url(self):
        """Test KeyVaultManager initialization with explicit URL."""
        url = "https://test-vault.vault.azure.net/"
        manager = KeyVaultManager(url)
        assert manager.key_vault_url == url
    
    def test_initialization_from_environment(self):
        """Test KeyVaultManager initialization from environment variable."""
        url = "https://env-vault.vault.azure.net/"
        with patch.dict(os.environ, {'AZURE_KEY_VAULT_URL': url}):
            manager = KeyVaultManager()
            assert manager.key_vault_url == url
    
    def test_initialization_without_url_raises_error(self):
        """Test that initialization without URL raises ConfigurationError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError, match="Azure Key Vault URL not configured"):
                KeyVaultManager()
    
    @pytest.mark.asyncio
    async def test_get_secret_success(self, key_vault_manager, mock_secret_client):
        """Test successful secret retrieval."""
        # Arrange
        secret_name = "test-secret"
        secret_value = "test-value"
        mock_secret = Mock()
        mock_secret.value = secret_value
        mock_secret_client.get_secret.return_value = mock_secret
        
        # Act
        result = await key_vault_manager.get_secret(secret_name)
        
        # Assert
        assert result == secret_value
        mock_secret_client.get_secret.assert_called_once_with(secret_name)
    
    @pytest.mark.asyncio
    async def test_get_secret_not_found(self, key_vault_manager, mock_secret_client):
        """Test secret retrieval when secret doesn't exist."""
        # Arrange
        secret_name = "nonexistent-secret"
        mock_secret_client.get_secret.side_effect = ResourceNotFoundError("Secret not found")
        
        # Act & Assert
        with pytest.raises(ConfigurationError, match=f"Secret '{secret_name}' not found"):
            await key_vault_manager.get_secret(secret_name)
    
    @pytest.mark.asyncio
    async def test_get_secret_azure_error(self, key_vault_manager, mock_secret_client):
        """Test secret retrieval with Azure error.""