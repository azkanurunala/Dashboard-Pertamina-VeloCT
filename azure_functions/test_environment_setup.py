#!/usr/bin/env python3
"""
Test script to verify environment setup is working correctly.
Tests basic connectivity and configuration loading.
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def load_environment():
    """Load environment variables from .env file."""
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        print("❌ .env file not found!")
        return False
    
    print("✅ .env file found")
    
    # Simple .env parser
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes if present
                value = value.strip('"\'')
                os.environ[key] = value
    
    return True

def test_database_config():
    """Test database configuration."""
    print("\n🔍 Testing Database Configuration...")
    
    connection_string = os.getenv('AZURE_SQL_CONNECTION_STRING')
    if connection_string and 'pei-dashboard.database.windows.net' in connection_string:
        print("✅ Database connection string configured")
        return True
    else:
        print("❌ Database connection string missing or invalid")
        return False

def test_key_vault_config():
    """Test Key Vault configuration."""
    print("\n🔍 Testing Key Vault Configuration...")
    
    vault_url = os.getenv('AZURE_KEY_VAULT_URL')
    tenant_id = os.getenv('AZURE_TENANT_ID')
    
    if vault_url == 'https://peidashboard.vault.azure.net/':
        print("✅ Key Vault URL configured correctly")
    else:
        print(f"❌ Key Vault URL incorrect: {vault_url}")
        return False
    
    if tenant_id == '16aa065d-2fd1-4cc3-a18b-bc36dddcac40':
        print("✅ Tenant ID configured correctly")
    else:
        print(f"❌ Tenant ID incorrect: {tenant_id}")
        return False
    
    return True

def test_storage_config():
    """Test storage configuration."""
    print("\n🔍 Testing Storage Configuration...")
    
    storage_connection = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    if storage_connection:
        print("✅ Storage connection string configured")
        return True
    else:
        print("❌ Storage connection string missing")
        return False

def test_test_mode():
    """Test that we're in test mode."""
    print("\n🔍 Testing Test Mode Configuration...")
    
    test_mode = os.getenv('TEST_MODE', '').lower()
    use_mocks = os.getenv('USE_MOCK_SERVICES', '').lower()
    
    if test_mode == 'true':
        print("✅ Test mode enabled")
    else:
        print("❌ Test mode not enabled")
        return False
    
    if use_mocks == 'true':
        print("✅ Mock services enabled")
    else:
        print("❌ Mock services not enabled")
        return False
    
    return True

def test_imports():
    """Test that required modules can be imported."""
    print("\n🔍 Testing Python Module Imports...")
    
    modules_to_test = [
        'azure.identity',
        'azure.keyvault.secrets', 
        'azure.storage.blob',
        'hypothesis',
        'pytest'
    ]
    
    all_good = True
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✅ {module} - OK")
        except ImportError as e:
            print(f"❌ {module} - FAILED: {e}")
            all_good = False
    
    return all_good

def main():
    """Main test function."""
    print("🧪 Environment Setup Test")
    print("=" * 50)
    
    tests = [
        ("Load Environment", load_environment),
        ("Database Config", test_database_config),
        ("Key Vault Config", test_key_vault_config),
        ("Storage Config", test_storage_config),
        ("Test Mode", test_test_mode),
        ("Module Imports", test_imports)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} - EXCEPTION: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Environment is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the configuration.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)