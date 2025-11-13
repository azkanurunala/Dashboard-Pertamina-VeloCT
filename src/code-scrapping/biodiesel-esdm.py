import requests
import pandas as pd
import time
import re
import os
import pdfplumber
from datetime import datetime
from tqdm import tqdm

def parse_date(date_str):
    """Convert Indonesian date format to YYYY-MM-DD"""
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
    """Check if article title matches biodiesel criteria"""
    keywords = ["HIP", "BBN", "JENIS", "BIODIESEL", "BULAN"]
    return all(keyword in title.upper() for keyword in keywords)

def safe_read_excel(filename):
    """Safely read Excel file with multiple fallback strategies"""
    if not os.path.exists(filename):
        print(f"⚠️  File tidak ditemukan: {filename}")
        return None
    
    file_size = os.path.getsize(filename)
    print(f"📊 Ukuran file: {file_size} bytes")
    
    # Strategy 1: Try openpyxl (XLSX standard)
    try:
        print("🔄 Mencoba baca dengan openpyxl...")
        df = pd.read_excel(filename, engine='openpyxl')
        print(f"✅ Berhasil! {len(df)} baris")
        return df
    except Exception as e1:
        print(f"❌ openpyxl gagal: {type(e1).__name__}")
    
    # Strategy 2: Try xlrd (old XLS)
    try:
        print("🔄 Mencoba baca dengan xlrd (XLS format)...")
        df = pd.read_excel(filename, engine='xlrd')
        print(f"✅ Berhasil dengan xlrd! {len(df)} baris")
        
        # Convert to proper XLSX
        print("🔄 Mengkonversi ke XLSX format...")
        backup_xls = filename.replace('.xlsx', f'_XLS_BACKUP_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xls')
        os.rename(filename, backup_xls)
        print(f"✓ Backup XLS: {backup_xls}")
        
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"✅ Dikonversi ke XLSX!")
        return df
    except Exception as e2:
        print(f"❌ xlrd gagal: {type(e2).__name__}")
    
    # Strategy 3: Try reading as CSV (last resort)
    try:
        print("🔄 Mencoba baca sebagai CSV...")
        df = pd.read_csv(filename.replace('.xlsx', '.csv'))
        print(f"✅ Berhasil dengan CSV! {len(df)} baris")
        return df
    except Exception as e3:
        print(f"❌ CSV gagal: {type(e3).__name__}")
    
    # All strategies failed - file is corrupt
    print("❌ Semua metode gagal, file corrupt!")
    backup_name = filename.replace('.xlsx', f'_CORRUPT_{datetime.now().strftime("%Y%m%d_%H%M%S")}.bak')
    try:
        import shutil
        shutil.move(filename, backup_name)
        print(f"✓ File corrupt dipindahkan ke: {backup_name}")
    except Exception as e:
        print(f"⚠️  Gagal backup: {e}")
    
    return None

def get_missing_months_from_excel(filename='../hasil-scrapping/Data Terstruktur.xlsx'):
    """Calculate how many months of data are missing"""
    
    # Pastikan folder ada
    folder = os.path.dirname(filename)
    if folder and not os.path.exists(folder):
        print(f"📁 Membuat folder: {folder}")
        os.makedirs(folder, exist_ok=True)
    
    abs_path = os.path.abspath(filename)
    print(f"🔍 File path: {abs_path}")
    
    # Use safe read function
    df = safe_read_excel(filename)
    
    if df is None:
        print("💡 Membuat file baru...")
        df_new = pd.DataFrame(columns=['Date', 'Bulan HIP', 'HIP Biodiesel IDR/L'])
        
        # Save with openpyxl (more reliable)
        try:
            df_new.to_excel(filename, index=False, engine='openpyxl')
            print(f"✅ File baru berhasil dibuat!")
        except Exception as e:
            print(f"❌ Gagal membuat file: {e}")
        
        return None
    
    if df.empty or 'Date' not in df.columns:
        print("📭 File Excel kosong")
        return None
    
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    last_date = df['Date'].max()
    
    if pd.isna(last_date):
        print("📭 Tidak ada tanggal valid")
        return None
    
    last_month = last_date.month
    last_year = last_date.year
    now = datetime.now()
    current_month = now.month
    current_year = now.year
    
    diff = (current_year - last_year) * 12 + (current_month - last_month)
    
    if diff <= 0:
        print(f"✅ Data sudah up-to-date (terakhir: {last_month}/{last_year})")
        return 0
    
    print(f"📅 Terakhir: {last_month}/{last_year}, Sekarang: {current_month}/{current_year}")
    print(f"⏳ Selisih: {diff} bulan")
    return diff

