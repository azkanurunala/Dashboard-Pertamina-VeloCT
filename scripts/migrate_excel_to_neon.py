"""
One-time migration: read all sheets from OneDrive Excel files and upsert into Neon PostgreSQL.

Prerequisites:
  1. Set up Neon DB and run scripts/create_tables.sql
  2. Set NEON_DB_URL in .env
  3. Set MS_CLIENT_* in .env (OneDrive credentials)
  4. Run: python scripts/migrate_excel_to_neon.py

Tables migrated:
  news_articles, news_sentiment,
  data_biodiesel, data_bioetanol, data_harga_minyak, data_eia, data_cpo, data_saf,
  data_kapasitas_ebt, data_crackspread_bbm, data_crackspread_non_bbm,
  data_crackspread_bbm_year, data_iaea_country_stats,
  data_iaea_nuclear_capacity, data_iaea_electrical

WTE tables (data_wte_*): dynamic columns — run wte_sipsn.py with STORAGE_BACKEND=neon instead.
"""

import os
import sys

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from helpers.onedrive_helper import download_excel_from_onedrive, get_access_token
from helpers import neon_helper
from helpers.storage_backend import (
    SHEET_TO_TABLE,
    SHEET_CONFLICT_COLS,
    _IAEA_VALUE_COL,
    _melt_iaea,
)

NEWS_FILE_PATH      = os.getenv("ONEDRIVE_FILE_PATH",      "/results/(News)Scrapping.xlsx")
SENTIMENT_FILE_PATH = os.getenv("ONEDRIVE_SENTIMENT_PATH", "/results/(News)Sentiment.xlsx")
DATA_FILE_PATH      = os.getenv("ONEDRIVE_DATA_PATH",      "/results/(Terstruktur)Data Scrapping.xlsx")

SENTIMENT_SHEET_COLS = ["Tanggal awal", "Tanggal akhir", "Summary", "Summary Data"]

WTE_SHEETS = {"(Data)WTE_Sumber", "(Data)WTE_Komposisi", "(Data)WTE_Timbulan"}


def _migrate_workbook(token, file_path: str, table_name: str, conflict_cols: list[str],
                      topic_col: str | None, sheet_names: list[str]) -> None:
    buf = download_excel_from_onedrive(token, file_path)
    if buf is None:
        print(f"  [SKIP] File not found: {file_path}")
        return
    xf = pd.ExcelFile(buf)
    total = 0
    for sheet in sheet_names:
        if sheet not in xf.sheet_names:
            print(f"  [SKIP] Sheet not found: {sheet}")
            continue
        df = pd.read_excel(xf, sheet_name=sheet)
        if df.empty:
            print(f"  [SKIP] Empty: {sheet}")
            continue
        if topic_col:
            df[topic_col] = sheet
        n = neon_helper.upsert_df(table_name, df, conflict_cols)
        print(f"  {sheet}: {n} rows → {table_name}")
        total += n
    xf.close()
    print(f"  Total: {total} rows")


def _migrate_structured_sheet(token, sheet_name: str) -> None:
    if sheet_name in WTE_SHEETS:
        print(f"  [SKIP] WTE sheets migrated by running wte_sipsn.py with STORAGE_BACKEND=neon")
        return
    buf = download_excel_from_onedrive(token, DATA_FILE_PATH)
    if buf is None:
        print("  [SKIP] Structured data file not found on OneDrive.")
        return
    xf = pd.ExcelFile(buf)
    if sheet_name not in xf.sheet_names:
        print(f"  [SKIP] Sheet not in workbook: {sheet_name}")
        xf.close()
        return
    df = pd.read_excel(xf, sheet_name=sheet_name)
    xf.close()
    if df.empty:
        print(f"  [SKIP] Empty: {sheet_name}")
        return
    table    = SHEET_TO_TABLE[sheet_name]
    conflict = SHEET_CONFLICT_COLS[sheet_name]
    if sheet_name in _IAEA_VALUE_COL:
        df = _melt_iaea(df, sheet_name)
    n = neon_helper.upsert_df(table, df, conflict)
    print(f"  {sheet_name} → {table}: {n} rows")


