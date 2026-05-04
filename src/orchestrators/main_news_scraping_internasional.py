import os
import re
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers.onedrive_helper import (
    download_excel_from_onedrive,
    get_access_token,
    read_excel_sheet_from_onedrive,
    write_multiple_sheets_to_onedrive,
)
from news.bioenergytimes import scrape_bioenergytimes
from news.cnbc import main_google_news_cnbc
from news.cnn import main_google_news_cnn
from news.energiesmedia import scrape_energiesmedia
from news.oilprice import scrape_oilprice
from news.spglobal_news import scrape_spglobal as scrape_news_sap
from news.scmp import main_scmp
from news.the_guardian import scrape_the_guardian as scrape_theguardian


# CONFIG

ONEDRIVE_FILE_PATH = os.getenv("ONEDRIVE_FILE_PATH", "/results/(News)Scraping_final.xlsx")


# KEYWORD SYNONYMS

SINONIM_DICT: dict[str, list[str]] = {
    ### Makroekonomi ###
    # "geopolitical risk ": ["geopolitical pressure "],
    # "volatility index ": [
    #     "market volatility ", "financial volatility ", "trade volatility ",
    # ],
    # "dxy ": ["dollar index "],
    # "purchasing manufaktur index ": [
    #     "manufaktur index ", "purchasing manufacturing index", "manufacturing pmi ",
    # ],
    # "purchasing services index ": [
    #     "services index ", "services pmi ",
    # ],

    # ### Hulu Migas ###
    # "oil price ": ["crude oil "],
    # "oil volume ": ["bbm volume "],

    ## Produk Kilang Pertamina ###
    "pertamina oil price ": ["oil price "],
    "pertamina oil volume ": ["oil volume ", "bbm volume "],
    "RON 92 ": [
        "pertamax ", "RON 95 ", "RON 97 ", "Residual FO ", "Fuel Oil", "Jet Fuel ", "Avtur ",
        "Kerosene ", "refinery ", "refined products ", "refining ", "oil products ", "Gasoline ",
        "Heavy Oil ", "Diesel ", "Gasoil ", "Naphtha ", "LPG ", "Biodiesel ", "Biogasoline ",
        "Petroleum Coke ", "Oil price ", "fuel cost ", "fuel price ",
    ],

    # ### Petrokimia Hulu ###
    # "Petrochemical ": [
    #     "chemical ", "aromatic ", "olefin ", "polymer ", "LPG ",
    #     "Paraxylene ", "Propylene ", "Benzene ", "Green Coke ",
    #     "petrochemicals ", "petrokimia ", "petrochemical complex ",
    #     "aromatic compound ", "BTX aromatic ", "senyawa aromatik ",
    #     "green petroleum coke ", "petroleum coke ", "polyethylene",
    #     "polypropylene", "etilena", "propilena",
    # ],

    # ### Bioenergi ###
    # "SAF ": [
    #     "UCO ", "sustainable aviation fuel ", "used cooking oil ",
    #     "CORSIA ", "SAFCo ", "biorefinery ", "bioavtur ", "pome ",
    # ],
}


# SCRAPING SOURCES PER KEYWORD

SUMBER_DICT: dict[str, list] = {
    # ### Makroekonomi ###
    # "geopolitical risk ": [main_google_news_cnn, main_google_news_cnbc, main_scmp, scrape_theguardian],
    # "volatility index ": [main_google_news_cnn, main_google_news_cnbc, main_scmp, scrape_theguardian],
    # "dxy ": [main_google_news_cnn, main_google_news_cnbc],
    # "purchasing manufaktur index ": [scrape_news_sap],
    # "purchasing services index ": [scrape_news_sap],

    # ### Hulu Migas ###
    # "oil price ": [scrape_oilprice],
    # "oil volume ": [scrape_oilprice],

    ### Produk Kilang Pertamina ###
    "pertamina oil price ": [scrape_oilprice],
    "pertamina oil volume ": [scrape_oilprice],
    "RON 92 ": [scrape_news_sap, main_google_news_cnbc, main_google_news_cnn, scrape_energiesmedia, scrape_bioenergytimes, scrape_theguardian],

    # ### Petrokimia Hulu ###
    # "Petrochemical ": [scrape_news_sap, main_google_news_cnbc, main_google_news_cnn, scrape_energiesmedia, scrape_bioenergytimes],

    # ### Bioenergi ###
    # "SAF ": [scrape_news_sap, main_google_news_cnbc, main_google_news_cnn],
}


# SHEET → KEYWORD MAPPING & ACTIVE SHEETS

