from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm
import requests
import pandas as pd
import time, re, os
from PyPDF2 import PdfReader
import re
import pdfplumber
from datetime import datetime
from urllib.parse import urljoin
import glob
import os

options = Options()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

base_url = "https://ebtke.esdm.go.id/artikel/pengumuman"
driver.get(base_url)
time.sleep(4)

def parse_date(date_str):
    months = {
        'Januari': '01', 'Februari': '02', 'Maret': '03', 'April': '04',
        'Mei': '05', 'Juni': '06', 'Juli': '07', 'Agustus': '08',
        'September': '09', 'Oktober': '10', 'November': '11', 'Desember': '12'
    }
    date_match = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{4})', date_str)
    if date_match:
        day = date_match.group(1).zfill(2)
        month = months.get(date_match.group(2))
        year = date_match.group(3)
        return f"{year}-{month}-{day}"
    return None


def extract_article_date(card):
    try:
        metadata = card.find_element(By.CSS_SELECTOR, ".article-metadata").text.strip()
        date_part = metadata.split("|")[0].strip()
        days = ["Senin,", "Selasa,", "Rabu,", "Kamis,", "Jumat,", "Sabtu,", "Minggu,"]
        for day in days:
            date_part = date_part.replace(day, "")
        return parse_date(date_part.strip())
    except Exception:
        return None


def matches_biodiesel_criteria(title):
    keywords = ["HIP", "BBN", "JENIS", "BIODIESEL", "BULAN"]
    return all(keyword in title.upper() for keyword in keywords)


def extract_article_info(card):
    try:
        title = card.find_element(By.CSS_SELECTOR, ".article-title").text.strip()
        if not matches_biodiesel_criteria(title):
            return None
        href = card.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
        article_date = extract_article_date(card)
        return {
            "Judul": title,
            "url": href,
            "Date": article_date
        }
    except Exception:
        return None


def get_missing_months_from_excel(filename='Data Terstruktur EBT.xlsx'):
    try:
        df = pd.read_excel(filename, engine='openpyxl')
        if df.empty or 'Date' not in df.columns:
            print("File Excel kosong, asumsikan scraping awal")
            return None
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        last_date = df['Date'].max()
        if pd.isna(last_date):
            print("File Excel kosong, asumsikan scraping awal")
            return None
        last_month = last_date.month
        last_year = last_date.year
        now = datetime.now()
        current_month = now.month
        current_year = now.year
        diff = (current_year - last_year) * 12 + (current_month - last_month)
        if diff <= 0:
            print(f"Data sudah up-to-date (bulan terakhir: {last_month}/{last_year})")
            return 0 
        print(f"Bulan terakhir di file: {last_month}/{last_year}, bulan sekarang: {current_month}/{current_year}, selisih: {diff}")
        return diff
    except FileNotFoundError:
        print("File Excel tidak ditemukan, asumsikan scraping awal")
        return None


def scrape_biodiesel_articles(driver, excel_filename='Data Terstruktur EBT.xlsx', max_scroll_attempts=20):
    missing_months = get_missing_months_from_excel(excel_filename)
    if missing_months == 0:
        print("Tidak ada artikel baru yang perlu diambil")
        return [], missing_months
    elif missing_months is None:
        print("File kosong, ambil semua artikel yang tersedia")
        max_articles = 9999 
    else:
        max_articles_per_month = 10
        max_articles = missing_months * max_articles_per_month
        print(f"\nMulai scraping: target {max_articles} artikel")
    data = []
    scroll_attempts = 0
    while scroll_attempts < max_scroll_attempts and (len(data) < max_articles or missing_months is None):
        cards = driver.find_elements(By.CSS_SELECTOR, ".product-article-card")
        for card in cards[len(data):]:
            article_info = extract_article_info(card)
            if article_info:
                data.append(article_info)
        if missing_months is not None and len(data) >= max_articles:
            break
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        scroll_attempts += 1
    unique_data = []
    seen_keys = set()
    for item in data:
        key = (item.get("Judul"), item.get("Date"))
        if key not in seen_keys:
            seen_keys.add(key)
            unique_data.append(item)
    print(f"\nTotal artikel ditemukan: {len(data)}")
    print(f"Setelah hapus duplikat: {len(unique_data)}")
    return unique_data, missing_months

data, missing_months = scrape_biodiesel_articles(driver)
print(f"\nTotal artikel HIP-BBN-JENIS-BIODIESEL ditemukan: {len(data)}")
for item in data:
    print(f"{item['Date']} - {item['Judul']}")

print(missing_months)

def find_pdf_link_in_article(driver):
    try:
        all_paragraphs = driver.find_elements(By.TAG_NAME, "p")
        all_links = driver.find_elements(By.TAG_NAME, "a")
        for link in all_links:
            href = link.get_attribute("href")
            text = link.text.strip()
            if href and "drive.esdm.go.id" in href:
                if "Biodiesel" in text or "HIP" in text or "BBN" in text:
                    print(f"Link PDF cocok: {text}")
                    return href
        for link in all_links:
            href = link.get_attribute("href")
            if href and (".pdf" in href.lower() or "drive.esdm.go.id" in href):
                print(f"Link PDF alternatif: {href}")
                return href      
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def get_direct_download_url(driver, pdf_url):
    try:
        driver.get(pdf_url)
        time.sleep(3)
        download_btn = driver.find_element(By.XPATH, "//a[contains(@href, '/s/') or contains(@href, 'download')]")
        return download_btn.get_attribute("href")
    except:
        return pdf_url + "&mode=list&download=1"

