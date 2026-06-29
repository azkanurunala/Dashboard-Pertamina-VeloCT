import os
import re
import sys
import time
from datetime import datetime

import pandas as pd
import pdfplumber
import requests
from dotenv import load_dotenv
from tqdm import tqdm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers.storage_backend import storage

load_dotenv()


# Constants

ONEDRIVE_FILE_PATH = os.getenv("ONEDRIVE_DATA_PATH", "/results/(Terstruktur)Data_Scraping_final.xlsx")
SHEET_NAME         = "(Data)Biodesel"

ESDM_API_URL     = "https://ebtke.esdm.go.id/api/api/artikel"
ARTICLE_BASE_URL = "https://ebtke.esdm.go.id/artikel/pengumuman"

MAX_ARTICLES_INIT      = 400
MAX_ARTICLES_PER_MONTH = 10

ARTICLE_KEYWORDS = ["HIP", "BBN", "JENIS", "BIODIESEL", "BULAN"]

# Regex to extract HIP value from HTML article content (fallback)
# Matches patterns like "Rp 14.262/liter" or "sebesar 14.262"
HIP_HTML_RE = re.compile(
    r"(?:Rp\.?\s*|sebesar\s+|HIP[^\d]*)"   # optional prefix
    r"(\d{1,2}[.,]\d{3})"                   # value like 14.262 or 14,262
    r"\s*(?:/\s*[Ll]iter|\/[Ll]|IDR)?",     # optional suffix
    re.IGNORECASE,
)

# Regex to extract Bulan HIP from HTML article content (fallback)
BULAN_HIP_HTML_RE = re.compile(
    r"bulan\s+(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus"
    r"|September|Oktober|November|Desember)\s+(\d{4})\s+sebesar",
    re.IGNORECASE,
)

MONTHS_ID_TO_NUM = {
    "Januari": 1,  "Februari": 2,  "Maret": 3,    "April": 4,
    "Mei": 5,      "Juni": 6,      "Juli": 7,      "Agustus": 8,
    "September": 9,"Oktober": 10,  "November": 11, "Desember": 12,
}
MONTHS_NUM_TO_ID = {v: k for k, v in MONTHS_ID_TO_NUM.items()}


# Date Utilities

def parse_date(date_str):
    """Parse Indonesian date string (e.g. '1 Januari 2026') to YYYY-MM-DD."""
    date_match = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})", date_str)
    if date_match:
        day   = date_match.group(1).zfill(2)
        month = str(MONTHS_ID_TO_NUM.get(date_match.group(2), "")).zfill(2)
        year  = date_match.group(3)
        return f"{year}-{month}-{day}" if month != "00" else None
    return None


# Missing Months Check

def get_missing_months_from_excel(sheet_name=SHEET_NAME):
    """
    Compare the latest Bulan HIP in storage against the current month.

    Returns:
        0    — data is up-to-date
        int  — number of missing months
        None — file/sheet not found or unreadable (treat as fresh start)
    """
    try:
        df = storage.read_structured_sheet(sheet_name)
        if df.empty or "Bulan HIP" not in df.columns:
            print("[Check] Sheet kosong atau kolom 'Bulan HIP' tidak ada, asumsikan scraping awal.")
            return None

        df = df[df["Bulan HIP"].notna()]
        if df.empty:
            print("[Check] Tidak ada data Bulan HIP, asumsikan scraping awal.")
            return None

        def parse_bulan_hip(bulan_str):
            try:
                parts = bulan_str.strip().split()
                if len(parts) >= 2:
                    month = MONTHS_ID_TO_NUM.get(parts[0])
                    year  = int(parts[-1])
                    if month and year:
                        return pd.Timestamp(year=year, month=month, day=1)
            except Exception:
                pass
            return None

        df["parsed_bulan_hip"] = df["Bulan HIP"].apply(parse_bulan_hip)
        df = df[df["parsed_bulan_hip"].notna()]
        if df.empty:
            print("[Check] Tidak bisa parse Bulan HIP, asumsikan scraping awal.")
            return None

        last_date  = df["parsed_bulan_hip"].max()
        now        = datetime.now()
        diff       = (now.year - last_date.year) * 12 + (now.month - last_date.month)
        last_bulan = df.loc[df["parsed_bulan_hip"] == last_date, "Bulan HIP"].iloc[0]

        if diff <= 0:
            print(f"[Check] Data sudah up-to-date (bulan terakhir: {last_bulan}).")
            return 0

        print(f"[Check] Bulan HIP terakhir : {last_bulan}")
        print(f"[Check] Bulan sekarang     : {MONTHS_NUM_TO_ID[now.month]} {now.year}")
        print(f"[Check] Selisih            : {diff} bulan")
        return diff

    except Exception as exc:
        print(f"[Check] Error membaca file: {exc} — asumsikan scraping awal.")
        return None


