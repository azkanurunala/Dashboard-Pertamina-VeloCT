import os
import re
import sys
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers.storage_backend import storage

load_dotenv()


# Constants

ONEDRIVE_FILE_PATH = os.getenv("ONEDRIVE_DATA_PATH", "/results/(Terstruktur)Data_Scraping_final.xlsx")
SHEET_NAME         = "(Data)EIA"

API_KEY      = os.getenv("EIA_API_KEY")
BASE_API_URL = "https://api.eia.gov/v2/steo/data/"
STEO_URL     = "https://www.eia.gov/outlooks/steo/data/browser/"

SERIES_IDS = {
    "PAPR_WORLD":  "World Total Production",
    "PAPR_OPEC":   "OPEC Production",
    "PAPR_NONOPEC":"Non-OPEC Production",
    "COPR_WORLD":  "Crude Oil",
    "PATC_WORLD":  "World Total Consumption",
    "PATC_OECD":   "OECD Consumption",
}

MONTHS_EN_TO_NUM = {
    "January": 1, "February": 2, "March": 3,    "April": 4,
    "May": 5,     "June": 6,     "July": 7,      "August": 8,
    "September": 9,"October": 10,"November": 11, "December": 12,
}
MONTHS_ID_TO_NUM = {
    "januari": 1,  "februari": 2,  "maret": 3,    "april": 4,
    "mei": 5,      "juni": 6,      "juli": 7,      "agustus": 8,
    "september": 9,"oktober": 10,  "november": 11, "desember": 12,
}
MONTHS_NUM_TO_ID = {
    1: "Januari", 2: "Februari", 3: "Maret",    4: "April",
    5: "Mei",     6: "Juni",     7: "Juli",      8: "Agustus",
    9: "September",10: "Oktober",11: "November", 12: "Desember",
}


# Release Date Check

def get_eia_release_dates():
    """
    Scrape current and next EIA STEO release dates from the EIA website.

    Returns a dict with success flag and parsed datetime objects.
    """
    try:
        response = requests.get(STEO_URL, timeout=10)
        response.raise_for_status()
        soup          = BeautifulSoup(response.text, "html.parser")
        pub_title_div = soup.find("div", class_="pub_title")

        if not pub_title_div:
            return {"success": False, "error": "Could not find pub_title div"}

        p_tag = pub_title_div.find("p")
        if not p_tag:
            return {"success": False, "error": "Could not find paragraph tag"}

        text = p_tag.get_text()

        release_match = re.search(r"Release Date:\s*(\w+)\s+(\d+),\s+(\d+)", text)
        next_match    = re.search(r"Next Release Date:\s*(\w+)\s+(\d+),\s+(\d+)", text)

        if not release_match:
            return {"success": False, "error": "Could not parse Release Date"}
        if not next_match:
            return {"success": False, "error": "Could not parse Next Release Date"}

        def _parse(match):
            month_name = match.group(1)
            day        = int(match.group(2))
            year       = int(match.group(3))
            month      = MONTHS_EN_TO_NUM.get(month_name)
            if not month:
                raise ValueError(f"Unknown month: {month_name}")
            return datetime(year, month, day), f"{month_name} {day}, {year}"

        release_date,      release_date_str      = _parse(release_match)
        next_release_date, next_release_date_str = _parse(next_match)

        return {
            "success":              True,
            "release_date":         release_date,
            "release_date_str":     release_date_str,
            "next_release_date":    next_release_date,
            "next_release_date_str":next_release_date_str,
        }

    except requests.exceptions.RequestException as exc:
        return {"success": False, "error": f"Network error: {exc}"}
    except Exception as exc:
        return {"success": False, "error": f"Unexpected error: {exc}"}


# Last Entry Check

def read_last_entry_from_excel():
    """
    Read the EIA sheet and return (last_year, last_month_num) of the latest entry.

    Returns (None, None) if the sheet is empty, missing, or unreadable.
    """
    try:
        df = storage.read_structured_sheet(SHEET_NAME)
        if df.empty or "Bulan" not in df.columns or "Tahun" not in df.columns:
            print("[Check] Sheet kosong atau format salah — semua data akan diunduh.")
            return None, None

        df["Bulan"]      = df["Bulan"].astype(str).str.lower()
        df["Bulan_Angka"] = df["Bulan"].map(MONTHS_ID_TO_NUM)
        df = df.dropna(subset=["Bulan_Angka"])

        if df.empty:
            print("[Check] Tidak ada data valid — semua data akan diunduh.")
            return None, None

        last_row = df.sort_values(["Tahun", "Bulan_Angka"]).iloc[-1]
        print(f"[Check] Data terakhir: {last_row['Bulan'].capitalize()} {int(last_row['Tahun'])}")
        return int(last_row["Tahun"]), int(last_row["Bulan_Angka"])

    except ValueError:
        print(f"[Check] Sheet '{SHEET_NAME}' tidak ditemukan — semua data akan diunduh.")
        return None, None
    except Exception as exc:
        print(f"[Check] Error membaca Excel: {exc}")
        return None, None

