import requests
import pandas as pd
import time
import re
import os
import pdfplumber
from datetime import datetime
from tqdm import tqdm

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

def matches_biodiesel_criteria(title):
    keywords = ["HIP", "BBN", "JENIS", "BIODIESEL", "BULAN"]
    return all(keyword in title.upper() for keyword in keywords)

def get_missing_months_from_excel(filename='../hasil-scrapping/Biodiesel_Fix.xlsx'):
    try:
        df = pd.read_excel(filename, engine="openpyxl")
        if df.empty or 'Bulan HIP' not in df.columns:
            print("File Excel kosong atau kolom 'Bulan HIP' tidak ada, asumsikan scraping awal")
            return None
        df = df[df['Bulan HIP'].notna()]
        if df.empty:
            print("Tidak ada data Bulan HIP, asumsikan scraping awal")
            return None
        months_map = {
            'Januari': 1, 'Februari': 2, 'Maret': 3, 'April': 4,
            'Mei': 5, 'Juni': 6, 'Juli': 7, 'Agustus': 8,
            'September': 9, 'Oktober': 10, 'November': 11, 'Desember': 12
        }
        def parse_bulan_hip(bulan_str):
            try:
                parts = bulan_str.strip().split()
                if len(parts) >= 2:
                    month_name = parts[0]
                    year = int(parts[-1])  
                    month = months_map.get(month_name)
                    if month and year:
                        return pd.Timestamp(year=year, month=month, day=1)
            except:
                pass
            return None
        df['parsed_bulan_hip'] = df['Bulan HIP'].apply(parse_bulan_hip)
        df = df[df['parsed_bulan_hip'].notna()]
        if df.empty:
            print("Tidak bisa parse Bulan HIP, asumsikan scraping awal")
            return None
        last_date = df['parsed_bulan_hip'].max()
        last_month = last_date.month
        last_year = last_date.year
        now = datetime.now()
        current_month = now.month
        current_year = now.year
        diff = (current_year - last_year) * 12 + (current_month - last_month)
        
        if diff <= 0:
            print(f"Data sudah up-to-date (bulan terakhir: {last_month}/{last_year})")
            return 0
        month_names_id = {
            1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
            5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
            9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
        }
        last_bulan_hip = df.loc[df['parsed_bulan_hip'] == last_date, 'Bulan HIP'].iloc[0]
        print(f"Bulan HIP terakhir di file: {last_bulan_hip}")
        print(f"Bulan sekarang: {month_names_id[current_month]} {current_year}")
        print(f"Selisih: {diff} bulan")
        return diff
    except FileNotFoundError:
        print("File Excel tidak ditemukan, asumsikan scraping awal")
        return None
    except Exception as e:
        print(f"Error membaca file: {e}")
        print("Asumsikan scraping awal")
        return None

def extract_pdf_url_from_html(html_content):
    if not html_content:
        return None
    match = re.search(r'href=["\']([^"\']*drive\.esdm\.go\.id[^"\']*)["\']', html_content)
    if match:
        return match.group(1)
    return None

def scrape_biodiesel_articles_api(excel_filename='../hasil-scrapping/Biodiesel_Fix.xlsx'):
    missing_months = get_missing_months_from_excel(excel_filename)
    if missing_months == 0:
        print("Tidak ada artikel baru yang perlu diambil")
        return [], missing_months
    elif missing_months is None:
        print("File kosong, ambil semua artikel")
        length = 200 
    else:
        max_articles_per_month = 10
        length = missing_months * max_articles_per_month
        print(f"Target: {length} artikel ({missing_months} bulan)")
    base_api_url = "https://ebtke.esdm.go.id/api/api/artikel"
    api_url = f"{base_api_url}?kategori_slug=pengumuman&start=0&length={length}&is_published=true"
    print(f"\nMengambil {length} artikel dari API...")
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        json_data = response.json()
        if 'data' not in json_data or not json_data['data']:
            print("Tidak ada data")
            return [], missing_months
        articles = json_data['data']
        print(f"Berhasil ambil {len(articles)} artikel dari API")
        data = []
        for article in articles:
            title = article.get('judul', '').strip()
            if matches_biodiesel_criteria(title):
                date_str = article.get('tanggal_publikasi') or article.get('tgl_upload', '')
                article_date = date_str
                slug = article.get('slug', '')
                article_url = f"https://ebtke.esdm.go.id/artikel/pengumuman/{slug}"
                konten = article.get('konten', '')
                pdf_url = extract_pdf_url_from_html(konten)
                data.append({
                    "Judul": title,
                    "url": article_url,
                    "Date": article_date,
                    "konten": konten,
                    "pdf_url": pdf_url
                })
        print(f"{len(data)} artikel biodiesel ditemukan")
        unique_data = []
        seen_keys = set()
        for item in data:
            key = (item.get("Judul"), item.get("Date"))
            if key not in seen_keys:
                seen_keys.add(key)
                unique_data.append(item)
        if len(unique_data) < len(data):
            print(f"Setelah deduplikasi: {len(unique_data)} artikel")
        return unique_data, missing_months
    except requests.exceptions.RequestException as e:
        print(f"Error API: {e}")
        return [], missing_months

