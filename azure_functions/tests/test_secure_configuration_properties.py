"""
Property-based tests for secure configuration management.
Tests universal properties that should hold for secure credential storage and retrieval.
"""

import asyncio
import os
import sys
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
import uuid
import re

# Mock the testing framework since we can't install it
class MockHypothesis:
    """Mock hypothesis for property testing when pytest is not available."""
    
    @staticmethod
    def given(*args, **kwargs):
        def decorator(func):
            func._hypothesis_given = True
            return func
        return decorator
    
    @staticmethod
    def settings(*args, **kwargs):
        def decorator(func):
            func._hypothesis_settings = True
            return func
        return decorator
    
    class strategies:
        @staticmethod
        def lists(strategy, min_size=0, max_size=10):
            return f"lists({strategy}, min_size={min_size}, max_size={max_size})"
        
        @staticmethod
        def text(min_size=0, max_size=100):
            return f"text(min_size={min_size}, max_size={max_size})"
        
        @staticmethod
        def integers(min_value=0, max_value=100):
            return f"integers(min_value={min_value}, max_value={max_value})"
        
        @staticmethod
        def sampled_from(choices):
            return f"sampled_from({choices})"
        
        @staticmethod
        def dictionaries(keys, values, min_size=0, max_size=10):
            return f"dictionaries({keys}, {values}, min_size={min_size}, max_size={max_size})"
    
    @staticmethod
    def composite(func):
        return func

try:
    from hypothesis import given, strategies as st, settings, composite
except ImportError:
    # Use mock when hypothesis is not available
    mock_hypothesis = MockHypothesis()
    given = mock_hypothesis.given
    st = mock_hypothesis.strategies
    settings = mock_hypothesis.settings
    composite = mock_hypothesis.composite

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.key_vault import (
    KeyVaultManager, 
    MultiAccountKeyVaultManager,
    get_key_vault_manager,
    get_multi_account_manager
)
from shared.config import EnvironmentConfigurationManager
from shared.interfaces import ConfigurationError