def should_run_scraping():
    """
    Compare the Next Release Date stored in storage against today's date.

    Returns (should_run, release_info).
    """
    print("[Check] Memeriksa apakah scraping diperlukan...")
    release_info = get_eia_release_dates()

    if not release_info["success"]:
        print(f"[Check] Warning: {release_info.get('error')} — tetap jalankan scraping.")
        return True, None

    print(f"[Check] Release Date website     : {release_info['release_date_str']}")
    print(f"[Check] Next Release Date website: {release_info['next_release_date_str']}")

    try:
        df = storage.read_structured_sheet(SHEET_NAME)
        if df.empty or "Next Release Date" not in df.columns:
            print("[Check] Next Release Date tidak ditemukan — jalankan scraping.")
            return True, release_info

        last_next_release_str = df["Next Release Date"].iloc[-1]
        if pd.isna(last_next_release_str):
            print("[Check] Next Release Date kosong — jalankan scraping.")
            return True, release_info

        last_next_release = pd.to_datetime(last_next_release_str).replace(tzinfo=None)
        today             = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)

        print(f"[Check] Next Release Date Excel  : {last_next_release.strftime('%B %d, %Y')}")

        if today > last_next_release:
            print(f"[Check] Hari ini ({today.strftime('%Y-%m-%d')}) >= Next Release Date — jalankan scraping.")
            return True, release_info
        else:
            print(f"[Check] Hari ini ({today.strftime('%Y-%m-%d')}) < Next Release Date — skip.")
            return False, release_info

    except ValueError:
        print(f"[Check] Sheet '{SHEET_NAME}' tidak ditemukan — jalankan scraping.")
        return True, release_info
    except Exception as exc:
        print(f"[Check] Error: {exc} — tetap jalankan scraping.")
        return True, release_info


# Needed Data Calculation

def get_needed_data():
    """
    Calculate which months need to be fetched based on the last entry in storage.

    Returns:
        None  — no existing data, fetch all from 2015
        []    — data already up to date
        list  — list of (year, month) tuples to fetch
    """
    last_year, last_month = read_last_entry_from_excel()

    today = datetime.today()
    cur_month = today.month - 1
    cur_year  = today.year
    if cur_month == 0:
        cur_month = 12
        cur_year -= 1

    if last_year is None or last_month is None:
        print("[Fetch] Tidak ada data existing — ambil semua data.")
        return None

    next_month = last_month + 1
    next_year  = last_year
    if next_month > 12:
        next_month = 1
        next_year += 1

    if next_year > cur_year or (next_year == cur_year and next_month > cur_month):
        print(f"[Fetch] Data sudah up-to-date ({MONTHS_NUM_TO_ID[last_month]} {last_year}).")
        return []

    # Kumpulkan semua bulan yang kurang
    needed   = []
    current  = (next_year, next_month)
    while current[0] < cur_year or (current[0] == cur_year and current[1] <= cur_month):
        needed.append(current)
        m = current[1] + 1
        y = current[0]
        if m > 12:
            m = 1
            y += 1
        current = (y, m)

    print(f"[Fetch] Akan mengambil {len(needed)} bulan: {needed[0]} s.d. {needed[-1]}")
    return needed

def get_date_range(needed_data):
    """Convert needed_data list to (start_str, end_str) for the EIA API."""
    if needed_data is None:
        today     = datetime.today()
        end_month = today.month - 1
        end_year  = today.year
        if end_month == 0:
            end_month = 12
            end_year -= 1
        start_str = "2015-01"
        end_str   = f"{end_year}-{end_month:02d}"
        print(f"[Fetch] Range: {start_str} s.d. {end_str}")
        return start_str, end_str

    if not needed_data:
        return None, None

    start_str = f"{needed_data[0][0]}-{needed_data[0][1]:02d}"
    end_str   = f"{needed_data[-1][0]}-{needed_data[-1][1]:02d}"
    print(f"[Fetch] Range: {start_str} s.d. {end_str}")
    return start_str, end_str


# EIA API Fetch

def fetch_eia_series(series_id, start, end):
    """
    Fetch monthly data for a single EIA STEO series ID.

    Returns a list of records, or [] on failure.
    """
    params = {
        "api_key":           API_KEY,
        "frequency":         "monthly",
        "data[0]":           "value",
        "facets[seriesId][]": series_id,
        "start":             start,
        "end":               end,
    }
    print(f"[Fetch] {series_id}...")
    try:
        response = requests.get(BASE_API_URL, params=params, timeout=30)
        response.raise_for_status()
        data    = response.json()
        records = data.get("response", {}).get("data", [])
        print(f"[Fetch] {series_id}: {len(records)} records.")
        return records
    except requests.exceptions.RequestException as exc:
        print(f"[Fetch] Error {series_id}: {exc}")
        return []


# Data Transform

