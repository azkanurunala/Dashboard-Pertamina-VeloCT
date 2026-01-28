"""
Test function to verify all imports work correctly
"""
import logging
import json
from datetime import datetime
import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    """Test all critical imports"""
    logging.info('Testing imports...')
    
    results = {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
        "imports": {}
    }
    
    # Test each import
    imports_to_test = [
        ("azure.functions", "azure.functions"),
        ("requests", "requests"),
        ("beautifulsoup4", "bs4"),
        ("lxml", "lxml"),
        ("aiohttp", "aiohttp"),
        ("pyodbc", "pyodbc"),
        ("scrapers.cnbc_scraper", "..scrapers.cnbc_scraper"),
        ("shared.config", "..shared.config"),
        ("shared.database_handler", "..shared.database_handler"),
        ("shared.models", "..shared.models"),
    ]
    
    for name, import_path in imports_to_test:
        try:
            __import__(import_path.replace("..", "azure_functions").replace(".", "/"))
            results["imports"][name] = {"status": "OK", "error": None}
        except Exception as e:
            results["imports"][name] = {"status": "FAILED", "error": str(e)}
    
    # Check if any failed
    failed = [k for k, v in results["imports"].items() if v["status"] == "FAILED"]
    if failed:
        results["status"] = "partial"
        results["failed_imports"] = failed
    
    return func.HttpResponse(
        json.dumps(results, indent=2),
        status_code=200,
        mimetype="application/json"
    )
