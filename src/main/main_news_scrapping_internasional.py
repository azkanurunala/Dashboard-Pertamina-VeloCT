import pandas as pd
import time
from datetime import datetime, timedelta
import sys
import os
import re
from dotenv import load_dotenv


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from helpers.onedrive_helper import (
    get_access_token,
    read_excel_sheet_from_onedrive,
    write_multiple_sheets_to_onedrive, 
    download_excel_from_onedrive 
)

from code_scrapping.cnn import main_google_news_cnn
from code_scrapping.cnbc import main_google_news_cnbc
from code_scrapping.oilprice import scrape_oilprice
from code_scrapping.scrape_sandp_news import scrape_news_sap

load_dotenv()

ONEDRIVE_FILE_PATH = os.getenv("ONEDRIVE_FILE_PATH", "/results/(News)Scrapping.xlsx")

sinonim_dict = {
    "indeks risiko geopolitik": ["tekanan geopolitik", "geopolitical risk", "geopolitical pressure"],
    "indeks volatilitas": ["volatility index"],
    "indeks kinerja manufaktur": ["purchasing manufaktur index"],
    "indeks kinerja jasa": ["purchasing services index"],
    "harga minyak": ["oil price", "minyak mentah","crude oil"],
    "volume minyak": ["volume bbm", "oil volume", "minyak mentah", "volume minyak"],
    "SAF" : ["UCO ", "sustainable aviation fuel ", "used cooking oil ", "CORSIA ", "SAFCo ", "biorefinery ", "minyak jelantah ", "bioavtur "]
}

sumber_dict = {
    "indeks risiko geopolitik": [main_google_news_cnn, main_google_news_cnbc],
    "indeks volatilitas": [main_google_news_cnn, main_google_news_cnbc],
    "indeks kinerja manufaktur": [scrape_news_sap],
    "indeks kinerja jasa": [scrape_news_sap],
    "harga minyak": [scrape_oilprice],
    "volume minyak": [scrape_oilprice], 
    "SAF" : [scrape_news_sap, main_google_news_cnbc, main_google_news_cnn]
}

sheet_to_keyword = {
    "(News)indeks risiko geopolitik": "indeks risiko geopolitik",
    "(News)indeks volatilitas": "indeks volatilitas",
    "(News)indeks kinerja manufaktur": "indeks kinerja manufaktur",
    "(News)indeks kinerja jasa": "indeks kinerja jasa",  
    "(News)Harga Minyak": "harga minyak",
    "(News)Volume Minyak": "volume minyak",
    "(News)SAF" : "SAF"
    
}

def standardize_format(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["title", "date", "url", "content", "source", "keyword"])
    
    column_mapping = {
        'Judul': 'title',
        'judul': 'title',
        'Title': 'title',
        'Tanggal': 'date',
        'tanggal': 'date',
        'Date': 'date',
        'Link': 'url',
        'link': 'url',
        'URL': 'url',
        'Konten': 'content',
        'konten': 'content',
        'Content': 'content',
    }
    
    df = df.rename(columns=column_mapping)
    
    required_columns = ["title", "date", "url", "content"]
    for col in required_columns:
        if col not in df.columns:
            df[col] = "N/A"
    
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
    
    df['date'] = df['date'].apply(clean_date)
    
    column_order = ["title", "date", "url", "content", "source", "keyword"]
    existing_cols = [col for col in column_order if col in df.columns]
    df = df[existing_cols]
    
    return df


def scrape_keyword(keyword, tanggal_filter):
    hasil_final = pd.DataFrame()
    semua_keyword = [keyword] + sinonim_dict.get(keyword, [])
    sumber = sumber_dict.get(keyword)
    
    for kata in semua_keyword:
        print(f"\nMencoba scraping dengan kata kunci: '{kata}'")
        hasil_list = []
        
        for scrape_func in sumber:
            nama_sumber = scrape_func.__name__.replace("scrape_", "").replace("main_", "").upper()
            source_mapping = {
                "KONTAN_BBM": "KONTAN",
                "KONTAN_BIODIESEL": "KONTAN",
                "GOOGLE_NEWS_CNN": "CNN",
                "GOOGLE_NEWS_CNBC": "CNBC",
                "NEWS_SAP": "S&P"
            }
            nama_sumber = source_mapping.get(nama_sumber, nama_sumber)
            print(f"Scraping dari {nama_sumber}...")
            
            try:
                data = scrape_func(kata, tanggal_filter)
                if data is not None and len(data) > 0:
                    df_temp = pd.DataFrame(data)
                    df_temp["source"] = nama_sumber
                    df_temp = standardize_format(df_temp)
                    hasil_list.append(df_temp)
                    print(f"Dapat {len(df_temp)} berita dari {nama_sumber}.")
                else:
                    print(f"Tidak ada berita dari {nama_sumber}.")
            except Exception as e:
                print(f"Gagal scrape {nama_sumber}: {e}")
        
        if hasil_list:
            df_temp_keyword = pd.concat(hasil_list, ignore_index=True)
            df_temp_keyword["keyword"] = kata
            hasil_final = pd.concat([hasil_final, df_temp_keyword], ignore_index=True)
    
    if hasil_final.empty:
        hasil_final = pd.DataFrame(columns=["title", "date", "url", "content", "source", "keyword"])
    
    return hasil_final


