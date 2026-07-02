import io
import os
import re
import sys
import time
import traceback
from collections import Counter
from datetime import datetime

import easyocr
import fitz
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from PIL import Image

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers.storage_backend import storage

load_dotenv()


# Constants

ONEDRIVE_FILE_PATH = os.getenv("ONEDRIVE_DATA_PATH", "/results/(Terstruktur)Data_Scraping_final.xlsx")
SHEET_NAME         = "(Data)Harga Minyak"

MIGAS_URL  = "https://www.migas.esdm.go.id/post/read/harga-minyak-mentah"
PDF_FOLDER = "../results/hasil-migas-esdm-pdf"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    )
}
REQUEST_TIMEOUT = 30

MONTHS_ID_TO_NUM = {
    "januari": 1,  "februari": 2,  "maret": 3,    "april": 4,
    "mei": 5,      "juni": 6,      "juli": 7,      "agustus": 8,
    "september": 9,"oktober": 10,  "november": 11, "desember": 12,
}
MONTHS_NUM_TO_ID = {v: k.capitalize() for k, v in MONTHS_ID_TO_NUM.items()}

_MONTH_PATTERN = (
    r"(?:Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus"
    r"|September|Oktober|November|Desember)"
)

# Fuzzy month pattern — tolerates internal spaces between letters produced by OCR
# on documents using spaced/monospace fonts (e.g. "Ap r i l", "A p r i 1").
# Also handles '1' misread as 'l' in April.
_MONTH_PATTERN_FUZZY = (
    r"(?:"
    r"J\s*a\s*n\s*u\s*a\s*r\s*i"
    r"|F\s*e\s*b\s*r\s*u\s*a\s*r\s*i"
    r"|M\s*a\s*r\s*e\s*t"
    r"|A\s*p\s*r\s*i\s*[l1]"
    r"|M\s*e\s*i"
    r"|J\s*u\s*n\s*i"
    r"|J\s*u\s*l\s*i"
    r"|A\s*g\s*u\s*s\s*t\s*u\s*s"
    r"|S\s*e\s*p\s*t\s*e\s*m\s*b\s*e\s*r"
    r"|O\s*k\s*t\s*o\s*b\s*e\s*r"
    r"|N\s*o\s*v\s*e\s*m\s*b\s*e\s*r"
    r"|D\s*e\s*s\s*e\s*m\s*b\s*e\s*r"
    r")"
)

# Pre-compiled patterns reused across pages
_PAT_KEYWORD   = re.compile(r"harga\s+rata[\s-]+rata\s+minyak\s+mentah", re.IGNORECASE)
# OCR sometimes inserts a space between "US" and "$", or misreads "$" as "S"/"8"
_PAT_PRICE     = re.compile(r"US\s*[\$S8]\s*([\d.,]+)")
_PAT_BRENT_SLC = re.compile(r"(?:S\s*L\s*C|SLC)\s+([\d.,]+)", re.IGNORECASE)

