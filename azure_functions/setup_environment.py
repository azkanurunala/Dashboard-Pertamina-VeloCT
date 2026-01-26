#!/usr/bin/env python3
"""
Environment setup script for Azure Functions project.
Handles dependency installation and environment configuration.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors gracefully."""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} - FAILED")
            print(f"   Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description} - EXCEPTION: {str(e)}")
        return False

def check_python_version():
    """Check if Python version is compatible."""
    print("🔍 Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Requires Python 3.8+")
        return False

def install_dependencies():
    """Install required dependencies with proper error handling."""
    print("\n📦 Installing Dependencies...")
    
    # Core dependencies that must be installed
    core_deps = [
        "azure-identity>=1.15.0",
        "azure-keyvault-secrets>=4.7.0", 
        "azure-storage-blob>=12.19.0",
        "hypothesis>=6.92.1",
        "pytest>=7.4.3",
        "pytest-asyncio>=0.21.1"
    ]
    
    # Try installing with user flag to avoid permission issues
    for dep in core_deps:
        success = run_command(f"python -m pip install --user {dep}", f"Installing {dep}")
        if not success:
            print(f"⚠️  Failed to install {dep}, trying without --user flag...")
            run_command(f"python -m pip install {dep}", f"Installing {dep} (system)")

def create_env_template():
    """Create environment template files."""
    print("\n📝 Creating environment template...")
    
    env_template = """# Azure Functions Environment Configuration
# Copy this to .env and fill in your actual values

# Azure Storage Account
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=your_account;AccountKey=your_key;EndpointSuffix=core.windows.net
AZURE_STORAGE_ACCOUNT_NAME=your_storage_account
AZURE_STORAGE_ACCOUNT_KEY=your_storage_key

# Azure Key Vault
AZURE_KEY_VAULT_URL=https://your-keyvault.vault.azure.net/
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret
AZURE_TENANT_ID=your_tenant_id

# SQL Server Database
SQL_SERVER_CONNECTION_STRING=Driver={ODBC Driver 18 for SQL Server};Server=your_server.database.windows.net;Database=your_database;Uid=your_username;Pwd=your_password;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;

# Microsoft Copilot API
COPILOT_API_ENDPOINT=https://api.copilot.microsoft.com/
COPILOT_API_KEY=your_copilot_key

# Testing Configuration
TEST_MODE=true
USE_MOCK_SERVICES=true
"""
    
    with open(".env.template", "w") as f:
        f.write(env_template)
    
    print("✅ Created .env.template file")
    print("   Please copy this to .env and fill in your actual Azure credentials")

def check_azure_cli():
    """Check if Azure CLI is installed."""
    print("\n🔍 Checking Azure CLI...")
    success = run_command("az --version", "Checking Azure CLI installation")
    if not success:
        print("⚠️  Azure CLI not found. Please install it from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli")
        return False
    return True

def main():
    """Main setup function."""
    print("🚀 Azure Functions Environment Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    install_dependencies()
    
    # Create environment template
    create_env_template()
    
    # Check Azure CLI
    check_azure_cli()
    
    print("\n" + "=" * 50)
    print("🎉 Setup Complete!")
    print("\nNext steps:")
    print("1. Copy .env.template to .env and fill in your Azure credentials")
    print("2. Run: az login (to authenticate with Azure)")
    print("3. Test the setup with: python ./simple_connection_test.py")
    print("4. Run property tests with: python ./tests/test_blob_storage_usage_properties.py")

if __name__ == "__main__":
    main()