def download_pdf(url, filename):
    try:
        if not url.startswith('http'):
            url = 'https://' + url
        if 'drive.esdm.go.id' in url and 'download' not in url:
            url = url + '&mode=list&download=1' if '?' in url else url + '?download=1'
        response = requests.get(url, stream=True, timeout=30)
        if 'application/pdf' not in response.headers.get('content-type', '').lower():
            return False
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"Error download: {e}")
        return False

def scrape_and_download_pdfs(data, missing_months):
    pdf_links = []
    if missing_months == 0:
        print("Tidak ada artikel baru, semua data sudah lengkap.")
        return pdf_links
    elif missing_months is None:
        print("Scraping awal: ambil semua artikel yang tersedia.")
        filtered_data = data
    else:
        filtered_data = data[:missing_months]
        print(f"Menargetkan {len(filtered_data)} artikel terbaru (untuk {missing_months} bulan hilang).")
    for item in tqdm(filtered_data, desc="Mencari file PDF"):
        pdf_url = item.get('pdf_url')
        if not pdf_url:
            print(f"\nTidak ada PDF URL: {item['Judul'][:50]}...")
            continue
        filename = f"HIP_BBN_{item['Date']}.pdf".replace(":", "-")
        if download_pdf(pdf_url, filename):
            item["pdf_filename"] = filename
            pdf_links.append(item)
        else:
            print(f"\nGagal mendownload PDF dari {pdf_url}")
        time.sleep(0.3)
    return pdf_links

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
            try:
                os.remove(pdf_file)
                print(f"PDF dihapus: {pdf_file}")
            except Exception as e:
                print(f"Gagal menghapus {pdf_file}: {e}")
    return excel_data

def save_to_excel(data, filename='../hasil-scrapping/Biodiesel_Fix.xlsx'):
    if not data:
        print("Tidak ada data baru untuk disimpan")
        return None
    
    folder = os.path.dirname(filename)
    if folder:
        os.makedirs(folder, exist_ok=True)
    
    new_df = pd.DataFrame(data)
    new_df['HIP Biodiesel IDR/L'] = new_df['HIP Biodiesel IDR/L'].apply(
        lambda x: str(x).strip().replace('.', ',')
    )
    new_df['Date'] = pd.to_datetime(new_df['Date'], errors='coerce')
    
    if os.path.exists(filename):
        try:
            existing_df = pd.read_excel(filename)
            existing_df['Date'] = pd.to_datetime(existing_df['Date'], errors='coerce')
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        except Exception as e:
            print("File existing corrupt, buat file baru:", e)
            combined_df = new_df
    else:
        combined_df = new_df
    
    combined_df = combined_df.drop_duplicates(subset=['Bulan HIP'], keep='last')
    combined_df = combined_df.sort_values(by='Date', ascending=True)
    combined_df['Date'] = combined_df['Date'].dt.strftime('%Y-%m-%d')

    try:
        combined_df.to_excel(filename, index=False)
        print(f"\nData saved to: {filename}")
        print(f"Total rows: {len(combined_df)} (sorted ascending by Date)")
        return combined_df
    except Exception as e:
        print(f"Error saving to Excel: {e}")
        return None

if __name__ == "__main__":
    print("="*60)
    print("SCRAPER HIP BBN BIODIESEL (API VERSION)")
    print("="*60)
    data, missing_months = scrape_biodiesel_articles_api()
    if not data:
        print("\nTidak ada data untuk diproses")
    else:
        print(f"\nTotal artikel biodiesel: {len(data)}")
        pdf_links = scrape_and_download_pdfs(data, missing_months)
        if not pdf_links:
            print("\nTidak ada PDF yang berhasil didownload")
        else:
            excel_data = parse_all_pdfs(pdf_links)
            if not excel_data:
                print("\nTidak ada data HIP yang berhasil di-extract")
            else:
                df = save_to_excel(excel_data)
                print("\n" + "="*60)
                print("SELESAI!")
                print("="*60)