# Date patterns for OCR mode.
# Problem: "tanggal" appears in Mengingat references AND in the signing block.
#   Mengingat: "Nomor 138 K/12/MEM/2019 tanggal 30 Juli 2019 tentang Formula..."
#   Signing:   "Ditetapkan di Jakarta\npada tanggal 2 Januari 2020"
#
# Key invariant: signing date ALWAYS has "pada tanggal"; Mengingat refs use bare "tanggal".
# Additional complication: EasyOCR commonly misreads "Jakarta" as "Jakaria"/"Jakrta"/etc.
# Fix: use \w+ instead of literal "Jakarta" in the Ditetapkan anchor patterns.
#
# Patterns are ordered best->worst. The quality-tracking logic in _extract_from_scanned_pdf
# allows a better pattern on a later page to OVERWRITE a worse one set earlier.
_DATE_PATTERNS_OCR = [
    # pat[0]: Full anchor — "Ditetapkan di <city> pada tanggal DD Month YYYY"
    (rf"Ditetapkan\s+di\s*\w+.*?pada\s+tanggal\s+(\d{{1,2}})\s+({_MONTH_PATTERN_FUZZY})\s+(\d{{4}})",
     re.IGNORECASE | re.DOTALL),
    # pat[1]: Signer-name anchor — "Ditetapkan di … DD Month YYYY … ttd/name"
    (rf"Ditetapkan\s+di\s*\w+.*?(\d{{1,2}})\s+({_MONTH_PATTERN_FUZZY})\s+(\d{{4}})"
     rf".*?(?:MENTERI[\s]+ENERGI|DIREKTUR[\s]+JENDERAL|BAHLIL|ARIFIN|IGNASIUS|TUTUKA|ttd)",
     re.IGNORECASE | re.DOTALL),
    # pat[2]: Lampiran header — "NOMOR … TANGGAL [:] DD Month YYYY"
    #         CRITICAL: NO re.IGNORECASE here — must match uppercase NOMOR/TANGGAL only.
    #         With IGNORECASE, "Nomor 35.K/… tanggal 21 Januari 2026 tentang" (Mengingat)
    #         would also match because lowercase "tanggal" becomes equivalent to TANGGAL.
    (rf"NOMOR\s*:?\s*[\w.\s/]+\s+TANGGAL\s*:?\s*(\d{{1,2}})\s+({_MONTH_PATTERN_FUZZY})\s+(\d{{4}})",
     re.DOTALL),   # ← DOTALL only, NO IGNORECASE
    # pat[3]: Lampiran header with colon — "TANGGAL : DD Month YYYY"
    (rf"TANGGAL\s*:\s*(\d{{1,2}})\s+({_MONTH_PATTERN_FUZZY})\s+(\d{{4}})",
     re.IGNORECASE | re.DOTALL),
    # pat[4]: BSrE footer "DD Month YYYY\nDitandatangani"
    (rf"(\d{{1,2}})\s+({_MONTH_PATTERN_FUZZY})\s+(\d{{4}})\s*\nDitandatangani",
     re.IGNORECASE | re.DOTALL),
    # pat[5]: BSrE footer variant 2 "<SK>\nDD Month YYYY\n"
    (rf"[\w./]+/\d{{4}}\n(\d{{1,2}})\s+({_MONTH_PATTERN_FUZZY})\s+(\d{{4}})\n",
     re.IGNORECASE | re.DOTALL),
    # pat[6]: "pada tanggal DD Month YYYY" NOT followed by "tentang"
    (rf"pada\s+tanggal\s+(\d{{1,2}})\s+({_MONTH_PATTERN_FUZZY})\s+(\d{{4}})(?!.{{0,60}}tentang)",
     re.IGNORECASE | re.DOTALL),
    # pat[7]: Bare date NOT followed by "tentang" (last resort)
    (rf"(\d{{1,2}})\s+({_MONTH_PATTERN_FUZZY})\s+(\d{{4}})(?!.{{0,60}}tentang)",
     re.IGNORECASE | re.DOTALL),
]
_DATE_PATTERN_RELIABLE_THRESHOLD = 6  # pats 0-6 anchored; pat 7 bare

# Lazy EasyOCR loader (initialised only when actually needed)
_ocr_reader = None


# Date Utilities

def _normalize_month(raw: str) -> str:
    """Remove OCR-inserted spaces and fix '1'->'l' in month names."""
    return re.sub(r"\s+", "", raw).replace("1", "l").capitalize()


def _month_diff(bulan_icp: str, bulan_tanggal: str) -> int | None:
    """Return how many months bulan_tanggal is AFTER bulan_icp (0=same, 1=next, etc.), mod 12."""
    n_icp = MONTHS_ID_TO_NUM.get(bulan_icp.lower())
    n_tgl = MONTHS_ID_TO_NUM.get(bulan_tanggal.lower())
    if not n_icp or not n_tgl:
        return None
    return (n_tgl - n_icp) % 12


def _tanggal_in_range(tanggal: str, bulan_icp: str, max_ahead: int = 2) -> bool:
    """
    Return True if the month in tanggal is 1..max_ahead months after bulan_icp.
    Rejects: same month (diff=0), too far ahead (diff>max_ahead), or negative.

    max_ahead=2 covers all known cases:
      - Normal: diff=1 (ICP Jan -> signed Feb, etc.)
      - November -> Januari: diff=2 (cross-year, still valid)
    Anything further (e.g. "30 Juli" for ICP Oktober = diff 9) is an OCR false capture.

    Returns True if bulan_icp is None/unknown (can't check, don't reject).
    """
    if not tanggal or not bulan_icp:
        return True
    for nama_bln in MONTHS_ID_TO_NUM:
        if nama_bln in tanggal.lower():
            diff = _month_diff(bulan_icp, nama_bln)
            if diff is None:
                return True
            return 1 <= diff <= max_ahead
    return True  # no month name in tanggal — can't check


# Last Entry Check

def read_last_entry_from_excel():
    """Return (last_year, last_month_num) of the newest row in the sheet."""
    try:
        df = storage.read_structured_sheet(SHEET_NAME)

        if df.empty or "Bulan" not in df.columns or "Tahun" not in df.columns:
            print("[Check] Sheet kosong atau format salah — semua PDF akan diunduh.")
            return None, None

        df["Bulan"]       = df["Bulan"].astype(str).str.lower()
        df["Bulan_Angka"] = df["Bulan"].map(MONTHS_ID_TO_NUM)
        df = df.dropna(subset=["Bulan_Angka"])

        if df.empty:
            return None, None

        last_row = df.sort_values(["Tahun", "Bulan_Angka"]).iloc[-1]
        print(f"[Check] Data terakhir: {last_row['Bulan'].capitalize()} {int(last_row['Tahun'])}")
        return int(last_row["Tahun"]), int(last_row["Bulan_Angka"])

    except ValueError:
        print(f"[Check] Sheet '{SHEET_NAME}' tidak ditemukan — semua PDF akan diunduh.")
        return None, None
    except Exception as exc:
        print(f"[Check] Error membaca Excel: {exc}")
        return None, None