def main():
    print("\n" + "="*60)
    print("NEWS SCRAPING TO ONEDRIVE")
    print("="*60)
    
    print("\nAuthenticating to Microsoft Graph API...")
    try:
        access_token = get_access_token()
        print("Authentication successful")
    except Exception as e:
        print(f"Authentication failed: {e}")
        return
    
    # tanggal_filter = "2025-12-3"
    tanggal_filter = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"\nTanggal filter: {tanggal_filter}")
    
    sheet_names = [
        "(News)indeks risiko geopolitik",
        "(News)indeks volatilitas",
        "(News)indeks kinerja manufaktur",
        "(News)indeks kinerja jasa",
        "(News)Harga Minyak",
        "(News)Volume Minyak",
        "(News)SAF"
    ]
    
    print(f"\nLoading existing data from OneDrive...")
    print(f"File: {ONEDRIVE_FILE_PATH}")

    excel_buffer = download_excel_from_onedrive(access_token, ONEDRIVE_FILE_PATH)
    
    all_sheets = {}
    if excel_buffer is None:
        print("File tidak ditemukan, akan membuat file baru")
        for sheet_name in sheet_names:
            all_sheets[sheet_name] = pd.DataFrame()
    else:
        print("File ditemukan, membaca semua sheets...")
        
        excel_buffer.seek(0)
        
        excel_file = pd.ExcelFile(excel_buffer)
        
        for sheet_name in sheet_names:
            try:
                if sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    all_sheets[sheet_name] = df
                    print(f"  Sheet '{sheet_name}': {len(df)} baris")
                else:
                    print(f"  Sheet '{sheet_name}': tidak ada, akan dibuat baru")
                    all_sheets[sheet_name] = pd.DataFrame()
            except Exception as e:
                print(f"  Sheet '{sheet_name}': error - {e}, akan dibat baru")
                all_sheets[sheet_name] = pd.DataFrame()
        
        excel_file.close()
    
    print("\n" + "="*60)
    print("MULAI SCRAPING")
    print("="*60)
    
    for sheet_name in sheet_names:
        keyword_asli = sheet_to_keyword.get(sheet_name)
        if not keyword_asli:
            print(f"Keyword untuk sheet '{sheet_name}' tidak ditemukan di mapping. Lewati.")
            continue
        
        print(f"\n{'-'*60}")
        print(f"{sheet_name}")
        print(f"Keyword: {keyword_asli}")
        print(f"{'-'*60}")
        
        hasil_df = scrape_keyword(keyword_asli, tanggal_filter)
        
        if sheet_name in all_sheets and not all_sheets[sheet_name].empty:
            combined_df = pd.concat([all_sheets[sheet_name], hasil_df], ignore_index=True)
            print(f"\n  Data existing: {len(all_sheets[sheet_name])} baris")
            print(f"  Data baru: {len(hasil_df)} baris")
        else:
            combined_df = hasil_df
            print(f"\n  Data baru: {len(hasil_df)} baris")
        
        all_sheets[sheet_name] = combined_df
        print(f"  Total: {len(combined_df)} baris")
        
        print("\nIstirahat 60 detik...")
        time.sleep(60)
    
    print("\n" + "="*60)
    print("MENYIMPAN KE ONEDRIVE")
    print("="*60)
    
    try:
        write_multiple_sheets_to_onedrive(access_token, ONEDRIVE_FILE_PATH, all_sheets)
        
        print("\n" + "="*60)
        print("SELESAI!")
        print(f"File: {ONEDRIVE_FILE_PATH}")
        print(f"Total sheets: {len(sheet_names)}")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\nError saat menyimpan: {e}")
        raise

if __name__ == "__main__":
    main() 