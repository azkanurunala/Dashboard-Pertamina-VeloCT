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


def run_step(step_name, func):
    """Jalankan satu fungsi step dengan logging waktu mulai/selesai/durasi."""
    start = time.time()
    print(SEPARATOR)
    print(f"[Main] >>> START {step_name} @ {time.strftime('%H:%M:%S')}")
    print(SEPARATOR)
    try:
        func()
        elapsed = time.time() - start
        print(f"[Main] ✓ {step_name} SELESAI dalam {elapsed:.1f}s ({elapsed/60:.1f} menit)")
        return True
    except Exception as e:
        elapsed = time.time() - start
        print(f"[Main] ✗ ERROR pada {step_name} setelah {elapsed:.1f}s: {e}")
        import traceback
        traceback.print_exc()
        return False


# Public Entry Point

def run_daily_scraping():
    """Jalankan pipeline scraping harian lokal: news, CPO, dan sentiment secara berurutan."""
    pipeline_start = time.time()
    try:
        # ===== STEP 1: News Scraping =====
        run_step("STEP 1: News Scraping", main_news_scraping)

        print(f"[Main] Istirahat {STEP_SLEEP_SECONDS} detik sebelum melanjutkan ke CPO scraping...")
        time.sleep(STEP_SLEEP_SECONDS)

        # ===== STEP 2: CPO Price Scraping =====
        run_step("STEP 2: CPO Price Scraping", main_scraper_cpo)

        print(f"[Main] Istirahat {STEP_SLEEP_SECONDS} detik sebelum melanjutkan ke News Sentiment Summarization...")
        time.sleep(STEP_SLEEP_SECONDS)

        # ===== STEP 3: News Sentiment Summarization =====
        run_step("STEP 3: News Sentiment Summarization", main_sentiment_news)

    except Exception as e:
        print(f"[Main] ERROR FATAL SAAT SCRAPING: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        total_elapsed = time.time() - pipeline_start
        print(SEPARATOR)
        print(f"[Main] TOTAL WAKTU PIPELINE: {total_elapsed:.1f}s ({total_elapsed/60:.1f} menit)")
        print(SEPARATOR)


# Script Entry Point

if __name__ == "__main__":
    run_daily_scraping()