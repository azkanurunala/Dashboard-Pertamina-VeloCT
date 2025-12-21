import pandas as pd
import time
from datetime import datetime, timedelta
import sys
import os
import re 
from io import BytesIO
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from helpers.onedrive_helper import (get_access_token,download_excel_from_onedrive,upload_excel_to_onedrive,read_excel_sheet_from_onedrive)

load_dotenv()
ONEDRIVE_FILE_PATH = os.getenv("ONEDRIVE_FILE_PATH")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from code_scrapping.bisnis_indonesia import main_bisnis_indonesia
from code_scrapping.kompas import main_kompas
from code_scrapping.tempo import scrape_tempo
from code_scrapping.cnn import scrape_cnn_international 
from code_scrapping.kontan_bbm import scrape_kontan_bbm
from code_scrapping.kontan_biodiesel import scrape_kontan_biodiesel
from code_scrapping.kontan import scrape_kontan
from code_scrapping.cnn import scrape_cnn_international
from code_scrapping.cnbc_id import main_cnbc
from code_scrapping.cnbc import scrape_cnbc_international
from code_scrapping.oilprice import scrape_oilprice
from code_scrapping.bloomberg_technoz import main_bloomberg_technoz
from code_scrapping.bps import main_bps


# === SINONIM KEYWORD ===
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
    "bioetanol": ["tebu", "gula", "molase", "etanol", "ethanol", "bioethanol", "tetes tebu"],          
    "harga minyak" : ["oil price", "minyak mentah","crude oil"], 
    "volume minyak" : ["volume bbm", "oil volume", "minyak mentah", "volume minyak"], 
    "harga produk kilang pertamina" : ["bbm","harga kilang pertamina", "kilang pertamina", "kilang", "refinery", "harga pertamina"], 
    "volume produk kilang pertamina" : ["bbm", "volume kilang pertamina", "volume kilang", "refinery", "volume pertamina"]
}

# === PEMETAAN SUMBER PER KEYWORD ===
sumber_dict = {
    "indeks risiko geopolitik": [scrape_cnn_international, scrape_cnbc_international],
    "indeks volatilitas": [scrape_cnn_international, scrape_cnbc_international],
    "kurs": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "ihsg": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "inflasi": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc, main_bps],
    "bi rate": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "jibor": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "indeks sales retail": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "indeks kepercayaan konsumen": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "indeks kinerja manufaktur": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "indeks kinerja jasa": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "neraca perdagangan": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc, main_bps],
    "pertumbuhan domestik bruto": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc, main_bps],
    "bioenergi": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    "bioetanol": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    "harga minyak" : [scrape_kontan_bbm, main_bisnis_indonesia, scrape_oilprice, main_bloomberg_technoz], 
    "volume minyak" : [scrape_kontan_bbm, main_bisnis_indonesia, scrape_oilprice, main_bloomberg_technoz], 
    "harga produk kilang pertamina" : [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    "volume produk kilang pertamina" : [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz]
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
        """Extract YYYY-MM-DD from various date formats"""
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
    sumber = sumber_dict.get(keyword, [main_kompas, main_bisnis_indonesia, scrape_tempo, scrape_kontan])
    for kata in semua_keyword:
        print(f"\nMencoba scraping dengan kata kunci: '{kata}'")
        hasil_list = []
        for scrape_func in sumber:
            nama_sumber = scrape_func.__name__.replace("scrape_", "").replace("main_", "").upper()
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
    "(News)Bioetanol": "bioetanol",
    "(News)Harga Minyak": "harga minyak",
    "(News)Volume Minyak" : "volume minyak",
    "(News)Harga Produk Kilang" : "harga produk kilang pertamina", 
    "(News)Volume Produk Kilang" : "volume produk kilang pertamina"
}