# Article Scraping

def _matches_criteria(title):
    """Return True if article title contains all required biodiesel keywords."""
    title_upper = title.upper()
    return all(kw in title_upper for kw in ARTICLE_KEYWORDS)

def _extract_pdf_url_from_html(html_content):
    """
    Extract PDF URL from article HTML content.
    Checks Google Drive first, then falls back to ESDM Drive.
    """
    if not html_content:
        return None

    # Priority 1: Google Drive
    match = re.search(
        r'href=["\']([^"\']*drive\.google\.com/file/d/[^"\']*)["\']',
        html_content,
    )
    if match:
        return match.group(1)

    # Fallback: ESDM Drive
    match = re.search(
        r'href=["\']([^"\']*drive\.esdm\.go\.id[^"\']*)["\']',
        html_content,
    )
    return match.group(1) if match else None

def scrape_biodiesel_articles_api(sheet_name=SHEET_NAME):
    """
    Fetch biodiesel HIP articles from ESDM API based on missing months.

    Returns:
        (articles, missing_months) — articles is a deduplicated list of dicts.
    """
    missing_months = get_missing_months_from_excel(sheet_name)

    if missing_months == 0:
        print("[Scrape] Tidak ada artikel baru yang perlu diambil.")
        return [], missing_months
    elif missing_months is None:
        print("[Scrape] File kosong, ambil semua artikel.")
        length = MAX_ARTICLES_INIT
    else:
        length = missing_months * MAX_ARTICLES_PER_MONTH
        print(f"[Scrape] Target: {length} artikel ({missing_months} bulan).")

    api_url = f"{ESDM_API_URL}?kategori_slug=pengumuman&start=0&length={length}&is_published=true"
    print(f"\n[Scrape] Mengambil {length} artikel dari API...")

    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        json_data = response.json()
    except requests.exceptions.RequestException as exc:
        print(f"[Scrape] Error API: {exc}")
        return [], missing_months

    articles_raw = json_data.get("data", [])
    if not articles_raw:
        print("[Scrape] Tidak ada data dari API.")
        return [], missing_months

    print(f"[Scrape] {len(articles_raw)} artikel diterima dari API.")

    data = []
    for article in articles_raw:
        title = article.get("judul", "").strip()
        if not _matches_criteria(title):
            continue
        slug   = article.get("slug", "")
        konten = article.get("konten", "")
        data.append({
            "Judul":   title,
            "url":     f"{ARTICLE_BASE_URL}/{slug}",
            "Date":    article.get("tanggal_publikasi") or article.get("tgl_upload", ""),
            "konten":  konten,
            "pdf_url": _extract_pdf_url_from_html(konten),
        })

    print(f"[Scrape] {len(data)} artikel biodiesel ditemukan.")

    # Deduplikasi
    seen   = set()
    unique = []
    for item in data:
        key = (item["Judul"], item["Date"])
        if key not in seen:
            seen.add(key)
            unique.append(item)

    if len(unique) < len(data):
        print(f"[Scrape] Setelah deduplikasi: {len(unique)} artikel.")

    return unique, missing_months


# PDF Download

def download_pdf(url, filename):
    """
    Download a PDF from Google Drive or ESDM Drive and save to disk.

    Returns True on success, False otherwise.
    """
    try:
        if not url.startswith("http"):
            url = "https://" + url

        # Google Drive: convert share URL to direct download URL
        gdrive_match = re.search(r"/file/d/([^/]+)", url)
        if gdrive_match:
            file_id = gdrive_match.group(1)
            url = f"https://drive.google.com/uc?export=download&id={file_id}"
        elif "drive.esdm.go.id" in url and "download" not in url:
            url = url + ("&mode=list&download=1" if "?" in url else "?download=1")

        response = requests.get(url, stream=True, timeout=30)
        content_type = response.headers.get("content-type", "").lower()

        # Reject HTML responses (e.g. login redirect)
        if "text/html" in content_type:
            print(f"[Download] Response adalah HTML — kemungkinan redirect ke login.")
            return False

        if "application/pdf" not in content_type and "octet-stream" not in content_type:
            return False

        # Verify PDF magic bytes
        content = response.content
        if not content.startswith(b"%PDF"):
            print(f"[Download] File bukan PDF valid (magic bytes salah).")
            return False

        with open(filename, "wb") as f:
            f.write(content)
        return True

    except Exception as exc:
        print(f"[Download] Error: {exc}")
        return False

