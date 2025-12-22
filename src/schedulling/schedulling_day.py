import time
from datetime import datetime
import sys
import os


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main.main_news_scrapping import main as main_news_scraping
from code_scrapping.scrapping_cpo import main_scraper_cpo

def run_daily_scraping():
    try:
        # print(">>> STEP 1: Menjalankan News Scraping")
        # print("-" * 70)
        # try:
        #     main_news_scraping()
        #     print("\nNews Scraping selesai")
        # except Exception as e:
        #     print(f"\n✗ ERROR pada News Scraping: {e}")
        #     import traceback
        #     traceback.print_exc()
        print("\nIstirahat 60 detik sebelum melanjutkan ke CPO scraping...")
        # time.sleep(60)
        # ===== STEP 2: CPO Price Scraping =====
        print("\n>>> STEP 2: Menjalankan CPO Price Scraping")
        print("-" * 70)
        try:
            main_scraper_cpo()
            print("\nCPO Price Scraping selesai")
        except Exception as e:
            print(f"\nERROR pada CPO Scraping: {e}")
            import traceback
            traceback.print_exc()
    except Exception as e:
        print(f"\n✗ ERROR FATAL SAAT SCRAPING: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)  


if __name__ == "__main__":
    run_daily_scraping()