"""
Script to update all scraper functions with comprehensive logging.
This script adds AzureLoggingManager to all scraper functions.
"""

import os
import re
from pathlib import Path

# List of all scraper functions
SCRAPER_FUNCTIONS = [
    "kompas_scraper_function",
    "kontan_scraper_function",
    "bps_scraper_function",
    "bisnis_indonesia_scraper_function",
    "cnbc_indonesia_scraper_function",
    "oilprice_scraper_function",
    "theguardian_scraper_function",
    "reuters_scraper_function",
    "tempo_scraper_function",
    "cnn_scraper_function"
]

def get_scraper_source_name(function_name: str) -> str:
    """Extract source name from function name."""
    # Remove _scraper_function suffix and convert to title case
    source = function_name.replace("_scraper_function", "")
    source_map = {
        "kompas": "Kompas",
        "kontan": "Kontan",
        "bps": "BPS",
        "bisnis_indonesia": "Bisnis Indonesia",
        "cnbc_indonesia": "CNBC Indonesia",
        "oilprice": "OilPrice",
        "theguardian": "The Guardian",
        "reuters": "Reuters",
        "tempo": "Tempo",
        "cnn": "CNN"
    }
    return source_map.get(source, source.title())

def add_logging_import(content: str) -> str:
    """Add AzureLoggingManager import if not present."""
    if "from ..shared.azure_logging import AzureLoggingManager" in content:
        return content
    
    # Find the last import statement
    import_pattern = r'(try:\s+from \.\.shared\.logging_config import setup_logging.*?raise\s+)'
    match = re.search(import_pattern, content, re.DOTALL)
    
    if match:
        # Add after logging_config import
        new_import = '''
try:
    from ..shared.azure_logging import AzureLoggingManager
    logging.info("✓ Successfully imported AzureLoggingManager")
except Exception as e:
    logging.error(f"✗ IMPORT ERROR - AzureLoggingManager: {str(e)}", exc_info=True)
    raise

'''
        content = content[:match.end()] + new_import + content[match.end():]
    
    return content

def update_main_function(content: str, source_name: str, function_name: str) -> str:
    """Update main function to use AzureLoggingManager."""
    
    # Pattern to find the main function
    main_pattern = r'def main\(req: func\.HttpRequest\) -> func\.HttpResponse:.*?(?=\ndef |\Z)'
    
    # New main function with logging
    new_main = f'''def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main Azure Function entry point for {source_name} news scraping.
    
    Expected parameters:
    - keywords: List of keywords to search for (optional)
    - start_date: Start date in YYYY-MM-DD format (optional, defaults to 7 days ago)
    - end_date: End date in YYYY-MM-DD format (optional, defaults to today)
    - save_to_db: Whether to save results to database (optional, defaults to true)
    """
    # Initialize comprehensive logging
    correlation_id = req.headers.get('x-correlation-id')
    log_manager = AzureLoggingManager(
        function_name="{function_name}",
        correlation_id=correlation_id
    )
    
    try:
        # Parse request parameters
        params = _parse_request_parameters(req)
        
        # Log function start
        log_manager.log_function_start(
            trigger_type="http",
            parameters={{
                "keywords": params['keywords'],
                "start_date": params['start_date'].isoformat(),
                "end_date": params['end_date'].isoformat(),
                "save_to_db": params['save_to_db']
            }}
        )
        
        # Run the scraping operation
        result = asyncio.run(_scrape_news(params, log_manager))
        
        # Log function completion
        log_manager.log_function_end(
            status="success",
            result_summary={{
                "articles_found": result['results']['articles_found'],
                "articles_saved": result['results']['articles_saved'],
                "execution_time_seconds": result['execution_time_seconds']
            }}
        )
        
        # Return successful response
        return func.HttpResponse(
            json.dumps(result, indent=2, default=str),
            status_code=200,
            mimetype="application/json"
        )
        
    except ValueError as e:
        # Log parameter validation error
        log_manager.log_error(
            error=e,
            context_data={{
                "error_type": "parameter_validation",
                "operation": "parse_parameters"
            }}
        )
        
        log_manager.log_function_end(
            status="failed",
            result_summary={{"error": "Invalid parameters", "message": str(e)}}
        )
        
        return func.HttpResponse(
            json.dumps({{
                "status": "error",
                "error": "Invalid parameters",
                "message": str(e),
                "error_type": "ValueError",
                "execution_id": log_manager.execution_id,
                "timestamp": datetime.utcnow().isoformat()
            }}),
            status_code=400,
            mimetype="application/json"
        )
        
    except Exception as e:
        # Log unexpected error
        log_manager.log_error(
            error=e,
            context_data={{
                "error_type": "unexpected_error",
                "operation": "scraping",
                "parameters": params if 'params' in locals() else {{}}
            }}
        )
        
        log_manager.log_function_end(
            status="failed",
            result_summary={{"error": "Internal server error", "message": str(e)}}
        )
        
        # Get detailed error info
        import traceback
        error_traceback = traceback.format_exc()
        
        return func.HttpResponse(
            json.dumps({{
                "status": "error",
                "error": "Internal server error",
                "message": str(e),
                "error_type": type(e).__name__,
                "execution_id": log_manager.execution_id,
                "traceback": error_traceback.split('\\n')[-5:],  # Last 5 lines
                "timestamp": datetime.utcnow().isoformat()
            }}),
            status_code=500,
            mimetype="application/json"
        )


'''
    
    content = re.sub(main_pattern, new_main, content, flags=re.DOTALL)
    return content

def update_scrape_function(content: str, source_name: str) -> str:
    """Update scrape function to use log_manager."""
    
    # Find the scrape function (it might have different names)
    scrape_patterns = [
        r'async def _scrape_\w+_news\(params: Dict\[str, Any\]\) -> Dict\[str, Any\]:',
        r'async def _scrape_news\(params: Dict\[str, Any\]\) -> Dict\[str, Any\]:'
    ]
    
    for pattern in scrape_patterns:
        if re.search(pattern, content):
            # Update function signature to include log_manager
            content = re.sub(
                pattern,
                lambda m: m.group(0).replace(
                    'params: Dict[str, Any])',
                    'params: Dict[str, Any], log_manager: AzureLoggingManager)'
                ),
                content
            )
            break
    
    # Add logging calls at key points
    # This is a simplified version - you may need to customize per scraper
    
    return content

def update_scraper_function(function_name: str):
    """Update a single scraper function with comprehensive logging."""
    source_name = get_scraper_source_name(function_name)
    file_path = Path(f"azure_functions/{function_name}/__init__.py")
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return False
    
    print(f"📝 Updating {function_name} ({source_name})...")
    
    try:
        # Read current content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add import
        content = add_logging_import(content)
        
        # Update main function
        content = update_main_function(content, source_name, function_name)
        
        # Update scrape function
        content = update_scrape_function(content, source_name)
        
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Successfully updated {function_name}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating {function_name}: {e}")
        return False

def main():
    """Update all scraper functions."""
    print("=" * 70)
    print("UPDATING ALL SCRAPER FUNCTIONS WITH COMPREHENSIVE LOGGING")
    print("=" * 70)
    print()
    
    success_count = 0
    fail_count = 0
    
    for function_name in SCRAPER_FUNCTIONS:
        if update_scraper_function(function_name):
            success_count += 1
        else:
            fail_count += 1
        print()
    
    print("=" * 70)
    print(f"SUMMARY: {success_count} successful, {fail_count} failed")
    print("=" * 70)

if __name__ == "__main__":
    main()
