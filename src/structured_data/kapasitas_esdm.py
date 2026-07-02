import os
import sys
import traceback

import pandas as pd
import requests
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers.storage_backend import storage

load_dotenv()


# Constants

ONEDRIVE_FILE_PATH = os.getenv("ONEDRIVE_DATA_PATH", "/results/(Terstruktur)Data_Scraping_final.xlsx")
SHEET_NAME         = "(Data)Kapasitas_EBT"

API_URL     = "https://ebtke.esdm.go.id/api/api/konten/data-angka"
API_TIMEOUT = 30

MONTHS_EN_TO_NUM = {
    "January": 1,  "February": 2,  "March": 3,    "April": 4,
    "May": 5,      "June": 6,      "July": 7,      "August": 8,
    "September": 9,"October": 10,  "November": 11, "December": 12,
}

KAPASITAS_FIELDS = [
    "plta", "pltm", "pltmh", "pltp", "plts", "plts_atap",
    "pltb", "pltbm", "pltbg", "pltsa", "pltbn", "plt_hybrid", "total",
]


# API Fetch

def fetch_ebtke_data():
    """
    Fetch the latest EBT power plant capacity data from the EBTKE API.

    Returns a single-row DataFrame, or None on failure.
    """
    print("[Fetch] Mengambil data kapasitas pembangkit EBT...")
    try:
        response = requests.get(API_URL, timeout=API_TIMEOUT)
        response.raise_for_status()

        data          = response.json()
        kapasitas_data = data.get("data", {}).get("dataAngkaKapasitasPembangkit", {})

        if not kapasitas_data:
            print("[Fetch] Data kapasitas pembangkit tidak ditemukan di response API.")
            return None

        bulan = MONTHS_EN_TO_NUM.get(kapasitas_data.get("bulan"), kapasitas_data.get("bulan"))
        row   = {
            "tahun": kapasitas_data.get("tahun"),
            "bulan": bulan,
            **{field: kapasitas_data.get(field) for field in KAPASITAS_FIELDS},
        }

        df = pd.DataFrame([row])
        print(f"[Fetch] Data berhasil diambil: tahun={row['tahun']}, bulan={row['bulan']}.")
        return df

    except requests.exceptions.RequestException as exc:
        print(f"[Fetch] Error request ke API: {exc}")
        traceback.print_exc()
        return None
    except Exception as exc:
        print(f"[Fetch] Error tidak terduga: {exc}")
        traceback.print_exc()
        return None


# Duplicate Check

def check_data_exists(tahun, bulan):
    """
    Check if a row with the given tahun and bulan already exists in storage.

    Returns True if found, False otherwise.
    """
    try:
        df = storage.read_structured_sheet(SHEET_NAME)
        if df.empty or "tahun" not in df.columns or "bulan" not in df.columns:
            print(f"[Check] Sheet kosong atau kolom tidak ditemukan.")
            return False

        found = not df[(df["tahun"].astype(str) == str(tahun)) &
                       (df["bulan"].astype(str) == str(bulan))].empty
        if found:
            print(f"[Check] Data tahun {tahun} bulan {bulan} sudah ada.")
        else:
            print(f"[Check] Data tahun {tahun} bulan {bulan} belum ada.")
        return found

    except Exception as exc:
        print(f"[Check] Error saat cek data: {exc}")
        traceback.print_exc()
        return False


# Data Merge

def _merge_data(df_existing, df_new):
    """
    Concatenate existing and new DataFrames, deduplicate by tahun+bulan, and sort.
    """
    df_combined = pd.concat([df_existing, df_new], ignore_index=True)

    if "tahun" in df_combined.columns and "bulan" in df_combined.columns:
        df_combined = df_combined.drop_duplicates(subset=["tahun", "bulan"], keep="last")

    if "tahun" in df_combined.columns:
        df_combined["tahun"] = pd.to_numeric(df_combined["tahun"], errors="coerce")
        df_combined = df_combined.sort_values(["tahun", "bulan"], ascending=True)

    print(f"[Merge] Data setelah merge: {len(df_combined)} rows.")
    return df_combined


# Save to Storage

def save_to_onedrive(df_new):
    """
    Merge new capacity data with existing storage sheet, deduplicate, sort, and write.
    """
    if df_new is None or df_new.empty:
        print("[Save] Tidak ada data untuk disimpan.")
        return

    print(f"\n{'='*60}")
    print("[Save] Menyimpan data ke storage")
    print(f"{'='*60}")

    try:
        df_existing = storage.read_structured_sheet(SHEET_NAME)
        if df_existing.empty:
            print("[Save] Sheet kosong — membuat baru...")
            df_merged = df_new
        else:
            print(f"[Save] Data existing : {len(df_existing)} rows.")
            print(f"[Save] Data baru     : {len(df_new)} rows.")
            df_merged = _merge_data(df_existing, df_new)

        storage.write_structured_sheet(SHEET_NAME, df_merged)

        print(f"\n{'='*60}")
        print("[Save] DATA BERHASIL DISIMPAN")
        print(f"{'='*60}")
        print(f"[Save] Sheet: {SHEET_NAME}")

    except Exception as exc:
        print(f"[Save] Error saat menyimpan data: {exc}")
        traceback.print_exc()


# Public Entry Point

def main_ebtke_scraper():
    """
    Run the full EBT capacity scraping workflow:
    fetch latest data, check duplicate, save to storage.
    """
    print(f"\n{'='*60}")
    print("SCRAPER KAPASITAS EBT (EBTKE API)")
    print(f"{'='*60}")
    print(f"\n[Main] Sheet: {SHEET_NAME}")

    df_new = fetch_ebtke_data()
    if df_new is None or df_new.empty:
        print("\n[Main] Tidak ada data yang berhasil diambil.")
        return

    tahun = df_new.iloc[0]["tahun"]
    bulan = df_new.iloc[0]["bulan"]

    if check_data_exists(tahun, bulan):
        print(f"\n[Main] Data tahun {tahun} bulan {bulan} sudah ada — skip upload.")
        return

    save_to_onedrive(df_new)

    print(f"\n{'='*60}")
    print("[Main] SELESAI!")
    print(f"{'='*60}\n")


# Script Entry Point

if __name__ == "__main__":
    main_ebtke_scraper()