# Data Fetching

def fetch_html_from_website(url):
    """Ambil HTML dari URL dan kembalikan sebagai string."""
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as exc:
        print(f"[Fetch] Error mengakses website: {exc}")
        return None


def extract_relevant_pdf_links(html_content, last_year, last_month):
    """Parse HTML dan kembalikan dict {tahun: [{'Bulan', 'Bulan_Angka', 'url'}]} untuk PDF baru."""
    soup          = BeautifulSoup(html_content, "html.parser")
    pdf_links     = {}
    tahun_pattern = re.compile(r"20\d{2}")
    rows          = soup.find_all("tr")

    tahun_row, data_row = next(
        (
            (row, rows[i + 1])
            for i, row in enumerate(rows[:-1])
            if any(
                td.find("b") and tahun_pattern.search(td.find("b").get_text())
                for td in row.find_all("td")
            )
        ),
        (None, None),
    )

    if not tahun_row or not data_row:
        print("[Fetch] Tidak ditemukan struktur tabel yang valid.")
        return {}

    tahun_list = [
        int(match.group())
        for td in tahun_row.find_all("td")
        if (match := tahun_pattern.search(td.get_text()))
    ]

    if not tahun_list:
        return {}

    print(f"[Fetch] Data tersedia untuk tahun: {sorted(set(tahun_list))}")
    tahun_mulai = last_year or min(tahun_list)

    for tahun, td in zip(tahun_list, data_row.find_all("td")):
        if tahun < tahun_mulai:
            continue
        for a in td.find_all("a", href=True):
            bulan_text  = a.text.strip().lower()
            bulan_angka = MONTHS_ID_TO_NUM.get(bulan_text)
            if not bulan_angka:
                continue
            if tahun == tahun_mulai and last_month and bulan_angka <= last_month:
                continue
            href = a["href"]
            if not href.startswith("http"):
                href = f"https://migas.esdm.go.id{href}"
            pdf_links.setdefault(tahun, []).append({
                "Bulan":       bulan_text.capitalize(),
                "Bulan_Angka": bulan_angka,
                "url":         href,
            })

    return pdf_links


# PDF Download

def _download_with_retry(url: str, timeout: int = 60,
                          max_retries: int = 4, backoff_base: float = 3.0) -> bytes:
    """
    Download URL dengan retry + exponential backoff.
    Retry pada: ConnectionError, Timeout, ConnectionReset, 5xx status.
    Raise exception terakhir jika semua retry habis.
    """
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, timeout=timeout, stream=True)
            resp.raise_for_status()
            return resp.content
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError) as exc:
            last_exc = exc
        except requests.exceptions.HTTPError as exc:
            # Retry hanya untuk 5xx; 4xx langsung raise
            if exc.response is not None and exc.response.status_code < 500:
                raise
            last_exc = exc

        if attempt < max_retries:
            wait = backoff_base * (2 ** (attempt - 1))   # 3s, 6s, 12s
            print(f"[Download] Percobaan {attempt} gagal ({type(last_exc).__name__}). "
                  f"Retry dalam {wait:.0f}s...")
            time.sleep(wait)

    raise last_exc


def download_pdfs(pdf_links, folder=PDF_FOLDER):
    """Download semua PDF dari dict pdf_links ke folder lokal."""
    os.makedirs(folder, exist_ok=True)

    # Bersihkan file PDF sisa dari run sebelumnya yang gagal
    stale = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
    if stale:
        for f in stale:
            try:
                os.remove(os.path.join(folder, f))
            except Exception as exc:
                print(f"[Download] Gagal hapus sisa {f}: {exc}")

    total = sum(len(v) for v in pdf_links.values())
    print(f"\n[Download] {total} file PDF ditemukan...")

    failed = []
    for tahun, items in pdf_links.items():
        for item in items:
            bulan    = item["Bulan"]
            url      = item["url"]
            filename = f"{tahun}_{bulan}.pdf"
            path     = os.path.join(folder, filename)
            try:
                content = _download_with_retry(url)
                with open(path, "wb") as f:
                    f.write(content)
                print(f"  ✓ {filename}")
            except Exception as exc:
                print(f"  ✗ {filename} -> Gagal: {exc}")
                failed.append(filename)

    if failed:
        print(f"  ⚠ {len(failed)} file gagal: {', '.join(failed)}")
        print("    Jalankan ulang untuk mencoba lagi.")


# PDF Parsing

def _get_ocr_reader():
    """Inisialisasi EasyOCR reader secara lazy (hanya saat pertama dibutuhkan)."""
    global _ocr_reader
    if _ocr_reader is None:
        print("[OCR] Initialising EasyOCR reader …")
        _ocr_reader = easyocr.Reader(["id", "en"], gpu=False)
    return _ocr_reader


