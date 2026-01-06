import requests
import pandas as pd
import json
import os
import sys
from dotenv import load_dotenv
from io import BytesIO
from openpyxl import load_workbook
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from helpers.onedrive_helper import (
    get_access_token,
    download_excel_from_onedrive,
    upload_excel_to_onedrive
)

load_dotenv()

ONEDRIVE_FILE_PATH = os.getenv("ONEDRIVE_DATA_PATH", "/results/(Terstruktur)Data Scrapping.xlsx")
SHEET_NAME = "(Data)SAF"

def load_tokens(token_file_path="../token.json"):
    try:
        with open(token_file_path, 'r') as f:
            token_data = json.load(f)
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')
            print("Token berhasil dimuat dari file")
            return access_token, refresh_token
    except FileNotFoundError:
        print(f"File {token_file_path} tidak ditemukan")
        return None, None
    except json.JSONDecodeError:
        print(f"Error membaca JSON dari {token_file_path}")
        return None, None

def save_tokens(token_data, token_file_path="../token.json"):
    try:
        with open(token_file_path, 'w') as f:
            json.dump(token_data, f, indent=2)
            print("Token baru berhasil disimpan")
        return True
    except Exception as e:
        print(f"Error menyimpan token: {e}")
        return False

def refresh_access_token(refresh_token, token_file_path="../token.json"):
    url = "https://api.ci.spglobal.com/auth/api/refresh"
    payload = {
        "refresh_token": refresh_token
    }
    try:
        print("Memperbarui access token...")
        print(f"Refresh token: {refresh_token[:20]}...")
        response = requests.post(url, data=payload, timeout=30)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        response.raise_for_status()
        token_data = response.json()
        new_access_token = token_data.get('access_token')
        new_refresh_token = token_data.get('refresh_token', refresh_token)
        save_tokens(token_data, token_file_path)
        print("Access token berhasil diperbarui")
        return new_access_token, new_refresh_token
    except requests.exceptions.RequestException as e:
        print(f"Error saat refresh token: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        return None, None

def get_historical_data(access_token, symbols, start_date, end_date, fields=None):
    if fields is None:
        fields = ["UOM", "Currency", "description"]
    url = "https://api.ci.spglobal.com/market-data/v3/value/history/symbol"
    symbols_str = ",".join([f'"{s}"' for s in symbols])
    filter_query = f'symbol IN ({symbols_str}) AND assessDate>"{start_date}" AND assessDate<"{end_date}"'
    params = {
        "Field": ",".join(fields),
        "Filter": filter_query,
        "PageSize" : 2000
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    try:
        print(f"Mengambil data historis dari {start_date} hingga {end_date}...")
        print(f"\nDEBUG - Request details:")
        print(f"  URL: {url}")
        print(f"  Params: {params}")
        print(f"  Filter: {filter_query}")
        response = requests.get(url, params=params, headers=headers, timeout=60)
        print(f"\nDEBUG - Response:")
        print(f"  Status: {response.status_code}")
        print(f"  Full URL: {response.url}")
        response.raise_for_status()
        data = response.json()
        flat_data = []
        if data and isinstance(data, dict) and 'results' in data:
            results = data['results']
            print(f"Total symbols ditemukan: {len(results)}")
            if len(results) > 0:
                first_item = results[0]
                print(f"\nDEBUG - Item pertama:")
                print(f"  Symbol: {first_item.get('symbol')}")
                print(f"  Keys: {list(first_item.keys())}")
                print(f"  referenceData: {first_item.get('referenceData')}")
            for item in results:
                symbol = item.get('symbol', '')
                reference_data = item.get('referenceData', {})
                currency = reference_data.get('currency', '')
                description = reference_data.get('description', '')
                uom = reference_data.get('uom', '')
                data_list = item.get('data', [])
                for data_point in data_list:
                    assess_date = data_point.get('assessDate', '')
                    mod_date = data_point.get('modDate', '')
                    if assess_date and 'T' in assess_date:
                        assess_date = assess_date.split('T')[0]
                    flat_data.append({
                        'symbol': symbol,
                        'assessDate': assess_date,
                        'value': data_point.get('value', ''),
                        'modDate': mod_date
                    })
        if not flat_data:
            print("Tidak ada data yang ditemukan")
            return None
        df = pd.DataFrame(flat_data)
        if 'value' in df.columns:
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
        print(f"Berhasil mengambil {len(df)} baris data")
        return df
    except requests.exceptions.RequestException as e:
        print(f"Error saat mengambil data: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return None

def get_current_data(access_token, symbols, fields=None):
    url = "https://api.ci.spglobal.com/market-data/v3/value/current/symbol"
    symbols_str = ",".join([f'"{s}"' for s in symbols])
    filter_query = f'symbol IN ({symbols_str})'
    params = {
        "Field": ",".join(fields),
        "Filter": filter_query
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    try:
        print(f"Mengambil data current untuk symbols: {symbols}")
        print(f"\nDEBUG - Request details:")
        print(f"  URL: {url}")
        print(f"  Params: {params}")
        print(f"  Filter: {filter_query}")
        response = requests.get(url, params=params, headers=headers, timeout=60)
        print(f"\nDEBUG - Response:")
        print(f"  Status: {response.status_code}")
        print(f"  Full URL: {response.url}")
        response.raise_for_status()
        data = response.json()
        flat_data = []
        if data and isinstance(data, dict) and 'results' in data:
            results = data['results']
            print(f"Total symbols ditemukan: {len(results)}")
            for item in results:
                symbol = item.get('symbol', '')
                data_list = item.get('data', [])
                for data_point in data_list:
                    assess_date = data_point.get('assessDate', '')
                    mod_date = data_point.get('modDate', '')
                    if assess_date and 'T' in assess_date:
                        assess_date = assess_date.split('T')[0]
                    flat_data.append({
                        'symbol': symbol,
                        'assessDate': assess_date,
                        'value': data_point.get('value', ''),
                        'modDate': mod_date
                    })
        if not flat_data:
            print("Tidak ada data yang ditemukan")
            return None
        df = pd.DataFrame(flat_data)
        if 'value' in df.columns:
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
        print(f"Berhasil mengambil {len(df)} baris data (sebelum drop duplicate)")
        if 'assessDate' in df.columns and 'modDate' in df.columns:
            df = df.sort_values('modDate', ascending=False)
            df = df.drop_duplicates(subset=['symbol', 'assessDate'], keep='first')
            print(f"Setelah drop duplicate: {len(df)} baris data")
        print("\nSample data:")
        print(df.head(3))
        return df
    except requests.exceptions.RequestException as e:
        print(f"Error saat mengambil data: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return None
    
def pivot_data_to_columns(df):
    symbol_map = {
        'UCFCC00': 'UCO',
        'SFSMR00': 'SAF'
    }
    df['suffix'] = df['symbol'].map(symbol_map)
    df_value = df.pivot_table(
        index='assessDate',
        columns='suffix',
        values='value',
        aggfunc='first'
    ).reset_index()
    df_value.columns = ['assessDate'] + [f'value_{col}' for col in df_value.columns if col != 'assessDate']
    df_moddate = df.pivot_table(
        index='assessDate',
        columns='suffix',
        values='modDate',
        aggfunc='first'
    ).reset_index()
    df_moddate.columns = ['assessDate'] + [f'modDate_{col}' for col in df_moddate.columns if col != 'assessDate']
    df_final = df_value.merge(df_moddate, on='assessDate', how='outer')
    column_order = ['assessDate', 'value_UCO', 'value_SAF', 'modDate_UCO', 'modDate_SAF']
    for col in column_order:
        if col not in df_final.columns:
            df_final[col] = None
    return df_final[column_order].sort_values('assessDate')

def merge_with_existing_data(df_old, df_new):
    if df_old.empty:
        return df_new
    if df_new.empty:
        return df_old
    for col in ['assessDate', 'value_UCO', 'value_SAF', 'modDate_UCO', 'modDate_SAF']:
        if col not in df_old.columns:
            df_old[col] = None
        if col not in df_new.columns:
            df_new[col] = None
    df_merged = df_old.merge(
        df_new,
        on='assessDate',
        how='outer',
        suffixes=('_old', '_new')
    )
    for symbol in ['UCO', 'SAF']:
        value_col = f'value_{symbol}'
        moddate_col = f'modDate_{symbol}'
        if f'{value_col}_new' in df_merged.columns and f'{value_col}_old' in df_merged.columns:
            df_merged[value_col] = df_merged[f'{value_col}_new'].fillna(df_merged[f'{value_col}_old'])
        elif f'{value_col}_new' in df_merged.columns:
            df_merged[value_col] = df_merged[f'{value_col}_new']
        elif f'{value_col}_old' in df_merged.columns:
            df_merged[value_col] = df_merged[f'{value_col}_old']
        if f'{moddate_col}_new' in df_merged.columns and f'{moddate_col}_old' in df_merged.columns:
            df_merged[moddate_col] = df_merged[f'{moddate_col}_new'].fillna(df_merged[f'{moddate_col}_old'])
        elif f'{moddate_col}_new' in df_merged.columns:
            df_merged[moddate_col] = df_merged[f'{moddate_col}_new']
        elif f'{moddate_col}_old' in df_merged.columns:
            df_merged[moddate_col] = df_merged[f'{moddate_col}_old']
    cols_to_drop = [col for col in df_merged.columns if col.endswith('_old') or col.endswith('_new')]
    df_merged = df_merged.drop(columns=cols_to_drop)
    column_order = ['assessDate', 'value_UCO', 'value_SAF', 'modDate_UCO', 'modDate_SAF']
    df_merged = df_merged[column_order]
    print(f"Data sebelum deduplikasi: {len(df_merged)} baris")
    df_merged = df_merged.drop_duplicates(
        subset=['assessDate', 'value_UCO', 'value_SAF'], 
        keep='last'
    )
    print(f"Data setelah deduplikasi (keep yang baru): {len(df_merged)} baris")
    df_merged = df_merged.sort_values('assessDate', ascending=True).reset_index(drop=True)
    print(f"\n[MERGE] Data berhasil di-merge:")
    print(f"  Data lama: {len(df_old)} rows")
    print(f"  Data baru: {len(df_new)} rows")
    print(f"  Data final: {len(df_merged)} rows")
    return df_merged

def scrape_spglobal_current(symbols=None, fields=None):
    if symbols is None:
        symbols = ["SFSMR00", "UCFCC00"]
    access_token, refresh_token = load_tokens()
    if not access_token or not refresh_token:
        print("Gagal memuat token dari file")
        return None
    df = get_current_data(access_token, symbols, fields)
    if df is None:
        print("Mencoba refresh token...")
        new_access_token, _ = refresh_access_token(refresh_token)
        if new_access_token:
            df = get_current_data(new_access_token, symbols, fields)
        else:
            print("Gagal refresh token")
            return None

def read_sap_sheet_from_onedrive(access_token, file_path, sheet_name):
    excel_buffer = download_excel_from_onedrive(access_token, file_path)
    if excel_buffer is None:
        print(f"! File tidak ditemukan, akan membuat baru")
        return pd.DataFrame()
    try:
        df = pd.read_excel(excel_buffer, sheet_name=sheet_name)
        print(f"Berhasil baca sheet '{sheet_name}', rows={len(df)}")
        return df
    except Exception as e:
        print(f"! Sheet '{sheet_name}' tidak ditemukan, akan membuat baru")
        return pd.DataFrame()

def write_sap_sheet_to_onedrive(access_token, file_path, sheet_name, df_new):
    print(f"\nMenyiapkan file Excel untuk OneDrive...")
    df_old = read_sap_sheet_from_onedrive(access_token, file_path, sheet_name)
    df_final = merge_with_existing_data(df_old, df_new)
    excel_buffer = download_excel_from_onedrive(access_token, file_path)
    output_buffer = BytesIO()
    if excel_buffer is None:
        print("File baru, hanya ada 1 sheet")
        with pd.ExcelWriter(output_buffer, engine='openpyxl', mode='w') as writer:
            df_final.to_excel(writer, sheet_name=sheet_name, index=False)
    else:
        print("File existing, mode update")
        try:
            wb = load_workbook(excel_buffer)
            visible_sheets = [s for s in wb.worksheets if s.sheet_state == 'visible']
            if len(visible_sheets) == 0:
                print("Fixing hidden sheets...")
                wb.worksheets[0].sheet_state = 'visible'
                wb.active = 0
            for sheet in wb.worksheets:
                if sheet.sheet_state != 'visible':
                    sheet.sheet_state = 'visible'
            temp_buffer = BytesIO()
            wb.save(temp_buffer)
            wb.close()
            temp_buffer.seek(0)
            with pd.ExcelWriter(temp_buffer, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                df_final.to_excel(writer, sheet_name=sheet_name, index=False)
            output_buffer = temp_buffer
        except Exception as e:
            print(f"Error saat update: {e}, fallback ke create new")
            with pd.ExcelWriter(output_buffer, engine='openpyxl', mode='w') as writer:
                df_final.to_excel(writer, sheet_name=sheet_name, index=False)
    output_buffer.seek(0)
    print(f"Uploading ke OneDrive: {file_path}")
    upload_excel_to_onedrive(access_token, file_path, output_buffer)
    print("Upload selesai!")

def main_daily():
    symbols = ["SFSMR00", "UCFCC00"]
    fields = ["UOM", "Currency", "description"]
    
    try:
        onedrive_access_token = get_access_token()
        print("OneDrive authentication successful")
    except Exception as e:
        print(f"OneDrive authentication failed: {e}")
        exit(1)
    
    print("\nLoading S&P Global API tokens...")
    spglobal_access_token, spglobal_refresh_token = load_tokens()
    if not spglobal_access_token or not spglobal_refresh_token:
        print("Gagal memuat S&P Global token dari file")
        exit(1)
    print("\n" + "=" * 60)
    print("SCRAPING CURRENT DATA")
    print("=" * 60)
    df_current = get_current_data(spglobal_access_token, symbols, fields)
    if df_current is None:
        print("Mencoba refresh token...")
        new_access_token, _ = refresh_access_token(spglobal_refresh_token)
        if new_access_token:
            df_current = get_current_data(new_access_token, symbols, fields)
        else:
            print("Gagal refresh token untuk current data")
            exit(1)
    if df_current is None:
        print("\n[CURRENT] Gagal mengambil data current")
        exit(1)
    print(f"\n[CURRENT] Data berhasil diambil!")
    print(f"[CURRENT] Total data: {len(df_current)} baris")
    df_pivoted = pivot_data_to_columns(df_current)
    print("\n" + "=" * 60)
    print("MENYIMPAN KE ONEDRIVE")
    print("=" * 60)
    write_sap_sheet_to_onedrive(onedrive_access_token, ONEDRIVE_FILE_PATH, SHEET_NAME, df_pivoted)
    print("\n" + "=" * 60)
    print("DATA BERHASIL DISIMPAN KE ONEDRIVE")
    print("=" * 60)
    print(f"  File: {ONEDRIVE_FILE_PATH}")
    print(f"  Sheet: {SHEET_NAME}")
    print(f"  Format: assessDate | value_UCO | value_SAF | modDate_UCO | modDate_SAF")
    print(f"  Total rows: {len(df_pivoted)}")
    print("\n" + "=" * 60)
    print("SELESAI")
    print("=" * 60)

def main_weekly():
    symbols = ["SFSMR00", "UCFCC00"]
    fields = ["UOM", "Currency", "description"]
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    start_date = "2024-01-01"
    end_date = datetime.today().strftime("%Y-%m-%d")
    try:
        onedrive_access_token = get_access_token()
        print("OneDrive authentication successful")
    except Exception as e:
        print(f"OneDrive authentication failed: {e}")
        exit(1)
    print("\nLoading S&P Global API tokens...")
    spglobal_access_token, spglobal_refresh_token = load_tokens()
    if not spglobal_access_token or not spglobal_refresh_token:
        print("Gagal memuat S&P Global token dari file")
        exit(1)
    print("\n" + "=" * 60)
    print("SCRAPING HISTORICAL DATA (WEEKLY)")
    print("=" * 60)
    print(f"Period: {start_date} to {end_date}")
    df_historical = get_historical_data(spglobal_access_token, symbols, start_date, end_date, fields)
    if df_historical is None:
        print("Mencoba refresh token...")
        new_access_token, _ = refresh_access_token(spglobal_refresh_token)
        if new_access_token:
            df_historical = get_historical_data(new_access_token, symbols, start_date, end_date, fields)
        else:
            print("Gagal refresh token untuk historical data")
            exit(1)
    if df_historical is None:
        print("\n[HISTORICAL] Gagal mengambil data historical")
        exit(1)
    print(f"\n[HISTORICAL] Data berhasil diambil!")
    print(f"[HISTORICAL] Total data: {len(df_historical)} baris")
    df_pivoted = pivot_data_to_columns(df_historical)
    print("\n" + "=" * 60)
    print("MENYIMPAN KE ONEDRIVE")
    print("=" * 60)
    write_sap_sheet_to_onedrive(onedrive_access_token, ONEDRIVE_FILE_PATH, SHEET_NAME, df_pivoted)
    print("\n" + "=" * 60)
    print("DATA BERHASIL DISIMPAN KE ONEDRIVE")
    print("=" * 60)
    print(f"  File: {ONEDRIVE_FILE_PATH}")
    print(f"  Sheet: {SHEET_NAME}")
    print(f"  Format: assessDate | value_UCO | value_SAF | modDate_UCO | modDate_SAF")
    print(f"  Total rows: {len(df_pivoted)}") 
    print("\n" + "=" * 60)
    print("SELESAI")
    print("=" * 60)

if __name__ == "__main__":
    main_daily()