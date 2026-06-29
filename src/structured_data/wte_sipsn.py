import os
import sys
import traceback
from datetime import datetime

import pandas as pd
import requests
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers.storage_backend import storage

load_dotenv()


# Constants

ONEDRIVE_FILE_PATH = os.getenv("ONEDRIVE_DATA_PATH", "/results/(Terstruktur)Data_Scraping_final.xlsx")

# REVISI 1: URL lama (sipsn.kemenlh.go.id) mati sejak Oktober 2024 akibat
# pemecahan KLHK via Perpres 139/2024. Ganti ke mirror legacy yang masih aktif.
API_URL = "https://sampahnasional.kemenlh.go.id/indikatif/public/home/ajax_list"

SHEET_MAPPING = {
    "sumber":    "(Data)WTE_Sumber",
    "komposisi": "(Data)WTE_Komposisi",
    "timbulan":  "(Data)WTE_Timbulan",
}

COLUMN_RENAME = {
    "nama_dati2":     "Nama Kota/Kabupaten",
    "nama_propinsi":  "Nama Provinsi",
}

DEDUP_ID_COLS = ["tahun", "Nama Provinsi", "Nama Kota/Kabupaten"]

# REVISI 2: Tambah headers agar request tidak diblok (domain baru lebih ketat)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://sampahnasional.kemenlh.go.id/indikatif",
}


# Duplicate Check

def _year_exists_in_storage(tahun: str) -> dict[str, bool]:
    """
    Check whether data for the given year already exists in each WTE sheet in storage.

    Returns a dict {jenis: bool} for 'sumber', 'komposisi', 'timbulan'.
    """
    result = {}
    for jenis, sheet_name in SHEET_MAPPING.items():
        try:
            df = storage.read_structured_sheet(sheet_name)
            found = not df.empty and str(tahun) in df["tahun"].astype(str).values
            result[jenis] = found
            print(f"[Check] [{jenis}] Data tahun {tahun}: {'Sudah ada' if found else 'Belum ada'}.")
        except Exception:
            result[jenis] = False
    return result


# Data Fetching

def fetch_all_data(tahun: str = "2025") -> dict[str, pd.DataFrame]:
    """
    Fetch WTE data for all three jenis (sumber, komposisi, timbulan) from SIPSN API.

    Returns a dict {jenis: DataFrame}.
    """
    all_data = {}

    # REVISI 3: Gunakan session agar cookie XSRF-TOKEN dari homepage
    # otomatis tersimpan dan disertakan di setiap POST berikutnya.
    # Tanpa ini, domain baru mengembalikan 403 Forbidden.
    session = requests.Session()
    try:
        session.get(
            "https://sampahnasional.kemenlh.go.id/indikatif",
            headers={k: v for k, v in HEADERS.items()
                     if k not in ["Content-Type", "X-Requested-With"]},
            timeout=15,
        )
    except Exception as exc:
        print(f"[Fetch] Peringatan: gagal ambil homepage untuk cookie — {exc}")

    for jenis in SHEET_MAPPING:
        print(f"[Fetch] Mengambil data {jenis} tahun {tahun}...")
        try:
            response = session.post(          # pakai session, bukan requests.post
                API_URL,
                data={"length": "-1", "jenis": jenis, "tahun": tahun},
                headers=HEADERS,
                timeout=30,
            )
            if response.status_code == 200:
                df = pd.DataFrame(response.json()["data"])
                df = df.rename(columns=COLUMN_RENAME)
                all_data[jenis] = df
                print(f"[Fetch] {jenis}: {len(df)} records.")
            else:
                print(f"[Fetch] Gagal ambil data {jenis}: status {response.status_code}.")
        except Exception as exc:
            print(f"[Fetch] Error {jenis}: {exc}")

    return all_data


# Data Merge — tidak ada perubahan

def _merge_data_by_year(df_existing: pd.DataFrame, df_new: pd.DataFrame) -> pd.DataFrame:
    """
    Concatenate existing and new DataFrames, deduplicate by tahun+location, and sort by tahun.
    """
    df_combined = pd.concat([df_existing, df_new], ignore_index=True)

    id_cols = [c for c in DEDUP_ID_COLS if c in df_combined.columns]
    if id_cols:
        df_combined = df_combined.drop_duplicates(subset=id_cols, keep="last")

    if "tahun" in df_combined.columns:
        df_combined["tahun"] = pd.to_numeric(df_combined["tahun"], errors="coerce")
        df_combined = df_combined.sort_values("tahun", ascending=True)

    print(f"[Merge] Data setelah merge: {len(df_combined)} rows.")
    return df_combined


# Save to Storage

def save_to_storage(data_dict: dict[str, pd.DataFrame], tahun: str) -> None:
    """
    Merge new WTE data with existing storage sheets, deduplicate, and write.
    """
    if not data_dict or all(df.empty for df in data_dict.values()):
        print("[Save] Tidak ada data untuk disimpan.")
        return

    print(f"\n{'='*60}")
    print(f"[Save] Menyimpan data tahun {tahun} ke storage...")
    print(f"{'='*60}")

    try:
        for jenis, df_new in data_dict.items():
            sheet_name = SHEET_MAPPING[jenis]
            print(f"\n[Save] Sheet: {sheet_name}")

            existing = storage.read_structured_sheet(sheet_name)
            if not existing.empty:
                print(f"[Save]   Data existing         : {len(existing)} rows.")
                print(f"[Save]   Data baru (tahun {tahun}): {len(df_new)} rows.")
                df_merged = _merge_data_by_year(existing, df_new)
            else:
                df_merged = df_new
                print(f"[Save]   Sheet kosong — akan membuat baru.")

            storage.write_structured_sheet(sheet_name, df_merged)
            print(f"[Save]   Saved: {len(df_merged)} rows.")

        print(f"\n{'='*60}")
        print("[Save] DATA BERHASIL DISIMPAN")
        print(f"{'='*60}")

    except Exception as exc:
        print(f"[Save] Error saat menyimpan: {exc}")
        traceback.print_exc()


# Public Entry Point

def main_sipsn_scraper() -> None:
    print(f"\n{'='*60}")
    print("SCRAPER SIPSN WTE")
    print(f"{'='*60}")

    tahun_sekarang = datetime.now().year
    tahun_awal     = 2015

    print(f"\n[Main] Scraping tahun {tahun_awal} s.d. {tahun_sekarang}...")

    for tahun in range(tahun_awal, tahun_sekarang + 1):
        tahun_str = str(tahun)
        print(f"\n{'='*60}")
        print(f"[Main] Memproses tahun {tahun_str}...")
        print(f"{'='*60}")

        data_status = _year_exists_in_storage(tahun_str)

        if all(data_status.values()):
            print(f"[Main] Semua data tahun {tahun_str} sudah ada — skip.")
            continue

        missing = [jenis for jenis, exists in data_status.items() if not exists]
        print(f"[Main] Data yang belum ada: {', '.join(missing)}")

        data_dict = fetch_all_data(tahun=tahun_str)

        if not data_dict:
            print(f"[Main] Tidak ada data untuk tahun {tahun_str} — kemungkinan belum tersedia, skip.")
            continue

        save_to_storage(data_dict, tahun_str)

    print(f"\n{'='*60}")
    print("[Main] SELESAI!")
    print(f"{'='*60}\n")


# Script Entry Point

if __name__ == "__main__":
    main_sipsn_scraper()