def _parse_price(raw: str) -> float | None:
    """Convert a raw price string like '79.34', '71,11', or '1.234,56' to float."""
    raw = raw.strip()
    if not raw:
        return None
    # Format Eropa: titik ribuan + koma desimal -> "1.234,56"
    if re.match(r"^\d{1,3}(\.\d{3})+,\d{1,2}$", raw):
        return float(raw.replace(".", "").replace(",", "."))
    # Koma sebagai desimal: "71,11"
    if re.match(r"^\d{1,3},\d{1,2}$", raw):
        return float(raw.replace(",", "."))
    # Titik sebagai desimal: "79.34"
    if re.match(r"^\d{1,3}\.\d{1,2}$", raw):
        return float(raw)
    # Angka bulat tanpa desimal: "80"
    if re.match(r"^\d{2,3}$", raw):
        return float(raw)
    # Fallback: hapus titik ribuan, ganti koma desimal
    try:
        return float(raw.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _clean_ocr_text(text: str) -> str:
    """Normalise common OCR misreads of 'US$' prefix."""
    text = re.sub(r"\bUSS(\d)",                r"US$\1",  text)
    text = re.sub(r"\bUS8(\d{2,3}[.,]\d{2})", r"US$\1",  text)
    text = re.sub(r"\bU\s*[Ss]\s*[8S\$]?\s*(?=\d)", "US$", text)
    return text


def _is_digital_pdf(pdf: fitz.Document, sample_pages: int = 3) -> bool:
    """
    Return True if the PDF has meaningful extractable text
    (i.e. it is a digital / e-signed document, NOT a scanned image).
    Threshold: at least one of the first `sample_pages` pages has > 100 chars.
    """
    for i in range(min(sample_pages, len(pdf))):
        if len(pdf[i].get_text().strip()) > 100:
            return True
    return False


def _infer_month_from_filename(filename: str):
    """
    Try to infer (tahun, bulan_str) from filename patterns like:
      "2023_Juli.pdf", "juli_2023.pdf", "2023-07.pdf"
    Returns (tahun: int | None, bulan: str | None).
    """
    base = os.path.splitext(os.path.basename(filename))[0].lower()

    # Pattern: "2023_Juli" or "Juli_2023"
    m = re.search(
        rf"(\d{{4}})[_\-]({_MONTH_PATTERN.lower()})|({_MONTH_PATTERN.lower()})[_\-](\d{{4}})",
        base, re.IGNORECASE
    )
    if m:
        if m.group(1):
            return int(m.group(1)), m.group(2).capitalize()
        return int(m.group(4)), m.group(3).capitalize()

    # Pattern: numeric month "2023_07" or "07_2023"
    m2 = re.search(r"(\d{4})[_\-](\d{2})|(\d{2})[_\-](\d{4})", base)
    if m2:
        if m2.group(1):
            tahun, mo = int(m2.group(1)), int(m2.group(2))
        else:
            mo, tahun = int(m2.group(3)), int(m2.group(4))
        bulan_str = MONTHS_NUM_TO_ID.get(mo)
        if bulan_str:
            return tahun, bulan_str

    return None, None


def _extract_from_digital_pdf(pdf: fitz.Document, filepath: str):
    """
    Extract ICP data from a *digital* (e-signed / text-layer) PDF.

    Targets three patterns in priority order:
      A) KEEMPAT diktum  ->  "US$ 79.34/barrel"   (most reliable, 2023+)
      B) rata-rata sentence  ->  "US$ XX.XX/barrel"
      C) BULAN <month> header in Lampiran title

    For Dated Brent, reads the DATED BRENT column value from Lampiran table.
    For signing date, reads the line following "pada tanggal".
    """
    full_text = "\n".join(pdf[i].get_text() for i in range(len(pdf)))

    find_month = None
    find_price = None
    find_date  = None
    find_brent = None

    # ── Price + Month ────────────────────────────────────────────────────────
    # Diktum evolution:
    #   2019–2022: KEDUA  "Harga rata-rata … US$ XX.XX/barrel"
    #   2023–2025: KEEMPAT "… ditetapkan sebesar US$ XX.XX/barrel"
    #   2026+    : KEDUA again (restructured to 3 diktum only)

    # Pattern A: named diktum + month + price (covers both KEEMPAT and KEDUA)
    m = re.search(
        rf"(?:KEEMPAT|KEDUA)\s*:?.*?bulan\s+({_MONTH_PATTERN_FUZZY})\s*[\n\s]*(\d{{4}})\s+ditetapkan\s+sebesar\s+US\$\s*([\d.,]+)/bar\w*",
        full_text, re.IGNORECASE | re.DOTALL
    )
    if m:
        find_month = _normalize_month(m.group(1))
        find_price = _parse_price(m.group(3))

    # Pattern A2: diktum price only (month extracted separately)
    if not find_price:
        m = re.search(
            r"\n(?:KEEMPAT|KEDUA)\b.*?US\$\s*([\d.,]+)/bar\w*",
            full_text, re.DOTALL
        )
        if m:
            find_price = _parse_price(m.group(1))
            m_mo = re.search(
                rf"\n(?:KEEMPAT|KEDUA)\b.*?bulan\s+({_MONTH_PATTERN_FUZZY})",
                full_text, re.DOTALL
            )
            if m_mo:
                find_month = _normalize_month(m_mo.group(1))

    # Pattern B: generic rata-rata sentence (fallback for any format)
    if not find_price:
        m = re.search(
            rf"\n(?:KEEMPAT|KEDUA)\b.*?bulan\s+({_MONTH_PATTERN_FUZZY})[\s\S]*?US\$\s*([\d.,]+)/bar\w*",
            full_text, re.DOTALL
        )
        if m:
            find_month = _normalize_month(m.group(1))
            find_price = _parse_price(m.group(2))

    # Pattern C: infer month from BULAN header if month still missing
    if find_price and not find_month:
        m = re.search(rf"BULAN\s+({_MONTH_PATTERN})\s+(\d{{4}})", full_text, re.IGNORECASE)
        if m:
            find_month = m.group(1).capitalize()

    # ── Dated Brent ──────────────────────────────────────────────────────────
    # Strategy 1: SLC row — "S L C  DATED BRENT ... val  alpha  harga"
    m_slc_row = re.search(
        r"S\s*L\s*C\s+DATED\s+BRENT[^0-9]*([\d.,]+)\s+([-]?[\d.,]+)\s+([\d.,]+)",
        full_text, re.IGNORECASE
    )
    if m_slc_row:
        brent_candidate = _parse_price(m_slc_row.group(1))
        if brent_candidate and 15 < brent_candidate < 200:
            find_brent = brent_candidate

    # Strategy 2: DATED BRENT label frequency
    if not find_brent:
        brent_candidates = re.findall(
            r"DATED\s+BRENT[^\d]*([\d]{2,3}[.,]\d{2})",
            full_text, re.IGNORECASE
        )
        counted = Counter(brent_candidates)
        if counted:
            most_common_val, freq = counted.most_common(1)[0]
            if freq >= 2:
                find_brent = _parse_price(most_common_val)

    # Strategy 3: frequency analysis — Dated Brent repeats for every main crude row (≥4×)
    if not find_brent:
        all_candidates = re.findall(r'\b(\d{2,3}[.,]\d{2})\b', full_text)
        counted_all = Counter(all_candidates)
        for val_str, freq in counted_all.most_common():
            if freq >= 4:
                candidate = _parse_price(val_str)
                if candidate and 15 < candidate < 200:
                    find_brent = candidate
                    break

    # ── Signing date ─────────────────────────────────────────────────────────
    date_patterns = [
        rf"Ditetapkan\s+di\s*\w+.*?pada\s+tanggal\s+(\d{{1,2}})\s+({_MONTH_PATTERN_FUZZY})\s+(\d{{4}})",
        rf"NOMOR\s*:?\s*[\w.\s/]+\s+TANGGAL\s*:?\s*(\d{{1,2}})\s+({_MONTH_PATTERN_FUZZY})\s+(\d{{4}})",
        rf"TANGGAL\s*:\s*(\d{{1,2}})\s+({_MONTH_PATTERN_FUZZY})\s+(\d{{4}})",
        rf"(\d{{1,2}})\s+({_MONTH_PATTERN_FUZZY})\s+(\d{{4}})\s*\nDitandatangani",
        rf"[\w./]+/\d{{4}}\n(\d{{1,2}})\s+({_MONTH_PATTERN_FUZZY})\s+(\d{{4}})\n",
        rf"pada\s+tanggal\s+(\d{{1,2}})\s+({_MONTH_PATTERN_FUZZY})\s+(\d{{4}})(?!.{{0,60}}tentang)",
    ]

    for pat in date_patterns:
        m = re.search(pat, full_text, re.IGNORECASE | re.DOTALL)
        if m:
            find_date = f"{m.group(1)} {_normalize_month(m.group(2))}"
            break

    return find_month, find_price, find_date, find_brent


def _extract_from_scanned_pdf(pdf: fitz.Document, filepath: str,
                               start_page: int = 1, end_page: int = 8):
    """
    Extract ICP data dari *scanned* PDF menggunakan EasyOCR.
    OCR is expensive; we stop as soon as all four fields are found.
    """
    reader    = _get_ocr_reader()
    start_idx = max(0, start_page - 1)
    end_idx   = min(end_page, len(pdf))

    find_month           = None
    find_price           = None
    find_date            = None
    find_brent           = None
    date_pattern_quality = 999  # lower = better; tracks which pattern last set find_date
    date_in_range        = False  # True only when current find_date passes range check

    for i in range(start_idx, end_idx):
        page    = pdf[i]
        pix     = page.get_pixmap(dpi=300)
        img     = Image.open(io.BytesIO(pix.tobytes()))
        results = reader.readtext(np.array(img), detail=0)
        text    = _clean_ocr_text(" ".join(results))

        # ── Signing date ─────────────────────────────────────────────────────
        # Keep scanning if: no date yet, current date is out-of-range, or quality is low.
        # Range check (ICP+1..ICP+2) filters out Mengingat reference dates like
        # "30 Juli 2019 tentang Formula" that are months away from the signing date.
        if not find_date or not date_in_range or date_pattern_quality >= _DATE_PATTERN_RELIABLE_THRESHOLD:
            for pat_idx, (pat, flags) in enumerate(_DATE_PATTERNS_OCR):
                m = re.search(pat, text, flags)
                if m:
                    candidate      = f"{m.group(1)} {_normalize_month(m.group(2))}"
                    candidate_ok   = _tanggal_in_range(candidate, find_month)
                    # Accept if better quality, OR current out-of-range and this is valid
                    should_update  = (
                        pat_idx < date_pattern_quality
                        or (not date_in_range and candidate_ok)
                    )
                    if should_update or not find_date:
                        find_date            = candidate
                        date_pattern_quality = pat_idx
                        date_in_range        = candidate_ok
                    break

        # ── Dated Brent ──────────────────────────────────────────────────────
        if not find_brent:
            # Pattern 1: "SLC <value>" — SLC is always row 1 in the main crude table,
            # its first column value equals Dated Brent.
            m = _PAT_BRENT_SLC.search(text.upper())
            if m:
                candidate = _parse_price(m.group(1))
                if candidate and 15 < candidate < 200:
                    find_brent = candidate

            # Pattern 2: explicit "DATED BRENT" label near a number
            if not find_brent:
                m2 = re.search(
                    r"(?:Dated\s+Brent|DATED\s+BRENT)[^\d]*([\d]{2,3}[.,]\d{2})",
                    text, re.IGNORECASE
                )
                if m2:
                    candidate = _parse_price(m2.group(1))
                    if candidate and 15 < candidate < 200:
                        find_brent = candidate

            # Pattern 3: frequency — Dated Brent is the same value repeated for every
            # main crude row (6–9 times). Find the most-repeated 2-decimal number
            # in the plausible range and appearing ≥4 times on this page.
            if not find_brent:
                candidates_ocr = re.findall(r"\b(\d{2,3}[.,]\d{2})\b", text)
                counted = Counter(candidates_ocr)
                for val_str, freq in counted.most_common():
                    if freq >= 4:
                        candidate = _parse_price(val_str)
                        if candidate and 15 < candidate < 200:
                            find_brent = candidate
                            break

        # ── ICP price + month ────────────────────────────────────────────────
        # Format evolution:
        #   2019–2021: diktum KEDUA  "Harga rata-rata … bulan <Month> <YYYY> ditetapkan sebesar US$ XX.XX/barrel"
        #   2022+    : diktum KEEMPAT (same sentence structure)
        # Both are captured by _PAT_KEYWORD since the keyword "harga rata-rata minyak mentah" appears in both.
        # _PAT_PRICE now also handles OCR artefacts like "US $ 63.26" or "US S 63.26".
        if not (find_price and find_month) and _PAT_KEYWORD.search(text):
            for sentence in re.split(r"[.!?]\s+", text):
                if not _PAT_KEYWORD.search(sentence):
                    continue
                bulan_m = re.search(_MONTH_PATTERN, sentence, re.IGNORECASE)
                harga_m = _PAT_PRICE.search(sentence)
                if bulan_m and harga_m:
                    find_month = bulan_m.group(0).capitalize()
                    find_price = _parse_price(harga_m.group(1))
                    break
            # Fallback: sentence splitting may fail if OCR produced no sentence-ending punctuation.
            # Try matching the full text directly.
            if not find_price:
                m_full = re.search(
                    rf"rata[\s-]+rata.*?bulan\s+({_MONTH_PATTERN}).*?US\s*[\$S8]\s*([\d.,]+)/bar\\w+",
                    text, re.IGNORECASE | re.DOTALL
                )
                if m_full:
                    find_month = find_month or m_full.group(1).capitalize()
                    find_price = _parse_price(m_full.group(2))

        # Early exit when everything is found AND date is in valid range
        if find_month and find_price and find_brent and find_date and date_in_range:
            break

    # If date was found but never passed the range check, discard it
    if find_date and not date_in_range:
        print(f"[OCR] ⚠ Tanggal '{find_date}' di luar rentang ICP+1..ICP+2 "
              f"untuk bulan {find_month} — dikosongkan.")
        find_date = None

    return find_month, find_price, find_date, find_brent


def _extract_hybrid(pdf: fitz.Document, filepath: str):
    """
    Used when a PDF has partial text (e.g. cover page is text, inner pages are scans).
    Run digital extraction first; fill missing fields with OCR.
    """
    find_month, find_price, find_date, find_brent = _extract_from_digital_pdf(pdf, filepath)

    missing = [f for f, v in [("month", find_month), ("price", find_price),
                               ("date",  find_date),  ("brent", find_brent)] if not v]
    if missing:
        ocr_month, ocr_price, ocr_date, ocr_brent = _extract_from_scanned_pdf(pdf, filepath)
        find_month = find_month or ocr_month
        find_price = find_price or ocr_price
        find_date  = find_date  or ocr_date
        find_brent = find_brent or ocr_brent

    return find_month, find_price, find_date, find_brent


def extract_icp_from_pdf(filepath: str, start_page: int = 1, end_page: int = 8):
    """
    Auto-detect PDF type (digital / scanned / hybrid) dan ekstrak:
      (find_month, find_price, find_date, find_brent)
    Any field may be None if not found.
    """
    filename = os.path.basename(filepath)
    try:
        pdf = fitz.open(filepath)
    except Exception as exc:
        print(f"  ✗ {filename}: Tidak bisa dibuka — {exc}")
        return None, None, None, None

    try:
        digital = _is_digital_pdf(pdf)

        # Guard: skip formula-only Kepmen (no monthly ICP price)
        # E.g. SK 305.K/MG.01/MEM.M/2022 — contains formula table but no diktum KEEMPAT.
        sample_text = "\n".join(pdf[i].get_text() for i in range(min(4, len(pdf))))
        is_formula_doc = (
            re.search(r"FORMULA HARGA MINYAK MENTAH", sample_text, re.IGNORECASE)
            and not re.search(
                r"HARGA MINYAK MENTAH INDONESIA\s+BULAN\s+" + _MONTH_PATTERN,
                sample_text, re.IGNORECASE
            )
            and not re.search(r"KEEMPAT", sample_text, re.IGNORECASE)
        )
        if is_formula_doc:
            print(f"  ⚠ {filename}: Dokumen formula (bukan ICP bulanan) — dilewati")
            return None, None, None, None

        if digital:
            # Detect hybrid: some pages are digital, but Lampiran (last pages with table data)
            # may be scanned images — indicated by very low char count on those pages.
            total_pages = len(pdf)
            lampiran_pages_are_scan = any(
                len(pdf[i].get_text().strip()) < 50
                for i in range(max(0, total_pages - 3), total_pages)
            )
            if lampiran_pages_are_scan:
                # Lampiran pages are scanned -> need OCR for Brent
                result = _extract_hybrid(pdf, filepath)
            else:
                result = _extract_from_digital_pdf(pdf, filepath)
                # Rescue: some PDFs have garbled text layer (e.g. embedded scan with bad OCR)
                # where digital extraction misses fields. If Brent or price still missing,
                # fall back to OCR as well.
                find_month, find_price, find_date, find_brent = result
                missing = [f for f, v in [("brent", find_brent), ("price", find_price)] if not v]
                if missing:
                    ocr_month, ocr_price, ocr_date, ocr_brent = _extract_from_scanned_pdf(
                        pdf, filepath, start_page, end_page)
                    find_brent = find_brent or ocr_brent
                    find_price = find_price or ocr_price
                    find_month = find_month or ocr_month
                    find_date  = find_date  or ocr_date
                result = (find_month, find_price, find_date, find_brent)
        else:
            result = _extract_from_scanned_pdf(pdf, filepath, start_page, end_page)

        find_month, find_price, find_date, find_brent = result

        # Last resort: infer month from filename if still missing
        if not find_month:
            _, fname_month = _infer_month_from_filename(filename)
            if fname_month:
                find_month = fname_month

        # Print hasil ringkas per PDF
        harga_str = f"US${find_price}"  if find_price else "—"
        brent_str = f"US${find_brent}"  if find_brent else "—"
        tgl_str   = find_date           if find_date  else "—"
        print(f"  ✓ {filename} -> Harga={harga_str} | Brent={brent_str} | Tanggal={tgl_str}")

        return find_month, find_price, find_date, find_brent

    except Exception as exc:
        print(f"  ✗ {filename}: Error — {exc}")
        traceback.print_exc()
        return None, None, None, None
    finally:
        pdf.close()


def extract_icp_from_all_pdfs(folder: str = PDF_FOLDER,
                               tahun_filter: int | None = None) -> pd.DataFrame:
    """
    Extract ICP data dari semua PDF di *folder*.
    Jika *tahun_filter* diset, hanya file dengan tahun tersebut yang diproses.
    File yang berhasil diekstrak akan dihapus.
    Returns DataFrame dengan kolom: Tahun, Bulan, Harga, Harga_Brent, Tanggal.
    """
    pdf_files = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
    print(f"\n[Parse] Membaca {len(pdf_files)} file PDF...")

    results = []
    for file in sorted(pdf_files):
        filepath = os.path.join(folder, file)

        # Tahun filter: hapus dan lewati file dari tahun yang salah
        if tahun_filter is not None:
            match = re.match(r"(\d{4})_", file)
            file_tahun = int(match.group(1)) if match else None
            if file_tahun != tahun_filter:
                print(f"  - {file}: tahun {file_tahun} dilewati (filter={tahun_filter})")
                try:
                    os.remove(filepath)
                except Exception:
                    pass
                continue

        bulan, harga, tanggal, harga_brent = extract_icp_from_pdf(filepath)

        if bulan and harga:
            # Prefer year from filename; fall back to inferred
            match = re.match(r"(\d{4})_", file)
            if match:
                tahun = int(match.group(1))
            else:
                tahun, _ = _infer_month_from_filename(file)

            # Validasi tanggal (safety net untuk digital PDF path).
            # OCR scanner sudah filter via _tanggal_in_range secara internal.
            # Ini safety net untuk kasus dari digital/hybrid path.
            tanggal_valid = tanggal
            if tanggal and bulan and not _tanggal_in_range(tanggal, bulan):
                print(f"  ⚠ Tanggal '{tanggal}' di luar rentang valid untuk ICP {bulan} -> dikosongkan")
                tanggal_valid = None

            results.append({
                "Tahun":       tahun,
                "Bulan":       bulan,
                "Harga":       str(harga),
                "Harga_Brent": str(harga_brent) if harga_brent else None,
                "Tanggal":     tanggal_valid,
            })
            try:
                os.remove(filepath)
            except Exception as exc:
                print(f"[Parse] Gagal hapus {file}: {exc}")
        else:
            print(f"  ✗ {file} -> Tidak ditemukan harga ICP (file dipertahankan)")

    return pd.DataFrame(results)


# Save to Storage

def save_to_onedrive(df: pd.DataFrame):
    """Merge new ICP data with existing sheet, deduplicate, sort, and write."""
    if df.empty:
        print("[Save] Tidak ada data baru untuk disimpan.")
        return

    print("\n[Save] Menyimpan ke storage...")

    # Load existing
    try:
        existing_df = storage.read_structured_sheet(SHEET_NAME)

        if existing_df.empty:
            df_combined = df
        else:
            df_combined = pd.concat([existing_df, df], ignore_index=True)
            # Deduplikasi
            df_combined.drop_duplicates(subset=["Tahun", "Bulan"], keep="last", inplace=True)
            # Paksa urutan kolom mengikuti existing
            df_combined = df_combined[existing_df.columns]
            print(f"  Data lama : {len(existing_df)} baris")

        # Sorting
        df_combined["Bulan_Lower"] = df_combined["Bulan"].astype(str).str.lower()
        df_combined["Bulan_Angka"] = df_combined["Bulan_Lower"].map(MONTHS_ID_TO_NUM)
        df_combined = df_combined.sort_values(["Tahun", "Bulan_Angka"])
        df_combined = df_combined.drop(columns=["Bulan_Lower", "Bulan_Angka"])

    except Exception as exc:
        print(f"  ⚠ Error baca sheet existing: {exc}")
        df_combined = df

    print(f"  Data baru  : {len(df)} baris")
    print(f"  Total      : {len(df_combined)} baris")

    try:
        storage.write_structured_sheet(SHEET_NAME, df_combined)
        print(f"  ✓ Simpan berhasil -> sheet {SHEET_NAME}")

    except Exception as exc:
        print(f"  ✗ Error saat menyimpan: {exc}")
        traceback.print_exc()


# Public Entry Point

def main_price_esdm(tahun_filter: int | None = None):
    """
    Full ICP price-scraping workflow:
    check last entry -> fetch HTML -> extract PDF links ->
    download PDFs -> extract data -> save to storage.
    """
    print(f"\n{'='*60}")
    print("SCRAPER ICP MIGAS ESDM")
    print(f"{'='*60}")

    last_year, last_month = read_last_entry_from_excel()

    html = fetch_html_from_website(MIGAS_URL)
    if not html:
        return

    pdf_links = extract_relevant_pdf_links(html, last_year, last_month)
    if not pdf_links:
        print("  Tidak ada PDF baru untuk diproses.")
        return

    if tahun_filter is not None:
        pdf_links = {k: v for k, v in pdf_links.items() if k == tahun_filter}
        if not pdf_links:
            print(f"  Tidak ada PDF untuk tahun {tahun_filter}.")
            return
        print(f"  Filter: tahun {tahun_filter}")

    download_pdfs(pdf_links)

    df = extract_icp_from_all_pdfs(tahun_filter=tahun_filter)
    if df.empty:
        print("  Tidak ada data yang berhasil diekstrak.")
        return

    print("\n[Main] Hasil:")
    print(df.to_string(index=False))

    save_to_onedrive(df)

    print(f"\n{'='*60}")
    print("SELESAI")
    print(f"{'='*60}\n")


# Script Entry Point

if __name__ == "__main__":
    main_price_esdm()