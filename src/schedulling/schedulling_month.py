import time
from datetime import datetime
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from code_scrapping.migas_eia import main_eia
from code_scrapping.migas_esdm import main_price_esdm
from code_scrapping.biodiesel_esdm_scrape import main_biodiesel_esdm
from code_scrapping.bioetanol_esdm_scrape import main_bioetanol_esdm

def run_monthly_tasks():
    try:
        print("\n" + "=" * 70)
        print("MONTHLY TASK SCHEDULER")
        print("=" * 70)
        
        # ===== STEP 1: EIA Data Scraping =====
        print("\n>>> STEP 1: Menjalankan EIA Data Scraping")
        print("-" * 70)
        try:
            main_eia()
            print("EIA Data Scraping selesai")
        except Exception as e:
            print(f"ERROR pada EIA Data Scraping: {e}")
            import traceback
            traceback.print_exc()

        # ===== STEP 2: ESDM Price Data Scraping =====
        print("\n>>> STEP 2: Menjalankan ESDM Price Data Scraping")
        print("-" * 70)
        try:
            main_price_esdm()
            print("ESDM Price Data Scraping selesai")
        except Exception as e:
            print(f"ERROR pada ESDM Price Data Scraping: {e}")
            import traceback
            traceback.print_exc()

        # ===== STEP 3: Biodiesel ESDM Data Scraping =====
        print("\n>>> STEP 3: Menjalankan Biodiesel ESDM Data Scraping")
        print("-" * 70)
        try:
            main_biodiesel_esdm()
            print("Biodiesel ESDM Data Scraping selesai")
        except Exception as e:
            print(f"ERROR pada Biodiesel ESDM Data Scraping: {e}")
            import traceback
            traceback.print_exc()

        # ===== STEP 4: Bioetanol ESDM Data Scraping =====
        print("\n>>> STEP 4: Menjalankan Bioetanol ESDM Data Scraping")
        print("-" * 70)
        try:
            main_bioetanol_esdm()
            print("Bioetanol ESDM Data Scraping selesai")
        except Exception as e:
            print(f"ERROR pada Bioetanol ESDM Data Scraping: {e}")
            import traceback
            traceback.print_exc()
        print("\n" + "=" * 70)
        print("MONTHLY TASKS COMPLETED")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\nERROR FATAL SAAT MENJALANKAN MONTHLY TASKS: {e}")
        import traceback