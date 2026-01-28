"""
Simple test function to check environment variables
"""
import logging
import json
import os
import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    """Test function to check environment configuration"""
    logging.info('Test environment function triggered')
    
    try:
        # Check all relevant environment variables
        env_vars = {
            "DatabaseConnectionString": os.getenv("DatabaseConnectionString", "NOT SET"),
            "StorageConnectionString": os.getenv("StorageConnectionString", "NOT SET"),
            "KEY_VAULT_URL": os.getenv("KEY_VAULT_URL", "NOT SET"),
            "AZURE_CLIENT_ID": os.getenv("AZURE_CLIENT_ID", "NOT SET"),
            "AzureWebJobsStorage": os.getenv("AzureWebJobsStorage", "NOT SET")[:50] + "..." if os.getenv("AzureWebJobsStorage") else "NOT SET",
            "FUNCTIONS_WORKER_RUNTIME": os.getenv("FUNCTIONS_WORKER_RUNTIME", "NOT SET"),
            "FUNCTIONS_EXTENSION_VERSION": os.getenv("FUNCTIONS_EXTENSION_VERSION", "NOT SET"),
            "PYTHON_VERSION": os.getenv("PYTHON_VERSION", "NOT SET"),
        }
        
        # Check if DatabaseConnectionString starts with Key Vault reference
        db_conn = os.getenv("DatabaseConnectionString", "")
        is_keyvault_ref = db_conn.startswith("@Microsoft.KeyVault")
        
        result = {
            "status": "success",
            "message": "Environment check completed",
            "environment_variables": env_vars,
            "database_connection_is_keyvault_reference": is_keyvault_ref,
            "database_connection_preview": db_conn[:100] if db_conn else "NOT SET"
        }
        
        return func.HttpResponse(
            json.dumps(result, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in test function: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "error": str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )
