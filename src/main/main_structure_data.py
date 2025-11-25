import pandas as pd
import sys
import os
import re 

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from code_scrapping.migas_eia import main_eia
from code_scrapping.migas_esdm import main_price_esdm
from code_scrapping.biodiesel_esdm_scrape import main_biodiesel_esdm
from code_scrapping.cpo import update_harga_komoditas_gapki

def run_all_tasks():
    print("=== Memulai Proses Scraping Data ===\n")
    print("--- [1/4] Menjalankan EIA Scraper ---")
    try:
        main_eia()
        print("SUCCESS: EIA Scraper selesai.\n")
    except Exception as e:
        print(f"ERROR: EIA Scraper gagal. Pesan: {e}\n")
    print("--- [2/4] Menjalankan ESDM Price Scraper ---")
    try:
        main_price_esdm()
        print("SUCCESS: ESDM Price Scraper selesai.\n")
    except Exception as e:
        print(f"ERROR: ESDM Price Scraper gagal. Pesan: {e}\n")
    print("--- [3/4] Menjalankan Biodiesel ESDM Scraper ---")
    try:
        main_biodiesel_esdm()
        print("SUCCESS: Biodiesel ESDM Scraper selesai.\n")
    except Exception as e:
        print(f"ERROR: Biodiesel ESDM Scraper gagal. Pesan: {e}\n")
    print("--- [4/4] Menjalankan GAPKI CPO Updater ---")
    try:
        update_harga_komoditas_gapki()
        print("SUCCESS: GAPKI CPO Updater selesai.\n")
    except Exception as e:
        print(f"ERROR: GAPKI CPO Updater gagal. Pesan: {e}\n")
    print("=== Semua proses selesai ===")
if __name__ == "__main__":
    run_all_tasks()
