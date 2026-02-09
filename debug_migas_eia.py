import asyncio
import json
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'azure_functions')))

from azure_functions.migas_eia_scraper_function import _scrape_data
from shared.azure_logging import AzureLoggingManager

async def test_migas_eia():
    print("Directly testing Migas EIA scraper logic...")
    log_manager = AzureLoggingManager(function_name="test_migas_eia")
    params = {
        "keywords": ["oil"],
        "start_date": datetime(2024, 1, 1),
        "end_date": datetime(2024, 2, 1),
        "save_to_db": False
    }
    
    try:
        result = await _scrape_data(params, log_manager)
        print("Result:")
        print(json.dumps(result, indent=2, default=str))
    except Exception as e:
        print(f"Exception during scraping: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_migas_eia())
