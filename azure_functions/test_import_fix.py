"""
Simple test script to verify import fixes work correctly.
Tests that the cnbc_scraper_function's imports work without errors.
"""
import sys
import os

# Add the azure_functions directory to the path
azure_functions_dir = os.path.dirname(os.path.abspath(__file__))
if azure_functions_dir not in sys.path:
    sys.path.insert(0, azure_functions_dir)

print("Testing CNBC scraper imports...")
print(f"Working directory: {azure_functions_dir}")

try:
    print("\n1. Testing shared.models import...")
    from shared.models import NewsArticle, ScrapingConfig
    print("   ✓ shared.models imported successfully")
    
    print("\n2. Testing shared.interfaces import...")
    from shared.interfaces import INewsScraperFunction
    print("   ✓ shared.interfaces imported successfully")
    
    print("\n3. Testing scrapers.exceptions import...")
    from scrapers.exceptions import ScrapingError
    print("   ✓ scrapers.exceptions imported successfully")
    
    print("\n4. Testing scrapers.base_scraper import...")
    from scrapers.base_scraper import BaseNewsScraper
    print("   ✓ scrapers.base_scraper imported successfully")
    
    print("\n5. Testing scrapers.cnbc_scraper import...")
    from scrapers.cnbc_scraper import CNBCNewsScraper
    print("   ✓ scrapers.cnbc_scraper imported successfully")
    
    print("\n" + "="*50)
    print("ALL IMPORTS SUCCESSFUL!")
    print("="*50)
    print("\nThe cnbc_scraper_function should now work in Azure Functions.")
    
except ImportError as e:
    print(f"\n✗ IMPORT ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"\n✗ UNEXPECTED ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