SHEET_TO_KEYWORD: dict[str, str] = {
    # ### Makroekonomi ###
    # "(News)Indeks Risiko Geopolitik": "geopolitical risk ",
    # "(News)Indeks Volatilitas": "volatility index ",
    # "(News)Kurs": "dxy ",
    # "(News)Indeks Kinerja Manufaktur": "purchasing manufaktur index ",
    # "(News)Indeks Kinerja Jasa": "purchasing services index ",

    # ### Hulu Migas ###
    # "(News)Harga Minyak": "oil price ",
    # "(News)Volume Minyak": "oil volume ",

    ### Produk Kilang Pertamina ###
    "(News)Harga Produk Kilang": "pertamina oil price ",
    "(News)Volume Produk Kilang": "pertamina oil volume ",
    "(News)Crackspread BBM": "RON 92 ",

    # ### Petrokimia Hulu ###
    # "(News)Crackspread Non-BBM": "Petrochemical ",

    # ### Bioenergi ###
    # "(News)SAF": "SAF ",
}

ACTIVE_SHEETS: list[str] = [
    # ### Makroekonomi ###
    # "(News)Indeks Risiko Geopolitik",
    # "(News)Indeks Volatilitas",
    # "(News)Kurs",
    # "(News)Indeks Kinerja Manufaktur",
    # "(News)Indeks Kinerja Jasa",

    # ### Hulu Migas ###
    # "(News)Harga Minyak",
    # "(News)Volume Minyak",

    ### Produk Kilang Pertamina ###
    "(News)Harga Produk Kilang",
    "(News)Volume Produk Kilang",
    "(News)Crackspread BBM",

    # ### Petrokimia Hulu ###
    # "(News)Crackspread Non-BBM",

    # ### Bioenergi ###
    # "(News)SAF",
]


# COLUMN STANDARDIZATION

SOURCE_NAME_MAP: dict[str, str] = {
    "KONTAN_BBM":       "KONTAN",
    "KONTAN_BIODIESEL": "KONTAN",
    "GOOGLE_NEWS_CNN":  "CNN",
    "GOOGLE_NEWS_CNBC": "CNBC",
    "SPGLOBAL":         "S&P",
}

