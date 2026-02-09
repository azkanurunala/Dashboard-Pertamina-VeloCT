"""
Simple test function to verify new deployment works.
This function just returns basic info without any complex imports.
"""

import azure.functions as func
import json
from datetime import datetime


def main(req: func.HttpRequest) -> func.HttpResponse:
    """Simple test function to verify deployment."""
    
    return func.HttpResponse(
        json.dumps({
            "status": "success",
            "message": "test_new_deploy_function is working!",
            "timestamp": datetime.utcnow().isoformat(),
            "function_name": "test_new_deploy_function"
        }),
        status_code=200,
        mimetype="application/json"
    )
