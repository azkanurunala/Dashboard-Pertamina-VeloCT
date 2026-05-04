import requests
import pandas as pd
import os
import sys
from dotenv import load_dotenv
from io import BytesIO
from openpyxl import load_workbook
from datetime import datetime, timedelta
import tqdm
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from helpers.onedrive_helper import (
    get_access_token,
    download_excel_from_onedrive,
    upload_excel_to_onedrive
)

load_dotenv()

ONEDRIVE_FILE_PATH = os.getenv("ONEDRIVE_DATA_PATH", "/results/(Terstruktur)Data Scraping.xlsx")
SHEET_NAME_SAF = "(Data)SAF"
SP_USERNAME = os.getenv("S&P_USERNAME")
SP_PASSWORD = os.getenv("S&P_PASSWORD")
SHEET_NAME_FORECAST_BBM_LONG = "(Data)Crackspread_BBM_YEAR"
SHEET_NAME_FORECAST_BBM_SHORT = "(Data)Crackspread_BBM"
SHEET_NAME_PETROCHEMICAL = "(Data)Crackspread_NON_BBM"

def login_spglobal(username=None, password=None):
    if username is None:
        username = SP_USERNAME
    if password is None:
        password = SP_PASSWORD
    if not username or not password:
        print("Error: S&P_USERNAME atau S&P_PASSWORD tidak ditemukan di environment variables")
        return None
    url = "https://api.ci.spglobal.com/auth/api"
    payload = {
        "username": username,
        "password": password
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    try:
        print("Login ke S&P Global API...")
        print(f"Username: {username}")
        response = requests.post(url, data=payload, headers=headers, timeout=30)
        print(f"Status code: {response.status_code}")
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data.get('access_token')
        if access_token:
            print("Login berhasil! Access token diperoleh.")
            return access_token
        else:
            print("Login gagal: access_token tidak ditemukan dalam response")
            print(f"Response: {token_data}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error saat login: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        return None

def get_historical_data(access_token, symbols, start_date, end_date, fields=None, page_size=2000):
    if fields is None:
        fields = ["UOM", "Currency", "description"]
    url = "https://api.ci.spglobal.com/market-data/v3/value/history/symbol"
    symbols_str = ",".join([f'"{s}"' for s in symbols])
    filter_query = f'symbol IN ({symbols_str}) AND assessDate>"{start_date}" AND assessDate<"{end_date}"'
    params = {
        "Field": ",".join(fields),
        "Filter": filter_query,
        "PageSize": page_size
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
                data_list = item.get('data', [])
                for data_point in data_list:
                    bate = data_point.get('bate', '')
                    if bate != 'c' and symbol not in ['PTAAF10', 'PTAAM10']:
                        continue
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
                    bate = data_point.get('bate', '')
                    if bate != 'c' and symbol not in ['PTAAF10', 'PTAAM10']:
                        continue
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
    
# Petrochemical 
def get_historical_price_petrochemical_short_term(access_token, productName, Basis, Year, Month=1, pageSize=1000, selects=None):
    if selects is None:
        selects = ["Product", "Value", "DateMonth", "DateYear"] 
    url = "https://api.ci.spglobal.com/odata/petchem-analytics/v1.2/Prices"
    filter_str = f"Product eq '{productName}' and DateYear eq {Year} and DateMonth eq {Month} and Basis eq '{Basis}'"
    params = {
        "$select": ",".join(selects), 
        "$filter": filter_str, 
        "$top": pageSize
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    try: 
        print(f"Mengambil data petrochemical untuk {productName} tahun {Year} bulan {Month}")
        response = requests.get(url, params=params, headers=headers, timeout=60)
        print(f"Status: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        flat_data = []
        if data and isinstance(data, dict):
            results = data.get('value', [])
            print(f"Total data yang ditemukan untuk {productName}: {len(results)}")
            for item in results: 
                flat_item = {
                    'Year': item.get('DateYear'), 
                    'Month': item.get('DateMonth'), 
                    f'Price_{productName}': item.get('Value')
                }
                flat_data.append(flat_item)
        return flat_data
    except requests.exceptions.RequestException as e:
        print(f"Error saat mengambil data {productName}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        return []

def pivot_data_petrochemical(all_data):
    if not all_data:
        return pd.DataFrame()
    df_combined = pd.DataFrame()
    for data in all_data:
        if data:
            df_temp = pd.DataFrame(data)
            if df_combined.empty:
                df_combined = df_temp
            else:
                df_combined = df_combined.merge(
                    df_temp, 
                    on=['Year', 'Month'], 
                    how='outer'
                )
    if not df_combined.empty:
        df_combined = df_combined.sort_values(['Year', 'Month']).reset_index(drop=True)
    return df_combined

def get_non_bbm_price_from_bbm_forecast(access_token, year, month, unitName="MT"):
    priceSymbols = ["PCAAS00", "PTAAF10", "PTAAM10"]
    fields = ["year", "month", "price", "priceSymbol"]
    url = "https://api.ci.spglobal.com/energy-price-forecast/v1/prices-short-term"
    symbols_str = ",".join([f'"{s}"' for s in priceSymbols])
    filter_query = f'priceSymbol IN ({symbols_str}) AND year={year} AND month={month} AND unitName="{unitName}"'
    params = {
        "field": ",".join(fields),  
        "filter": filter_query,    
        "pageSize": 100
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    try:
        print(f"Mengambil harga Brent, Butane, Propane untuk year={year}, month={month}")
        response = requests.get(url, params=params, headers=headers, timeout=60)
        print(f"Status: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        
        prices = {
            'Brent': None,
            'Butane': None,
            'Propane': None
        }
        
        if data and isinstance(data, dict):
            results = data.get('results', [])
            print(f"Total symbols ditemukan: {len(results)}")
            symbol_map = {
                'PCAAS00': 'Brent',
                'PTAAF10': 'Butane',
                'PTAAM10': 'Propane'
            }
            for item in results:
                symbol = item.get('priceSymbol')
                price = item.get('price')
                if symbol in symbol_map and price is not None:
                    name = symbol_map[symbol]
                    prices[name] = float(price)
                    print(f"  {name}: ${price}")
        for name, price in prices.items():
            if price is None:
                print(f"  WARNING: {name} tidak ditemukan")
        return prices
    except requests.exceptions.RequestException as e:
        print(f"Error saat mengambil harga: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
        return {'Brent': None, 'Butane': None, 'Propane': None}

def main_petrochemical_short_term():
    products = [
        {"name": "Paraxylene", "basis": "Spot CFR China"},
        {"name": "Propylene", "basis": "CFR SE Asia"},
        {"name": "Benzene", "basis": "Spot FOB Korea"},
    ]
    current_date = datetime.today()
    current_year = current_date.year
    current_month = current_date.month
    if current_month == 1:
        current_month = 12
        current_year = current_year - 1
    else:
        current_month = current_month - 1
    # current_year = 2024
    # current_month = 12
    try:
        onedrive_access_token = get_access_token()
        print("OneDrive authentication successful")
    except Exception as e:
        print(f"OneDrive authentication failed: {e}")
        exit(1)
    print("\nLogin ke S&P Global API...")
    spglobal_access_token = login_spglobal()
    if not spglobal_access_token:
        print("Gagal login ke S&P Global API")
        exit(1)
    all_data = []
    for product in products:
        data = get_historical_price_petrochemical_short_term(
            spglobal_access_token,
            product['name'],
            product['basis'],
            current_year,
            current_month
        )
        if data:
            print(f"Berhasil: {len(data)} records untuk {product['name']}")
            all_data.append(data)
        else:
            print(f"Gagal mengambil data untuk {product['name']}")
    if not all_data:
        print("\n[ERROR] Tidak ada data yang berhasil diambil")
        exit(1)
    df_pivoted = pivot_data_petrochemical(all_data)
    print(f"\nData petrochemical berhasil di-pivot: {len(df_pivoted)} baris")
    prices = get_non_bbm_price_from_bbm_forecast(
        spglobal_access_token,
        current_year,
        current_month,
        unitName="MT"
    )
    df_pivoted['Price_Brent'] = prices['Brent']
    df_pivoted['Price_Butane'] = prices['Butane']
    df_pivoted['Price_Propane'] = prices['Propane']
    if prices['Butane'] is not None and prices['Propane'] is not None:
        lpg_price = 0.5 * prices['Butane'] + 0.5 * prices['Propane']
        df_pivoted['Price_LPG'] = lpg_price
        print(f"\nHarga LPG (0.5*Butane + 0.5*Propane): ${lpg_price}/MT")
    else:
        df_pivoted['Price_LPG'] = None
        print("\n[WARNING] Harga Butane atau Propane tidak tersedia, LPG tidak dapat dihitung")
    if prices['Brent'] is not None:
        print(f"\nMenghitung crackspread dengan Brent = ${prices['Brent']}/MT")
        for product in products:
            product_name = product['name']
            price_col = f'Price_{product_name}'
            crackspread_col = f'Price_{product_name}_crackspread'
            if price_col in df_pivoted.columns:
                df_pivoted[crackspread_col] = df_pivoted[price_col] - prices['Brent']
                print(f"Crackspread {product_name} dihitung: {price_col} - Brent")
            else:
                df_pivoted[crackspread_col] = None
                print(f"Data {product_name} tidak tersedia")
    else:
        print("\n[WARNING] Harga Brent tidak tersedia, crackspread tidak dapat dihitung")
        for product in products:
            df_pivoted[f'Price_{product["name"]}_crackspread'] = None
    if prices['Brent'] is not None and 'Price_LPG' in df_pivoted.columns and df_pivoted['Price_LPG'].iloc[0] is not None:
        df_pivoted['Price_LPG_crackspread'] = df_pivoted['Price_LPG'] - prices['Brent']
        print(f"Crackspread LPG dihitung: LPG - Brent")
    else:
        df_pivoted['Price_LPG_crackspread'] = None
        print("Crackspread LPG tidak dapat dihitung")
    column_order = ['Year', 'Month']
    for product in products:
        price_col = f'Price_{product["name"]}'
        if price_col in df_pivoted.columns:
            column_order.append(price_col)
    column_order.extend(['Price_Butane', 'Price_Propane', 'Price_LPG', 'Price_Brent'])
    for product in products:
        crackspread_col = f'Price_{product["name"]}_crackspread'
        if crackspread_col in df_pivoted.columns:
            column_order.append(crackspread_col)
    column_order.append('Price_LPG_crackspread')
    for col in column_order:
        if col not in df_pivoted.columns:
            df_pivoted[col] = None
    df_pivoted = df_pivoted[column_order]
    write_sap_sheet_to_onedrive(
        onedrive_access_token,
        ONEDRIVE_FILE_PATH,
        SHEET_NAME_PETROCHEMICAL,
        df_pivoted,
        merge_key=['Year', 'Month']
    )

def get_historical_price_energy_forecast_long_term(access_token, priceSymbols, start_date, end_date, unitName, fields=None, page_size=1000): 
    if fields is None: 
        fields = ["year", "price", "priceSymbol"]
    url = "https://api.ci.spglobal.com/energy-price-forecast/v1/prices-long-term"
    symbols_str = ",".join([f'"{s}"' for s in priceSymbols])
    filter_query = f'priceSymbol IN ({symbols_str}) AND year>={start_date} AND year<={end_date} AND unitName="{unitName}"'
    params = {
        "field": ",".join(fields),  
        "filter": filter_query,    
        "pageSize": page_size       
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    try:
        print(f"Mengambil data historis price forecast dari {start_date} hingga {end_date}")
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
        if data and isinstance(data, dict):
            metadata = data.get('metadata', {})
            count = metadata.get('count', 0)
            print(f"\nTotal records ditemukan: {count}")
            results = data.get('results', [])
            if len(results) > 0:
                print(f"\nDEBUG - Item pertama:")
                first_item = results[0]
                print(f"  Year: {first_item.get('year')}")
                print(f"  Price: {first_item.get('price')}")
                print(f"  Price Symbol: {first_item.get('priceSymbol')}")
                print(f"  Keys available: {list(first_item.keys())}")
            for item in results:
                flat_item = {
                    'year': item.get('year'),
                    'price': item.get('price'),
                    'priceSymbol': item.get('priceSymbol')
                }
                for field in fields:
                    if field not in flat_item and field in item:
                        flat_item[field] = item.get(field)
                flat_data.append(flat_item)
        if not flat_data:
            print("Tidak ada data yang ditemukan")
            return None
        df = pd.DataFrame(flat_data)
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
        if 'year' in df.columns:
            df['year'] = pd.to_numeric(df['year'], errors='coerce').astype('Int64')
        df = df.sort_values(['year', 'priceSymbol'], ascending=[True, True])
        print(f"\nBerhasil mengambil {len(df)} baris data")
        print(f"Price symbols: {df['priceSymbol'].unique().tolist()}")
        print(f"Year range: {df['year'].min()} - {df['year'].max()}")
        return df
    except requests.exceptions.RequestException as e:
        print(f"Error saat mengambil data: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        return None
    
def get_historical_price_energy_forecast_short_term(access_token, priceSymbols, year, month, unitName, fields=None, page_size=1000):
    if fields is None: 
        fields = ["year", "month", "price", "priceSymbol"]
    url = "https://api.ci.spglobal.com/energy-price-forecast/v1/prices-short-term"
    symbols_str = ",".join([f'"{s}"' for s in priceSymbols])
    filter_query = f'priceSymbol IN ({symbols_str}) AND year={year} AND month={month} AND unitName="{unitName}"'
    # filter_query = f'priceSymbol IN ({symbols_str}) AND year>=2022 AND year<2022 AND unitName="BBL"'
    params = {
        "field": ",".join(fields),  
        "filter": filter_query,    
        "pageSize": page_size       
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    try:
        print(f"Mengambil data historis price forecast untuk year={year}, month={month}")
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
        if data and isinstance(data, dict):
            metadata = data.get('metadata', {})
            count = metadata.get('count', 0)
            print(f"\nTotal records ditemukan: {count}")
            results = data.get('results', [])
            if len(results) > 0:
                print(f"\nDEBUG - Item pertama:")
                first_item = results[0]
                print(f"  Year: {first_item.get('year')}")
                print(f"  Month: {first_item.get('month')}")
                print(f"  Price: {first_item.get('price')}")
                print(f"  Price Symbol: {first_item.get('priceSymbol')}")
                print(f"  Keys available: {list(first_item.keys())}")
            for item in results:
                flat_item = {
                    'year': item.get('year'),
                    'month': item.get('month'),
                    'price': item.get('price'),
                    'priceSymbol': item.get('priceSymbol')
                }
                for field in fields:
                    if field not in flat_item and field in item:
                        flat_item[field] = item.get(field)
                flat_data.append(flat_item)
        if not flat_data:
            print("Tidak ada data yang ditemukan")
            return None
        df = pd.DataFrame(flat_data)
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
        if 'year' in df.columns:
            df['year'] = pd.to_numeric(df['year'], errors='coerce').astype('Int64')
        if 'month' in df.columns:
            df['month'] = pd.to_numeric(df['month'], errors='coerce').astype('Int64')
        df = df.sort_values(['year', 'month', 'priceSymbol'], ascending=[True, True, True])
        print(f"\nBerhasil mengambil {len(df)} baris data")
        print(f"Price symbols: {df['priceSymbol'].unique().tolist()}")
        print(f"Year range: {df['year'].min()} - {df['year'].max()}")
        if 'month' in df.columns:
            print(f"Month range: {df['month'].min()} - {df['month'].max()}")
        return df
    except requests.exceptions.RequestException as e:
        print(f"Error saat mengambil data: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        return None
    
def pivot_data_to_columns_price_forecast_bbm_short_term(df):
    symbol_map = {
        'PGAEY00': 'RON92',
        'PGAEZ00': 'RON95',
        'PGAMS00': 'RON97',
        'AMFSA00': 'FO05',
        'PJABF00': 'JetKero',
        'AAPPF00': 'GO50',
        'AACUE00': 'GO2500', 
        'PCAAS00': 'Brent'
    }
    df['suffix'] = df['priceSymbol'].map(symbol_map)
    df_price = df.pivot_table(
        index=['year', 'month'],
        columns='suffix',
        values='price',
        aggfunc='first'
    ).reset_index()
    df_price.columns = ['year', 'month'] + [f'price_{col}' for col in df_price.columns if col not in ['year', 'month']]
    if 'price_Brent' not in df_price.columns:
        print("WARNING: Tidak ada data Brent ditemukan!")
        products = ['RON92', 'RON95', 'RON97', 'FO05', 'JetKero', 'GO50', 'GO2500']
        for product in products:
            price_col = f'price_{product}'
            if price_col in df_price.columns:
                df_price[f'price_{product}_crackspread'] = None
        return df_price.sort_values(['year', 'month'])
    print("Brent data found, calculating crackspreads...")
    products = ['RON92', 'RON95', 'RON97', 'FO05', 'JetKero', 'GO50', 'GO2500']
    for product in products:
        price_col = f'price_{product}'
        crackspread_col = f'price_{product}_crackspread'
        if price_col in df_price.columns:
            df_price[crackspread_col] = df_price[price_col] - df_price['price_Brent']
        else:
            df_price[crackspread_col] = None
    column_order = [
        'year', 'month',
        # Product prices
        'price_RON92', 'price_RON95', 'price_RON97', 
        'price_FO05', 'price_JetKero', 'price_GO50', 'price_GO2500',
        # Brent
        'price_Brent',
        # Crackspreads
        'price_RON92_crackspread', 'price_RON95_crackspread', 'price_RON97_crackspread',
        'price_FO05_crackspread', 'price_JetKero_crackspread', 
        'price_GO50_crackspread', 'price_GO2500_crackspread'
    ]
    for col in column_order:
        if col not in df_price.columns:
            df_price[col] = None
    return df_price[column_order].sort_values(['year', 'month'])

def pivot_data_to_columns_price_forecast_bbm(df):
    symbol_map = {
        'PGAEY00': 'RON92',
        'PGAEZ00': 'RON95',
        'PGAMS00': 'RON97',
        'AMFSA00': 'FO05',
        'PJABF00': 'JetKero',
        'AAPPF00': 'GO50',
        'AACUE00': 'GO2500', 
        'PCAAS00': 'Brent'
    }
    df['suffix'] = df['priceSymbol'].map(symbol_map)
    df_price = df.pivot_table(
        index='year',
        columns='suffix',
        values='price',
        aggfunc='first'
    ).reset_index()
    df_price.columns = ['year'] + [f'price_{col}' for col in df_price.columns if col != 'year']
    if 'price_Brent' not in df_price.columns:
        print("WARNING: Tidak ada data Brent ditemukan!")
        products = ['RON92', 'RON95', 'RON97', 'FO05', 'JetKero', 'GO50', 'GO2500']
        for product in products:
            price_col = f'price_{product}'
            if price_col in df_price.columns:
                df_price[f'price_{product}_crackspread'] = None
        return df_price.sort_values('year')
    print("Brent data found, calculating crackspreads...")
    products = ['RON92', 'RON95', 'RON97', 'FO05', 'JetKero', 'GO50', 'GO2500']
    for product in products:
        price_col = f'price_{product}'
        crackspread_col = f'price_{product}_crackspread'
        if price_col in df_price.columns:
            df_price[crackspread_col] = df_price[price_col] - df_price['price_Brent']
        else:
            df_price[crackspread_col] = None
    column_order = [
        'year',
        # Product prices
        'price_RON92', 'price_RON95', 'price_RON97', 
        'price_FO05', 'price_JetKero', 'price_GO50', 'price_GO2500',
        # Brent
        'price_Brent',
        # Crackspreads
        'price_RON92_crackspread', 'price_RON95_crackspread', 'price_RON97_crackspread',
        'price_FO05_crackspread', 'price_JetKero_crackspread', 
        'price_GO50_crackspread', 'price_GO2500_crackspread'
    ]
    for col in column_order:
        if col not in df_price.columns:
            df_price[col] = None
    return df_price[column_order].sort_values('year')

def main_price_forecast_short_term_bbm():
    priceSymbols = [
        "PGAEY00", 
        "PGAEZ00", 
        "PGAMS00",
        "AMFSA00",
        "PJABF00",
        "AAPPF00",
        "AACUE00",
        "PCAAS00" 
    ]
    current_date = datetime.today()
    current_year = current_date.year
    current_month = current_date.month
    if current_month == 1:
        current_month = 12
        current_year = current_year - 1
    else:
        current_month = current_month - 1
    unitName = "BBL"
    fields = ["year", "month", "price", "priceSymbol"]
    try:
        onedrive_access_token = get_access_token()
        print("OneDrive authentication successful")
    except Exception as e:
        print(f"OneDrive authentication failed: {e}")
        exit(1)
    print("\nLogin ke S&P Global API...")
    spglobal_access_token = login_spglobal()
    if not spglobal_access_token:
        print("Gagal login ke S&P Global API")
        exit(1)
    print("\n" + "=" * 60)
    print("SCRAPING PRICE FORECAST SHORT-TERM - BBM")
    print("=" * 60)
    print(f"Period: {current_year}-{current_month:02d}")
    print(f"Symbols: {', '.join(priceSymbols)}")
    df_forecast = get_historical_price_energy_forecast_short_term(
        spglobal_access_token,
        priceSymbols,
        current_year,
        current_month,
        unitName,
        fields
    )
    if df_forecast is None or df_forecast.empty:
        print("\n[FORECAST] Gagal mengambil data forecast")
        exit(1)
    print(f"\n[FORECAST] Data berhasil diambil!")
    print(f"[FORECAST] Total data: {len(df_forecast)} baris")
    print(f"[FORECAST] Symbols found: {df_forecast['priceSymbol'].unique().tolist()}")
    df_pivoted = pivot_data_to_columns_price_forecast_bbm_short_term(df_forecast)
    print(f"\n[FORECAST] Data setelah pivot: {len(df_pivoted)} baris")
    print(f"[FORECAST] Columns: {list(df_pivoted.columns)}")
    print("\n" + "=" * 60)
    print("MENYIMPAN KE ONEDRIVE")
    print("=" * 60)
    write_sap_sheet_to_onedrive(
        onedrive_access_token,
        ONEDRIVE_FILE_PATH,
        SHEET_NAME_FORECAST_BBM_SHORT,
        df_pivoted,
        merge_key=['year', 'month']
    )
    print("\n" + "=" * 60)
    print("DATA BERHASIL DISIMPAN KE ONEDRIVE")
    print("=" * 60)
    print(f"  File: {ONEDRIVE_FILE_PATH}")
    print(f"  Sheet: {SHEET_NAME_FORECAST_BBM_SHORT}")
    print(f"  Format: year | month | price_RON92 | ... | price_Brent | crackspreads")
    print(f"  Total rows: {len(df_pivoted)}")
    print("\n" + "=" * 60)
    print("SELESAI")
    print("=" * 60)

def main_price_forecast_long_term_bbm():
    priceSymbols = [
        "PGAEY00", 
        "PGAEZ00", 
        "PGAMS00",
        "AMFSA00",
        "PJABF00", 
        "AAPPF00",  
        "AACUE00", 
        "PCAAS00"
    ]
    current_year = datetime.today().year
    start_year = current_year
    end_year = current_year
    unitName = "BBL"
    fields = ["year", "price", "priceSymbol"]
    try:
        onedrive_access_token = get_access_token()
        print("OneDrive authentication successful")
    except Exception as e:
        print(f"OneDrive authentication failed: {e}")
        exit(1)
    print("\nLogin ke S&P Global API...")
    spglobal_access_token = login_spglobal()
    if not spglobal_access_token:
        print("Gagal login ke S&P Global API")
        exit(1)
    print("\n" + "=" * 60)
    print("SCRAPING PRICE FORECAST LONG-TERM - BBM")
    print("=" * 60)
    print(f"Period: {start_year} to {end_year}")
    print(f"Symbols: {', '.join(priceSymbols)}")
    df_forecast = get_historical_price_energy_forecast_long_term(
        spglobal_access_token,
        priceSymbols,
        start_year,
        end_year,
        unitName,
        fields
    )
    if df_forecast is None or df_forecast.empty:
        print("\n[FORECAST] Gagal mengambil data forecast")
        exit(1)
    print(f"\n[FORECAST] Data berhasil diambil!")
    print(f"[FORECAST] Total data: {len(df_forecast)} baris")
    print(f"[FORECAST] Symbols found: {df_forecast['priceSymbol'].unique().tolist()}")
    df_pivoted = pivot_data_to_columns_price_forecast_bbm(df_forecast)
    print(f"\n[FORECAST] Data setelah pivot: {len(df_pivoted)} baris")
    print(f"[FORECAST] Columns: {list(df_pivoted.columns)}")
    print("\n" + "=" * 60)
    print("MENYIMPAN KE ONEDRIVE")
    print("=" * 60)
    write_sap_sheet_to_onedrive(
        onedrive_access_token,
        ONEDRIVE_FILE_PATH,
        SHEET_NAME_FORECAST_BBM_LONG,
        df_pivoted,
        merge_key='year' 
    )
    print("\n" + "=" * 60)
    print("DATA BERHASIL DISIMPAN KE ONEDRIVE")
    print("=" * 60)
    print(f"  File: {ONEDRIVE_FILE_PATH}")
    print(f"  Sheet: {SHEET_NAME_FORECAST_BBM_LONG}")
    print(f"  Format: year | price_RON92 | ... | price_Brent | crackspreads")
    print(f"  Total rows: {len(df_pivoted)}")
    print("\n" + "=" * 60)
    print("SELESAI")
    print("=" * 60)

def merge_with_existing_data_forecast(df_old, df_new):
    if df_old.empty:
        return df_new
    if df_new.empty:
        return df_old
    all_columns = set(df_old.columns) | set(df_new.columns)
    for col in all_columns:
        if col not in df_old.columns:
            df_old[col] = None
        if col not in df_new.columns:
            df_new[col] = None
    df_merged = df_old.merge(
        df_new,
        on='year', 
        how='outer',
        suffixes=('_old', '_new')
    )
    for col in list(df_merged.columns):
        if col.endswith('_old'):
            base_col = col.replace('_old', '')
            new_col = f'{base_col}_new'
            if new_col in df_merged.columns:
                df_merged[base_col] = df_merged[new_col].fillna(df_merged[col])
            else:
                df_merged[base_col] = df_merged[col]
        elif col.endswith('_new') and f'{col.replace("_new", "")}_old' not in df_merged.columns:
            base_col = col.replace('_new', '')
            df_merged[base_col] = df_merged[col]
    cols_to_drop = [col for col in df_merged.columns if col.endswith('_old') or col.endswith('_new')]
    df_merged = df_merged.drop(columns=cols_to_drop)
    print(f"Data sebelum deduplikasi: {len(df_merged)} baris")
    price_columns = [col for col in df_merged.columns if col.startswith('price_')]
    subset_cols = ['year'] + price_columns
    df_merged = df_merged.drop_duplicates(subset=subset_cols, keep='last')
    print(f"Data setelah deduplikasi (keep yang baru): {len(df_merged)} baris")
    df_merged = df_merged.sort_values('year', ascending=True).reset_index(drop=True)
    print(f"\n[MERGE] Data berhasil di-merge:")
    print(f"  Data lama: {len(df_old)} rows")
    print(f"  Data baru: {len(df_new)} rows")
    print(f"  Data final: {len(df_merged)} rows")
    return df_merged

def merge_with_existing_data_petrochemical(df_old, df_new):
    if df_old.empty:
        return df_new
    if df_new.empty:
        return df_old
    all_columns = set(df_old.columns) | set(df_new.columns)
    for col in all_columns:
        if col not in df_old.columns:
            df_old[col] = None
        if col not in df_new.columns:
            df_new[col] = None
    df_merged = df_old.merge(
        df_new,
        on=['Year', 'Month'], 
        how='outer',
        suffixes=('_old', '_new')
    )
    for col in list(df_merged.columns):
        if col.endswith('_old'):
            base_col = col.replace('_old', '')
            new_col = f'{base_col}_new'
            if new_col in df_merged.columns:
                df_merged[base_col] = df_merged[new_col].fillna(df_merged[col])
            else:
                df_merged[base_col] = df_merged[col]
        elif col.endswith('_new') and f'{col.replace("_new", "")}_old' not in df_merged.columns:
            base_col = col.replace('_new', '')
            df_merged[base_col] = df_merged[col]
    cols_to_drop = [col for col in df_merged.columns if col.endswith('_old') or col.endswith('_new')]
    df_merged = df_merged.drop(columns=cols_to_drop)
    print(f"Data sebelum deduplikasi: {len(df_merged)} baris")
    price_columns = [col for col in df_merged.columns if col.startswith('Price_')]
    subset_cols = ['Year', 'Month'] + price_columns
    df_merged = df_merged.drop_duplicates(subset=subset_cols, keep='last')
    print(f"Data setelah deduplikasi (keep yang baru): {len(df_merged)} baris")
    df_merged = df_merged.sort_values(['Year', 'Month'], ascending=True).reset_index(drop=True)
    print(f"\n[MERGE] Data berhasil di-merge:")
    print(f"  Data lama: {len(df_old)} rows")
    print(f"  Data baru: {len(df_new)} rows")
    print(f"  Data final: {len(df_merged)} rows")
    return df_merged


def pivot_data_to_columns_saf(df):
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

def pivot_data_to_columns_bbm(df):
    symbol_map = {
        'PGAEY00': 'RON92',
        'PGAEZ00': 'RON95',
        'PGAMS00': 'RON97',
        'AMFSA00': 'FO05',
        'PJABF00': 'JetKero',
        'AAPPF00': 'GO50',
        'AACUE00': 'GO2500', 
        'PCAAS00': 'Brent'
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
    if 'value_RON92' in df_final.columns:
        df_final['value_RON92_MT'] = df_final['value_RON92'] * 0.120
    else: 
        df_final['value_RON92_MT'] = None

    if 'value_RON95' in df_final.columns:
        df_final['value_RON95_MT'] = df_final['value_RON95'] * 0.120
    else: 
        df_final['value_RON95_MT'] = None

    if 'value_RON97' in df_final.columns:
        df_final['value_RON97_MT'] = df_final['value_RON97'] * 0.120
    else: 
        df_final['value_RON97_MT'] = None

    if 'value_FO05' in df_final.columns:
        df_final['value_FO05_MT'] = df_final['value_FO05']
        df_final['value_FO05'] = df_final['value_FO05'] * 0.15748
    else: 
        df_final['value_FO05_MT'] = None
        df_final['value_FO05'] = None

    if 'value_JetKero' in df_final.columns:
        df_final['value_JetKero_MT'] = df_final['value_JetKero'] * 0.127
    else: 
        df_final['value_JetKero_MT'] = None

    if 'value_GO50' in df_final.columns:
        df_final['value_GO50_MT'] = df_final['value_GO50'] * 0.134
    else: 
        df_final['value_GO50_MT'] = None
    
    if 'value_GO2500' in df_final.columns:
        df_final['value_GO2500_MT'] = df_final['value_GO2500'] * 0.134
    else: 
        df_final['value_GO2500_MT'] = None  
        
    if 'value_Brent' in df_final.columns:
        df_final['value_Brent_MT'] = df_final['value_Brent'] * 0.134
    else:
        df_final['value_Brent_MT'] = None
    # Crackspread BBL (product - Brent BBL)
    products = ['RON92', 'RON95', 'RON97', 'FO05', 'JetKero', 'GO50', 'GO2500']
    for product in products:
        value_col = f'value_{product}'
        final_col = f'value_{product}_final'
        if value_col in df_final.columns and 'value_Brent' in df_final.columns:
            df_final[final_col] = (df_final[value_col]) - (df_final['value_Brent'])
        else:
            df_final[final_col] = None
    # Crackspread MT (product_MT - Brent_MT)
    for product in products:
        value_col_mt = f'value_{product}_MT'
        final_col_mt = f'value_{product}_MT_final'
        if value_col_mt in df_final.columns and 'value_Brent_MT' in df_final.columns:
            df_final[final_col_mt] = (df_final[value_col_mt]) - (df_final['value_Brent_MT'])
        else:
            df_final[final_col_mt] = None
    
    column_order = [
        'assessDate',
        # Value columns (BBL)
        'value_RON92', 'value_RON95', 'value_RON97', 'value_FO05',
        'value_JetKero', 'value_GO50', 'value_GO2500', 'value_Brent',
        # Value columns (MT)
        'value_RON92_MT', 'value_RON95_MT', 'value_RON97_MT', 'value_FO05_MT',
        'value_JetKero_MT', 'value_GO50_MT', 'value_GO2500_MT', 'value_Brent_MT',
        # Final columns BBL (crackspread)
        'value_RON92_final', 'value_RON95_final', 'value_RON97_final', 'value_FO05_final',
        'value_JetKero_final', 'value_GO50_final', 'value_GO2500_final',
        # Final columns MT (crackspread)
        'value_RON92_MT_final', 'value_RON95_MT_final', 'value_RON97_MT_final', 'value_FO05_MT_final',
        'value_JetKero_MT_final', 'value_GO50_MT_final', 'value_GO2500_MT_final',
        # ModDate columns
        'modDate_RON92', 'modDate_RON95', 'modDate_RON97', 'modDate_FO05',
        'modDate_JetKero', 'modDate_GO50', 'modDate_GO2500', 'modDate_Brent'
    ]
    for col in column_order:
        if col not in df_final.columns:
            df_final[col] = None
    return df_final[column_order].sort_values('assessDate')

def merge_with_existing_data(df_old, df_new):
    if df_old.empty:
        return df_new
    if df_new.empty:
        return df_old
    all_columns = set(df_old.columns) | set(df_new.columns)
    for col in all_columns:
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
    value_cols = [col for col in df_merged.columns if col.startswith('value_') and not col.endswith(('_old', '_new'))]
    moddate_cols = [col for col in df_merged.columns if col.startswith('modDate_') and not col.endswith(('_old', '_new'))]
    for col in list(df_merged.columns):
        if col.endswith('_old'):
            base_col = col.replace('_old', '')
            new_col = f'{base_col}_new'
            if new_col in df_merged.columns:
                df_merged[base_col] = df_merged[new_col].fillna(df_merged[col])
            else:
                df_merged[base_col] = df_merged[col]
        elif col.endswith('_new') and f'{col.replace("_new", "")}_old' not in df_merged.columns:
            base_col = col.replace('_new', '')
            df_merged[base_col] = df_merged[col]
    cols_to_drop = [col for col in df_merged.columns if col.endswith('_old') or col.endswith('_new')]
    df_merged = df_merged.drop(columns=cols_to_drop)
    print(f"Data sebelum deduplikasi: {len(df_merged)} baris")
    value_columns = [col for col in df_merged.columns if col.startswith('value_')]
    subset_cols = ['assessDate'] + value_columns
    df_merged = df_merged.drop_duplicates(subset=subset_cols, keep='last')
    print(f"Data setelah deduplikasi (keep yang baru): {len(df_merged)} baris")
    df_merged = df_merged.sort_values('assessDate', ascending=True).reset_index(drop=True)
    print(f"\n[MERGE] Data berhasil di-merge:")
    print(f"  Data lama: {len(df_old)} rows")
    print(f"  Data baru: {len(df_new)} rows")
    print(f"  Data final: {len(df_merged)} rows")
    return df_merged

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
    
def merge_with_existing_data_forecast_short_term(df_old, df_new):
    if df_old.empty:
        return df_new
    if df_new.empty:
        return df_old
    all_columns = set(df_old.columns) | set(df_new.columns)
    for col in all_columns:
        if col not in df_old.columns:
            df_old[col] = None
        if col not in df_new.columns:
            df_new[col] = None
    df_merged = df_old.merge(
        df_new,
        on=['year', 'month'], 
        how='outer',
        suffixes=('_old', '_new')
    )
    for col in list(df_merged.columns):
        if col.endswith('_old'):
            base_col = col.replace('_old', '')
            new_col = f'{base_col}_new'
            if new_col in df_merged.columns:
                df_merged[base_col] = df_merged[new_col].fillna(df_merged[col])
            else:
                df_merged[base_col] = df_merged[col]     
        elif col.endswith('_new') and f'{col.replace("_new", "")}_old' not in df_merged.columns:
            base_col = col.replace('_new', '')
            df_merged[base_col] = df_merged[col]
    cols_to_drop = [col for col in df_merged.columns if col.endswith('_old') or col.endswith('_new')]
    df_merged = df_merged.drop(columns=cols_to_drop)
    print(f"Data sebelum deduplikasi: {len(df_merged)} baris")
    price_columns = [col for col in df_merged.columns if col.startswith('price_')]
    subset_cols = ['year', 'month'] + price_columns
    df_merged = df_merged.drop_duplicates(subset=subset_cols, keep='last')
    print(f"Data setelah deduplikasi (keep yang baru): {len(df_merged)} baris")
    df_merged = df_merged.sort_values(['year', 'month'], ascending=True).reset_index(drop=True)
    print(f"\n[MERGE] Data berhasil di-merge:")
    print(f"  Data lama: {len(df_old)} rows")
    print(f"  Data baru: {len(df_new)} rows")
    print(f"  Data final: {len(df_merged)} rows")
    return df_merged

def write_sap_sheet_to_onedrive(access_token, file_path, sheet_name, df_new, merge_key='assessDate'):
    print(f"\nMenyiapkan file Excel untuk OneDrive...")
    df_old = read_sap_sheet_from_onedrive(access_token, file_path, sheet_name)
    if merge_key == 'year':
        df_final = merge_with_existing_data_forecast(df_old, df_new)
    elif merge_key == ['year', 'month'] or (isinstance(merge_key, list) and 'month' in merge_key):
        df_final = merge_with_existing_data_forecast_short_term(df_old, df_new)
    elif merge_key == ['Year', 'Month'] or (isinstance(merge_key, list) and 'Month' in merge_key):
        df_final = merge_with_existing_data_petrochemical(df_old, df_new)
    else:
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

def main_saf_daily():
    symbols = ["SFSMR00", "UCFCC00"]
    fields = ["UOM", "Currency", "description"]
    try:
        onedrive_access_token = get_access_token()
        print("OneDrive authentication successful")
    except Exception as e:
        print(f"OneDrive authentication failed: {e}")
        exit(1)
    print("\nLoading S&P Global API tokens...")
    spglobal_access_token = login_spglobal()
    if not spglobal_access_token:
        print("Gagal login ke S&P Global API")
    print("\n" + "=" * 60)
    print("SCRAPING CURRENT DATA - SAF")
    print("=" * 60)
    df_current = get_current_data(spglobal_access_token, symbols, fields)
    if df_current is None:
        print("\n[CURRENT] Gagal mengambil data current")
        exit(1)
    print(f"\n[CURRENT] Data berhasil diambil!")
    print(f"[CURRENT] Total data: {len(df_current)} baris")
    df_pivoted = pivot_data_to_columns_saf(df_current)
    print("\n" + "=" * 60)
    print("MENYIMPAN KE ONEDRIVE")
    print("=" * 60)
    write_sap_sheet_to_onedrive(onedrive_access_token, ONEDRIVE_FILE_PATH, SHEET_NAME_SAF, df_pivoted)
    print("\n" + "=" * 60)
    print("DATA BERHASIL DISIMPAN KE ONEDRIVE")
    print("=" * 60)
    print(f"  File: {ONEDRIVE_FILE_PATH}")
    print(f"  Sheet: {SHEET_NAME_SAF}")
    print(f"  Format: assessDate | value_UCO | value_SAF | modDate_UCO | modDate_SAF")
    print(f"  Total rows: {len(df_pivoted)}")
    print("\n" + "=" * 60)
    print("SELESAI")
    print("=" * 60)

def main_saf_weekly():
    symbols = ["SFSMR00", "UCFCC00"]
    fields = ["UOM", "Currency", "description"]
    end_date = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=7)).strftime("%Y-%m-%d")
    try:
        onedrive_access_token = get_access_token()
        print("OneDrive authentication successful")
    except Exception as e:
        print(f"OneDrive authentication failed: {e}")
        exit(1)
    print("\nLoading S&P Global API tokens...")
    print("\nLogin ke S&P Global API...")
    spglobal_access_token = login_spglobal()
    if not spglobal_access_token:
        print("Gagal login ke S&P Global API")
        exit(1)
    print("\n" + "=" * 60)
    print("SCRAPING HISTORICAL DATA (WEEKLY) - SAF")
    print("=" * 60)
    print(f"Period: {start_date} to {end_date}")
    df_historical = get_historical_data(spglobal_access_token, symbols, start_date, end_date, fields)
    if df_historical is None:
        print("\n[HISTORICAL] Gagal mengambil data historical")
        exit(1)
    print(f"\n[HISTORICAL] Data berhasil diambil!")
    print(f"[HISTORICAL] Total data: {len(df_historical)} baris")
    df_pivoted = pivot_data_to_columns_saf(df_historical)
    print("\n" + "=" * 60)
    print("MENYIMPAN KE ONEDRIVE")
    print("=" * 60)
    write_sap_sheet_to_onedrive(onedrive_access_token, ONEDRIVE_FILE_PATH, SHEET_NAME_SAF, df_pivoted)
    print("\n" + "=" * 60)
    print("DATA BERHASIL DISIMPAN KE ONEDRIVE")
    print("=" * 60)
    print(f"  File: {ONEDRIVE_FILE_PATH}")
    print(f"  Sheet: {SHEET_NAME_SAF}")
    print(f"  Format: assessDate | value_UCO | value_SAF | modDate_UCO | modDate_SAF")
    print(f"  Total rows: {len(df_pivoted)}")
    print("\n" + "=" * 60)
    print("SELESAI")
    print("=" * 60)


if __name__ == "__main__":
    main_price_forecast_short_term_bbm()