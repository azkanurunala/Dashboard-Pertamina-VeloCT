import os
import sys
import requests
import pandas as pd
from io import BytesIO
from openpyxl import load_workbook
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from helpers.onedrive_helper import (
    get_access_token,
    download_excel_from_onedrive,
    upload_excel_to_onedrive
)

load_dotenv()

ONEDRIVE_FILE_PATH = os.getenv("ONEDRIVE_DATA_PATH", "/results/(Terstruktur)Data Scrapping.xlsx")
API_URL = "https://sipsn.kemenlh.go.id/sipsn/public/home/ajax_list"
SHEET_MAPPING = {
    'sumber': '(Data)WTE_Sumber',
    'komposisi': '(Data)WTE_Komposisi',
    'timbulan': '(Data)WTE_Timbulan'
}

def clean_column_names(df):
    rename_dict = {
        'nama_dati2': 'Nama Kota/Kabupaten',
        'nama_propinsi': 'Nama Provinsi'
    }
    df.rename(columns=rename_dict, inplace=True)
    return df

def fetch_all_data(tahun: str = '2025'):
    jenis_list = ['sumber', 'komposisi', 'timbulan']
    all_data = {}
    for jenis in jenis_list:
        print(f"Mengambil data {jenis}...")
        payload = {
            'length': '-1',
            'jenis': jenis,
            'tahun': tahun,
        }
        response = requests.post(API_URL, data=payload)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data['data'])
            df = clean_column_names(df)
            all_data[jenis] = df
            print(f"Data {jenis}: {len(df)} records")
        else:
            print(f"Gagal ambil data {jenis}: {response.status_code}")
    return all_data

def save_to_onedrive(access_token, data_dict: dict):
    print("\nMenyimpan hasil ke OneDrive...")
    if not data_dict or all(df.empty for df in data_dict.values()):
        print("Tidak ada data untuk disimpan")
        return
    excel_buffer = download_excel_from_onedrive(access_token, ONEDRIVE_FILE_PATH)
    output_buffer = BytesIO()
    try:
        if excel_buffer is None:
            print("File tidak ada di OneDrive, membuat file baru...")
            with pd.ExcelWriter(output_buffer, engine='openpyxl', mode='w') as writer:
                for jenis, df in data_dict.items():
                    sheet_name = SHEET_MAPPING[jenis]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    print(f"  - Sheet '{sheet_name}': {len(df)} rows")
        else:
            print("File ditemukan di OneDrive, updating sheets...")
            excel_buffer.seek(0)
            wb = load_workbook(excel_buffer)
            visible_sheets = [s for s in wb.worksheets if s.sheet_state == 'visible']
            if len(visible_sheets) == 0:
                wb.worksheets[0].sheet_state = 'visible'
                wb.active = 0
            for jenis, df in data_dict.items():
                sheet_name = SHEET_MAPPING[jenis]
                if sheet_name in wb.sheetnames:
                    del wb[sheet_name]
                ws = wb.create_sheet(sheet_name)
                for col_idx, col_name in enumerate(df.columns, 1):
                    ws.cell(row=1, column=col_idx, value=col_name)
                for row_idx, row_data in enumerate(df.values, 2):
                    for col_idx, value in enumerate(row_data, 1):
                        ws.cell(row=row_idx, column=col_idx, value=value)
                print(f"  - Sheet '{sheet_name}': {len(df)} rows")
            wb.save(output_buffer)
            wb.close()
        output_buffer.seek(0)
        verify_wb = load_workbook(output_buffer)
        print(f"\nVerifikasi - Sheets di buffer: {verify_wb.sheetnames}")
        verify_wb.close()
        output_buffer.seek(0)
        print(f"\nUploading ke OneDrive: {ONEDRIVE_FILE_PATH}")
        upload_excel_to_onedrive(access_token, ONEDRIVE_FILE_PATH, output_buffer)
        
        print("Upload selesai!")
        print(f"Saved to OneDrive: {ONEDRIVE_FILE_PATH}")
    except Exception as e:
        print(f"Error saving to OneDrive: {e}")
        import traceback
        traceback.print_exc()

def main_sipsn_scraper():
    print("\nAuthenticating to Microsoft Graph API...")
    try:
        access_token = get_access_token()
        print("Authentication successful\n")
    except Exception as e:
        print(f"Authentication failed: {e}")
        return
    data_dict = fetch_all_data(tahun='2025')
    if data_dict:
        save_to_onedrive(access_token, data_dict)
    else:
        print("\nTidak ada data yang berhasil diambil")

if __name__ == "__main__":
    main_sipsn_scraper()