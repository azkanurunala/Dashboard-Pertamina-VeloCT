import os
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import fitz
from PIL import Image
import easyocr
import io
import numpy as np

_MONTH_TO_NUMBER = {
    'januari': 1, 'februari': 2, 'maret': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'agustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'desember': 12
}
_NUMBER_TO_MONTH = {v: k.capitalize() for k, v in _MONTH_TO_NUMBER.items()}
reader = easyocr.Reader(['id', 'en'], gpu=False)
_MONTH_PATTERN = r"(?:Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)"
_PRICE_PATTERN = r"US\$[\s]*([\d.,]+)"
_DATE_PATTERN = rf"Ditetapkan\s+di\s+Jakarta.*?\s+(\d{{1,2}})\s+({_MONTH_PATTERN})\s+(\d{{4}}).*?(?:MENTERI\s+ENERGI|BAHLIL|ttd)"

# ============================== FUNGSI: Baca Excel ==============================
def read_last_entry_from_excel(excel_path: str, sheet_name: str):
    if not os.path.exists(excel_path):
        print("File Excel belum ada, semua PDF akan diunduh.")
        return None, None
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name, engine='openpyxl')
        if df.empty or "Bulan" not in df.columns or "Tahun" not in df.columns:
            print("Sheet kosong atau format salah. Semua PDF akan diunduh.")
            return None, None
        df["Bulan"] = df["Bulan"].astype(str).str.lower()
        df["Bulan_Angka"] = df["Bulan"].map(_MONTH_TO_NUMBER)
        df = df.dropna(subset=["Bulan_Angka"])
        if df.empty:
            print("Tidak ada data valid di Excel. Semua PDF akan diunduh.")
            return None, None
        df_sorted = df.sort_values(["Tahun", "Bulan_Angka"])
        last_row = df_sorted.iloc[-1]
        print(f"Data terakhir di Excel: {last_row['Bulan'].capitalize()} {int(last_row['Tahun'])}")
        return int(last_row["Tahun"]), int(last_row["Bulan_Angka"])
    except ValueError:
        print(f"Sheet '{sheet_name}' tidak ditemukan. Semua PDF akan diunduh.")
        return None, None
    except Exception as e:
        print(f"Error membaca Excel: {e}")
        return None, None

# ============================== FUNGSI: Fetch HTML ==============================
def fetch_html_from_website(url: str):
    try:
        headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        )}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        print("Berhasil mengambil HTML dari website")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error mengakses website: {e}")
        return None

# ============================== FUNGSI: Ambil Link PDF ==============================
def extract_relevant_pdf_links(html_content: str, last_year: int | None, last_month: int | None):
    soup = BeautifulSoup(html_content, 'html.parser')
    pdf_links = {}
    tahun_pattern = re.compile(r"20\d{2}")
    rows = soup.find_all("tr")
    tahun_row, data_row = next(
        ((row, rows[i + 1]) for i, row in enumerate(rows[:-1])
         if any(td.find("b") and tahun_pattern.search(td.find("b").get_text()) for td in row.find_all("td"))),
        (None, None)
    )
    if not tahun_row or not data_row:
        print("Tidak ditemukan struktur tabel yang valid.")
        return {}
    tahun_list = [
        int(match.group())
        for td in tahun_row.find_all("td")
        if (match := tahun_pattern.search(td.get_text()))
    ]
    if not tahun_list:
        print("Tidak ada tahun yang valid ditemukan.")
        return {}
    print(f"Ditemukan data untuk tahun: {sorted(set(tahun_list))}")
    tahun_mulai = last_year or min(tahun_list)
    data_tds = data_row.find_all("td")
    for tahun, td in zip(tahun_list, data_tds):
        if tahun < tahun_mulai:
            continue
        for a in td.find_all("a", href=True):
            bulan_text = a.text.strip().lower()
            bulan_angka = _MONTH_TO_NUMBER[bulan_text]
            if tahun == tahun_mulai and last_month and bulan_angka <= last_month:
                continue
            href = a["href"]
            if not href.startswith("http"):
                href = f"https://migas.esdm.go.id{href}"
            pdf_links.setdefault(tahun, []).append({
                "Bulan": bulan_text.capitalize(),
                "Bulan_Angka": bulan_angka,
                "url": href
            })
    return pdf_links

# ============================== FUNGSI: Download PDF ==============================
def download_pdfs(pdf_links: dict, folder: str = "../results/hasil-migas-esdm-pdf"):
    os.makedirs(folder, exist_ok=True)
    total = sum(len(v) for v in pdf_links.values())
    print(f"\nMulai download {total} file PDF...\n")
    for tahun, items in pdf_links.items():
        for item in items:
            bulan, url = item["Bulan"], item["url"]
            filename = f"{tahun}_{bulan}.pdf"
            path = os.path.join(folder, filename)
            try:
                print(f"Downloading {filename} ...")
                response = requests.get(url, timeout=60)
                response.raise_for_status()
                with open(path, "wb") as f:
                    f.write(response.content)
                print(f"Selesai: {filename}")
            except Exception as e:
                print(f"Gagal download {filename}: {e}")

# ============================== OCR & Ekstraksi Harga dan Bulan ==============================
def clean_ocr_text(text: str) -> str:
    text = re.sub(r'\bUSS(\d)', r'US$\1', text)
    text = re.sub(r'\bUS8(\d{2,3}[.,]\d{2})', r'US$\1', text)
    text = re.sub(r'\bU\s*[Ss]\s*[8S\$]?\s*(?=\d)', 'US$', text)
    return text