COLUMN_RENAME_MAP: dict[str, str] = {
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

REQUIRED_COLUMNS: list[str] = ["title", "date", "url", "content"]
COLUMN_ORDER:     list[str] = ["title", "date", "url", "content", "source", "keyword"]
EMPTY_DF = pd.DataFrame(columns=COLUMN_ORDER)


# HELPER FUNCTIONS

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

def generate_date_range(start_date: str, end_date: str) -> list[str]:
    """Generate list of dates between start_date and end_date (inclusive, YYYY-MM-DD)."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end   = datetime.strptime(end_date,   "%Y-%m-%d")
    if start > end:
        raise ValueError(f"start_date ({start_date}) tidak boleh lebih besar dari end_date ({end_date})")
    dates, current = [], start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates


# CORE SCRAPING LOGIC

def scrape_keyword(keyword: str, tanggal_filter: str) -> pd.DataFrame:
    """
    Scrape all synonyms of a keyword from all configured sources and return
    a combined, standardized DataFrame.
    """
    hasil_final   = pd.DataFrame()
    semua_keyword = [keyword] + SINONIM_DICT.get(keyword, [])
    sumber        = SUMBER_DICT.get(keyword, [])

    for kata in semua_keyword:
        print(f"\n  Keyword: '{kata}'")
        hasil_list: list[pd.DataFrame] = []

        for scrape_func in sumber:
            raw_name    = scrape_func.__name__.replace("scrape_", "").replace("main_", "").upper()
            nama_sumber = SOURCE_NAME_MAP.get(raw_name, raw_name)
            print(f"    Scraping from {nama_sumber}...")

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
                    print(f"    {len(df_temp)} article(s) from {nama_sumber}.")
                else:
                    print(f"    No articles from {nama_sumber}.")

            except Exception as exc:
                print(f"    Failed to scrape {nama_sumber}: {exc}")

        if hasil_list:
            df_kata            = pd.concat(hasil_list, ignore_index=True)
            df_kata["keyword"] = kata
            hasil_final        = pd.concat([hasil_final, df_kata], ignore_index=True)

    return hasil_final if not hasil_final.empty else EMPTY_DF.copy()


# MAIN

def main() -> None:
    """
    Run the full global news scraping workflow: authenticate, load existing
    OneDrive data, scrape each active sheet's keyword, merge results, and
    write the updated file back to OneDrive.
    """
    print("\n" + "=" * 60)
    print("NEWS SCRAPING TO ONEDRIVE")
    print("=" * 60)

    # === KONFIGURASI TANGGAL ===
    # Pilih salah satu mode:

    # Mode 1: Satu tanggal spesifik
    # tanggal_list = ["2026-04-21"]

    # Mode 2: Range tanggal
    START_DATE   = "2026-04-29"
    END_DATE     = "2026-04-30"
    tanggal_list = generate_date_range(START_DATE, END_DATE)

    # Mode 3: Kemarin
    # tanggal_list = [(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")]

    # Mode 4: Hari ini
    # tanggal_list = [datetime.now().strftime("%Y-%m-%d")]
    # ===========================

    print(f"\nAkan scraping untuk {len(tanggal_list)} tanggal:")
    for t in tanggal_list:
        print(f"  - {t}")

    print("\nAuthenticating to Microsoft Graph API...")
    try:
        access_token = get_access_token()
        print("Authentication successful.")
    except Exception as exc:
        print(f"Authentication failed: {exc}")
        return

    # --- Load existing sheets dari OneDrive SEKALI di awal ---
    print(f"\nLoading existing data from OneDrive...")
    print(f"File: {ONEDRIVE_FILE_PATH}")

    excel_buffer = download_excel_from_onedrive(access_token, ONEDRIVE_FILE_PATH)
    all_sheets: dict[str, pd.DataFrame] = {}

    if excel_buffer is None:
        print("[Main] File not found — a new file will be created.")
        for sheet_name in ACTIVE_SHEETS:
            all_sheets[sheet_name] = pd.DataFrame()
    else:
        print("[Main] File found — reading all sheets...")
        excel_buffer.seek(0)
        excel_file = pd.ExcelFile(excel_buffer)
        for sheet_name in ACTIVE_SHEETS:
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

    # --- Loop per tanggal ---
    total_dates = len(tanggal_list)

    for date_idx, tanggal_filter in enumerate(tanggal_list, 1):
        print("\n" + "=" * 60)
        print(f"SCRAPING TANGGAL {date_idx}/{total_dates}: {tanggal_filter}")
        print("=" * 60)

        for sheet_name in ACTIVE_SHEETS:
            keyword_asli = SHEET_TO_KEYWORD.get(sheet_name)
            if not keyword_asli:
                print(f"\n[Main] No keyword mapping for '{sheet_name}' — skipping.")
                continue

            print(f"\n{'-' * 60}")
            print(f"Sheet  : {sheet_name}")
            print(f"Keyword: {keyword_asli}")
            print(f"Tanggal: {tanggal_filter}")
            print(f"{'-' * 60}")

            hasil_df = scrape_keyword(keyword_asli, tanggal_filter)

            existing = all_sheets.get(sheet_name, pd.DataFrame())
            if not existing.empty:
                combined_df = pd.concat([existing, hasil_df], ignore_index=True)
                print(f"\n  Data existing : {len(existing)} row(s)")
                print(f"  Data baru     : {len(hasil_df)} row(s)")
            else:
                combined_df = hasil_df
                print(f"\n  Data baru: {len(hasil_df)} row(s)")

            combined_df = remove_duplicates(combined_df)
            all_sheets[sheet_name] = combined_df
            print(f"  Total (after dedup): {len(combined_df)} row(s)")

            print("\nIstirahat 60 detik antar keyword...")
            time.sleep(60)

        # Simpan ke OneDrive setiap selesai 1 tanggal
        print(f"\n{'=' * 60}")
        print(f"MENYIMPAN PROGRES — Selesai tanggal {tanggal_filter} ({date_idx}/{total_dates})")
        print(f"{'=' * 60}")

        try:
            access_token = get_access_token()  # Refresh token setiap save
            write_multiple_sheets_to_onedrive(access_token, ONEDRIVE_FILE_PATH, all_sheets)
            print(f"Berhasil disimpan ke OneDrive.")
        except Exception as exc:
            print(f"Error saat menyimpan setelah tanggal {tanggal_filter}: {exc}")
            print("Melanjutkan ke tanggal berikutnya...")

        # Jeda antar tanggal (kecuali tanggal terakhir)
        if date_idx < total_dates:
            jeda = 60
            print(f"\nIstirahat {jeda} detik sebelum tanggal berikutnya...")
            time.sleep(jeda)

    # --- Summary akhir ---
    print("\n" + "=" * 60)
    print("SELESAI SEMUA TANGGAL!")
    print(f"File            : {ONEDRIVE_FILE_PATH}")
    print(f"Sheets          : {len(ACTIVE_SHEETS)}")
    print(f"Tanggal diproses: {tanggal_list[0]} s/d {tanggal_list[-1]}")
    print(f"Total baris     : {sum(len(df) for df in all_sheets.values())}")
    print("=" * 60 + "\n")


# ENTRY POINT

if __name__ == "__main__":
    main()