"""Test CNBC import to find errors."""
import sys
import os
import traceback

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing imports...")

try:
    print("1. Testing scrapers.cnbc_scraper import...")
    from scrapers.cnbc_scraper import CNBCNewsScraper
    print("   OK: CNBCNewsScraper imported successfully")
except Exception as e:
    print(f"   FAILED: {e}")
    traceback.print_exc()

try:
    print("2. Testing shared.models import...")
    from shared.models import NewsArticle
    print("   OK: NewsArticle imported successfully")
except Exception as e:
    print(f"   FAILED: {e}")
    traceback.print_exc()

try:
    print("3. Testing shared.database_handler import...")
    from shared.database_handler import DatabaseHandler
    print("   OK: DatabaseHandler imported successfully")
except Exception as e:
    print(f"   FAILED: {e}")
    traceback.print_exc()

try:
    print("4. Testing shared.config import...")
    from shared.config import get_database_connection_string
    print("   OK: get_database_connection_string imported successfully")
except Exception as e:
    print(f"   FAILED: {e}")
    traceback.print_exc()

try:
    print("5. Testing shared.logging_config import...")
    from shared.logging_config import setup_logging
    print("   OK: setup_logging imported successfully")
except Exception as e:
    print(f"   FAILED: {e}")
    traceback.print_exc()

try:
    print("6. Testing shared.azure_logging import...")
    from shared.azure_logging import AzureLoggingManager
    print("   OK: AzureLoggingManager imported successfully")
except Exception as e:
    print(f"   FAILED: {e}")
    traceback.print_exc()

try:
    print("7. Testing full function import...")
    from cnbc_scraper_function import main
    print("   OK: main function imported successfully")
except Exception as e:
    print(f"   FAILED: {e}")
    traceback.print_exc()

print("\nTest complete!")
