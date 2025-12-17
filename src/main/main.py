import pandas as pd
import time
from datetime import datetime
import sys
import os
import re
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import json

# ============================================================================
# GOOGLE SHEETS AUTHENTICATION
# ============================================================================

def get_gspread_client():
    """
    Connect to Google Sheets using Service Account
    
    Setup:
    1. Enable Google Sheets API di Google Cloud Console
    2. Create Service Account
    3. Download JSON credentials
    4. Share your Google Sheet with service account email
    """
    
    # Check if credentials in env (for GitHub Actions)
    creds_json = os.getenv('GOOGLE_CREDENTIALS')
    
    if creds_json:
        # From GitHub Secrets (JSON string)
        print("📋 Using GOOGLE_CREDENTIALS from environment")
        creds_dict = json.loads(creds_json)
        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
    else:
        # From local file - check multiple possible locations
        possible_paths = [
            'credentials.json',
            os.path.join(os.path.dirname(__file__), 'credentials.json'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'credentials.json')
        ]
        
        creds_file = None
        for path in possible_paths:
            if os.path.exists(path):
                creds_file = path
                break
        
        if not creds_file:
            raise Exception(
                "\n❌ No credentials.json found!\n"
                "\n📝 Make sure credentials.json is in one of:\n"
                "   - Project root folder\n"
                "   - scrapper/main_scrapper/ folder\n"
                "\n   Download from: https://console.cloud.google.com\n"
                "   Service Account → Keys → Add Key → JSON\n"
            )
        
        print(f"📋 Using credentials from: {creds_file}")
        credentials = Credentials.from_service_account_file(
            creds_file,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
    
    client = gspread.authorize(credentials)
    print("✅ Connected to Google Sheets")
    return client

# ============================================================================
# SCRAPING MODULES
# ============================================================================

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from code_scrapping.bisnis_indonesia import main_bisnis_indonesia
from code_scrapping.kompas import main_kompas
from code_scrapping.tempo import scrape_tempo
from code_scrapping.cnn import scrape_cnn_international 
from code_scrapping.kontan_bbm import scrape_kontan_bbm
from code_scrapping.kontan_biodiesel import scrape_kontan_biodiesel
from code_scrapping.kontan import scrape_kontan
from code_scrapping.cnbc_id import main_cnbc
from code_scrapping.cnbc import scrape_cnbc_international
from code_scrapping.oilprice import scrape_oilprice
from code_scrapping.bloomberg_technoz import main_bloomberg_technoz

# ============================================================================
# GOOGLE SHEETS OPERATIONS
# ============================================================================

def read_worksheet_gsheet(worksheet):
    """Read data from Google Sheets worksheet"""
    try:
        data = worksheet.get_all_values()
        if not data or len(data) <= 1:
            return pd.DataFrame()
        
        headers = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=headers)
        return df
    except Exception as e:
        print(f"⚠️  Error reading worksheet: {e}")
        return pd.DataFrame()

def write_worksheet_gsheet(worksheet, df):
    """Write data to Google Sheets worksheet"""
    try:
        # Clear existing data
        worksheet.clear()
        
        # Prepare data
        headers = df.columns.tolist()
        values = [headers] + df.values.tolist()
        
        # Convert all to strings and handle NaN
        values = [[str(cell) if pd.notna(cell) else "" for cell in row] for row in values]
        
        # Write to sheet
        worksheet.update('A1', values)
        
        print(f"✅ Successfully wrote {len(df)} rows")
        return True
    except Exception as e:
        print(f"❌ Error writing to worksheet: {e}")
        return False

def get_or_create_worksheet(spreadsheet, sheet_name):
    """Get existing worksheet or create new one"""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        print(f"📄 Found existing sheet: {sheet_name}")
        return worksheet
    except gspread.exceptions.WorksheetNotFound:
        print(f"📝 Creating new sheet: {sheet_name}")
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
        return worksheet

# ============================================================================
# SCRAPING LOGIC (SAMA SEPERTI SEBELUMNYA)
# ============================================================================

sinonim_dict = {
    "indeks risiko geopolitik": ["tekanan geopolitik", "geopolitical risk", "geopolitical pressure"],
    "indeks volatilitas": ["volatility index"],
    "kurs": ["nilai tukar rupiah"],
    "ihsg": ["pasar saham"],
    "inflasi": ["inflation"],
    "bi rate": ["suku bunga", "bunga bi"],
    "jibor": ["jakarta interbank offered rate"],
    "indeks sales retail": ["indeks penjualan ritel", "indeks penjualan retail", "indeks retail", "indeks ritel"],
    "indeks kepercayaan konsumen": ["indeks kepercayaan pelanggan"],
    "indeks kinerja manufaktur": ["purchasing manufaktur index"],
    "indeks kinerja jasa": ["purchasing services index"],
    "neraca perdagangan": ["trade balance"],
    "pertumbuhan domestik bruto": ["PDB", "pertumbuhan ekonomi"],
    "bioenergi": ["minyak kelapa sawit", "crude palm oil", "CPO", "minyak sawit", "kelapa sawit", "sawit", 
                  "HIP BBN Biodesel","biodiesel", "harga fame", "harga indeks pasar biodiesel", "b40", "b50", "biodiesel", "biofuel"],
    "harga minyak" : ["oil price", "minyak mentah","crude oil"], 
    "volume minyak" : ["volume bbm", "oil volume", "minyak mentah", "volume minyak"], 
    "harga produk kilang pertamina" : ["bbm","harga kilang pertamina", "kilang pertamina", "kilang", "refinery", "harga pertamina"], 
    "volume produk kilang pertamina" : ["bbm", "volume kilang pertamina", "volume kilang", "refinery", "volume pertamina"]
}

