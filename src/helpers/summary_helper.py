import os

import google.generativeai as genai
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

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
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("[Setup] GEMINI_API_KEY not found in .env file.")

    genai.configure(api_key=api_key)
    print("[Setup] Gemini configured successfully.")
    # gemini-2.5-flash / gemini-2.5-flash-lite were retired by Google (404) — pinned to
    # the current-generation equivalent tier.
    return genai.GenerativeModel("gemini-3.1-flash-lite")

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