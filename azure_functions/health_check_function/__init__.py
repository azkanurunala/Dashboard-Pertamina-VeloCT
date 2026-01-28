"""
Health Check Azure Function.
Simple HTTP-triggered function to verify the deployment is working.
"""

import logging
import json
import sys
import os
from datetime import datetime
import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Health check endpoint that tests imports step by step.
    """
    result = {
        "status": "starting",
        "timestamp": datetime.utcnow().isoformat(),
        "python_version": sys.version,
        "sys_path": sys.path[:5],  # First 5 paths
        "import_tests": []
    }
    
    # Add parent directory to path
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    result["parent_dir"] = parent_dir
    result["parent_dir_exists"] = os.path.exists(parent_dir)
    
    # List directories in parent
    try:
        result["parent_contents"] = os.listdir(parent_dir)[:20]
    except Exception as e:
        result["parent_contents_error"] = str(e)
    
    # Test imports one by one
    import_tests = []
    
    # Test 1: Basic shared.models
    try:
        from shared.models import NewsArticle
        import_tests.append({"module": "shared.models.NewsArticle", "status": "success"})
    except Exception as e:
        import_tests.append({"module": "shared.models.NewsArticle", "status": "failed", "error": str(e)})
    
    # Test 2: shared.interfaces
    try:
        from shared.interfaces import INewsScraperFunction
        import_tests.append({"module": "shared.interfaces.INewsScraperFunction", "status": "success"})
    except Exception as e:
        import_tests.append({"module": "shared.interfaces.INewsScraperFunction", "status": "failed", "error": str(e)})
    
    # Test 3: shared.database_handler
    try:
        from shared.database_handler import DatabaseHandler
        import_tests.append({"module": "shared.database_handler.DatabaseHandler", "status": "success"})
    except Exception as e:
        import_tests.append({"module": "shared.database_handler.DatabaseHandler", "status": "failed", "error": str(e)})
    
    # Test 4: shared.config
    try:
        from shared.config import get_database_connection_string
        import_tests.append({"module": "shared.config.get_database_connection_string", "status": "success"})
    except Exception as e:
        import_tests.append({"module": "shared.config.get_database_connection_string", "status": "failed", "error": str(e)})
    
    # Test 5: scrapers.exceptions
    try:
        from scrapers.exceptions import ScrapingError
        import_tests.append({"module": "scrapers.exceptions.ScrapingError", "status": "success"})
    except Exception as e:
        import_tests.append({"module": "scrapers.exceptions.ScrapingError", "status": "failed", "error": str(e)})
    
    # Test 6: scrapers.base_scraper
    try:
        from scrapers.base_scraper import BaseNewsScraper
        import_tests.append({"module": "scrapers.base_scraper.BaseNewsScraper", "status": "success"})
    except Exception as e:
        import_tests.append({"module": "scrapers.base_scraper.BaseNewsScraper", "status": "failed", "error": str(e)})
    
    # Test 7: scrapers.reuters_scraper  
    try:
        from scrapers.reuters_scraper import ReutersNewsScraper
        import_tests.append({"module": "scrapers.reuters_scraper.ReutersNewsScraper", "status": "success"})
    except Exception as e:
        import_tests.append({"module": "scrapers.reuters_scraper.ReutersNewsScraper", "status": "failed", "error": str(e)})
    
    # Test 8: scrapers.cnn_scraper
    try:
        from scrapers.cnn_scraper import CNNNewsScraper
        import_tests.append({"module": "scrapers.cnn_scraper.CNNNewsScraper", "status": "success"})
    except Exception as e:
        import_tests.append({"module": "scrapers.cnn_scraper.CNNNewsScraper", "status": "failed", "error": str(e)})
    
    # Test 9: shared.azure_logging
    try:
        from shared.azure_logging import AzureLoggingManager
        import_tests.append({"module": "shared.azure_logging.AzureLoggingManager", "status": "success"})
    except Exception as e:
        import_tests.append({"module": "shared.azure_logging.AzureLoggingManager", "status": "failed", "error": str(e)})
    
    # Test 10: Import the ACTUAL reuters_scraper_function module
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "reuters_function", 
            os.path.join(parent_dir, "reuters_scraper_function", "__init__.py")
        )
        reuters_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reuters_module)
        import_tests.append({"module": "reuters_scraper_function.__init__", "status": "success", "has_main": hasattr(reuters_module, 'main')})
    except Exception as e:
        import traceback
        import_tests.append({
            "module": "reuters_scraper_function.__init__", 
            "status": "failed", 
            "error": str(e),
            "traceback": traceback.format_exc().split('\n')[-10:]
        })
    
    # Test 11: Import the ACTUAL cnn_scraper_function module
    try:
        spec = importlib.util.spec_from_file_location(
            "cnn_function", 
            os.path.join(parent_dir, "cnn_scraper_function", "__init__.py")
        )
        cnn_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cnn_module)
        import_tests.append({"module": "cnn_scraper_function.__init__", "status": "success", "has_main": hasattr(cnn_module, 'main')})
    except Exception as e:
        import traceback
        import_tests.append({
            "module": "cnn_scraper_function.__init__", 
            "status": "failed", 
            "error": str(e),
            "traceback": traceback.format_exc().split('\n')[-10:]
        })
    
    # Test 12-19: Test all other failing scraper function modules
    failing_functions = [
        "oilprice_scraper_function",
        "theguardian_scraper_function",
        "kompas_scraper_function",
        "tempo_scraper_function",
        "kontan_scraper_function",
        "cnbc_indonesia_scraper_function",
        "bisnis_indonesia_scraper_function",
        "bps_scraper_function"
    ]
    
    for func_name in failing_functions:
        try:
            spec = importlib.util.spec_from_file_location(
                func_name, 
                os.path.join(parent_dir, func_name, "__init__.py")
            )
            if spec and spec.loader:
                test_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(test_module)
                import_tests.append({
                    "module": f"{func_name}.__init__", 
                    "status": "success", 
                    "has_main": hasattr(test_module, 'main')
                })
            else:
                import_tests.append({
                    "module": f"{func_name}.__init__", 
                    "status": "failed", 
                    "error": "Could not find module spec"
                })
        except Exception as e:
            import traceback
            import_tests.append({
                "module": f"{func_name}.__init__", 
                "status": "failed", 
                "error": str(e),
                "traceback": traceback.format_exc().split('\n')[-10:]
            })
    
    result["import_tests"] = import_tests
    
    # Count failures
    failures = [t for t in import_tests if t["status"] == "failed"]
    result["total_tests"] = len(import_tests)
    result["failures"] = len(failures)
    result["status"] = "healthy" if len(failures) == 0 else "unhealthy"
    
    return func.HttpResponse(
        json.dumps(result, indent=2),
        status_code=200 if result["status"] == "healthy" else 500,
        mimetype="application/json"
    )