def scrape_and_download_pdfs(data, missing_months):
    """
    Download PDF files for each article. Filters data based on missing_months.

    Articles without a PDF URL or with a failed download are still returned
    so that the HTML fallback can be attempted during parsing.
    """
    if missing_months == 0:
        print("[Download] Tidak ada artikel baru, semua data sudah lengkap.")
        return []
    elif missing_months is None:
        print("[Download] Scraping awal — ambil semua artikel yang tersedia.")
        filtered_data = data
    else:
        filtered_data = data[:missing_months]
        print(f"[Download] Menargetkan {len(filtered_data)} artikel terbaru (untuk {missing_months} bulan hilang).")

    for item in tqdm(filtered_data, desc="[Download] Mengunduh PDF"):
        pdf_url = item.get("pdf_url")
        if not pdf_url:
            print(f"\n[Download] Tidak ada PDF URL: {item['Judul'][:50]}...")
            item["pdf_filename"] = None
            continue

        filename = f"HIP_BBN_{item['Date']}.pdf".replace(":", "-").replace(" ", "_")
        if download_pdf(pdf_url, filename):
            item["pdf_filename"] = filename
        else:
            print(f"\n[Download] Gagal mengunduh PDF dari {pdf_url}")
            item["pdf_filename"] = None
        time.sleep(0.3)

    return filtered_data


# PDF Parsing

def find_hip_value_and_month_in_table(table):
    """
    Parse a PDF table to extract HIP value (Rupiah/Liter) and Bulan HIP.

    Searches for a row containing '(RUPIAH/LITER)' and reads the next row.
    """
    hip_value = None
    hip_month = None

    for row_idx, row in enumerate(table):
        if not row:
            continue
        for cell in row:
            text = str(cell) if cell else ""
            if "(RUPIAH/LITER)" not in text.upper():
                continue
            if row_idx + 1 >= len(table):
                continue

            next_row = table[row_idx + 1]

            for val in reversed(next_row):
                if val:
                    val_clean = str(val).replace(",", ".").replace(" ", "").strip()
                    match = re.match(r"^(\d+(?:\.\d+)?)$", val_clean)
                    if match:
                        hip_value = float(match.group(1))
                        break

            for val in reversed(next_row):
                if isinstance(val, str) and re.search(
                    r"(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus"
                    r"|September|Oktober|November|Desember)\s+\d{4}",
                    val,
                ):
                    hip_month = val.strip()
                    break

            if hip_value:
                return hip_value, hip_month

    return hip_value, hip_month

def extract_hip_from_pdf(pdf_file):
    """Open a PDF and extract HIP value and month from its tables."""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    hip_value, hip_month = find_hip_value_and_month_in_table(table)
                    if hip_value:
                        return hip_value, hip_month
        return None, None
    except Exception as exc:
        print(f"[Parse] Error parsing {pdf_file}: {exc}")
        return None, None

def extract_hip_from_html_content(konten):
    if not konten:
        return None, None

    # Strip HTML tags dan normalize whitespace sebelum regex
    from bs4 import BeautifulSoup
    plain = BeautifulSoup(konten, "html.parser").get_text(separator=" ")
    plain = re.sub(r"\s+", " ", plain).strip()

    hip_value = None
    hip_month = None

    match_value = HIP_HTML_RE.search(plain)
    if match_value:
        raw = match_value.group(1).replace(".", "").replace(",", "")
        try:
            hip_value = float(raw)
        except ValueError:
            pass

    match_month = BULAN_HIP_HTML_RE.search(plain)
    if match_month:
        month_name = match_month.group(1).capitalize()
        year       = match_month.group(2)
        hip_month  = f"{month_name} {year}"

    return hip_value, hip_month

