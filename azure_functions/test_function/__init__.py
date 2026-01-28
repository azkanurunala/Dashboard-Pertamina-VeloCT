"""
Test function untuk verifikasi deployment Azure Functions.
Function ini akan test koneksi database dan konfigurasi dasar.
"""

import logging
import json
import os
from datetime import datetime
import azure.functions as func

# Import config helpers
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from shared.config import get_database_connection_string, _get_key_vault_secret


def main(req: func.HttpRequest) -> func.HttpResponse:
    """Main function untuk test endpoint."""
    logging.info('Test function processed a request.')
    
    try:
        # Test basic configuration
        config_status = test_configuration()
        
        # Test database connection (basic)
        db_status = test_database_config()
        
        # Test Azure services configuration
        azure_status = test_azure_services()
        
        # Compile results
        results = {
            "status": "success",
            "message": "Azure Functions News Scraping System Test",
            "timestamp": datetime.utcnow().isoformat(),
            "tests": {
                "configuration": config_status,
                "database": db_status,
                "azure_services": azure_status
            },
            "environment": {
                "python_version": get_python_version(),
                "function_runtime": os.getenv('FUNCTIONS_WORKER_RUNTIME', 'unknown'),
                "environment": os.getenv('ENVIRONMENT', 'unknown')
            }
        }
        
        # Determine overall status
        all_tests_passed = all([
            config_status.get('passed', False),
            db_status.get('passed', False),
            azure_status.get('passed', False)
        ])
        
        status_code = 200 if all_tests_passed else 206  # 206 = Partial Content
        
        return func.HttpResponse(
            json.dumps(results, indent=2),
            status_code=status_code,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Test function error: {str(e)}")
        
        error_response = {
            "status": "error",
            "message": f"Test function failed: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return func.HttpResponse(
            json.dumps(error_response, indent=2),
            status_code=500,
            mimetype="application/json"
        )


def test_configuration() -> dict:
    """Test basic configuration."""
    try:
        required_vars = [
            'FUNCTIONS_WORKER_RUNTIME',
            'FUNCTIONS_EXTENSION_VERSION',
            'WEBSITE_SITE_NAME'
        ]
        
        missing_vars = []
        present_vars = []
        
        for var in required_vars:
            if os.getenv(var):
                present_vars.append(var)
            else:
                missing_vars.append(var)
        
        return {
            "passed": len(missing_vars) == 0,
            "present_variables": present_vars,
            "missing_variables": missing_vars,
            "message": "Configuration check completed"
        }
        
    except Exception as e:
        return {
            "passed": False,
            "error": str(e),
            "message": "Configuration check failed"
        }


def test_database_config() -> dict:
    """Test database configuration and Key Vault access."""
    try:
        # Test environment variable
        env_var = os.getenv('DatabaseConnectionString')
        
        # Test Key Vault access
        key_vault_url = os.getenv('KEY_VAULT_URL')
        kv_secret = None
        kv_error = None
        
        if key_vault_url:
            try:
                kv_secret = _get_key_vault_secret('DatabaseConnectionString')
            except Exception as e:
                kv_error = str(e)
        
        # Try to get connection string using our helper
        connection_string = None
        helper_error = None
        try:
            connection_string = get_database_connection_string()
        except Exception as e:
            helper_error = str(e)
        
        return {
            "passed": connection_string is not None,
            "env_variable_present": env_var is not None,
            "env_variable_value": env_var[:50] + "..." if env_var and len(env_var) > 50 else env_var,
            "key_vault_url": key_vault_url,
            "key_vault_secret_retrieved": kv_secret is not None,
            "key_vault_error": kv_error,
            "connection_string_retrieved": connection_string is not None,
            "helper_error": helper_error,
            "message": "Database configuration check completed"
        }
            
    except Exception as e:
        return {
            "passed": False,
            "error": str(e),
            "message": "Database configuration check failed"
        }


def test_azure_services() -> dict:
    """Test Azure services configuration."""
    try:
        services = {
            "key_vault": os.getenv('AZURE_KEY_VAULT_URL'),
            "blob_storage": os.getenv('BLOB_STORAGE_CONNECTION_STRING'),
            "app_insights": os.getenv('APPINSIGHTS_INSTRUMENTATIONKEY'),
            "app_insights_connection": os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING')
        }
        
        configured_services = []
        missing_services = []
        
        for service, config in services.items():
            if config:
                configured_services.append(service)
            else:
                missing_services.append(service)
        
        return {
            "passed": len(missing_services) <= 1,  # Allow 1 missing service
            "configured_services": configured_services,
            "missing_services": missing_services,
            "message": f"Azure services check completed ({len(configured_services)}/{len(services)} configured)"
        }
        
    except Exception as e:
        return {
            "passed": False,
            "error": str(e),
            "message": "Azure services check failed"
        }


def get_python_version() -> str:
    """Get Python version."""
    try:
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    except:
        return "unknown"