def scrape_biodiesel_articles_api(excel_filename='../hasil-scrapping/Data Terstruktur.xlsx'):
    """Scrape articles using API instead of Selenium"""
    missing_months = get_missing_months_from_excel(excel_filename)
    
    if missing_months == 0:
        print("✅ Tidak ada artikel baru yang perlu diambil")
        return [], missing_months
    elif missing_months is None:
        print("🔄 File kosong/corrupt, ambil semua artikel")
        max_articles = 9999
        length = 200  # Ambil banyak sekaligus untuk scraping awal
    else:
        max_articles_per_month = 10
        max_articles = missing_months * max_articles_per_month
        length = min(max_articles, 200)  # Max 200 per request
        print(f"🎯 Target: {max_articles} artikel ({missing_months} bulan)")
    
    data = []
    start = 0
    base_api_url = "https://ebtke.esdm.go.id/api/api/artikel"
    
    print(f"\n🔄 Mengambil data dari API (length={length})...")
    
    while len(data) < max_articles or missing_months is None:
        # Hitung berapa artikel yang masih dibutuhkan
        remaining = max_articles - len(data) if missing_months is not None else 200
        current_length = min(remaining, length) if missing_months is not None else length
        
        api_url = f"{base_api_url}?kategori_slug=pengumuman&start={start}&length={current_length}&is_published=true"
        
        try:
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
            json_data = response.json()
            
            if 'data' not in json_data or not json_data['data']:
                print(f"✓ Tidak ada data lagi di start={start}")
                break
            
            articles = json_data['data']
            biodiesel_count = 0
            for article in articles:
                title = article.get('judul', '').strip()
                
                if matches_biodiesel_criteria(title):
                    date_str = article.get('tanggal_publikasi') or article.get('created_at', '')
                    article_date = parse_date(date_str) if date_str else None
                    
                    slug = article.get('slug', '')
                    article_url = f"https://ebtke.esdm.go.id/artikel/pengumuman/{slug}"
                    
                    data.append({
                        "Judul": title,
                        "url": article_url,
                        "Date": article_date,
                        "konten": article.get('konten', '')
                    })
                    biodiesel_count += 1
            
            if biodiesel_count > 0:
                print(f"  ✓ {biodiesel_count} artikel biodiesel ditemukan")
            
            # Stop jika sudah cukup
            if missing_months is not None and len(data) >= max_articles:
                print(f"✓ Target tercapai: {len(data)} artikel")
                break
            
            # Stop jika response lebih kecil dari request (akhir data)
            if len(articles) < current_length:
                print(f"✓ Mencapai akhir data (artikel < {current_length})")
                break
            
            start += current_length
            time.sleep(0.3)  # Reduced delay karena request lebih sedikit
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error API: {e}")
            break
    
    # Remove duplicates
    unique_data = []
    seen_keys = set()
    for item in data:
        key = (item.get("Judul"), item.get("Date"))
        if key not in seen_keys:
            seen_keys.add(key)
            unique_data.append(item)
    
    print(f"\n✓ Total artikel: {len(data)}")
    print(f"✓ Setelah deduplikasi: {len(unique_data)}")
    
    return unique_data, missing_months

def find_pdf_link_in_content(konten):
    """Extract PDF link from article content (HTML)"""
    try:
        matches = re.findall(r'href=["\']([^"\']*drive\.esdm\.go\.id[^"\']*)["\']', konten)
        if matches:
            return matches[0]
        
        matches = re.findall(r'href=["\']([^"\']*\.pdf[^"\']*)["\']', konten, re.IGNORECASE)
        if matches:
            return matches[0]
        
        return None
    except Exception as e:
        print(f"Error extracting PDF link: {e}")
        return None

def download_pdf(url, filename):
    """Download PDF file"""
    try:
        if 'drive.esdm.go.id' in url and 'download' not in url:
            url = url + '&mode=list&download=1' if '?' in url else url + '?download=1'
        
        response = requests.get(url, stream=True, timeout=30)
        
        if 'application/pdf' not in response.headers.get('content-type', '').lower():
            print(f"  ✗ Bukan PDF: {response.headers.get('content-type')}")
            return False
        
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        print(f"  ✓ Downloaded: {filename}")
        return True
    except Exception as e:
        print(f"  ✗ Error download: {e}")
        return False

def scrape_and_download_pdfs(data, missing_months):
    """Download PDFs from articles"""
    pdf_links = []
    
    if missing_months == 0:
        print("✅ Tidak ada artikel baru")
        return pdf_links
    elif missing_months is None:
        print("🔄 Scraping awal: ambil semua")
        filtered_data = data
    else:
        filtered_data = data[:missing_months]
        print(f"🎯 Menargetkan {len(filtered_data)} artikel terbaru")
    
    print("\n📥 Mengunduh PDF...")
    
    for item in tqdm(filtered_data, desc="Download PDF"):
        print(f"\n=== {item['Judul'][:60]}... ===")
        
        pdf_url = find_pdf_link_in_content(item.get('konten', ''))
        
        if not pdf_url:
            print("  ✗ Link PDF tidak ditemukan")
            continue
        
        print(f"  📄 PDF: {pdf_url}")
        
        item["pdf_url"] = pdf_url
        filename = f"HIP_BBN_{item['Date']}.pdf".replace(":", "-")
        
        if download_pdf(pdf_url, filename):
            item["pdf_filename"] = filename
            pdf_links.append(item)
        
        time.sleep(0.5)
    
    return pdf_links

