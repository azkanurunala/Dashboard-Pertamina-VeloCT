"""
Quick setup script for Azure Functions News Scraping System.
This script provides step-by-step guidance for completing the setup.
"""

import os
import sys
import subprocess
import json
from datetime import datetime


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"🔧 {title}")
    print("=" * 60)


def print_step(step_num, title, description):
    """Print a formatted step."""
    print(f"\n📋 Step {step_num}: {title}")
    print(f"   {description}")


def check_prerequisites():
    """Check if required tools are installed."""
    print_header("Checking Prerequisites")
    
    checks = []
    
    # Check Python
    try:
        python_version = sys.version.split()[0]
        print(f"✅ Python {python_version} - OK")
        checks.append(("Python", True))
    except:
        print("❌ Python - Not found")
        checks.append(("Python", False))
    
    # Check pip
    try:
        result = subprocess.run(["pip", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ pip - OK")
            checks.append(("pip", True))
        else:
            print("❌ pip - Not working")
            checks.append(("pip", False))
    except:
        print("❌ pip - Not found")
        checks.append(("pip", False))
    
    # Check pyodbc
    try:
        import pyodbc
        print(f"✅ pyodbc - OK")
        checks.append(("pyodbc", True))
    except ImportError:
        print("❌ pyodbc - Not installed")
        checks.append(("pyodbc", False))
    
    # Check Azure CLI
    try:
        result = subprocess.run(["az", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Azure CLI - OK")
            checks.append(("Azure CLI", True))
        else:
            print("❌ Azure CLI - Not working")
            checks.append(("Azure CLI", False))
    except:
        print("❌ Azure CLI - Not installed")
        checks.append(("Azure CLI", False))
    
    # Check Azure Functions Core Tools
    try:
        result = subprocess.run(["func", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Azure Functions Core Tools - OK")
            checks.append(("Azure Functions Core Tools", True))
        else:
            print("❌ Azure Functions Core Tools - Not working")
            checks.append(("Azure Functions Core Tools", False))
    except:
        print("❌ Azure Functions Core Tools - Not installed")
        checks.append(("Azure Functions Core Tools", False))
    
    return checks


def check_configuration():
    """Check configuration files."""
    print_header("Checking Configuration")
    
    # Check .env.azure
    env_file = ".env.azure"
    if os.path.exists(env_file):
        print(f"✅ {env_file} - Found")
        
        # Check connection string
        with open(env_file, 'r') as f:
            content = f.read()
            if "SQL_SERVER_CONNECTION_STRING" in content:
                print("✅ SQL Server connection string - Configured")
            else:
                print("❌ SQL Server connection string - Missing")
    else:
        print(f"❌ {env_file} - Not found")
    
    # Check host.json
    if os.path.exists("host.json"):
        print("✅ host.json - Found")
    else:
        print("❌ host.json - Missing")
    
    # Check requirements.txt
    if os.path.exists("requirements.txt"):
        print("✅ requirements.txt - Found")
    else:
        print("❌ requirements.txt - Missing")


def provide_installation_instructions():
    """Provide installation instructions for missing tools."""
    print_header("Installation Instructions")
    
    print_step(1, "Install Azure CLI", 
               "Download and install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-windows")
    
    print_step(2, "Install Node.js (if not installed)", 
               "Download from: https://nodejs.org/")
    
    print_step(3, "Install Azure Functions Core Tools", 
               "Run: npm install -g azure-functions-core-tools@4 --unsafe-perm true")
    
    print_step(4, "Login to Azure", 
               "Run: az login")


def provide_firewall_instructions():
    """Provide firewall configuration instructions."""
    print_header("Azure SQL Server Firewall Configuration")
    
    print("🔥 IMPORTANT: Your IP address needs to be added to the Azure SQL Server firewall")
    print(f"   Detected IP: 180.252.80.182")
    
    print_step(1, "Using Azure Portal", 
               "Go to Azure Portal > SQL Server 'pei-dashboard' > Networking > Add firewall rule")
    
    print_step(2, "Using Azure CLI", 
               "az sql server firewall-rule create --server pei-dashboard --resource-group PeiDashboard --name LocalDev --start-ip-address 180.252.80.182 --end-ip-address 180.252.80.182")


def provide_deployment_steps():
    """Provide deployment steps."""
    print_header("Deployment Steps")
    
    print_step(1, "Test Database Connection", 
               "python scripts/local-test.py")
    
    print_step(2, "Initialize Database Schema", 
               "python scripts/initialize-database.py")
    
    print_step(3, "Deploy Function App", 
               ".\\scripts\\deploy-functions.ps1 -FunctionAppName 'pei-dashboard'")
    
    print_step(4, "Test Deployment", 
               "Visit: https://pei-dashboard.azurewebsites.net/api/test_function")


def create_quick_commands():
    """Create quick command scripts."""
    print_header("Creating Quick Command Scripts")
    
    # Create test script
    test_script = """@echo off
echo Testing database connection...
python scripts/local-test.py
pause
"""
    
    with open("test-connection.bat", "w") as f:
        f.write(test_script)
    print("✅ Created test-connection.bat")
    
    # Create init script
    init_script = """@echo off
echo Initializing database schema...
python scripts/initialize-database.py
pause
"""
    
    with open("init-database.bat", "w") as f:
        f.write(init_script)
    print("✅ Created init-database.bat")
    
    # Create deploy script (if PowerShell is available)
    deploy_script = """@echo off
echo Deploying to Azure Functions...
powershell -ExecutionPolicy Bypass -File "scripts/deploy-functions.ps1" -FunctionAppName "pei-dashboard"
pause
"""
    
    with open("deploy-functions.bat", "w") as f:
        f.write(deploy_script)
    print("✅ Created deploy-functions.bat")


def main():
    """Main function."""
    print("🚀 Azure Functions News Scraping System - Quick Setup")
    print("=" * 60)
    print("This script will help you complete the setup process.")
    
    # Change to azure_functions directory if not already there
    if not os.path.exists("host.json"):
        if os.path.exists("azure_functions/host.json"):
            os.chdir("azure_functions")
            print("📁 Changed to azure_functions directory")
        else:
            print("❌ Cannot find azure_functions directory")
            return 1
    
    # Check prerequisites
    checks = check_prerequisites()
    
    # Check configuration
    check_configuration()
    
    # Determine what needs to be done
    missing_tools = [name for name, status in checks if not status]
    
    if missing_tools:
        print(f"\n⚠️ Missing tools: {', '.join(missing_tools)}")
        provide_installation_instructions()
    
    # Always show firewall instructions (main blocker)
    provide_firewall_instructions()
    
    # Show deployment steps
    provide_deployment_steps()
    
    # Create quick command scripts
    create_quick_commands()
    
    # Final summary
    print_header("Summary")
    print("📋 What you need to do:")
    print("1. ⚠️  Add your IP (180.252.80.182) to Azure SQL Server firewall")
    
    if "Azure CLI" in missing_tools:
        print("2. 📥 Install Azure CLI")
    
    if "Azure Functions Core Tools" in missing_tools:
        print("3. 📥 Install Azure Functions Core Tools")
    
    print("4. 🧪 Test database connection: python scripts/local-test.py")
    print("5. 🗄️  Initialize database: python scripts/initialize-database.py")
    print("6. 🚀 Deploy functions: .\\scripts\\deploy-functions.ps1 -FunctionAppName 'pei-dashboard'")
    
    print("\n💡 Quick commands created:")
    print("   - test-connection.bat")
    print("   - init-database.bat") 
    print("   - deploy-functions.bat")
    
    print("\n🎯 Priority: Fix the firewall rule first, then everything else will work!")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)