def main():
    print("=" * 60)
    print("ONE-TIME MIGRATION: OneDrive Excel → Neon PostgreSQL")
    print("=" * 60)

    token = get_access_token()
    print("[Auth] OneDrive token acquired.\n")

    # ── 1. News Articles ──────────────────────────────────────────────────────
    print("[1/3] Migrating news_articles...")
    from helpers.storage_backend import _NEWS_FILE_PATH
    all_news_sheets = [
        "(News)Indeks Risiko Geopolitik", "(News)Indeks Volatilitas", "(News)Kurs",
        "(News)IHSG", "(News)Inflasi", "(News)BI Rate", "(News)Indonia",
        "(News)Indeks Penjualan Ritel", "(News)Indeks Kepercayaan Knsmn",
        "(News)Indeks Kinerja Manufaktur", "(News)Indeks Kinerja Jasa",
        "(News)Neraca Perdagangan", "(News)PDB", "(News)Harga Minyak",
        "(News)Volume Minyak", "(News)Harga Produk Kilang", "(News)Volume Produk Kilang",
        "(News)Crackspread BBM", "(News)Biodiesel", "(News)SAF", "(News)Bioetanol",
        "(News)RUPTL", "(News)EBT", "(News)WTE", "(News)Nuklir",
    ]
    _migrate_workbook(token, NEWS_FILE_PATH, "news_articles", ["url", "topic"],
                      topic_col="topic", sheet_names=all_news_sheets)
    print()

    # ── 2. News Sentiment ─────────────────────────────────────────────────────
    print("[2/3] Migrating news_sentiment...")
    all_sentiment_sheets = [
        "(Summary)Nilai Tukar Rupiah", "(Summary)IHSG", "(Summary)Indonia",
        "(Summary)Idx Volatilitas", "(Summary)Idx Risiko Geopolitik", "(Summary)Inflasi",
        "(Summary)BI-Rate", "(Summary)Idx Penjualan Ritel", "(Summary)Idx Kepercayaan Konsumen",
        "(Summary)Idx PMI", "(Summary)Neraca Perdagangan", "(Summary)PDB",
        "(Summary)Harga Minyak", "(Summary)Volume Minyak", "(Summary)Harga Produk Kilang",
        "(Summary)Volume Produk Kilang", "(Summary)Biodiesel", "(Summary)Bioetanol",
        "(Summary)SAF", "(Summary)RUPTL", "(Summary)Harga EBT", "(Summary)Kapasitas EBT",
        "(Summary)WTE", "(Summary)Nuklir", "(Summary)Crackspread BBM",
        "(Summary)Crackspread_NonBBM",
    ]
    _migrate_workbook(token, SENTIMENT_FILE_PATH, "news_sentiment",
                      ["topic", "Tanggal awal"], topic_col="topic",
                      sheet_names=all_sentiment_sheets)
    print()

    # ── 3. Structured Data ────────────────────────────────────────────────────
    print("[3/3] Migrating structured data sheets...")
    structured_sheets = [
        "(Data)Biodesel", "(Data)Bioetanol", "(Data)Harga Minyak", "(Data)eia",
        "(Data)CPO", "(Data)SAF", "(Data)Kapasitas_EBT",
        "(Data)IAEA_Nuclear_Capacity", "(Data)IAEA_Electrical", "(Data)IAEA_Country_Stats",
        "(Data)Crackspread_BBM", "(Data)Crackspread_NON_BBM", "(Data)Crackspread_BBM_YEAR",
        # WTE: skip (dynamic columns — run wte_sipsn.py with STORAGE_BACKEND=neon)
    ]
    for sheet in structured_sheets:
        _migrate_structured_sheet(token, sheet)

    print()
    print("=" * 60)
    print("MIGRATION COMPLETE")
    print("For WTE data: run wte_sipsn.py once with STORAGE_BACKEND=neon")
    print("=" * 60)


if __name__ == "__main__":
    main()
