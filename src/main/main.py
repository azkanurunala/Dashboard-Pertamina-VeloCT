import pandas as pd
import time
from datetime import datetime, timedelta
import sys
import os
import re
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import json

def get_gspread_client():
    creds_json = os.getenv('GOOGLE_CREDENTIALS')
    if creds_json:
        print("Using GOOGLE_CREDENTIALS from environment")
        creds_dict = json.loads(creds_json)
        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
    else:
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
                "   - src/main/ folder\n"
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
        worksheet.clear()
        
        headers = df.columns.tolist()
        values = [headers] + df.values.tolist()
        
        values = [[str(cell) if pd.notna(cell) else "" for cell in row] for row in values]
        
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
# DATE RANGE GENERATOR
# ============================================================================

def generate_date_range(start_date, end_date):
    """Generate list of dates between start and end"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    return dates

# ============================================================================
# SCRAPING LOGIC
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
    "kurs": [main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "ihsg": [main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "inflasi": [main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "bi rate": [main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "jibor": [main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "indeks sales retail": [main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "indeks kepercayaan konsumen": [main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "indeks kinerja manufaktur": [main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "indeks kinerja jasa": [main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "neraca perdagangan": [main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "pertumbuhan domestik bruto": [main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
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
    sumber = sumber_dict.get(keyword, [main_kompas, main_bisnis_indonesia, scrape_tempo])
    
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
# MAIN FUNCTION WITH DATE RANGE
# ============================================================================

def main():
    print("\n" + "=" * 80)
    print("🚀 NEWS SCRAPER TO GOOGLE SHEETS (DATE RANGE)")
    print("=" * 80)
    
    # Load environment
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    
    # Configuration - support single date or range
    start_date = os.getenv('START_DATE')
    end_date = os.getenv('END_DATE')
    single_date = os.getenv('TANGGAL_FILTER')
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    
    # Determine date range
    if start_date and end_date:
        date_list = generate_date_range(start_date, end_date)
        print(f"\n📅 Date Range Mode: {start_date} to {end_date}")
    elif single_date:
        date_list = [single_date]
        print(f"\n📅 Single Date Mode: {single_date}")
    else:
        date_list = [datetime.now().strftime('%Y-%m-%d')]
        print(f"\n📅 Default Mode: Today ({date_list[0]})")
    
    print(f"   Spreadsheet ID: {spreadsheet_id[:20]}..." if spreadsheet_id else "   ❌ SPREADSHEET_ID not found!")
    print(f"   Total dates to process: {len(date_list)}")
    print(f"   Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not spreadsheet_id:
        print("\n❌ ERROR: SPREADSHEET_ID not found in .env!")
        return
    
    # Connect to Google Sheets
    try:
        print("\n🔗 Connecting to Google Sheets...")
        client = get_gspread_client()
        spreadsheet = client.open_by_key(spreadsheet_id)
        print(f"✅ Connected to: {spreadsheet.title}")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
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
    
    # Statistics
    total_sheets = len(sheet_names)
    total_dates = len(date_list)
    total_tasks = total_sheets * total_dates
    completed_tasks = 0
    failed_tasks = 0
    total_articles = 0
    start_time = datetime.now()
    
    # Process each date
    for date_idx, tanggal in enumerate(date_list, 1):
        print(f"\n" + "=" * 80)
        print(f"📅 DATE {date_idx}/{total_dates}: {tanggal}")
        print(f"=" * 80)
        
        # Process each sheet
        for sheet_idx, sheet_name in enumerate(sheet_names, 1):
            keyword_asli = sheet_to_keyword.get(sheet_name)
            if not keyword_asli:
                print(f"\n⚠️  Keyword not found for '{sheet_name}'. Skipping.")
                continue
            
            print(f"\n[{date_idx}/{total_dates}] [{sheet_idx}/{total_sheets}] {sheet_name}")
            print(f"🔑 Keyword: {keyword_asli.upper()}")
            print(f"📅 Date: {tanggal}")
            
            try:
                # Scrape data for this date
                hasil_df = scrape_keyword(keyword_asli, tanggal)
                articles_found = len(hasil_df)
                print(f"\n📊 Found: {articles_found} articles")
                
                # Get or create worksheet
                worksheet = get_or_create_worksheet(spreadsheet, sheet_name)
                
                # Read existing data
                existing_df = read_worksheet_gsheet(worksheet)
                
                if not existing_df.empty:
                    combined_df = pd.concat([existing_df, hasil_df], ignore_index=True)
                    combined_df = combined_df.drop_duplicates(subset=['url'], keep='first')
                    new_articles = len(combined_df) - len(existing_df)
                    print(f"✅ Combined: {len(combined_df)} total ({new_articles} new)")
                else:
                    combined_df = hasil_df
                    new_articles = articles_found
                    print(f"📝 New worksheet: {len(combined_df)} articles")
                
                # Write to Google Sheets
                success = write_worksheet_gsheet(worksheet, combined_df)
                
                if success:
                    completed_tasks += 1
                    total_articles += new_articles
                    print(f"✅ SUCCESS!")
                else:
                    raise Exception("Write failed")
                    
            except Exception as e:
                failed_tasks += 1
                print(f"❌ Error: {e}")
                # Save backup
                backup_filename = f"backup_{sheet_name}_{tanggal}.xlsx"
                if 'combined_df' in locals() and not combined_df.empty:
                    combined_df.to_excel(backup_filename, index=False)
                    print(f"💾 Backup saved: {backup_filename}")
            
            # Progress
            progress = ((date_idx - 1) * total_sheets + sheet_idx) / total_tasks * 100
            print(f"\n📈 Overall Progress: {progress:.1f}% ({completed_tasks}/{total_tasks} tasks)")
            
            # Rate limiting
            time.sleep(3)
        
        # Delay between dates
        if date_idx < total_dates:
            print(f"\n⏳ Waiting 10 seconds before next date...")
            time.sleep(10)
    
    # Final summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    print(f"\n" + "=" * 80)
    print(f"🎉 SCRAPING COMPLETE!")
    print(f"=" * 80)
    print(f"   Dates processed: {total_dates}")
    print(f"   Sheets processed: {total_sheets}")
    print(f"   Total tasks: {total_tasks}")
    print(f"   Successful: {completed_tasks}/{total_tasks} ({completed_tasks/total_tasks*100:.1f}%)")
    print(f"   Failed: {failed_tasks}/{total_tasks}")
    print(f"   New articles added: {total_articles}")
    print(f"   Duration: {duration}")
    print(f"   Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   End: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n💡 Next steps:")
    print(f"   1. Open your Google Sheet to verify data")
    print(f"   2. Check for any backup files if there were errors")
    print(f"=" * 80 + "\n")

if __name__ == "__main__":
    main()