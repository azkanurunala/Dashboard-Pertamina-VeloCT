
import sys
import os
import traceback

# Add azure_functions to path
sys.path.append(os.path.join(os.getcwd(), 'azure_functions'))

try:
    print("Attempting to import TempoNewsScraper...")
    from scrapers.tempo_scraper import TempoNewsScraper
    print("Import successful. Attempting instantiation...")
    scraper = TempoNewsScraper()
    print("Instantiation successful.")
except Exception:
    print("FAILED:")
    traceback.print_exc()
