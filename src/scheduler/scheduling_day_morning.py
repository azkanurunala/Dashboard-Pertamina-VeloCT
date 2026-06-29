import sys
import os
import time
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orchestrators.main_news_scraping_lokal import main as main_news_scraping
from orchestrators.main_sentiment_news_lokal_harian import main as main_sentiment_news
from structured_data.cpo_gapki import main_scraper_cpo


# Constants

STEP_SLEEP_SECONDS = 60
SEPARATOR          = "-" * 70


# Public Entry Point

def run_daily_scraping():
    """Jalankan pipeline scraping harian lokal: news, CPO, dan sentiment secara berurutan."""
    try:
        # ===== STEP 1: News Scraping =====
        print("[Main] >>> STEP 1: Menjalankan News Scraping")
        print(SEPARATOR)
        try:
            main_news_scraping()
            print("[Main] News Scraping selesai")
        except Exception as e:
            print(f"[Main] ✗ ERROR pada News Scraping: {e}")
            import traceback
            traceback.print_exc()

        print(f"[Main] Istirahat {STEP_SLEEP_SECONDS} detik sebelum melanjutkan ke CPO scraping...")
        time.sleep(STEP_SLEEP_SECONDS)

        # ===== STEP 2: CPO Price Scraping =====
        print("[Main] >>> STEP 2: Menjalankan CPO Price Scraping")
        print(SEPARATOR)
        try:
            main_scraper_cpo()
            print("[Main] CPO Price Scraping selesai")
        except Exception as e:
            print(f"[Main] ✗ ERROR pada CPO Scraping: {e}")
            import traceback
            traceback.print_exc()

        print(f"[Main] Istirahat {STEP_SLEEP_SECONDS} detik sebelum melanjutkan ke News Sentiment Summarization...")
        time.sleep(STEP_SLEEP_SECONDS)

        # ===== STEP 3: News Sentiment Summarization =====
        print("[Main] >>> STEP 3: Menjalankan News Sentiment Summarization")
        print(SEPARATOR)
        try:
            main_sentiment_news()
            print("[Main] News Sentiment Summarization selesai")
        except Exception as e:
            print(f"[Main] ERROR pada News Sentiment Summarization: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"[Main] ERROR FATAL SAAT SCRAPING: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


# Script Entry Point

if __name__ == "__main__":
    run_daily_scraping()