"""
Backfill news gap: Feb 13, 2026 - Apr 5, 2026
Jalankan semua scraper yang bisa diakses secara lokal.
"""
import asyncio, sys, os, json
sys.path.insert(0, 'c:/RunningProjects/Dashboard-Pertamina-VeloCT/azure_functions')

# Load settings first before importing modules that read env vars
settings_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\local.settings.json'
with open(settings_path) as f:
    settings = json.load(f)['Values']

os.environ['SQL_SERVER_CONNECTION_STRING'] = settings['SQL_SERVER_CONNECTION_STRING']
os.environ['BPS_API_KEY'] = settings.get('BPS_API_KEY', '8199b1a60c76d284ee3d2228a51b3743')
os.environ['EIA_API_KEY'] = settings.get('EIA_API_KEY', '')
os.environ['SP_USERNAME'] = settings.get('SP_USERNAME', '')
os.environ['SP_PASSWORD'] = settings.get('SP_PASSWORD', '')

from datetime import datetime
from shared.database_handler import DatabaseHandler
from shared.config import config_manager
from orchestration.orchestrator_function import _classify_article_categories

START_DATE = datetime(2026, 2, 13)
END_DATE   = datetime(2026, 4, 5)

# Scraper yang diketahui bisa jalan tanpa Selenium
SCRAPERS_TO_RUN = [
    ('bank_indonesia',  'scrapers.bank_indonesia_scraper',  'BankIndonesiaScraper',  {}),
    ('bps',             'scrapers.bps_scraper',             'BPSScraper',            {'api_key': '8199b1a60c76d284ee3d2228a51b3743'}),
    ('energiesmedia',   'scrapers.energiesmedia_scraper',   'EnergiesMediaScraper',  {}),
    ('scmp',            'scrapers.scmp_scraper',            'SCMPScraper',           {}),
    ('sandp_news',      'scrapers.sandp_news_scraper',      'SAndPNewsScraper',      {}),
    ('bioenergytimes',  'scrapers.bioenergytimes_scraper',  'BioenergyTimesScraper', {}),
    ('bloomberg_technoz','scrapers.bloomberg_technoz_scraper','BloombergTechnozScraper',{}),
    ('kontan_bbm',      'scrapers.kontan_bbm_scraper',      'KontanBBMScraper',      {}),
    ('kontan_biodiesel','scrapers.kontan_biodiesel_scraper','KontanBiodieselScraper',{}),
]

KEYWORDS = [
    "minyak", "energi", "BBM", "biodiesel", "bioetanol", "pertamina",
    "harga minyak", "oil price", "crude", "brent", "energy",
    "indeks", "konsumen", "bi rate", "suku bunga", "inflasi",
    "neraca perdagangan", "ihsg", "rupiah", "dollar"
]


async def run_scraper(name, module_path, class_name, init_kwargs):
    print(f"\n{'='*60}")
    print(f"Scraping: {name} ({START_DATE.date()} to {END_DATE.date()})")
    print(f"{'='*60}")

    try:
        import importlib
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)

        async with cls(**init_kwargs) as scraper:
            articles = await scraper.scrape_news(KEYWORDS, START_DATE, END_DATE)

        print(f"  Berhasil scrape: {len(articles)} artikel")
        return articles

    except Exception as e:
        print(f"  ERROR scraping {name}: {e}")
        return []


async def save_articles(db, articles):
    if not articles:
        return 0

    from shared.models import NewsArticle
    import uuid as _uuid

    categorized = []
    for article in articles:
        categories = _classify_article_categories(article.title, article.content)
        for category in categories:
            # New UUID per (article, category) to avoid PK violation
            new_article = NewsArticle(
                id=str(_uuid.uuid4()),
                title=article.title,
                content=article.content,
                url=article.url,
                source=article.source,
                published_date=article.published_date,
                scraped_date=article.scraped_date,
                keywords=list(article.keywords),
                language=article.language,
                author=article.author,
                category=category
            )
            categorized.append(new_article)

    try:
        await db.save_articles(categorized)
    except Exception as e:
        print(f"  save error: {e}")

    return len(categorized)


async def main():
    print(f"BACKFILL NEWS GAP: {START_DATE.date()} to {END_DATE.date()}")
    print(f"Total scrapers: {len(SCRAPERS_TO_RUN)}\n")

    # Init DB
    db_config = await config_manager.get_database_config()
    db = DatabaseHandler(db_config)

    total_scraped = 0
    total_saved = 0
    results = []

    for name, module_path, class_name, init_kwargs in SCRAPERS_TO_RUN:
        articles = await run_scraper(name, module_path, class_name, init_kwargs)
        total_scraped += len(articles)

        if articles:
            saved = await save_articles(db, articles)
            total_saved += saved
            print(f"  Tersimpan: {saved} row (multi-kategori dari {len(articles)} artikel)")

        results.append((name, len(articles)))

        # Jeda antar scraper
        await asyncio.sleep(2)

    print(f"\n{'='*60}")
    print(f"SELESAI")
    print(f"{'='*60}")
    print(f"Total artikel di-scrape : {total_scraped}")
    print(f"Total row tersimpan     : {total_saved}")
    print(f"\nPer scraper:")
    for name, count in results:
        status = "OK" if count > 0 else "--"
        print(f"  {status} {name:25} : {count} artikel")

asyncio.run(main())