sumber_dict = {
    "indeks risiko geopolitik": [scrape_cnn_international, scrape_cnbc_international],
    "indeks volatilitas": [scrape_cnn_international, scrape_cnbc_international],
    "kurs": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "ihsg": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "inflasi": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "bi rate": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "jibor": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "indeks sales retail": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "indeks kepercayaan konsumen": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "indeks kinerja manufaktur": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "indeks kinerja jasa": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "neraca perdagangan": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "pertumbuhan domestik bruto": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "bioenergi": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    "harga minyak" : [scrape_kontan_bbm, main_bisnis_indonesia, scrape_oilprice, main_bloomberg_technoz], 
    "volume minyak" : [scrape_kontan_bbm, main_bisnis_indonesia, scrape_oilprice, main_bloomberg_technoz], 
    "harga produk kilang pertamina" : [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    "volume produk kilang pertamina" : [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz]
}

def clean_date(date_str):
    if pd.isna(date_str) or date_str == "N/A" or date_str == "-":
        return "N/A"
    date_str = str(date_str).strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    if 'T' in date_str or ' ' in date_str:
        date_str = date_str.split('T')[0].split(' ')[0]
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    return "N/A"

def standardize_format(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["title", "date", "url", "content", "source", "keyword"])
    column_mapping = {
        'Judul': 'title', 'judul': 'title', 'Title': 'title',
        'Tanggal': 'date', 'tanggal': 'date', 'Date': 'date',
        'Link': 'url', 'link': 'url', 'URL': 'url',
        'Konten': 'content', 'konten': 'content', 'Content': 'content',
    }
    df = df.rename(columns=column_mapping)
    required_columns = ["title", "date", "url", "content"]
    for col in required_columns:
        if col not in df.columns:
            df[col] = "N/A"
    df['date'] = df['date'].apply(clean_date)
    column_order = ["title", "date", "url", "content", "source", "keyword"]
    existing_cols = [col for col in column_order if col in df.columns]
    df = df[existing_cols]
    return df

def scrape_keyword(keyword, tanggal_filter):
    hasil_final = pd.DataFrame()
    semua_keyword = [keyword] + sinonim_dict.get(keyword, [])
    sumber = sumber_dict.get(keyword, [main_kompas, main_bisnis_indonesia, scrape_tempo, scrape_kontan])
    
    for kata in semua_keyword:
        print(f"\n📌 Scraping keyword: '{kata}'")
        hasil_list = []
        
        for scrape_func in sumber:
            nama_sumber = scrape_func.__name__.replace("scrape_", "").replace("main_", "").upper()
            print(f"   🔍 Scraping from {nama_sumber}...")
            try:
                data = scrape_func(kata, tanggal_filter)
                if data is not None and len(data) > 0:
                    df_temp = pd.DataFrame(data)
                    df_temp["source"] = nama_sumber
                    df_temp = standardize_format(df_temp)
                    hasil_list.append(df_temp)
                    print(f"   ✅ Found {len(df_temp)} articles from {nama_sumber}")
                else:
                    print(f"   ⚠️  No articles from {nama_sumber}")
            except Exception as e:
                print(f"   ❌ Failed scraping {nama_sumber}: {e}")
        
        if hasil_list:
            df_temp_keyword = pd.concat(hasil_list, ignore_index=True)
            df_temp_keyword["keyword"] = kata
            hasil_final = pd.concat([hasil_final, df_temp_keyword], ignore_index=True)
    
    if hasil_final.empty:
        hasil_final = pd.DataFrame(columns=["title", "date", "url", "content", "source", "keyword"])
    
    return hasil_final

sheet_to_keyword = {
    "(News)indeks risiko geopolitik": "indeks risiko geopolitik",
    "(News)indeks volatilitas": "indeks volatilitas",
    "(News)Kurs": "kurs",
    "(News)IHSG": "ihsg",
    "(News)Inflasi": "inflasi",
    "(News)BI Rate": "bi rate",
    "(News)JIBOR": "jibor",
    "(News)indeks sales retail": "indeks sales retail",
    "(News)indeks kepercayaan knsmn": "indeks kepercayaan konsumen",
    "(News)indeks kinerja manufaktur": "indeks kinerja manufaktur",
    "(News)indeks kinerja jasa": "indeks kinerja jasa",
    "(News)neraca perdagangan": "neraca perdagangan",
    "(News)PDB": "pertumbuhan domestik bruto",
    "(News)Bioenergi": "bioenergi",
    "(News)Harga Minyak": "harga minyak",
    "(News)Volume Minyak" : "volume minyak",
    "(News)Harga Produk Kilang" : "harga produk kilang pertamina", 
    "(News)Volume Produk Kilang" : "volume produk kilang pertamina"
}

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    print("\n" + "=" * 80)
    print("🚀 NEWS SCRAPER TO GOOGLE SHEETS")
    print("=" * 80)
    
    # Load environment
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    
    # Configuration
    tanggal_filter = os.getenv('TANGGAL_FILTER', '2025-12-01')
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    
    print(f"\n📊 Configuration:")
    print(f"   Spreadsheet ID: {spreadsheet_id[:20]}..." if spreadsheet_id else "   ❌ SPREADSHEET_ID not found!")
    print(f"   Date Filter: {tanggal_filter}")
    print(f"   Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not spreadsheet_id:
        print("\n❌ ERROR: SPREADSHEET_ID not found in .env!")
        print("\n📝 To get SPREADSHEET_ID:")
        print("   1. Open your Google Sheet")
        print("   2. Look at the URL:")
        print("      https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit")
        print("   3. Copy the SPREADSHEET_ID part")
        print("   4. Add to .env: SPREADSHEET_ID=<paste_here>")
        return
    
    # Connect to Google Sheets
    try:
        print("\n🔗 Connecting to Google Sheets...")
        client = get_gspread_client()
        spreadsheet = client.open_by_key(spreadsheet_id)
        print(f"✅ Connected to: {spreadsheet.title}")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\n💡 Common issues:")
        print("   - Credentials not found or invalid")
        print("   - Sheet not shared with service account email")
        print("   - Wrong SPREADSHEET_ID")
        return
    
    # Sheet names
    sheet_names = [
        "(News)indeks risiko geopolitik",
        "(News)indeks volatilitas",
        "(News)Kurs",
        "(News)IHSG",
        "(News)Inflasi",
        "(News)BI Rate",
        "(News)JIBOR",
        "(News)indeks sales retail",
        "(News)indeks kepercayaan knsmn",
        "(News)indeks kinerja manufaktur",
        "(News)indeks kinerja jasa",
        "(News)neraca perdagangan",
        "(News)PDB",
        "(News)Bioenergi",
        "(News)Harga Minyak",
        "(News)Volume Minyak",
        "(News)Harga Produk Kilang", 
        "(News)Volume Produk Kilang"
    ]
    
    # Process each sheet
    total = len(sheet_names)
    success_count = 0
    
    for idx, sheet_name in enumerate(sheet_names, 1):
        keyword_asli = sheet_to_keyword.get(sheet_name)
        if not keyword_asli:
            print(f"\n⚠️  Keyword not found for '{sheet_name}'. Skipping.")
            continue
        
        print(f"\n{'='*80}")
        print(f"📄 SHEET {idx}/{total}: {sheet_name}")
        print(f"🔑 Keyword: {keyword_asli.upper()}")
        print(f"{'='*80}")
        
        # Scrape data
        hasil_df = scrape_keyword(keyword_asli, tanggal_filter)
        print(f"\n📊 Scraping result: {len(hasil_df)} new articles")
        
        try:
            # Get or create worksheet
            worksheet = get_or_create_worksheet(spreadsheet, sheet_name)
            
            # Read existing data
            print(f"📖 Reading existing data...")
            existing_df = read_worksheet_gsheet(worksheet)
            
            if not existing_df.empty:
                combined_df = pd.concat([existing_df, hasil_df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['url'], keep='first')
                print(f"✅ Combined data: {len(combined_df)} total rows")
            else:
                combined_df = hasil_df
                print(f"📝 New worksheet, no existing data")
            
            # Write to Google Sheets
            print(f"💾 Writing data to Google Sheets...")
            success = write_worksheet_gsheet(worksheet, combined_df)
            
            if success:
                print(f"✅ SUCCESS! {len(combined_df)} articles saved")
                success_count += 1
            else:
                raise Exception("Write failed")
                
        except Exception as e:
            print(f"❌ Error processing sheet: {e}")
            # Save backup locally
            local_filename = f"backup_{sheet_name}.xlsx"
            combined_df.to_excel(local_filename, index=False)
            print(f"💾 Backup saved: {local_filename}")
        
        # Rate limiting - Google Sheets has quotas
        if idx < total:
            print(f"\n⏳ Waiting 5 seconds before next sheet...")
            time.sleep(5)
    
    print(f"\n{'='*80}")
    print(f"🎉 SCRAPING COMPLETE!")
    print(f"{'='*80}")
    print(f"   Total sheets: {total}")
    print(f"   Successful: {success_count}")
    print(f"   Failed: {total - success_count}")
    print(f"   End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n💡 Next steps:")
    print(f"   1. Open your Google Sheet to verify data")
    print(f"   2. Copy to Excel locally if needed")
    print(f"   3. Setup GitHub Actions for automation")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()