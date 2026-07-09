import os

import google.generativeai as genai
import pandas as pd
from dotenv import load_dotenv


# Constants

# Maximum number of summary points generated per topic
SUMMARY_POINTS = 3

# Separator tag used to extract the summary block from the model response
SUMMARY_DELIMITER = "===SUMMARY==="


# Setup

def setup_gemini() -> genai.GenerativeModel:
    """
    Load the Gemini API key from .env and return a configured GenerativeModel instance.

    Raises ValueError if the API key is not found in the environment.
    """
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("[Setup] GEMINI_API_KEY not found in .env file.")

    genai.configure(api_key=api_key)
    print("[Setup] Gemini configured successfully.")
    # gemini-2.5-flash / gemini-2.5-flash-lite were retired by Google (404) — pinned to
    # the current-generation equivalent tier.
    return genai.GenerativeModel("gemini-3.1-flash-lite")


# Date Utilities

def get_last_summary_date(output_path: str, sheet_name: str) -> "pd.Timestamp | None":
    """
    Read the most recent summary date from an Excel sheet's 'Tanggal akhir' column.

    Returns None if the file does not exist, the sheet is missing, or the column is empty.
    """
    if not os.path.exists(output_path):
        return None

    try:
        df = pd.read_excel(output_path, sheet_name=sheet_name)
        last_date = pd.to_datetime(df["Tanggal akhir"].dropna()).max()
        print(f"[Date] Last summary date for '{sheet_name}': {last_date.date()}")
        return last_date
    except Exception as exc:
        print(f"[Date] Failed to read '{sheet_name}' from '{output_path}': {exc}")
        return None


# News Collection

def collect_news_from_sheets(
    excel_path: str,
    target_sheets: list[str],
    start_date: "pd.Timestamp",
    end_date: "pd.Timestamp",
) -> list[str]:
    """
    Collect article content from multiple Excel sheets filtered by date range.

    Returns a flat list of content strings from all matching rows across all sheets.
    """
    all_news_list: list[str] = []

    for sheet in target_sheets:
        print(f"[Collect] Reading sheet: {sheet}")
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet)
            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
            mask = (df["date"] >= start_date) & (df["date"] <= end_date)
            df_new = df.loc[mask].dropna(subset=["content"])
            all_news_list.extend(df_new["content"].tolist())
            print(f"[Collect] {len(df_new)} article(s) from '{sheet}'.")
        except Exception as exc:
            print(f"[Collect] Failed to read sheet '{sheet}': {exc}")

    return all_news_list


# Summarization

def summarize_all_news(
    model: genai.GenerativeModel,
    all_news_list: list[str],
    start_date: "pd.Timestamp",
    end_date: "pd.Timestamp",
    sheet_names: list[str],
    role_prompt: str,
    spesific_prompt: str,
) -> str | None:
    """
    Generate a structured news summary using the Gemini model.

    Combines all article content into a single prompt and returns the extracted
    summary block, or None if generation fails. Returns a "no news" message if
    the input list is empty.
    """
    if not all_news_list:
        print("[Summary] No articles available — skipping summarization.")
        return None

    all_news_text = "\n\n".join(all_news_list)

    prompt = f"""
    Kamu adalah analis {role_prompt} di Indonesia.

    Berikut kumpulan berita dari topik {', '.join(sheet_names)}
    antara tanggal {start_date.strftime('%d %B %Y')} dan {end_date.strftime('%d %B %Y')}:

    {all_news_text}

    Buatkan 3 poin ringkasan umum.
    Semua teks pada bagian ini jangan ada yang bold, dan tolong berikan nomor setiap poinnya.
    Pisahkan setiap poin dengan baris kosong (enter) agar lebih mudah dibaca.

    Gunakan panduan penulisan berikut:
    {spesific_prompt}

    Format jawaban (dengan baris kosong antar poin):
    ===SUMMARY===
    1) (poin pertama)

    2) (poin kedua)

    3) (poin ketiga)
    """

    try:
        response = model.generate_content(prompt)
        result = response.text
        summary = (
            result.split(SUMMARY_DELIMITER)[-1].strip()
            if SUMMARY_DELIMITER in result
            else result.strip()
        )
        print("[Summary] Summary generated successfully.")
        return summary

    except Exception as exc:
        print(f"[Summary] Failed to generate summary: {exc}")
        return None