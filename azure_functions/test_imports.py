import sys
sys.path.append('azure_functions')

try:
    from scrapers.kompas_scraper import scrape_kompas_news
    from scrapers.tempo_scraper import scrape_tempo_news
    from scrapers.bisnis_indonesia_scraper import scrape_bisnis_indonesia_news
    from scrapers.theguardian_scraper import scrape_theguardian_news
    from scrapers.oilprice_scraper import scrape_oilprice_news
    from scrapers.kontan_scraper import scrape_kontan_news
    from scrapers.cnbc_indonesia_scraper import scrape_cnbc_indonesia_news
    print('✓ All scraper imports successful')
except ImportError as e:
    print(f'✗ Import error: {e}')
except Exception as e:
    print(f'✗ Other error: {e}')