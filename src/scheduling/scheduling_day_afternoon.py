import time
from datetime import datetime
import sys
import os


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main.main_news_scrapping_internasional import main as main_news_scraping
from main.main_sentiment_news_internasional_harian import main as main_sentiment_news
from code_scrapping.scrape_sandp_data import main_saf_daily

def run_daily_scraping():
    try:
        # # ===== STEP 1: News Scraping =====
        print(">>> STEP 1: Menjalankan News Scraping")
        print("-" * 70)
        try:
            main_news_scraping()
            print("\nNews Scraping selesai")
        except Exception as e:
            print(f"\n✗ ERROR pada News Scraping: {e}")
            import traceback
            traceback.print_exc()
        print("\nIstirahat 60 detik sebelum melanjutkan ke Sentiment...")
        time.sleep(60)

        # ===== STEP 2: News Sentiment Summarization =====
        print("\n>>> STEP 2: Menjalankan News Sentiment Summarization")
        print("-" * 70)
        try:
            main_sentiment_news()
            print("\nNews Sentiment Summarization selesai")
        except Exception as e:
            print(f"\n✗ ERROR pada News Sentiment Summarization: {e}")
            import traceback
            traceback.print_exc()
        time.sleep(60)

        # ===== STEP 3: SAF & Crackspeed Scraping =====
        print("\n>>> STEP 3: Menjalankan SAF & Crackspeed Scraping")
        try:
            main_saf_daily()
            print("\nSAF Daily scraping selesai")
        except Exception as e:
            print(f"\n✗ ERROR pada SAF & Crackspeed Scraping: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"\nERROR FATAL SAAT SCRAPING: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)  


if __name__ == "__main__":
    run_daily_scraping()