def transform_to_dataframe(all_data, release_info=None):
    """
    Merge all series records into a single DataFrame with one row per period.

    Computes derived columns: Other Liquids and Non-OECD.
    """
    period_data: dict[str, dict] = {}

    for series_id, records in all_data.items():
        for record in records:
            period = record.get("period")
            value  = record.get("value")
            if period and value and value != "w":
                try:
                    period_data.setdefault(period, {})[series_id] = round(float(value), 2)
                except (ValueError, TypeError):
                    period_data.setdefault(period, {})[series_id] = None

    next_release_str = release_info["next_release_date_str"] if release_info and release_info["success"] else None

    rows = []
    for period in sorted(period_data.keys()):
        year, month    = int(period.split("-")[0]), int(period.split("-")[1])
        d              = period_data[period]
        world_prod     = d.get("PAPR_WORLD")
        opec           = d.get("PAPR_OPEC")
        non_opec       = d.get("PAPR_NONOPEC")
        crude_oil      = d.get("COPR_WORLD")
        world_cons     = d.get("PATC_WORLD")
        oecd           = d.get("PATC_OECD")
        other_liquids  = round(world_prod - crude_oil, 2) if world_prod and crude_oil else None
        non_oecd       = round(world_cons - oecd, 2)     if world_cons and oecd       else None

        rows.append({
            "Bulan":                  MONTHS_NUM_TO_ID.get(month, f"Month-{month}"),
            "Tahun":                  year,
            "Next Release Date":      next_release_str,
            "World Total Production": world_prod,
            "OPEC":                   opec,
            "Non-OPEC":               non_opec,
            "Crude Oil":              crude_oil,
            "Other Liquids":          other_liquids,
            "World Total Consumption": world_cons,
            "OECD":                   oecd,
            "Non-OECD":               non_oecd,
        })

    return pd.DataFrame(rows)


# Save to Storage

def save_to_onedrive(df):
    """
    Merge new EIA data with existing storage sheet, deduplicate, sort, and write.
    """
    if df.empty:
        print("[Save] DataFrame kosong, tidak ada yang disimpan.")
        return

    print(f"\n{'='*60}")
    print("[Save] Menyimpan data ke storage")
    print(f"{'='*60}")

    try:
        existing_df = storage.read_structured_sheet(SHEET_NAME)
        if existing_df.empty:
            print("[Save] Sheet kosong, akan membuat baru.")
            combined_df = df
        else:
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            combined_df.drop_duplicates(subset=["Bulan", "Tahun"], keep="last", inplace=True)
            combined_df["Bulan_Order"] = combined_df["Bulan"].map(
                {v: k for k, v in MONTHS_NUM_TO_ID.items()}
            )
            combined_df.sort_values(["Tahun", "Bulan_Order"], inplace=True)
            combined_df.drop(columns=["Bulan_Order"], inplace=True)
            print(f"[Save] Data lama: {len(existing_df)} baris.")
    except Exception as exc:
        print(f"[Save] Error membaca sheet existing: {exc}")
        combined_df = df

    print(f"[Save] Data baru              : {len(df)} baris.")
    print(f"[Save] Data setelah deduplikasi: {len(combined_df)} baris.")

    try:
        storage.write_structured_sheet(SHEET_NAME, combined_df)

        print(f"\n{'='*60}")
        print("[Save] DATA BERHASIL DISIMPAN")
        print(f"{'='*60}")
        print(f"[Save] Sheet     : {SHEET_NAME}")
        print(f"[Save] Total rows: {len(combined_df)}")
        print(f"[Save] Data baru : {len(df)} baris")

    except Exception as exc:
        print(f"[Save] Error saat menyimpan: {exc}")
        import traceback
        traceback.print_exc()


# Public Entry Point

def main_eia():
    """
    Run the full EIA STEO scraping workflow:
    check release date, fetch missing months, transform, save to storage.
    """
    print(f"\n{'='*60}")
    print("EIA STEO DATA SCRAPER")
    print(f"{'='*60}")
    print(f"\n[Main] Sheet: {SHEET_NAME}")

    should_run, release_info = should_run_scraping()
    if not should_run:
        print(f"\n{'='*60}")
        print("[Main] SKIPPED — data belum perlu diupdate.")
        print(f"{'='*60}\n")
        return

    print("\n[Main] Mengecek bulan yang perlu diambil...")
    needed_data = get_needed_data()

    if needed_data is not None and len(needed_data) == 0:
        print("[Main] Semua data sudah up-to-date.")
        return

    start, end = get_date_range(needed_data)
    if not start:
        return

    print(f"\n[Main] Fetching data dari EIA API ({start} s.d. {end})...")
    all_data = {}
    for series_id in SERIES_IDS:
        records = fetch_eia_series(series_id, start, end)
        if records:
            all_data[series_id] = records

    if not all_data:
        print("\n[Main] Tidak ada data yang berhasil diambil.")
        return

    print("\n[Main] Transforming data...")
    df = transform_to_dataframe(all_data, release_info)

    if df.empty:
        print("[Main] Tidak ada data valid untuk disimpan.")
        return

    print(f"[Main] {len(df)} baris berhasil ditransform.")
    print("\n[Main] Preview:")
    print(df.to_string(index=False))

    save_to_onedrive(df)

    print(f"\n{'='*60}")
    print("[Main] SELESAI!")
    print(f"{'='*60}\n")


# Script Entry Point

if __name__ == "__main__":
    main_eia()