def extract_icp_from_pdf(filepath: str, start_page: int = 2, end_page: int = 5):
    try:
        pdf = fitz.open(filepath)
        total_pages = len(pdf)
        start_idx, end_idx = max(0, start_page - 1), min(end_page, total_pages)
        _KEYWORD_PATTERN = r'harga\s+rata[\s-]+rata\s+minyak\s+mentah'
        find_month = None
        find_price = None
        find_date = None
        for i in range(start_idx, end_idx):
            page = pdf[i]
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes()))
            results = reader.readtext(np.array(img), detail=0)
            text = " ".join(results)
            text = clean_ocr_text(text)
            if not find_date:
                tanggal_match = re.search(_DATE_PATTERN, text, re.IGNORECASE | re.DOTALL)
                if tanggal_match:
                    day = tanggal_match.group(1)
                    month_nama = tanggal_match.group(2).capitalize()
                    find_date = f"{day} {month_nama}"
    
            if (not find_price or not find_month) and re.search(_KEYWORD_PATTERN, text, re.IGNORECASE):
                sentences = re.split(r'[.!?]\s+', text)
                for sentence in sentences:
                    if not re.search(_KEYWORD_PATTERN, sentence, re.IGNORECASE):
                        continue
                    bulan_match = re.search(_MONTH_PATTERN, sentence, re.IGNORECASE)
                    harga_match = re.search(_PRICE_PATTERN, sentence)
                    if bulan_match and harga_match:
                        find_month = bulan_match.group(0).capitalize() 
                        find_price = harga_match.group(1).replace(" ", "")
                        break 
            if find_month and find_price and find_date:
                break 
        return find_month, find_price, find_date
    except Exception as e:
        print(f"Error membaca {os.path.basename(filepath)}: {e}")
        return None, None, None

def extract_icp_from_all_pdfs(folder: str = "../results/hasil-migas-esdm-pdf"):
    results = []
    pdf_files = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
    print(f"\nMengekstrak {len(pdf_files)} file PDF...\n")
    for file in sorted(pdf_files):
        filepath = os.path.join(folder, file)
        bulan, harga, tanggal = extract_icp_from_pdf(filepath)
        if bulan and harga:
            match = re.match(r"(\d{4})_", file)
            tahun = int(match.group(1)) if match else None
            results.append({
                "Tahun": tahun, 
                "Bulan": bulan, 
                "Harga": f"{harga}",
                "Tanggal": tanggal 
            })
            try:
                os.remove(filepath)
            except Exception as e:
                print(f"Gagal hapus {file}: {e}")
        else:
            print(f"{file}: Tidak ditemukan harga ICP")
    return pd.DataFrame(results)

# ============================== MAIN ==============================
def main_price_esdm():
    EXCEL_PATH = "../results/Terstruktur(Data Scrapping).xlsx"
    SHEET_NAME = "(Data)Harga Minyak"
    URL = "https://www.migas.esdm.go.id/post/read/harga-minyak-mentah"
    print("="*80)
    print("SCRAPER ICP MIGAS ESDM")
    print("="*80)
    last_year, last_month = read_last_entry_from_excel(EXCEL_PATH, SHEET_NAME)
    html = fetch_html_from_website(URL)
    if not html:
        return
    pdf_links = extract_relevant_pdf_links(html, last_year, last_month)
    if not pdf_links:
        print("Tidak ada PDF baru.")
        return
    download_pdfs(pdf_links)
    df = extract_icp_from_all_pdfs("../results/hasil-migas-esdm-pdf")
    if not df.empty:
        print("\nHasil Akhir:")
        print(df)
        if os.path.exists(EXCEL_PATH):
            try:
                df_old = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME, engine='openpyxl')
                df_combined = pd.concat([df_old, df], ignore_index=True)
                df_combined.drop_duplicates(subset=["Tahun", "Bulan"], keep="last", inplace=True)
            except ValueError:
                print(f"Sheet '{SHEET_NAME}' tidak ditemukan, membuat sheet baru")
                df_combined = df
            except Exception as e:
                print(f"Gagal membaca file Excel lama: {e}")
                df_combined = df
        else:
            df_combined = df
        df_combined["Bulan_Lower"] = df_combined["Bulan"].astype(str).str.lower()
        df_combined["Bulan_Angka"] = df_combined["Bulan_Lower"].map(_MONTH_TO_NUMBER)
        df_combined = df_combined.sort_values(["Tahun", "Bulan_Angka"])
        df_combined = df_combined.drop(columns=["Bulan_Lower", "Bulan_Angka"])
        df_combined = df_combined.reset_index(drop=True)
        try:
            if os.path.exists(EXCEL_PATH):
                with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                    df_combined.to_excel(writer, sheet_name=SHEET_NAME, index=False)
            else:
                with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl', mode='w') as writer:
                    df_combined.to_excel(writer, sheet_name=SHEET_NAME, index=False) 
            print(f"\nData berhasil diperbarui di: {EXCEL_PATH}")
            print(f"Sheet: {SHEET_NAME}")
            print(f"Total rows: {len(df_combined)}")
        except Exception as e:
            print(f"Error menyimpan ke Excel: {e}")
    else:
        print("Tidak ada data yang berhasil diekstrak.")
if __name__ == "__main__":
    main_price_esdm()