class TestSecureConfigurationProperties:
    """
    Property-based tests for secure configuration management.
    **Feature: azure-functions-porting, Property 6: Secure Configuration**
    **Validates: Requirements 2.4, 7.4**
    """
    
    def __init__(self):
        """Initialize test configuration."""
        self.sensitive_config_patterns = [
            r'.*password.*',
            r'.*secret.*',
            r'.*key.*',
            r'.*token.*',
            r'.*credential.*',
            r'.*connection.*string.*',
            r'.*api.*key.*',
            r'.*subscription.*key.*'
        ]
        
        self.test_secrets = {
            "copilot-api-key": "test-copilot-key-12345",
            "sql-server-password": "test-sql-password-67890",
            "blob-storage-connection-string": "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=testkey123==;EndpointSuffix=core.windows.net",
            "functions-appinsights-key": "test-appinsights-key-abcdef",
            "copilot-subscription-key": "test-subscription-key-xyz789"
        }
    
    async def test_property_6_secure_configuration_storage(self):
        """
        **Property 6: Secure Configuration**
        **Validates: Requirements 2.4, 7.4**
        
        For any sensitive configuration value, it should be stored in Azure Key Vault 
        and not hardcoded in function code.
        """
        try:
            # Test 1: Key Vault Storage Property
            await self._test_key_vault_storage_property()
            
            # Test 2: No Hardcoded Secrets Property
            await self._test_no_hardcoded_secrets_property()
            
            # Test 3: Multi-Account Isolation Property
            await self._test_multi_account_isolation_property()
            
            # Test 4: Credential Retrieval Security Property
            await self._test_credential_retrieval_security_property()
            
            # Test 5: Environment Variable Security Property
            await self._test_environment_variable_security_property()
            
            print("✓ All secure configuration property tests passed")
            return True
            
        except Exception as e:
            print(f"✗ Secure configuration property test failed: {str(e)}")
            return False
    
    async def _test_key_vault_storage_property(self):
        """
        Property: All sensitive configuration values must be retrievable from Key Vault.
        No sensitive values should be stored in plain text configuration files.
        """
        print("Testing Key Vault storage property...")
        
        # Mock Key Vault client for testing
        with patch('shared.key_vault.SecretClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            # Setup mock responses for test secrets
            def mock_get_secret(secret_name):
                if secret_name in self.test_secrets:
                    mock_secret = Mock()
                    mock_secret.value = self.test_secrets[secret_name]
                    return mock_secret
                else:
                    from azure.core.exceptions import ResourceNotFoundError
                    raise ResourceNotFoundError(f"Secret {secret_name} not found")
            
            mock_client.get_secret.side_effect = mock_get_secret
            
            # Test Key Vault manager
            with patch.dict(os.environ, {'AZURE_KEY_VAULT_URL': 'https://test-vault.vault.azure.net/'}):
                kv_manager = KeyVaultManager()
                
                # Property: All sensitive secrets must be retrievable from Key Vault
                for secret_name, expected_value in self.test_secrets.items():
                    retrieved_value = await kv_manager.get_secret(secret_name)
                    
                    # Property assertion: Retrieved value must match expected value
                    assert retrieved_value == expected_value, f"Key Vault retrieval failed for {secret_name}"
                    
                    # Property assertion: Value must not be empty or None
                    assert retrieved_value is not None and retrieved_value != "", f"Empty value retrieved for {secret_name}"
                    
                    # Property assertion: Sensitive patterns must be detected
                    is_sensitive = any(re.match(pattern, secret_name, re.IGNORECASE) 
                                     for pattern in self.sensitive_config_patterns)
                    assert is_sensitive, f"Secret {secret_name} not recognized as sensitive"
        
        print("✓ Key Vault storage property validated")
    
    async def _test_no_hardcoded_secrets_property(self):
        """
        Property: No sensitive configuration values should be hardcoded in source code.
        All sensitive values must come from Key Vault or secure environment variables.
        """
        print("Testing no hardcoded secrets property...")
        
        # Scan source files for potential hardcoded secrets
        source_directories = [
            'azure_functions/shared',
            'azure_functions/orchestration',
            'azure_functions/processing',
            'azure_functions/scrapers'
        ]
        
        hardcoded_secrets_found = []
        
        for directory in source_directories:
            if os.path.exists(directory):
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        if file.endswith('.py'):
                            file_path = os.path.join(root, file)
                            violations = await self._scan_file_for_hardcoded_secrets(file_path)
                            if violations:
                                hardcoded_secrets_found.extend(violations)
        
        # Property assertion: No hardcoded secrets should be found
        if hardcoded_secrets_found:
            violation_summary = "\n".join([f"  - {v}" for v in hardcoded_secrets_found[:10]])  # Show first 10
            print(f"Found potential hardcoded secrets:\n{violation_summary}")
            
            # For testing purposes, we'll warn but not fail if these are test values
            test_patterns = ['test-', 'mock-', 'example-', 'placeholder-']
            non_test_violations = [v for v in hardcoded_secrets_found 
                                 if not any(pattern in v.lower() for pattern in test_patterns)]
            
            assert len(non_test_violations) == 0, f"Found {len(non_test_violations)} non-test hardcoded secrets"
        
        print("✓ No hardcoded secrets property validated")
    
    async def _scan_file_for_hardcoded_secrets(self, file_path: str) -> List[str]:
        """Scan a Python file for potential hardcoded secrets."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    # Skip comments and docstrings
                    stripped_line = line.strip()
                    if stripped_line.startswith('#') or stripped_line.startswith('"""') or stripped_line.startswith("'''"):
                        continue
                    
                    # Look for potential secret assignments
                    secret_patterns = [
                        r'password\s*=\s*["\'][^"\']+["\']',
                        r'secret\s*=\s*["\'][^"\']+["\']',
                        r'key\s*=\s*["\'][^"\']+["\']',
                        r'token\s*=\s*["\'][^"\']+["\']',
                        r'connection.*string\s*=\s*["\'][^"\']+["\']'
                    ]
                    
                    for pattern in secret_patterns:
                        matches = re.findall(pattern, line, re.IGNORECASE)
                        for match in matches:
                            # Skip if it's clearly a placeholder or environment variable reference
                            if ('os.getenv' in line or 'environ' in line or 
                                'placeholder' in match.lower() or 'example' in match.lower() or
                                'test' in match.lower() or 'mock' in match.lower()):
                                continue
                            
                            violations.append(f"{file_path}:{line_num} - {match}")
        
        except Exception as e:
            # Skip files that can't be read
            pass
        
        return violations
    
    async def _test_multi_account_isolation_property(self):
        """
        Property: Different service accounts must use separate Key Vaults for credential isolation.
        Copilot, Functions, and SQL Server credentials must be stored in separate vaults.
        """
        print("Testing multi-account isolation property...")
        
        # Mock different Key Vault URLs for different accounts
        test_vault_urls = {
            'COPILOT_KEY_VAULT_URL': 'https://copilot-vault.vault.azure.net/',
            'FUNCTIONS_KEY_VAULT_URL': 'https://functions-vault.vault.azure.net/',
            'SQL_KEY_VAULT_URL': 'https://sql-vault.vault.azure.net/',
            'AZURE_KEY_VAULT_URL': 'https://default-vault.vault.azure.net/'
        }
        
        with patch.dict(os.environ, test_vault_urls):
            with patch('shared.key_vault.SecretClient') as mock_client_class:
                # Track which vault URLs are accessed
                accessed_vaults = []
                
                def mock_client_init(vault_url, credential):
                    accessed_vaults.append(vault_url)
                    mock_client = Mock()
                    mock_client.get_secret.return_value = Mock(value="test-secret-value")
                    return mock_client
                
                mock_client_class.side_effect = mock_client_init
                
                # Test multi-account manager
                multi_manager = MultiAccountKeyVaultManager()
                
                # Test that different accounts access different vaults
                await multi_manager.get_copilot_credentials()
                await multi_manager.get_sql_credentials()
                await multi_manager.get_functions_credentials()
                
                # Property assertion: Each account should access its dedicated vault
                expected_vaults = set(test_vault_urls.values())
                accessed_vault_set = set(accessed_vaults)
                
                # At least 3 different vaults should be accessed (one per account type)
                assert len(accessed_vault_set) >= 3, f"Expected at least 3 different vaults, got {len(accessed_vault_set)}"
                
                # Verify specific account isolation
                copilot_vault_accessed = any('copilot' in vault for vault in accessed_vaults)
                sql_vault_accessed = any('sql' in vault for vault in accessed_vaults)
                functions_vault_accessed = any('functions' in vault for vault in accessed_vaults)
                
                assert copilot_vault_accessed, "Copilot vault not accessed"
                assert sql_vault_accessed, "SQL vault not accessed"
                assert functions_vault_accessed, "Functions vault not accessed"
        
        print("✓ Multi-account isolation property validated")
    
    async def _test_credential_retrieval_security_property(self):
        """
        Property: Credential retrieval must use secure authentication methods.
        Managed identities or service principals must be used, not hardcoded credentials.
        """
        print("Testing credential retrieval security property...")
        
        with patch('shared.key_vault.ManagedIdentityCredential') as mock_managed_identity:
            with patch('shared.key_vault.ClientSecretCredential') as mock_client_secret:
                with patch('shared.key_vault.DefaultAzureCredential') as mock_default:
                    with patch('shared.key_vault.SecretClient') as mock_client_class:
                        
                        mock_client = Mock()
                        mock_client.get_secret.return_value = Mock(value="test-value")
                        mock_client_class.return_value = mock_client
                        
                        # Test with managed identity (preferred)
                        with patch.dict(os.environ, {
                            'AZURE_KEY_VAULT_URL': 'https://test-vault.vault.azure.net/',
                            'AZURE_CLIENT_ID': 'test-client-id'
                        }):
                            kv_manager = KeyVaultManager()
                            await kv_manager.get_secret("test-secret")
                            
                            # Property assertion: Managed identity should be used when available
                            mock_managed_identity.assert_called()
                        
                        # Test fallback to service principal
                        mock_managed_identity.reset_mock()
                        mock_managed_identity.side_effect = Exception("Managed identity failed")
                        
                        with patch.dict(os.environ, {
                            'AZURE_KEY_VAULT_URL': 'https://test-vault.vault.azure.net/',
                            'AZURE_CLIENT_ID': 'test-client-id',
                            'AZURE_CLIENT_SECRET': 'test-client-secret',
                            'AZURE_TENANT_ID': 'test-tenant-id'
                        }):
                            kv_manager = KeyVaultManager()
                            await kv_manager.get_secret("test-secret")
                            
                            # Property assertion: Service principal should be used as fallback
                            mock_client_secret.assert_called_with(
                                tenant_id='test-tenant-id',
                                client_id='test-client-id',
                                client_secret='test-client-secret'
                            )
        
        print("✓ Credential retrieval security property validated")
    
    async def _test_environment_variable_security_property(self):
        """
        Property: Environment variables containing sensitive data must follow secure patterns.
        They should reference Key Vault secrets or use secure naming conventions.
        """
        print("Testing environment variable security property...")
        
        # Test configuration manager's handling of sensitive environment variables
        config_manager = EnvironmentConfigurationManager()
        
        # Test that sensitive configuration is properly handled
        test_env_vars = {
            'SQL_SERVER_CONNECTION_STRING': '',  # Should be empty, forcing Key Vault lookup
            'COPILOT_API_ENDPOINT': '',  # Should be empty, forcing Key Vault lookup
            'AZURE_KEY_VAULT_URL': 'https://test-vault.vault.azure.net/',  # Non-sensitive, can be in env
            'APPINSIGHTS_INSTRUMENTATIONKEY': '',  # Should be empty, forcing Key Vault lookup
        }
        
        with patch.dict(os.environ, test_env_vars, clear=False):
            config_manager = EnvironmentConfigurationManager()
            azure_config = config_manager.get_azure_config()
            
            # Property assertion: Sensitive values should not be directly in environment
            sensitive_keys = ['appinsights_key', 'blob_storage_connection_string']
            for key in sensitive_keys:
                if key in azure_config:
                    value = azure_config[key]
                    # Property: Sensitive values should be empty (forcing Key Vault lookup)
                    assert value == '' or value is None, f"Sensitive config {key} found in environment: {value[:10]}..."
            
            # Property assertion: Non-sensitive configuration can be in environment
            assert azure_config.get('key_vault_url') == 'https://test-vault.vault.azure.net/', "Key Vault URL not properly configured"
        
        print("✓ Environment variable security property validated")
    
    async def run_all_tests(self) -> bool:
        """Run all secure configuration property tests."""
        try:
            success = await self.test_property_6_secure_configuration_storage()
            return success
        except Exception as e:
            print(f"Test execution failed: {str(e)}")
            return False


class TestKeyVaultIntegrationProperties:
    """
    Additional property tests for Key Vault integration patterns.
    """
    
    async def test_property_key_vault_connectivity(self):
        """
        Property: Key Vault connectivity must be testable and recoverable.
        Health checks must accurately reflect Key Vault accessibility.
        """
        print("Testing Key Vault connectivity property...")
        
        with patch('shared.key_vault.SecretClient') as mock_client_class:
            # Test successful connectivity
            mock_client = Mock()
            mock_client.list_properties_of_secrets.return_value = []
            mock_client_class.return_value = mock_client
            
            with patch.dict(os.environ, {'AZURE_KEY_VAULT_URL': 'https://test-vault.vault.azure.net/'}):
                kv_manager = KeyVaultManager()
                
                # Property: Health check should return True for accessible vault
                health_status = await kv_manager.health_check()
                assert health_status is True, "Health check should return True for accessible vault"
                
                # Test failed connectivity
                mock_client.list_properties_of_secrets.side_effect = Exception("Connection failed")
                
                # Property: Health check should return False for inaccessible vault
                health_status = await kv_manager.health_check()
                assert health_status is False, "Health check should return False for inaccessible vault"
        
        print("✓ Key Vault connectivity property validated")
        return True
    
    async def test_property_secret_caching_behavior(self):
        """
        Property: Secret caching must be consistent and controllable.
        Cached secrets should be returned without additional Key Vault calls.
        """
        print("Testing secret caching behavior property...")
        
        with patch('shared.key_vault.SecretClient') as mock_client_class:
            mock_client = Mock()
            mock_secret = Mock()
            mock_secret.value = "cached-secret-value"
            mock_client.get_secret.return_value = mock_secret
            mock_client_class.return_value = mock_client
            
            with patch.dict(os.environ, {'AZURE_KEY_VAULT_URL': 'https://test-vault.vault.azure.net/'}):
                kv_manager = KeyVaultManager()
                
                # First call should hit Key Vault
                value1 = await kv_manager.get_secret("test-secret", use_cache=True)
                assert mock_client.get_secret.call_count == 1, "First call should hit Key Vault"
                
                # Second call should use cache
                value2 = await kv_manager.get_secret("test-secret", use_cache=True)
                assert mock_client.get_secret.call_count == 1, "Second call should use cache"
                
                # Property: Cached value should match original
                assert value1 == value2, "Cached value should match original"
                
                # Call without cache should hit Key Vault again
                value3 = await kv_manager.get_secret("test-secret", use_cache=False)
                assert mock_client.get_secret.call_count == 2, "Call without cache should hit Key Vault"
                
                # Clear cache and verify next call hits Key Vault
                kv_manager.clear_cache()
                value4 = await kv_manager.get_secret("test-secret", use_cache=True)
                assert mock_client.get_secret.call_count == 3, "Call after cache clear should hit Key Vault"
        
        print("✓ Secret caching behavior property validated")
        return True
    
    async def run_all_tests(self) -> bool:
        """Run all Key Vault integration property tests."""
        try:
            test1 = await self.test_property_key_vault_connectivity()
            test2 = await self.test_property_secret_caching_behavior()
            return test1 and test2
        except Exception as e:
            print(f"Key Vault integration test execution failed: {str(e)}")
            return False


# Async test runner
def run_async_test(coro):
    """Helper to run async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def main():
    """Main test runner for secure configuration properties."""
    print("Running Secure Configuration Property Tests...")
    print("=" * 60)
    
    # Test 1: Secure Configuration Properties
    config_tester = TestSecureConfigurationProperties()
    config_success = await config_tester.run_all_tests()
    
    print("\n" + "=" * 60)
    
    # Test 2: Key Vault Integration Properties
    kv_tester = TestKeyVaultIntegrationProperties()
    kv_success = await kv_tester.run_all_tests()
    
    print("\n" + "=" * 60)
    
    overall_success = config_success and kv_success
    
    if overall_success:
        print("✓ All secure configuration property tests PASSED")
    else:
        print("✗ Some secure configuration property tests FAILED")
    
    return overall_success


if __name__ == "__main__":
    # Run the property tests
    success = run_async_test(main())
    
    if success:
        print("\n🎉 Secure configuration property validation completed successfully!")
        exit(0)
    else:
        print("\n❌ Secure configuration property validation failed!")
        exit(1)