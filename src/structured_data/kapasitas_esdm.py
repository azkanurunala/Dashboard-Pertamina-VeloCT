import os
import sys
import requests
import pandas as pd
from io import BytesIO
from openpyxl import load_workbook
from dotenv import load_dotenv
import traceback
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from helpers.onedrive_helper import (
    get_access_token,
    download_excel_from_onedrive,
    upload_excel_to_onedrive
)

load_dotenv()

ONEDRIVE_FILE_PATH = os.getenv("ONEDRIVE_DATA_PATH", "/results/(Terstruktur)Data Scraping.xlsx")
API_URL = "https://ebtke.esdm.go.id/api/api/konten/data-angka"
SHEET_NAME = "(Data)Kapasitas_EBT"

def convert_month_to_number(month_name):
    month_mapping = {
        'January': 1,
        'February': 2,
        'March': 3,
        'April': 4,
        'May': 5,
        'June': 6,
        'July': 7,
        'August': 8,
        'September': 9,
        'October': 10,
        'November': 11,
        'December': 12
    }
    return month_mapping.get(month_name, month_name)

def fetch_ebtke_data():
    print("Mengambil data kapasitas pembangkit EBT...")
    try:
        response = requests.get(API_URL, timeout=30)
        if response.status_code == 200:
            data = response.json()
            kapasitas_data = data.get('data', {}).get('dataAngkaKapasitasPembangkit', {})
            if not kapasitas_data:
                print("Data kapasitas pembangkit tidak ditemukan di response API")
                return None
            bulan = convert_month_to_number(kapasitas_data.get('bulan'))
            row_data = {
                'tahun': kapasitas_data.get('tahun'),
                'bulan': bulan,
                'plta': kapasitas_data.get('plta'),
                'pltm': kapasitas_data.get('pltm'),
                'pltmh': kapasitas_data.get('pltmh'),
                'pltp': kapasitas_data.get('pltp'),
                'plts': kapasitas_data.get('plts'),
                'plts_atap': kapasitas_data.get('plts_atap'),
                'pltb': kapasitas_data.get('pltb'),
                'pltbm': kapasitas_data.get('pltbm'),
                'pltbg': kapasitas_data.get('pltbg'),
                'pltsa': kapasitas_data.get('pltsa'),
                'pltbn': kapasitas_data.get('pltbn'),
                'plt_hybrid': kapasitas_data.get('plt_hybrid'),
                'total': kapasitas_data.get('total'),
            }
            df = pd.DataFrame([row_data])
            print(f"Data berhasil diambil:")
            return df
        else:
            print(f"Gagal mengambil data. Status code: {response.status_code}")
            return None     
    except requests.exceptions.RequestException as e:
        print(f"Error saat request ke API: {e}")
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"Error tidak terduga: {e}")
        traceback.print_exc()
        return None
    
def check_data_exists_in_onedrive(access_token, tahun: int, bulan: str):
    try:
        excel_buffer = download_excel_from_onedrive(access_token, ONEDRIVE_FILE_PATH)
        if excel_buffer is None:
            print(f"File belum ada di OneDrive")
            return False
        excel_buffer.seek(0)
        wb = load_workbook(excel_buffer)
        if SHEET_NAME not in wb.sheetnames:
            print(f"Sheet '{SHEET_NAME}' belum ada")
            wb.close()
            return False
        ws = wb[SHEET_NAME]
        tahun_col = None
        bulan_col = None
        for col in range(1, ws.max_column + 1):
            header = ws.cell(1, col).value
            if header == 'tahun':
                tahun_col = col
            elif header == 'bulan':
                bulan_col = col
        if tahun_col is None or bulan_col is None:
            print("Kolom 'tahun' atau 'bulan' tidak ditemukan")
            wb.close()
            return False
        for row in range(2, ws.max_row + 1):
            row_tahun = ws.cell(row, tahun_col).value
            row_bulan = ws.cell(row, bulan_col).value
            if row_tahun == tahun and row_bulan == bulan:
                print(f"Data tahun {tahun} bulan {bulan} sudah ada di OneDrive")
                wb.close()
                return True
        print(f"Data tahun {tahun} bulan {bulan} belum ada")
        wb.close()
        return False
    except Exception as e:
        print(f"Error saat cek data: {e}")
        traceback.print_exc()
        return False
    
