import os
import sys
import time
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers.storage_backend import storage
from helpers.summary_helper import setup_gemini, summarize_all_news


# Constants

# Default start date used when no prior summary exists
DEFAULT_START_DATE = datetime(2026, 4, 17)


# Topic Configuration

TOPICS: dict[str, dict] = {
    "Nilai Tukar Rupiah": {
        "target_sheets": ["(News)Kurs"],
        "output_sheet": "(Summary)Nilai Tukar Rupiah",
        "role_prompt": "Ekonom",
        "spesific_prompt": (
            "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. "
            "Fokus pada waktu, aktor utama, dan dampaknya secara global atau regional "
            "dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan "
            "em dash/semicolon), dan exclude kasus-kasus hukum!"
        ),
    },

    "IHSG": {
        "target_sheets": ["(News)IHSG"],
        "output_sheet": "(Summary)IHSG",
        "role_prompt": "Ekonom",
        "spesific_prompt": (
            "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. "
            "Fokus pada waktu, aktor utama, dan dampaknya secara global atau regional "
            "dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan "
            "em dash/semicolon), dan exclude kasus-kasus hukum!"
        ),
    },

    "Indonia": {
        "target_sheets": ["(News)Indonia"],
        "output_sheet": "(Summary)Indonia",
        "role_prompt": "Ekonom",
        "spesific_prompt": (
            "ringkasan menggambarkan situasi pasar, kebijakan, atau keputusan utama. "
            "Fokus pada waktu, aktor utama, dan dampaknya secara global atau regional "
            "dan berikan data kuantitatif bila ada. Gaya Bahasa: Factual dan profesional, "
            "Tanpa opini atau spekulasi, Hindari tanda baca berlebihan (tidak gunakan "
            "em dash/semicolon), dan exclude kasus-kasus hukum!"
        ),
    },
}


# Topic Processing

def process_topic(
    model,
    topic_name: str,
    config: dict,
    existing_df: pd.DataFrame,
) -> pd.DataFrame | None:
    """
    Process a single topic: determine the date range, collect matching news from
    storage, generate a summary, and return the result as a single-row DataFrame.

    Returns None if no articles are found.
    """
    print(f"\n{'=' * 60}")
    print(f"[Topic] Processing: {topic_name}")
    print(f"{'=' * 60}")

    target_sheets = config["target_sheets"]

    # Determine start date from the last processed date or fall back to default
    last_date = None
    if not existing_df.empty and "Tanggal akhir" in existing_df.columns:
        try:
            last_date = pd.to_datetime(existing_df["Tanggal akhir"].max())
        except Exception:
            pass

    start_date = last_date + pd.Timedelta(days=1) if last_date is not None else DEFAULT_START_DATE
    today = pd.to_datetime(datetime.now().date())

    print(f"[Topic] Fetching scraping data...")

    sheets_data: dict[str, pd.DataFrame] = {}
    for sheet in target_sheets:
        df_news = storage.read_news_sheet(sheet)
        if not df_news.empty and "date" in df_news.columns:
            df_news["date"] = pd.to_datetime(df_news["date"], errors="coerce").dt.normalize()
            sheets_data[sheet] = df_news

    all_news_list: list[str] = []
    end_date = start_date

    while start_date <= today:
        end_date = start_date
        all_news_list = []

        for df_news in sheets_data.values():
            mask = (df_news["date"] >= start_date) & (df_news["date"] <= end_date)
            filtered_news = df_news[mask]
            for _, row in filtered_news.iterrows():
                if pd.notna(row.get("content")):
                    all_news_list.append(str(row["content"]))

        if all_news_list:
            print(f"[Topic] Date range: {start_date.date()} — {end_date.date()}")
            print(f"[Topic] {len(all_news_list)} article(s) found.")
            break

        print(f"[Topic] No articles on {start_date.date()}, trying next day...")
        start_date += pd.Timedelta(days=1)
    else:
        print(f"[Topic] No new articles found for '{topic_name}'.")
        return None

    summary = summarize_all_news(
        model,
        all_news_list,
        start_date,
        end_date,
        target_sheets,
        config["role_prompt"],
        config["spesific_prompt"],
    )

    print(f"[Topic] Summary result: {summary[:100] if summary else 'NONE/EMPTY'}")

    if summary:
        return pd.DataFrame([{
            "Tanggal awal": start_date.date(),
            "Tanggal akhir": end_date.date(),
            "Summary": summary,
        }])

    return None


# Main

def main() -> None:
    """
    Run the daily news summarization workflow for Indonesian economic indicators:
    authenticate, load existing sentiment data from OneDrive, process each topic,
    and save results back.
    """
    print("\n" + "=" * 60)
    print("NEWS SENTIMENT SUMMARIZATION")
    print("=" * 60)

    print("\n[Main] Setting up Gemini model...")
    model = setup_gemini()

    print(f"\n[Main] Loading existing sentiment data...")

    sheet_names = [config["output_sheet"] for config in TOPICS.values()]
    all_sheets  = storage.read_all_sentiment_sheets(sheet_names)

    # --- Summarization ---
    print("\n" + "=" * 60)
    print("STARTING SUMMARIZATION")
    print("=" * 60)

    for topic_name, config in TOPICS.items():
        try:
            output_sheet = config["output_sheet"]
            existing_df = all_sheets.get(output_sheet, pd.DataFrame())

            print(f"\n{'-' * 60}")
            print(f"[Main] Topic: {topic_name}")
            print(f"[Main] Output sheet: {output_sheet}")
            print(f"{'-' * 60}")

            new_data = process_topic(model, topic_name, config, existing_df)

            if new_data is not None:
                if not existing_df.empty:
                    combined_df = pd.concat([existing_df, new_data], ignore_index=True)
                    print(f"\n  Existing rows: {len(existing_df)}")
                    print(f"  New rows: {len(new_data)}")
                else:
                    combined_df = new_data
                    print(f"\n  New rows: {len(new_data)}")

                all_sheets[output_sheet] = combined_df
                print(f"  Total: {len(combined_df)} row(s)")
            else:
                print("[Main] No new data for this topic.")

            print("\n[Main] Waiting 60 seconds before next topic...")
            time.sleep(60)

        except Exception as exc:
            print(f"[Main] Error processing '{topic_name}': {exc}")
            continue

    # --- Save ---
    print("\n" + "=" * 60)
    print("SAVING")
    print("=" * 60)

    try:
        storage.write_sentiment_file(all_sheets)

        print("\n" + "=" * 60)
        print("DONE!")
        print(f"[Main] Sheets: {len(all_sheets)}")
        print("=" * 60 + "\n")

    except Exception as exc:
        print(f"\n[Main] Error while saving: {exc}")
        raise


# Script Entry Point

if __name__ == "__main__":
    load_dotenv()
    main()