def parse_all_pdfs(all_articles):
    """
    Extract HIP data from each article.

    Tries PDF first; falls back to HTML content if PDF is unavailable or fails.
    Deletes each PDF after successful extraction.
    Returns a list of dicts with Date, Bulan HIP, and HIP Biodiesel IDR/L.
    """
    excel_data = []

    for item in all_articles:
        title     = item.get("Judul", "")[:60]
        pdf_file  = item.get("pdf_filename")
        konten    = item.get("konten", "")
        date_raw  = str(item.get("Date", "") or "").strip()

        # Normalize date — drop time component if present
        date_clean = date_raw.split(" ")[0].split("T")[0]

        print(f"\n[Parse] {title}")

        hip_value  = None
        hip_month  = None
        hip_source = None

        # --- Attempt 1: PDF ---
        if pdf_file and os.path.exists(pdf_file):
            hip_value, hip_month = extract_hip_from_pdf(pdf_file)
            if hip_value:
                hip_source = "PDF"
                # PDF values are per-liter floats (e.g. 14.262), multiply × 1000
                hip_value = int(hip_value * 1000)
                print(f"[Parse] Sumber              : PDF")
                try:
                    os.remove(pdf_file)
                    print(f"[Parse] PDF dihapus         : {pdf_file}")
                except Exception as exc:
                    print(f"[Parse] Gagal menghapus PDF : {exc}")
            else:
                print(f"[Parse] PDF gagal di-parse — fallback ke konten HTML.")
        else:
            print(f"[Parse] PDF tidak tersedia — fallback ke konten HTML.")

        # --- Attempt 2: HTML fallback ---
        if hip_value is None:
            hip_value, hip_month = extract_hip_from_html_content(konten)
            if hip_value:
                hip_source = "HTML"
                # HTML values are already full IDR/L integers (e.g. 14262)
                hip_value = int(hip_value)
                print(f"[Parse] Sumber              : HTML")

        if hip_value:
            print(f"[Parse] HIP Biodiesel IDR/L : {hip_value}  [{hip_source}]")
            print(f"[Parse] Bulan HIP           : {hip_month}")
            print(f"[Parse] Date                : {date_clean}")

            excel_data.append({
                "Date":                date_clean,
                "Bulan HIP":          hip_month,
                "HIP Biodiesel IDR/L": hip_value,
            })
        else:
            print(f"[Parse] Gagal mengekstrak data dari artikel ini.")

    return excel_data


# Save to Storage

def save_to_excel(data, sheet_name=SHEET_NAME):
    """
    Merge new HIP data with existing storage sheet, deduplicate, sort, and write.

    Returns the combined DataFrame on success, None on failure.
    """
    if not data:
        print("[Save] Tidak ada data baru untuk disimpan.")
        return None

    print(f"\n{'='*60}")
    print("[Save] Menyimpan data ke storage")
    print(f"{'='*60}")

    new_df = pd.DataFrame(data)
    new_df["Date"] = pd.to_datetime(new_df["Date"], errors="coerce")
    print(f"[Save] Data baru: {len(new_df)} baris.")

    # Load existing data
    try:
        existing_df = storage.read_structured_sheet(sheet_name)
        if existing_df.empty:
            print("[Save] Sheet kosong, akan membuat baru.")
            combined_df = new_df
        else:
            existing_df["Date"] = pd.to_datetime(existing_df["Date"], errors="coerce")
            print(f"[Save] Data lama: {len(existing_df)} baris.")
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    except Exception as exc:
        print(f"[Save] Error membaca sheet existing: {exc}")
        combined_df = new_df

    # Deduplikasi dan sorting
    combined_df = combined_df.drop_duplicates(subset=["Bulan HIP"], keep="last")
    combined_df = combined_df.sort_values(by="Date", ascending=True)
    combined_df["Date"] = combined_df["Date"].dt.strftime("%Y-%m-%d")
    print(f"[Save] Data setelah deduplikasi: {len(combined_df)} baris.")

    try:
        storage.write_structured_sheet(sheet_name, combined_df)

        print(f"\n{'='*60}")
        print("[Save] DATA BERHASIL DISIMPAN")
        print(f"{'='*60}")
        print(f"[Save] Sheet     : {sheet_name}")
        print(f"[Save] Total rows: {len(combined_df)}")
        print(f"[Save] Data baru : {len(new_df)} baris")

        return combined_df

    except Exception as exc:
        print(f"[Save] Error saat menyimpan: {exc}")
        import traceback
        traceback.print_exc()
        return None


# Public Entry Point

def main_biodiesel_esdm():
    """
    Run the full Biodiesel HIP scraping workflow:
    fetch articles, download PDFs (with HTML fallback), save to storage.
    """
    print(f"\n{'='*60}")
    print("SCRAPER HIP BBN BIODIESEL (API VERSION)")
    print(f"{'='*60}")
    print(f"\n[Main] Sheet: {SHEET_NAME}")

    data, missing_months = scrape_biodiesel_articles_api(SHEET_NAME)
    if not data:
        print("\n[Main] Tidak ada data untuk diproses.")
        return

    print(f"\n[Main] Total artikel biodiesel: {len(data)}")

    all_articles = scrape_and_download_pdfs(data, missing_months)
    if not all_articles:
        print("\n[Main] Tidak ada artikel untuk diproses.")
        return

    excel_data = parse_all_pdfs(all_articles)
    if not excel_data:
        print("\n[Main] Tidak ada data HIP yang berhasil di-extract.")
        return

    df = save_to_excel(excel_data, SHEET_NAME)

    print(f"\n{'='*60}")
    if df is not None:
        print("[Main] SELESAI!")
    else:
        print("[Main] Gagal menyimpan data.")
    print(f"{'='*60}\n")


# Script Entry Point

if __name__ == "__main__":
    main_biodiesel_esdm()