def main():
    print("Melakukan autentikasi ke OneDrive...")
    # DEBUG: Cek environment variables
    print(f"DEBUG - MS_CLIENT_ID: {os.getenv('MS_CLIENT_ID')}")
    print(f"DEBUG - MS_TENANT_ID: {os.getenv('MS_TENANT_ID')}")
    print(f"DEBUG - MS_CLIENT_SECRET: {os.getenv('MS_CLIENT_SECRET')}")
    access_token = get_access_token()
    tanggal_filter = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    # tanggal_filter = "2025-12-04"
    use_onedrive = True
    # UNCOMENT KODE DIBAWAH KALO MAU KESIMPEN DI LOCAL
    # use_onedrive = False
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
                    "(News)Bioetanol",
                   "(News)Harga Minyak",
                   "(News)Volume Minyak",
                   "(News)Harga Produk Kilang", 
                   "(News)Volume Produk Kilang"
                ]
    all_sheets = {}
    if use_onedrive:
        print(f"\nMengunduh file dari OneDrive: {ONEDRIVE_FILE_PATH}")
        excel_buffer = download_excel_from_onedrive(access_token, ONEDRIVE_FILE_PATH)
        if excel_buffer:
            print("\nMemuat existing sheets...")
            with pd.ExcelFile(excel_buffer) as xls:
                for sheet_name in sheet_names:
                    try:
                        all_sheets[sheet_name] = pd.read_excel(xls, sheet_name=sheet_name)
                        print(f"Sheet '{sheet_name}': {len(all_sheets[sheet_name])} baris")
                    except:
                        all_sheets[sheet_name] = pd.DataFrame()
                        print(f"Sheet '{sheet_name}': buat baru")
        else:
            print("\nFile tidak ada di OneDrive, akan membuat file baru")
            for sheet_name in sheet_names:
                all_sheets[sheet_name] = pd.DataFrame()
    
    else:
        # ===== MODE LOCAL (COMMENTED OUT) =====
        # Load existing sheets dari file lokal
        # for sheet_name in sheet_names:
        #     try:
        #         all_sheets[sheet_name] = pd.read_excel(filename, sheet_name=sheet_name)
        #         print(f"Sheet '{sheet_name}': {len(all_sheets[sheet_name])} baris")
        #     except:
        #         all_sheets[sheet_name] = pd.DataFrame()
        #         print(f Sheet '{sheet_name}': buat baru")
        pass

    for sheet_name in sheet_names:
        keyword_asli = sheet_to_keyword.get(sheet_name)
        if not keyword_asli:
            print(f"Keyword untuk sheet '{sheet_name}' tidak ditemukan di mapping. Lewati.")
            continue
        print(f"\n{'='*50}")
        print(f"MULAI SCRAPING UNTUK: {sheet_name.upper()}")
        print(f"Keyword: {keyword_asli.upper()}")
        print(f"{'='*50}")
        hasil_df = scrape_keyword(keyword_asli, tanggal_filter)
        if sheet_name in all_sheets and not all_sheets[sheet_name].empty:
            combined_df = pd.concat([all_sheets[sheet_name], hasil_df], ignore_index=True)
            print(f"\nData existing: {len(all_sheets[sheet_name])} baris")
            print(f"Data baru: {len(hasil_df)} baris")
        else:
            combined_df = hasil_df
            print(f"\nData baru: {len(hasil_df)} baris")
        all_sheets[sheet_name] = combined_df
        print(f"Total berita untuk '{sheet_name}': {len(combined_df)} baris")
        print("Istirahat 1 menit sebelum lanjut...\n")
        time.sleep(60)
    if use_onedrive:
        print("\nMenyimpan semua data ke Excel buffer...")
        output_buffer = BytesIO()
        with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
            for sheet_name, df in all_sheets.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"Simpan sheet '{sheet_name}': {len(df)} baris")
        print(f"\nMengupload file ke OneDrive: {ONEDRIVE_FILE_PATH}")
        upload_excel_to_onedrive(access_token, ONEDRIVE_FILE_PATH, output_buffer)
        print("\n" + "="*50)
        print("SELESAI!")
        print(f"Total sheets diproses: {len(sheet_names)}")
        print(f"File tersimpan di OneDrive: {ONEDRIVE_FILE_PATH}")
        print("="*50)
    
    else:
        # ===== SIMPAN KE LOCAL (COMMENTED OUT) =====
        # Simpan ke file lokal
        # print("\nMenyimpan semua data ke file lokal...")
        # with pd.ExcelWriter(filename, engine='openpyxl', mode='w') as writer:
        #     for sheet_name, df in all_sheets.items():
        #         df.to_excel(writer, sheet_name=sheet_name, index=False)
        #         print(f"Simpan sheet '{sheet_name}': {len(df)} baris")
        # 
        # print("\n" + "="*50)
        # print("SELESAI!")
        # print(f"   Total sheets diproses: {len(sheet_names)}")
        # print(f"   File tersimpan di: {filename}")
        # print("="*50)
        pass


if __name__ == "__main__":
    main()