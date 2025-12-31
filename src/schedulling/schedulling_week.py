import sys
import os


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main.main_sentiment_news_mingguan import main as main_sentiment_news_mingguan

def run_weekly_tasks():
    try:
        # ===== STEP 1: News Sentiment Summarization (Mingguan) =====
        print("\n" + "=" * 70)
        print("WEEKLY TASK SCHEDULER")
        print("=" * 70)

        print("\n>>> STEP 1: Menjalankan News Sentiment Summarization (Mingguan)")
        print("-" * 70)
        try:
            main_sentiment_news_mingguan()
            print("\nNews Sentiment Summarization (Mingguan) selesai")
        except Exception as e:
            print(f"\n✗ ERROR pada News Sentiment Summarization (Mingguan): {e}")
            import traceback
            traceback.print_exc()

        print("\n" + "=" * 70)
        print("WEEKLY TASKS COMPLETED")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n✗ ERROR FATAL SAAT MENJALANKAN WEEKLY TASKS: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_weekly_tasks()