def download_pdf(url, filename):
    try:
        response = requests.get(url, stream=True, timeout=30)
        if 'application/pdf' not in response.headers.get('content-type', '').lower():
            print(f"✗ Bukan PDF: {response.headers.get('content-type')}")
            return False
        
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"✓ Downloaded: {filename}")
        return True
    except Exception as e:
        print(f"✗ Error download: {e}")
        return False

def scrape_and_download_pdfs(driver, data, missing_months):
    pdf_links = []

    # Jika tidak ada bulan hilang
    if missing_months == 0:
        print("Tidak ada artikel baru, semua data sudah lengkap.")
        return pdf_links

    # Jika scraping awal (file kosong)
    elif missing_months is None:
        print("Scraping awal: ambil semua artikel yang tersedia.")
        filtered_data = data

    # Jika hanya butuh artikel sesuai missing_months
    else:
        filtered_data = data[:missing_months]
        print(f"Menargetkan {len(filtered_data)} artikel terbaru (untuk {missing_months} bulan hilang).")

    # Proses download PDF untuk artikel yang ditargetkan
    for item in tqdm(filtered_data, desc="Mencari file PDF"):
        print(f"\n=== Membuka: {item['url']} ===")
        driver.get(item["url"])
        time.sleep(3)

        pdf_url = find_pdf_link_in_article(driver)
        if not pdf_url:
            print("Link tidak ditemukan.")
            continue

        direct_pdf_url = get_direct_download_url(driver, pdf_url)
        print(f"Direct PDF URL: {direct_pdf_url}")
        item["pdf_url"] = direct_pdf_url

        # Nama file PDF berdasarkan tanggal artikel
        filename = f"HIP_BBN_{item['Date']}.pdf".replace(":", "-")
        if download_pdf(direct_pdf_url, filename):
            item["pdf_filename"] = filename
            pdf_links.append(item)


    return pdf_links

pdf_links = scrape_and_download_pdfs(driver, data, missing_months)
print(f"\nTotal PDF berhasil didownload: {len(pdf_links)}")

def find_hip_value_and_month_in_table(table):
    hip_value = None
    hip_month = None
    for row_idx, row in enumerate(table):
        if not row:
            continue
        for col_idx, cell in enumerate(row):
            text = str(cell) if cell else ""
            if '(RUPIAH/LITER)' in text.upper():
                if row_idx + 1 >= len(table):
                    continue
                next_row = table[row_idx + 1]
                for val in reversed(next_row):
                    if val:
                        val_clean = str(val).replace(',', '.').replace(' ', '').strip()
                        match = re.match(r'^(\d+(?:\.\d+)?)$', val_clean)
                        if match:
                            hip_value = float(match.group(1))
                            break
                for val in reversed(next_row):
                    if isinstance(val, str) and re.search(
                        r'(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s+\d{4}',
                        val
                    ):
                        hip_month = val.strip()
                        break
                if hip_value:
                    return hip_value, hip_month
    return hip_value, hip_month


def extract_hip_from_pdf(pdf_file):
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    hip_value, hip_month = find_hip_value_and_month_in_table(table)
                    if hip_value:
                        return hip_value, hip_month
        return None, None
    except Exception as e:
        print(f"Error parsing {pdf_file}: {e}")
        return None, None


def parse_all_pdfs(pdf_links):
    excel_data = []
    for item in pdf_links:
        pdf_file = item.get('pdf_filename')
        if not pdf_file or not os.path.exists(pdf_file):
            print(f"PDF tidak ditemukan: {pdf_file}")
            continue
            
        print(f"\nParsing {pdf_file}")
        
        hip_per_liter, hip_month = extract_hip_from_pdf(pdf_file)
        date_artikel = item.get('Date', None)
        
        if hip_per_liter:
            print(f"HIP Biodiesel IDR/L: {hip_per_liter}")
            if hip_month:
                print(f"Bulan HIP: {hip_month}")
            print(f"Date artikel: {date_artikel}")
            
            excel_data.append({
                'Date': date_artikel,
                'Bulan HIP': hip_month,
                'HIP Biodiesel IDR/L': hip_per_liter
            })
    return excel_data


def save_to_excel(data, filename='Data Terstruktur EBT.xlsx'):
    if not data:
        print("Tidak ada data baru untuk disimpan")
        return None
    new_df = pd.DataFrame(data)
    new_df['Date'] = pd.to_datetime(new_df['Date'])
    try:
        existing_df = pd.read_excel(filename)
        print(f"File existing: {len(existing_df)} baris")
        existing_df['Date'] = pd.to_datetime(existing_df['Date'])
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df.drop_duplicates(
            subset=['Date', 'Bulan HIP'], 
            keep='last', 
            inplace=True
        )
        combined_df.sort_values('Date', ascending=True, inplace=True)
        print(f"Data gabungan: {len(combined_df)} baris")
    except FileNotFoundError:
        print("File belum ada, membuat baru")
        combined_df = new_df
    combined_df['Date'] = combined_df['Date'].dt.strftime('%Y-%m-%d')
    combined_df.to_excel(filename, index=False)
    print(f"\nData disimpan ke {filename}")
    return combined_df

excel_data = parse_all_pdfs(pdf_links)
df = save_to_excel(excel_data)