import time
from datetime import datetime
import sys
import os
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from structured_data.migas_eia import main_eia
from structured_data.migas_esdm import main_price_esdm
from structured_data.biodiesel_esdm import main_biodiesel_esdm
from structured_data.bioetanol_esdm import main_bioetanol_esdm
from structured_data.spglobal_data import main_petrochemical_short_term, main_price_forecast_short_term_bbm
from structured_data.wte_sipsn import main_sipsn_scraper
from structured_data.nuclear_iaea_pris import main_iaea_scraper
from structured_data.kapasitas_esdm import main_ebtke_scraper


def run_monthly_tasks():
    try:
        print("\n" + "=" * 70)
        print("MONTHLY TASK SCHEDULER")
        print("=" * 70)
        today = datetime.now()
        current_day = today.day

        # ===== STEP 1: EIA Data Scraping =====
        print("\n>>> STEP 1: Menjalankan EIA Data Scraping")
        print("-" * 70)
        try:
            main_eia()
            print("EIA Data Scraping selesai")
        except Exception as e:
            print(f"ERROR pada EIA Data Scraping: {e}")
            traceback.print_exc()

        # ===== STEP 2: ESDM Price Data Scraping =====
        print("\n>>> STEP 2: Menjalankan ESDM Price Data Scraping")
        print("-" * 70)
        try:
            main_price_esdm()
            print("ESDM Price Data Scraping selesai")
        except Exception as e:
            print(f"ERROR pada ESDM Price Data Scraping: {e}")
            traceback.print_exc()

        # ===== STEP 3: Biodiesel ESDM Data Scraping =====
        print("\n>>> STEP 3: Menjalankan Biodiesel ESDM Data Scraping")
        print("-" * 70)
        try:
            main_biodiesel_esdm()
            print("Biodiesel ESDM Data Scraping selesai")
        except Exception as e:
            print(f"ERROR pada Biodiesel ESDM Data Scraping: {e}")
            traceback.print_exc()

        # ===== STEP 4: Bioetanol ESDM Data Scraping =====
        print("\n>>> STEP 4: Menjalankan Bioetanol ESDM Data Scraping")
        print("-" * 70)
        try:
            main_bioetanol_esdm()
            print("Bioetanol ESDM Data Scraping selesai")
        except Exception as e:
            print(f"ERROR pada Bioetanol ESDM Data Scraping: {e}")
            traceback.print_exc()
       
        # ===== STEP 5: Harga dan Crackspread BBM dan Non BBM (Hanya tanggal 12) =====
        if current_day == 12:
            try:
                main_petrochemical_short_term()
            except Exception as e:
                print(f"ERROR pada Petrochemical Short Term: {e}")
                traceback.print_exc()
            try:
                main_price_forecast_short_term_bbm()
            except Exception as e:
                print(f"ERROR pada Price Forecast Short Term BBM: {e}")
                traceback.print_exc()
        else:
            print("STEP 5: Harga dan Crackspread BBM dan Non BBM - DILEWATI")

        # ==== STEP 6: Scraping Data Sampah dan Data Nuklir ====
        if current_day == 15:
            print("\nSTEP 6: Menjalankan Scraping Data Sampah dan Nuklir")
            print(f"Tanggal {current_day}, scraping dijalankan")
            try:
                main_sipsn_scraper()
                print("Scraping Data Sampah selesai")
            except Exception as e:
                print(f"ERROR pada Scraping Data Sampah: {e}")
                traceback.print_exc()
            try: 
                main_iaea_scraper()
                print("Scraping Data Nuklir selesai")
            except Exception as e: 
                print(f"ERROR pada Scraping Data Nuklir: {e}")
                traceback.print_exc()
        else:
            print("\nSTEP 6: Scraping Data Sampah dan Nuklir - DILEWATI")
            print(f"    [INFO] Tanggal {current_day}, bukan tanggal 15. Scraping tidak dijalankan")
            print("-" * 70)
            print("\n" + "=" * 70)
            print("MONTHLY TASKS COMPLETED")
            print("=" * 70 + "\n")

        # ==== STEP 7: Scraping Data Kapasitas EBT ====
        if current_day == 28: 
            print(f"\nSTEP 7: Menjalankan Scraping Data Kapasitas EBT")
            try:
                main_ebtke_scraper()
                print("Scraping data kapasitas EBT selesai")
            except Exception as e:
                print(f"ERROR pada Scraping Data Kapasitas EBT: {e}")
                traceback.print_exc()

    except Exception as e:
        print(f"\nERROR FATAL SAAT MENJALANKAN MONTHLY TASKS: {e}")
        import traceback

if __name__ == "__main__":
    run_monthly_tasks()