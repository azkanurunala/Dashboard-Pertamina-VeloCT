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
import tempfile

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from helpers.onedrive_helper import get_access_token

USER_EMAIL     = os.getenv("MS_USER_EMAIL", "")
GRAPH_DRIVE_URL = f"https://graph.microsoft.com/v1.0/users/{USER_EMAIL}/drive/root"


def _download_to_tempfile(token: str, file_path: str) -> str | None:
    """Stream OneDrive file to a local temp file. Returns temp path or None if 404."""
    url     = f"{GRAPH_DRIVE_URL}:{file_path}:/content"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers, stream=True)
    if r.status_code == 404:
        print(f"  [SKIP] Not found: {file_path}")
        return None
    if r.status_code != 200:
        raise Exception(f"[Download] Failed ({r.status_code}): {r.text[:200]}")
    suffix = os.path.splitext(file_path)[1] or ".xlsx"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        for chunk in r.iter_content(chunk_size=1 << 20):  # 1 MB chunks
            f.write(chunk)
    print(f"  [Download] {file_path} -> {tmp_path}")
    return tmp_path


def download_excel_from_onedrive(token: str, file_path: str):
    """Compatibility shim: stream to disk, return path (not BytesIO)."""
    return _download_to_tempfile(token, file_path)


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


NEWS_COLS      = ["title", "date", "url", "content", "source", "keyword", "topic"]
SENTIMENT_COLS = ["Tanggal awal", "Tanggal akhir", "Summary", "Summary Data", "topic"]

def _migrate_workbook(token, file_path: str, table_name: str, conflict_cols: list[str],
                      topic_col: str | None, sheet_names: list[str],
                      keep_cols: list[str] | None = None) -> None:
    tmp = download_excel_from_onedrive(token, file_path)
    if tmp is None:
        return
    try:
        xf = pd.ExcelFile(tmp)
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
            if keep_cols:
                present = [c for c in keep_cols if c in df.columns]
                df = df[present]
            n = neon_helper.upsert_df(table_name, df, conflict_cols)
            print(f"  {sheet}: {n} rows ->{table_name}")
            total += n
        xf.close()
        print(f"  Total: {total} rows")
    finally:
        os.unlink(tmp)


# Cache the structured data workbook path so we only download it once
_STRUCTURED_TMP: str | None = None

def _get_structured_tmp(token) -> str | None:
    global _STRUCTURED_TMP
    if _STRUCTURED_TMP and os.path.exists(_STRUCTURED_TMP):
        return _STRUCTURED_TMP
    _STRUCTURED_TMP = download_excel_from_onedrive(token, DATA_FILE_PATH)
    return _STRUCTURED_TMP


def _migrate_structured_sheet(token, sheet_name: str) -> None:
    if sheet_name in WTE_SHEETS:
        print(f"  [SKIP] WTE — run wte_sipsn.py with STORAGE_BACKEND=neon instead")
        return
    tmp = _get_structured_tmp(token)
    if tmp is None:
        print("  [SKIP] Structured data file not found on OneDrive.")
        return
    xf = pd.ExcelFile(tmp)
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
    neon_helper.create_table_if_needed(table, df, conflict)
    n = neon_helper.upsert_df(table, df, conflict)
    print(f"  {sheet_name} -> {table}: {n} rows")


def main():
    print("=" * 60)
    print("ONE-TIME MIGRATION: OneDrive Excel -> Neon PostgreSQL")
    print("=" * 60)

    token = get_access_token()
    print("[Auth] OneDrive token acquired.\n")

    # ── 1. News Articles ──────────────────────────────────────────────────────
    print("[1/3] Migrating news_articles...")
    all_news_sheets = [
        "(News)Indeks Risiko Geopolitik", "(News)Indeks Volatilitas", "(News)Kurs",
        "(News)IHSG", "(News)Inflasi", "(News)BI Rate", "(News)Indonia",
        "(News)Indeks Penjualan Ritel", "(News)Indeks Kepercayaan Knsmn",
        "(News)Indeks Kinerja Manufaktur", "(News)Indeks Kinerja Jasa",
        "(News)Neraca Perdagangan", "(News)PDB", "(News)Harga Minyak",
        "(News)Volume Minyak", "(News)Harga Produk Kilang", "(News)Volume Produk Kilang",
        "(News)Crackspread BBM", "(News)Crackspread Non-BBM",
        "(News)Biodiesel", "(News)SAF", "(News)Bioetanol",
        "(News)RUPTL", "(News)EBT", "(News)WTE", "(News)Nuklir",
    ]
    _migrate_workbook(token, NEWS_FILE_PATH, "news_articles", ["url", "topic"],
                      topic_col="topic", sheet_names=all_news_sheets,
                      keep_cols=NEWS_COLS)
    print()

    # ── 2. News Sentiment ─────────────────────────────────────────────────────
    print("[2/3] Migrating news_sentiment...")
    all_sentiment_sheets = [
        "(Summary)Nilai Tukar Rupiah", "(Summary)IHSG", "(Summary)Indonia",
        "(Summary)Idx Volatilitas", "(Summary)Idx Risiko Geopolitik", "(Summary)Inflasi",
        "(Summary)BI-Rate", "(Summary)Idx Penjualan Ritel", "(Summary)Idx Kepercayaan Konsum",
        "(Summary)Idx PMI", "(Summary)Neraca Perdagangan", "(Summary)PDB",
        "(Summary)Harga Minyak", "(Summary)Volume Minyak", "(Summary)Harga Produk Kilang",
        "(Summary)Volume Produk Kilang", "(Summary)Biodiesel", "(Summary)Bioetanol",
        "(Summary)SAF", "(Summary)RUPTL", "(Summary)Harga EBT", "(Summary)Kapasitas EBT",
        "(Summary)WTE", "(Summary)Nuklir", "(Summary)Crackspread BBM",
    ]
    _migrate_workbook(token, SENTIMENT_FILE_PATH, "news_sentiment",
                      ["topic", "Tanggal awal"], topic_col="topic",
                      sheet_names=all_sentiment_sheets,
                      keep_cols=SENTIMENT_COLS)
    print()

    # ── 3. Structured Data ────────────────────────────────────────────────────
    print("[3/3] Migrating structured data sheets...")
    structured_sheets = [
        "(Data)Biodesel", "(Data)Bioetanol", "(Data)Harga Minyak",
        "(Data)CPO", "(Data)SAF", "(Data)Kapasitas_EBT",
        "(Data)EIA",
        "(Data)IAEA_Nuclear_Capacity", "(Data)IAEA_Electrical", "(Data)IAEA_Country_Stats",
        "(Data)Crackspread_BBM", "(Data)Crackspread_NON_BBM", "(Data)Crackspread_BBM_YEAR",
        # WTE: skip (dynamic columns — run wte_sipsn.py with STORAGE_BACKEND=neon)
    ]
    for sheet in structured_sheets:
        _migrate_structured_sheet(token, sheet)

    # cleanup cached structured data temp file
    if _STRUCTURED_TMP and os.path.exists(_STRUCTURED_TMP):
        os.unlink(_STRUCTURED_TMP)

    print()
    print("=" * 60)
    print("MIGRATION COMPLETE")
    print("For WTE data: run wte_sipsn.py once with STORAGE_BACKEND=neon")
    print("=" * 60)


if __name__ == "__main__":
    main()
