import sys
import os
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orchestrators.main_sentiment_news_mingguan import main as main_sentiment_news_mingguan
from structured_data.spglobal_data import main_saf_weekly, main_crackspeed_bbm_weekly, main_crackspeed_non_bbm_weekly


# Constants

SEPARATOR_THIN  = "-" * 70
SEPARATOR_THICK = "=" * 70


# Public Entry Point

def run_weekly_tasks():
    """Jalankan pipeline scraping mingguan: sentiment news dan S&P weekly data."""
    try:
        print("\n" + SEPARATOR_THICK)
        print("WEEKLY TASK SCHEDULER")
        print(SEPARATOR_THICK)

        # ===== STEP 1: News Sentiment Summarization (Mingguan) =====
        print("\n[Main] >>> STEP 1: Menjalankan News Sentiment Summarization (Mingguan)")
        print(SEPARATOR_THIN)
        try:
            main_sentiment_news_mingguan()
            print("[Main] News Sentiment Summarization (Mingguan) selesai")
        except Exception as e:
            print(f"[Main] ERROR pada News Sentiment Summarization (Mingguan): {e}")
            traceback.print_exc()

        # ===== STEP 2: S&P Weekly Data Scraping =====
        print("\n[Main] >>> STEP 2: Menjalankan S&P Weekly Data Scraping")
        print(SEPARATOR_THIN)
        try:
            main_saf_weekly()
            main_crackspeed_bbm_weekly()
            main_crackspeed_non_bbm_weekly()
            print("[Main] S&P Weekly Data Scraping selesai")
        except Exception as e:
            print(f"[Main] ERROR pada S&P Weekly Data Scraping: {e}")
            traceback.print_exc()

        # ===== FOOTER =====
        print("\n" + SEPARATOR_THICK)
        print("WEEKLY TASKS COMPLETED")
        print(SEPARATOR_THICK + "\n")

    except Exception as e:
        print(f"[Main] ERROR FATAL SAAT MENJALANKAN WEEKLY TASKS: {e}")
        traceback.print_exc()
        sys.exit(1)


# Script Entry Point

if __name__ == "__main__":
    run_weekly_tasks()