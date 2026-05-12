import sys
import os
import time
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orchestrators.main_news_scraping_internasional import main as main_news_scraping
from orchestrators.main_sentiment_news_internasional_harian import main as main_sentiment_news
from structured_data.spglobal_data import main_saf_daily


# Constants

STEP_SLEEP_SECONDS = 60
SEPARATOR          = "-" * 70


# Public Entry Point

def run_daily_scraping():
    """Jalankan pipeline scraping harian: news, sentiment, dan SAF secara berurutan."""
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

        print(f"[Main] Istirahat {STEP_SLEEP_SECONDS} detik sebelum melanjutkan ke Sentiment...")
        time.sleep(STEP_SLEEP_SECONDS)

        # ===== STEP 2: News Sentiment Summarization =====
        print("[Main] >>> STEP 2: Menjalankan News Sentiment Summarization")
        print(SEPARATOR)
        try:
            main_sentiment_news()
            print("[Main] News Sentiment Summarization selesai")
        except Exception as e:
            print(f"[Main] ✗ ERROR pada News Sentiment Summarization: {e}")
            import traceback
            traceback.print_exc()

        time.sleep(STEP_SLEEP_SECONDS)

        # ===== STEP 3: SAF & Crackspeed Scraping =====
        print("[Main] >>> STEP 3: Menjalankan SAF & Crackspeed Scraping")
        try:
            main_saf_daily()
            print("[Main] SAF Daily scraping selesai")
        except Exception as e:
            print(f"[Main] ✗ ERROR pada SAF & Crackspeed Scraping: {e}")
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