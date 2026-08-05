import sys
import os
import time
import traceback
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from structured_data.biodiesel_esdm import main_biodiesel_esdm
from structured_data.bioetanol_esdm import main_bioetanol_esdm
from structured_data.kapasitas_esdm import main_ebtke_scraper
from structured_data.migas_esdm import main_price_esdm
from structured_data.migas_eia import main_eia
from structured_data.nuclear_iaea_pris import main_iaea_scraper
from structured_data.spglobal_data import (
    main_petrochemical_short_term,
    main_price_forecast_short_term_bbm,
    main_price_forecast_long_term_bbm,
)
from structured_data.wte_sipsn import main_sipsn_scraper


# Constants

SEPARATOR_THIN  = "-" * 70
SEPARATOR_THICK = "=" * 70

DAY_PETROCHEMICAL = 12
DAY_NUCLEAR       = 15
DAY_EBT           = 28


# Public Entry Point

def run_monthly_tasks():
    """Jalankan pipeline scraping bulanan: EIA, ESDM, BBM, sampah, nuklir, dan EBT."""
    # Setiap step tetap diisolasi (satu step gagal tidak menghentikan step lain),
    # tapi kegagalan dikumpulkan di sini supaya proses exit non-zero dan CI
    # (GitHub Actions) tampil merah, bukan diam-diam "sukses" padahal step gagal.
    failed_steps: list[str] = []

    try:
        print("\n" + SEPARATOR_THICK)
        print("MONTHLY TASK SCHEDULER")
        print(SEPARATOR_THICK)

        today       = datetime.now()
        current_day = today.day

        # Cron workflow monthly fire tanggal 1, 12, 15, dan 28.
        # Step 1-4 (scraping bulanan berat, termasuk OCR) cukup jalan sekali per
        # bulan: dilewati pada tanggal khusus 12/15/28, tetap jalan pada tanggal 1
        # maupun manual dispatch di tanggal lain.
        skip_base_steps = current_day in (DAY_PETROCHEMICAL, DAY_NUCLEAR, DAY_EBT)

        if skip_base_steps:
            print(f"\n[Main] STEP 1-4 DILEWATI (tanggal {current_day}: "
                  "hanya step bergating tanggal yang dijalankan)")
        else:
            # ===== STEP 1: EIA Data Scraping =====
            print("\n[Main] >>> STEP 1: Menjalankan EIA Data Scraping")
            print(SEPARATOR_THIN)
            try:
                main_eia()
                print("[Main] EIA Data Scraping selesai")
            except Exception as e:
                print(f"[Main] ERROR pada EIA Data Scraping: {e}")
                traceback.print_exc()
                failed_steps.append("EIA Data Scraping")

            # ===== STEP 2: ESDM Price Data Scraping =====
            print("\n[Main] >>> STEP 2: Menjalankan ESDM Price Data Scraping")
            print(SEPARATOR_THIN)
            try:
                main_price_esdm()
                print("[Main] ESDM Price Data Scraping selesai")
            except Exception as e:
                print(f"[Main] ERROR pada ESDM Price Data Scraping: {e}")
                traceback.print_exc()
                failed_steps.append("ESDM Price Data Scraping")

            # ===== STEP 3: Biodiesel ESDM Data Scraping =====
            print("\n[Main] >>> STEP 3: Menjalankan Biodiesel ESDM Data Scraping")
            print(SEPARATOR_THIN)
            try:
                main_biodiesel_esdm()
                print("[Main] Biodiesel ESDM Data Scraping selesai")
            except Exception as e:
                print(f"[Main] ERROR pada Biodiesel ESDM Data Scraping: {e}")
                traceback.print_exc()
                failed_steps.append("Biodiesel ESDM Data Scraping")

            # ===== STEP 4: Bioetanol ESDM Data Scraping =====
            print("\n[Main] >>> STEP 4: Menjalankan Bioetanol ESDM Data Scraping")
            print(SEPARATOR_THIN)
            try:
                main_bioetanol_esdm()
                print("[Main] Bioetanol ESDM Data Scraping selesai")
            except Exception as e:
                print(f"[Main] ERROR pada Bioetanol ESDM Data Scraping: {e}")
                traceback.print_exc()
                failed_steps.append("Bioetanol ESDM Data Scraping")

        # ===== STEP 5: Harga dan Crackspread BBM dan Non BBM (Hanya tanggal 12) =====
        if current_day == DAY_PETROCHEMICAL:
            print(f"\n[Main] >>> STEP 5: Menjalankan Harga dan Crackspread BBM dan Non BBM")
            print(SEPARATOR_THIN)
            try:
                main_petrochemical_short_term()
                print("[Main] Petrochemical Short Term selesai")
            except Exception as e:
                print(f"[Main] ERROR pada Petrochemical Short Term: {e}")
                traceback.print_exc()
                failed_steps.append("Petrochemical Short Term")
            try:
                main_price_forecast_short_term_bbm()
                print("[Main] Price Forecast Short Term BBM selesai")
            except Exception as e:
                print(f"[Main] ERROR pada Price Forecast Short Term BBM: {e}")
                traceback.print_exc()
                failed_steps.append("Price Forecast Short Term BBM")
            try:
                main_price_forecast_long_term_bbm()
                print("[Main] Price Forecast Long Term BBM selesai")
            except Exception as e:
                print(f"[Main] ERROR pada Price Forecast Long Term BBM: {e}")
                traceback.print_exc()
                failed_steps.append("Price Forecast Long Term BBM")
        else:
            print("[Main] STEP 5: Harga dan Crackspread BBM dan Non BBM - DILEWATI")

        # ===== STEP 6: Scraping Data Sampah dan Data Nuklir (Hanya tanggal 15) =====
        if current_day == DAY_NUCLEAR:
            print(f"\n[Main] >>> STEP 6: Menjalankan Scraping Data Sampah dan Nuklir")
            print(SEPARATOR_THIN)
            print(f"[Main] Tanggal {current_day}, scraping dijalankan")
            try:
                main_sipsn_scraper()
                print("[Main] Scraping Data Sampah selesai")
            except Exception as e:
                print(f"[Main] ERROR pada Scraping Data Sampah: {e}")
                traceback.print_exc()
                failed_steps.append("Scraping Data Sampah")
            try:
                main_iaea_scraper()
                print("[Main] Scraping Data Nuklir selesai")
            except Exception as e:
                print(f"[Main] ERROR pada Scraping Data Nuklir: {e}")
                traceback.print_exc()
                failed_steps.append("Scraping Data Nuklir")
        else:
            print("\n[Main] STEP 6: Scraping Data Sampah dan Nuklir - DILEWATI")
            print(f"[Main] Tanggal {current_day}, bukan tanggal {DAY_NUCLEAR}. Scraping tidak dijalankan")
            print(SEPARATOR_THIN)

        # ===== STEP 7: Scraping Data Kapasitas EBT (Hanya tanggal 28) =====
        if current_day == DAY_EBT:
            print(f"\n[Main] >>> STEP 7: Menjalankan Scraping Data Kapasitas EBT")
            print(SEPARATOR_THIN)
            try:
                main_ebtke_scraper()
                print("[Main] Scraping Data Kapasitas EBT selesai")
            except Exception as e:
                print(f"[Main] ERROR pada Scraping Data Kapasitas EBT: {e}")
                traceback.print_exc()
                failed_steps.append("Scraping Data Kapasitas EBT")
        else:
            print("[Main] STEP 7: Scraping Data Kapasitas EBT - DILEWATI")

        print("\n" + SEPARATOR_THICK)
        if failed_steps:
            print(f"MONTHLY TASKS COMPLETED WITH {len(failed_steps)} FAILED STEP(S): {', '.join(failed_steps)}")
        else:
            print("MONTHLY TASKS COMPLETED")
        print(SEPARATOR_THICK + "\n")

    except Exception as e:
        print(f"[Main] ERROR FATAL SAAT MENJALANKAN MONTHLY TASKS: {e}")
        traceback.print_exc()
        sys.exit(1)

    if failed_steps:
        sys.exit(1)


# Script Entry Point

if __name__ == "__main__":
    run_monthly_tasks()