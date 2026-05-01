import os
import re
import sys
import time
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers.onedrive_helper import (
    get_access_token,
    read_excel_sheet_from_onedrive,
    write_multiple_sheets_to_onedrive,
    download_excel_from_onedrive,
)

from code_scrapping.bioenergytimes import scrape_bioenergytimes
from code_scrapping.cnbc import main_google_news_cnbc
from code_scrapping.cnn import main_google_news_cnn
from code_scrapping.energiesmedia import scrape_energiesmedia
from code_scrapping.oilprice import scrape_oilprice
from code_scrapping.scrape_sandp_news import scrape_spglobal as scrape_news_sap
from code_scrapping.scmp import main_scmp
from code_scrapping.the_guardian import scrape_the_guardian as scrape_theguardian

load_dotenv()

# Config

ONEDRIVE_FILE_PATH = os.getenv("ONEDRIVE_FILE_PATH", "/results/(News)Scrapping_new.xlsx")

# Keyword synonyms

SINONIM_DICT = {
    # "geopolitical risk ": ["geopolitical pressure ", "geopolitics "],
    # "volatility index ": [
    #     # "volatility ",
    #     "market volatility ", "financial volatility "
    #     ],
    # "dxy ": [
    #     # "dollar ",
    #     "dollar index "
    #     ],
    "purchasing manufaktur index ": [
        "manufaktur index ",
        "purchasing manufacturing index", "manufacturing pmi "
        ],
    "purchasing services index ": [
        "services index ",
        "services pmi "
        ],
    # "oil price ": ["crude oil "],
    # "oil volume ": ["bbm volume "],
    # "SAF ": [
    #     "UCO ", "sustainable aviation fuel ", "used cooking oil ", "CORSIA ", "SAFCo ", "biorefinery ", "bioavtur ",
    #     "pome "
    #     ],
    # "RON 92 ": [
    #     "pertamax ", "RON 95 ", "RON 97 ", "Residual FO ", "Fuel Oil", "Jet Fuel ", "Avtur ",
    #     "Kerosene ", "refinery ", "refined products ", "refining ", "oil products ", "Gasoline ",
    #     "Heavy Oil ", "Diesel ", "Gasoil ", "Naphtha ", "LPG ", "Biodiesel ", "Biogasoline ",
    #     "Petroleum Coke ", "Oil price ", 
    #     # "fuel ",
    #     "fuel cost ", "fuel price ",
    # ],
    # "Petrochemical ": [
    #     "chemical ", "aromatic ", "olefin ", "polymer ", "LPG ",
    #     "Paraxylene ", "Propylene ", "Benzene ", "Green Coke ",
    #     "petrochemicals", "petrochemical complex", "aromatic compound", 
    #     "BTX aromatic", "green petroleum coke", "petroleum coke"
    # ],
}

# Scraping sources per keyword

SUMBER_DICT = {
    # "geopolitical risk ": [main_google_news_cnn, main_google_news_cnbc, main_scmp, scrape_theguardian],
    # "volatility index ": [main_google_news_cnn, main_google_news_cnbc, main_scmp, scrape_theguardian],
    # "dxy ": [main_google_news_cnn, main_google_news_cnbc],
    "purchasing manufaktur index ": [scrape_news_sap],
    "purchasing services index ": [scrape_news_sap],
    # "oil price ": [scrape_oilprice],
    # "oil volume ": [scrape_oilprice],
    # "SAF ": [scrape_news_sap, main_google_news_cnbc, main_google_news_cnn],
    # "RON 92 ": [scrape_news_sap, main_google_news_cnbc, main_google_news_cnn, scrape_energiesmedia, scrape_bioenergytimes, scrape_theguardian],
    # "Petrochemical ":  [scrape_news_sap, main_google_news_cnbc, main_google_news_cnn, scrape_energiesmedia, scrape_bioenergytimes],
}

# Sheet name → keyword mapping

