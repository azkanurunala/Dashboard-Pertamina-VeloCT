import sys
import os


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from orchestrators.main_sentiment_news_mingguan import main as main_sentiment_news_mingguan
from structured_data.spglobal_data import main_saf_weekly, main_crackspeed_bbm_weekly, main_crackspeed_non_bbm_weekly

def run_weekly_tasks():
    try:
        print("\n" + "=" * 70)
        print("WEEKLY TASK SCHEDULER")
        print("=" * 70)
        print("\n>>> STEP 1: Menjalankan News Sentiment Summarization (Mingguan)")
        print("-" * 70)
        try:
            main_sentiment_news_mingguan()
            print("News Sentiment Summarization (Mingguan) selesai")
        except Exception as e:
            print(f"ERROR pada News Sentiment Summarization (Mingguan): {e}")
            import traceback
            traceback.print_exc()

        # ===== STEP 2: S&P Weekly Data Scraping =====
        print("\n>>> STEP 2: Menjalankan S&P Weekly Data Scraping")
        print("-" * 70)
        try:
            main_saf_weekly()
            main_crackspeed_bbm_weekly()
            main_crackspeed_non_bbm_weekly()
            print("S&P Weekly Data Scraping selesai")
        except Exception as e:
            print(f"ERROR pada S&P Weekly Data Scraping: {e}")
            import traceback
            traceback.print_exc()

        # ===== FOOTER =====
        print("\n" + "=" * 70)
        print("WEEKLY TASKS COMPLETED")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\nERROR FATAL SAAT MENJALANKAN WEEKLY TASKS: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_weekly_tasks()