def merge_data(df_existing, df_new):
    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    if 'tahun' in df_combined.columns and 'bulan' in df_combined.columns:
        df_combined = df_combined.drop_duplicates(subset=['tahun', 'bulan'], keep='last')
    if 'tahun' in df_combined.columns:
        df_combined['tahun'] = pd.to_numeric(df_combined['tahun'], errors='coerce')
        df_combined = df_combined.sort_values(['tahun', 'bulan'], ascending=[True, True])
    print(f"Data setelah merge: {len(df_combined)} rows")
    return df_combined

def save_to_onedrive(access_token, df_new):
    if df_new is None or df_new.empty:
        print("Tidak ada data untuk disimpan")
        return
    excel_buffer = download_excel_from_onedrive(access_token, ONEDRIVE_FILE_PATH)
    output_buffer = BytesIO()
    try:
        if excel_buffer is None:
            with pd.ExcelWriter(output_buffer, engine='openpyxl', mode='w') as writer:
                df_new.to_excel(writer, sheet_name=SHEET_NAME, index=False)
            print(f"Sheet '{SHEET_NAME}' dibuat dengan {len(df_new)} rows")
        else:
            print("File ditemukan di OneDrive, merging data...\n")
            excel_buffer.seek(0)
            wb = load_workbook(excel_buffer)
            visible_sheets = [s for s in wb.worksheets if s.sheet_state == 'visible']
            if len(visible_sheets) == 0:
                wb.worksheets[0].sheet_state = 'visible'
                wb.active = 0
            if SHEET_NAME in wb.sheetnames:
                ws = wb[SHEET_NAME]
                headers = []
                for col in range(1, ws.max_column + 1):
                    headers.append(ws.cell(1, col).value)
                existing_data = []
                for row in range(2, ws.max_row + 1):
                    row_data = []
                    for col in range(1, ws.max_column + 1):
                        row_data.append(ws.cell(row, col).value)
                    existing_data.append(row_data)
                df_existing = pd.DataFrame(existing_data, columns=headers)
                print(f"Data existing: {len(df_existing)} rows")
                print(f"Data baru: {len(df_new)} rows")
                df_merged = merge_data(df_existing, df_new)
                del wb[SHEET_NAME]
                ws = wb.create_sheet(SHEET_NAME)
                for col_idx, col_name in enumerate(df_merged.columns, 1):
                    ws.cell(row=1, column=col_idx, value=col_name)
                for row_idx, row_data in enumerate(df_merged.values, 2):
                    for col_idx, value in enumerate(row_data, 1):
                        ws.cell(row=row_idx, column=col_idx, value=value)
                print(f"Merged: total {len(df_merged)} rows\n")
            else:
                print(f"Sheet '{SHEET_NAME}' belum ada, membuat baru...\n")
                ws = wb.create_sheet(SHEET_NAME)
                for col_idx, col_name in enumerate(df_new.columns, 1):
                    ws.cell(row=1, column=col_idx, value=col_name)
                for row_idx, row_data in enumerate(df_new.values, 2):
                    for col_idx, value in enumerate(row_data, 1):
                        ws.cell(row=row_idx, column=col_idx, value=value)
            wb.save(output_buffer)
            wb.close()
        output_buffer.seek(0)
        verify_wb = load_workbook(output_buffer)
        for sheet_name in verify_wb.sheetnames:
            ws = verify_wb[sheet_name]
        verify_wb.close()
        output_buffer.seek(0)
        print(f"Uploading ke OneDrive: {ONEDRIVE_FILE_PATH}")
        upload_excel_to_onedrive(access_token, ONEDRIVE_FILE_PATH, output_buffer)
    except Exception as e:
        print(f"\nError saat menyimpan data: {e}")
        traceback.print_exc()

def main_ebtke_scraper():
    try:
        access_token = get_access_token()
        print("Authentication successful\n")
    except Exception as e:
        print(f"Authentication failed: {e}")
        return
    df_new = fetch_ebtke_data()
    if df_new is None or df_new.empty:
        print("\nTidak ada data yang berhasil diambil")
        return
    tahun = df_new.iloc[0]['tahun']
    bulan = df_new.iloc[0]['bulan']
    data_exists = check_data_exists_in_onedrive(access_token, tahun, bulan)
    
    if data_exists:
        print(f"\nData tahun {tahun} bulan {bulan} sudah ada di OneDrive")
    save_to_onedrive(access_token, df_new)

if __name__ == "__main__":
    main_ebtke_scraper()