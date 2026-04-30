"""
News scraper functions for Azure Functions.
This module contains the base scraper class and individual scraper implementations.
"""

import sys
import os

# Add parent directory to Python path for absolute imports in Azure Functions
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from scrapers.base_scraper import BaseNewsScraper
from scrapers.exceptions import ScrapingError, RateLimitError, ValidationError
from scrapers.bps_scraper import BPSScraper, create_bps_scraper

# New scrapers - High Priority
from scrapers.bank_indonesia_scraper import BankIndonesiaScraper, scrape_bank_indonesia_news
from scrapers.bloomberg_technoz_scraper import BloombergTechnozScraper, scrape_bloomberg_technoz_news
from scrapers.kontan_bbm_scraper import KontanBBMScraper, scrape_kontan_bbm_news
from scrapers.kontan_biodiesel_scraper import KontanBiodieselScraper, scrape_kontan_biodiesel_news
from scrapers.sandp_data_scraper import SAndPDataScraper
from scrapers.google_news_scraper import GoogleNewsScraper, scrape_google_news

# Medium Priority
from scrapers.bioenergytimes_scraper import BioenergyTimesScraper, scrape_bioenergytimes_news
from scrapers.scmp_scraper import SCMPScraper, scrape_scmp_news
from scrapers.iaea_pris_scraper import IAEAPRISScraper, scrape_iaea_pris_data
from scrapers.migas_eia_scraper import MigasEIAScraper, scrape_migas_eia_data
from scrapers.energiesmedia_scraper import EnergiesMediaScraper, scrape_energiesmedia_news
from scrapers.cpo_scraper import CPOPriceScraper, scrape_cpo_prices
from scrapers.sandp_news_scraper import SAndPNewsScraper, scrape_sandp_news
from scrapers.sipsn_scraper import SIPSNDataScraper, scrape_sipsn_data

# ESDM Data Scrapers (PDF-based)
from scrapers.biodiesel_esdm_scraper import BiodieselESDMScraper, scrape_biodiesel_esdm
from scrapers.bioetanol_esdm_scraper import BioetanolESDMScraper, scrape_bioetanol_esdm
from scrapers.migas_esdm_scraper import MigasESDMScraper, scrape_migas_esdm_icp
from scrapers.kapasitas_ebt_scraper import KapasitasEBTScraper

# Additional lokal/intl scrapers referenced by src SUMBER_DICT
from scrapers.kontan_scraper import KontanNewsScraper, scrape_kontan_news
from scrapers.bisnis_indonesia_scraper import BisnisIndonesiaNewsScraper, scrape_bisnis_indonesia_news
from scrapers.kompas_scraper import KompasNewsScraper, scrape_kompas_news
from scrapers.tempo_scraper import TempoNewsScraper, scrape_tempo_news
from scrapers.cnbc_indonesia_scraper import CNBCIndonesiaNewsScraper, scrape_cnbc_indonesia_news
from scrapers.cnbc_scraper import CNBCNewsScraper, scrape_cnbc_news
from scrapers.cnn_scraper import CNNNewsScraper, scrape_cnn_news
from scrapers.theguardian_scraper import TheGuardianNewsScraper, scrape_theguardian_news
from scrapers.oilprice_scraper import OilPriceNewsScraper, scrape_oilprice_news
from scrapers.reuters_scraper import ReutersNewsScraper, scrape_reuters_news

__all__ = [
    'BaseNewsScraper',
    'ScrapingError',
    'RateLimitError',
    'ValidationError',
    'BPSScraper',
    'create_bps_scraper',
    # High Priority scrapers
    'BankIndonesiaScraper', 'scrape_bank_indonesia_news',
    'BloombergTechnozScraper', 'scrape_bloomberg_technoz_news',
    'KontanBBMScraper', 'scrape_kontan_bbm_news',
    'KontanBiodieselScraper', 'scrape_kontan_biodiesel_news',
    'SAndPDataScraper',
    'GoogleNewsScraper', 'scrape_google_news',
    # Medium Priority scrapers
    'BioenergyTimesScraper', 'scrape_bioenergytimes_news',
    'SCMPScraper', 'scrape_scmp_news',
    'IAEAPRISScraper', 'scrape_iaea_pris_data',
    'MigasEIAScraper', 'scrape_migas_eia_data',
    'EnergiesMediaScraper', 'scrape_energiesmedia_news',
    'CPOPriceScraper', 'scrape_cpo_prices',
    'SAndPNewsScraper', 'scrape_sandp_news',
    'SIPSNDataScraper', 'scrape_sipsn_data',
    # ESDM Data Scrapers
    'BiodieselESDMScraper', 'scrape_biodiesel_esdm',
    'BioetanolESDMScraper', 'scrape_bioetanol_esdm',
    'MigasESDMScraper', 'scrape_migas_esdm_icp',
    'KapasitasEBTScraper',
    # Additional lokal/intl scrapers referenced by src SUMBER_DICT
    'KontanNewsScraper', 'scrape_kontan_news',
    'BisnisIndonesiaNewsScraper', 'scrape_bisnis_indonesia_news',
    'KompasNewsScraper', 'scrape_kompas_news',
    'TempoNewsScraper', 'scrape_tempo_news',
    'CNBCIndonesiaNewsScraper', 'scrape_cnbc_indonesia_news',
    'CNBCNewsScraper', 'scrape_cnbc_news',
    'CNNNewsScraper', 'scrape_cnn_news',
    'TheGuardianNewsScraper', 'scrape_theguardian_news',
    'OilPriceNewsScraper', 'scrape_oilprice_news',
    'ReutersNewsScraper', 'scrape_reuters_news',
]


