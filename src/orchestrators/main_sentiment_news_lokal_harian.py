import os
import sys
import time
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers.onedrive_helper import (
    download_excel_from_onedrive,
    get_access_token,
    write_multiple_sheets_to_onedrive,
)
from helpers.summary_helper import setup_gemini, summarize_all_news


# Constants

ONEDRIVE_SCRAP_PATH = os.getenv("ONEDRIVE_FILE_PATH", "/results/(News)Scraping_new.xlsx")
ONEDRIVE_SENTIMENT_PATH = "/results/(News)Sentiment_final.xlsx"

# Default start date used when no prior summary exists
DEFAULT_START_DATE = datetime(2026, 4, 8)


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
    access_token: str,
) -> pd.DataFrame | None:
    """
    Process a single topic: determine the date range, collect matching news from
    OneDrive, generate a summary, and return the result as a single-row DataFrame.

    Returns None if the scraping file is unavailable or no articles are found.
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
    end_date = start_date

    print(f"[Topic] Date range: {start_date.date()} — {end_date.date()}")
    print(f"[Topic] Fetching scraping data from OneDrive: {ONEDRIVE_SCRAP_PATH}")

    excel_buffer = download_excel_from_onedrive(access_token, ONEDRIVE_SCRAP_PATH)
    if excel_buffer is None:
        print("[Topic] Scraping file not found on OneDrive.")
        return None

    # Collect matching articles from each target sheet
    all_news_list: list[str] = []
    excel_file = pd.ExcelFile(excel_buffer)

    for sheet in target_sheets:
        if sheet in excel_file.sheet_names:
            df_news = pd.read_excel(excel_file, sheet_name=sheet)
            if not df_news.empty and "date" in df_news.columns:
                df_news["date"] = pd.to_datetime(df_news["date"], errors="coerce")
                mask = (df_news["date"] >= start_date) & (df_news["date"] <= end_date)
                filtered_news = df_news[mask]
                for _, row in filtered_news.iterrows():
                    if pd.notna(row.get("content")):
                        all_news_list.append(str(row["content"]))

    excel_file.close()

    if not all_news_list:
        print(f"[Topic] No new articles found for '{topic_name}'.")
        return None

    print(f"[Topic] {len(all_news_list)} article(s) found.")

    summary = summarize_all_news(
        model,
        all_news_list,
        start_date,
        end_date,
        target_sheets,
        config["role_prompt"],
        config["spesific_prompt"],
    )

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
    print("NEWS SENTIMENT SUMMARIZATION TO ONEDRIVE")
    print("=" * 60)

    print("\nAuthenticating to Microsoft Graph API...")
    try:
        access_token = get_access_token()
        print("[Main] Authentication successful.")
    except Exception as exc:
        print(f"[Main] Authentication failed: {exc}")
        return

    print("\n[Main] Setting up Gemini model...")
    model = setup_gemini()

    print(f"\n[Main] Loading existing sentiment data from OneDrive...")
    print(f"[Main] File: {ONEDRIVE_SENTIMENT_PATH}")

    excel_buffer = download_excel_from_onedrive(access_token, ONEDRIVE_SENTIMENT_PATH)
    all_sheets: dict[str, pd.DataFrame] = {}

    if excel_buffer is None:
        print("[Main] File not found — a new file will be created.")
        for config in TOPICS.values():
            all_sheets[config["output_sheet"]] = pd.DataFrame()
    else:
        print("[Main] File found — reading all sheets...")
        excel_buffer.seek(0)
        excel_file = pd.ExcelFile(excel_buffer)

        for config in TOPICS.values():
            sheet_name = config["output_sheet"]
            try:
                if sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    all_sheets[sheet_name] = df
                    print(f"  '{sheet_name}': {len(df)} row(s)")
                else:
                    print(f"  '{sheet_name}': not found — will be created.")
                    all_sheets[sheet_name] = pd.DataFrame()
            except Exception as exc:
                print(f"  '{sheet_name}': error ({exc}) — will be created.")
                all_sheets[sheet_name] = pd.DataFrame()

        excel_file.close()

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

            new_data = process_topic(model, topic_name, config, existing_df, access_token)

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

    # --- Save to OneDrive ---
    print("\n" + "=" * 60)
    print("SAVING TO ONEDRIVE")
    print("=" * 60)

    try:
        write_multiple_sheets_to_onedrive(access_token, ONEDRIVE_SENTIMENT_PATH, all_sheets)

        print("\n" + "=" * 60)
        print("DONE!")
        print(f"[Main] File: {ONEDRIVE_SENTIMENT_PATH}")
        print(f"[Main] Sheets: {len(all_sheets)}")
        print("=" * 60 + "\n")

    except Exception as exc:
        print(f"\n[Main] Error while saving: {exc}")
        raise


# Script Entry Point

if __name__ == "__main__":
    load_dotenv()
    main()