SHEET_TO_KEYWORD = {
    # "(News)indeks risiko geopolitik": "geopolitical risk ",
    # "(News)indeks volatilitas": "volatility index ",
    # "(News)Kurs": "dxy ",
    "(News)indeks kinerja manufaktur": "purchasing manufaktur index ",
    "(News)indeks kinerja jasa": "purchasing services index ",
    # "(News)Harga Minyak": "oil price ",
    # "(News)Volume Minyak": "oil volume ",
    # "(News)SAF": "SAF ",
    # "(News)Crackspread_BBM":    "RON 92 ",
    # "(News)Crackspread_NonBBM": "Petrochemical ",
}

# Sheets to process (must match keys in SHEET_TO_KEYWORD)
ACTIVE_SHEETS = [
    # "(News)indeks risiko geopolitik",
    # "(News)indeks volatilitas",
    # "(News)Kurs",
    "(News)indeks kinerja manufaktur",
    "(News)indeks kinerja jasa",
    # "(News)Harga Minyak",
    # "(News)Volume Minyak",
    # "(News)SAF",
    # "(News)Crackspread_BBM",
    # "(News)Crackspread_NonBBM",
]

# Canonical source name overrides
SOURCE_NAME_MAP = {
    "KONTAN_BBM":      "KONTAN",
    "KONTAN_BIODIESEL": "KONTAN",
    "GOOGLE_NEWS_CNN":  "CNN",
    "GOOGLE_NEWS_CNBC": "CNBC",
    "SPGLOBAL":         "S&P",
}

# Column rename map for standardization
COLUMN_RENAME_MAP = {
    "Judul":   "title",
    "judul":   "title",
    "Title":   "title",
    "Tanggal": "date",
    "tanggal": "date",
    "Date":    "date",
    "Link":    "url",
    "link":    "url",
    "URL":     "url",
    "Konten":  "content",
    "konten":  "content",
    "Content": "content",
}

REQUIRED_COLUMNS = ["title", "date", "url", "content"]
COLUMN_ORDER     = ["title", "date", "url", "content", "source", "keyword"]
EMPTY_DF         = pd.DataFrame(columns=COLUMN_ORDER)

# Helpers

def _clean_date(date_str) -> str:
    """Normalize a date value to YYYY-MM-DD or 'N/A'."""
    if pd.isna(date_str) or date_str in ("N/A", "-"):
        return "N/A"
    date_str = str(date_str).strip().split("T")[0].split(" ")[0]
    return date_str if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str) else "N/A"