def find_hip_value_and_month_in_table(table):
    """Extract HIP value and month from PDF table"""
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
                            hip_value = match.group(1)
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
    """Extract HIP value from PDF"""
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
    """Parse all downloaded PDFs"""
    excel_data = []
    
    print("\n📊 Parsing PDF...")
    
    for item in pdf_links:
        pdf_file = item.get('pdf_filename')
        if not pdf_file or not os.path.exists(pdf_file):
            print(f"✗ PDF tidak ada: {pdf_file}")
            continue
        
        print(f"\n  📄 Parsing {pdf_file}")
        
        hip_per_liter, hip_month = extract_hip_from_pdf(pdf_file)
        date_artikel = item.get('Date', None)
        
        if hip_per_liter:
            print(f"  ✓ HIP: {hip_per_liter}")
            if hip_month:
                print(f"  ✓ Bulan: {hip_month}")
            print(f"  ✓ Date: {date_artikel}")
            
            excel_data.append({
                'Date': date_artikel,
                'Bulan HIP': hip_month,
                'HIP Biodiesel IDR/L': hip_per_liter
            })
            
            try:
                os.remove(pdf_file)
                print(f"  🗑️  PDF dihapus")
            except Exception as e:
                print(f"  ✗ Gagal hapus: {e}")
    
    return excel_data

def save_to_excel(data, filename='../hasil-scrapping/Data Terstruktur.xlsx'):
    """Save data to Excel file - FIXED VERSION"""
    if not data:
        print("⚠️  Tidak ada data baru")
        return None
    
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
    
    new_df = pd.DataFrame(data)
    new_df['HIP Biodiesel IDR/L'] = (new_df['HIP Biodiesel IDR/L']
                                      .apply(lambda x: str(x).strip().replace('.', ',')))
    new_df['Date'] = pd.to_datetime(new_df['Date'])
    
    # Try to read existing file
    existing_df = safe_read_excel(filename)
    
    if existing_df is not None and not existing_df.empty:
        print(f"📂 File existing: {len(existing_df)} baris")
        
        existing_df['Date'] = pd.to_datetime(existing_df['Date'], errors='coerce')
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df.drop_duplicates(
            subset=['Date', 'Bulan HIP'],
            keep='last',
            inplace=True
        )
        combined_df.sort_values('Date', ascending=True, inplace=True)
        
        print(f"📊 Data gabungan: {len(combined_df)} baris")
    else:
        print("📂 Membuat file baru")
        combined_df = new_df
    
    combined_df['Date'] = combined_df['Date'].dt.strftime('%Y-%m-%d')
    
    # CRITICAL FIX: Use openpyxl consistently!
    print(f"💾 Menyimpan dengan openpyxl engine...")
    
    try:
        # Direct save with openpyxl (no temp file needed)
        combined_df.to_excel(filename, index=False, engine='openpyxl')
        print(f"✅ Data disimpan: {filename}")
        
        # Verify
        print(f"🔍 Verifying...")
        test_df = pd.read_excel(filename, engine='openpyxl')
        print(f"✅ Verified OK: {len(test_df)} rows")
        
        return combined_df
        
    except Exception as e:
        print(f"❌ Error saving: {e}")
        
        # Fallback: try with xlsxwriter
        print(f"🔄 Mencoba dengan xlsxwriter...")
        try:
            combined_df.to_excel(filename, index=False, engine='xlsxwriter')
            print(f"✅ Berhasil dengan xlsxwriter!")
            return combined_df
        except Exception as e2:
            print(f"❌ xlsxwriter juga gagal: {e2}")
            return None

# Main execution
if __name__ == "__main__":
    print("="*60)
    print("🚀 SCRAPER HIP BBN BIODIESEL (FIXED VERSION)")
    print("="*60)
    
    # Step 1: Scrape articles
    data, missing_months = scrape_biodiesel_articles_api()
    print(f"\n✅ Total artikel: {len(data)}")
    
    if data:
        for item in data[:5]:
            print(f"  • {item['Date']} - {item['Judul'][:60]}...")
        if len(data) > 5:
            print(f"  ... dan {len(data)-5} lainnya")
    
    # Step 2: Download PDFs
    pdf_links = scrape_and_download_pdfs(data, missing_months)
    print(f"\n✅ PDF downloaded: {len(pdf_links)}")
    
    # Step 3: Parse PDFs
    excel_data = parse_all_pdfs(pdf_links)
    
    # Step 4: Save to Excel
    df = save_to_excel(excel_data)
    
    print("\n" + "="*60)
    print("✅ SELESAI!")
    print("="*60)