def standardize_format(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns, fill missing required columns, and normalize dates."""
    if df is None or df.empty:
        return EMPTY_DF.copy()

    df = df.rename(columns=COLUMN_RENAME_MAP)

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = "N/A"

    df["date"] = df["date"].apply(_clean_date)

    existing_cols = [col for col in COLUMN_ORDER if col in df.columns]
    return df[existing_cols]


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Drop duplicate rows based on URL."""
    if df.empty:
        return df
    return df.drop_duplicates(subset=["url"], keep="first")

# Core scraping logic

def scrape_keyword(keyword: str, tanggal_filter: str) -> pd.DataFrame:
    """Scrape all synonyms of a keyword from all configured sources."""
    hasil_final = pd.DataFrame()
    semua_keyword = [keyword] + SINONIM_DICT.get(keyword, [])
    sumber = SUMBER_DICT.get(keyword, [])

    for kata in semua_keyword:
        print(f"\n  Kata kunci: '{kata}'")
        hasil_list = []

        for scrape_func in sumber:
            raw_name   = scrape_func.__name__.replace("scrape_", "").replace("main_", "").upper()
            nama_sumber = SOURCE_NAME_MAP.get(raw_name, raw_name)
            print(f"    Scraping dari {nama_sumber}...")

            try:
                data = scrape_func(kata, tanggal_filter)
                if isinstance(data, pd.DataFrame):
                    df_temp = data
                elif data:
                    df_temp = pd.DataFrame(data)
                else:
                    df_temp = pd.DataFrame()

                if not df_temp.empty:
                    df_temp["source"] = nama_sumber
                    df_temp = standardize_format(df_temp)
                    hasil_list.append(df_temp)
                    print(f"    {len(df_temp)} berita dari {nama_sumber}")
                else:
                    print(f"    Tidak ada berita dari {nama_sumber}")

            except Exception as e:
                print(f"    Gagal scrape {nama_sumber}: {e}")

        if hasil_list:
            df_kata = pd.concat(hasil_list, ignore_index=True)
            df_kata["keyword"] = kata
            hasil_final = pd.concat([hasil_final, df_kata], ignore_index=True)

    return hasil_final if not hasil_final.empty else EMPTY_DF.copy()

# Main

def main():
    print("\n" + "=" * 60)
    print("NEWS SCRAPING TO ONEDRIVE")
    print("=" * 60)

    print("\nAuthenticating to Microsoft Graph API...")
    try:
        access_token = get_access_token()
        print("Authentication successful")
    except Exception as e:
        print(f"Authentication failed: {e}")
        return

    # tanggal_filter = "2026-04-06"
    tanggal_filter = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"\nTanggal filter: {tanggal_filter}")

    # --- Load existing sheets from OneDrive ---
    print(f"\nLoading existing data from OneDrive...")
    print(f"File: {ONEDRIVE_FILE_PATH}")

    excel_buffer = download_excel_from_onedrive(access_token, ONEDRIVE_FILE_PATH)
    all_sheets: dict[str, pd.DataFrame] = {}

    if excel_buffer is None:
        print("File tidak ditemukan, akan membuat file baru")
        for sheet_name in ACTIVE_SHEETS:
            all_sheets[sheet_name] = pd.DataFrame()
    else:
        print("File ditemukan, membaca semua sheets...")
        excel_buffer.seek(0)
        excel_file = pd.ExcelFile(excel_buffer)

        for sheet_name in ACTIVE_SHEETS:
            try:
                if sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    all_sheets[sheet_name] = df
                    print(f"  '{sheet_name}': {len(df)} baris")
                else:
                    print(f"  '{sheet_name}': tidak ada, akan dibuat baru")
                    all_sheets[sheet_name] = pd.DataFrame()
            except Exception as e:
                print(f"  '{sheet_name}': error ({e}), akan dibuat baru")
                all_sheets[sheet_name] = pd.DataFrame()

        excel_file.close()

    # --- Scraping ---
    print("\n" + "=" * 60)
    print("MULAI SCRAPING")
    print("=" * 60)

    for sheet_name in ACTIVE_SHEETS:
        keyword_asli = SHEET_TO_KEYWORD.get(sheet_name)
        if not keyword_asli:
            print(f"\nKeyword untuk '{sheet_name}' tidak ditemukan di mapping. Lewati.")
            continue

        print(f"\n{'-' * 60}")
        print(f"Sheet  : {sheet_name}")
        print(f"Keyword: {keyword_asli}")
        print(f"{'-' * 60}")

        hasil_df = scrape_keyword(keyword_asli, tanggal_filter)

        existing = all_sheets.get(sheet_name, pd.DataFrame())
        if not existing.empty:
            combined_df = pd.concat([existing, hasil_df], ignore_index=True)
            print(f"\n  Data existing : {len(existing)} baris")
            print(f"  Data baru     : {len(hasil_df)} baris")
        else:
            combined_df = hasil_df
            print(f"\n  Data baru: {len(hasil_df)} baris")

        combined_df = remove_duplicates(combined_df)
        all_sheets[sheet_name] = combined_df
        print(f"  Total (setelah deduplikasi): {len(combined_df)} baris")

        print("\nIstirahat 60 detik...")
        time.sleep(60)

    # --- Save to OneDrive ---
    print("\n" + "=" * 60)
    print("MENYIMPAN KE ONEDRIVE")
    print("=" * 60)

    try:
        print("\nMendapatkan fresh token untuk menyimpan...")
        access_token = get_access_token()
        write_multiple_sheets_to_onedrive(access_token, ONEDRIVE_FILE_PATH, all_sheets)

        print("\n" + "=" * 60)
        print("SELESAI!")
        print(f"File  : {ONEDRIVE_FILE_PATH}")
        print(f"Sheets: {len(ACTIVE_SHEETS)}")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\nError saat menyimpan: {e}")
        raise


if __name__ == "__main__":
    main()