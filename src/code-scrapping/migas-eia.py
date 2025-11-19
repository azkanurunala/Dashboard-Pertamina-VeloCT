import requests
import pandas as pd
from datetime import datetime
import os

_API_KEY = "kODFA7mKVrNKWrGyFiIk5fIdlC1AKGXzba5lJxzY"
_BASE_API_URL = "https://api.eia.gov/v2/steo/data/"
_EXCEL_PATH = "../hasil-scrapping/data_migas_eia.xlsx"

_MONTH_TO_NUMBER = {
    'januari': 1, 'februari': 2, 'maret': 3, 'april': 4,
    'mei': 5, 'juni': 6, 'juli': 7, 'agustus': 8,
    'september': 9, 'oktober': 10, 'november': 11, 'desember': 12
}
_NUMBER_TO_MONTH = {
    1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
    5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
    9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
}

_SERIES_IDS = {
    'PAPR_WORLD': 'World Total Production',
    'PAPR_OPEC': 'OPEC Production',
    'PAPR_NONOPEC': 'Non-OPEC Production',
    'COPR_WORLD': 'Crude Oil',
    'PATC_WORLD': 'World Total Consumption',
    'PATC_OECD': 'OECD Consumption'
}

def read_last_entry_from_excel(excel_path: str):
    if not os.path.exists(excel_path):
        print("File Excel belum ada, semua data akan diunduh.")
        return None, None
    try:
        df = pd.read_excel(excel_path)
        if df.empty or "Bulan" not in df.columns or "Tahun" not in df.columns:
            print("Excel kosong atau format salah. Semua data akan diunduh.")
            return None, None
        df["Bulan"] = df["Bulan"].astype(str).str.lower()
        df["Bulan_Angka"] = df["Bulan"].map(_MONTH_TO_NUMBER)
        df = df.dropna(subset=["Bulan_Angka"])
        if df.empty:
            print("Tidak ada data valid di Excel. Semua data akan diunduh.")
            return None, None
        df_sorted = df.sort_values(["Tahun", "Bulan_Angka"])
        last_row = df_sorted.iloc[-1]
        print(f"Data terakhir di Excel: {last_row['Bulan'].capitalize()} {int(last_row['Tahun'])}")
        return int(last_row["Tahun"]), int(last_row["Bulan_Angka"])
    except Exception as e:
        print(f"Error membaca Excel: {e}")
        return None, None

def get_migas_eia_needed_data():
    last_read_year, last_read_month = read_last_entry_from_excel(_EXCEL_PATH)
    today = datetime.today()
    month = today.month - 1
    year = today.year
    if month == 0:
        month = 12
        year -= 1
    needed_data = []
    if last_read_year is None or last_read_month is None:
        print(" No existing data found. Will fetch all available data.")
        return None
    while True:
        if year < last_read_year or (year == last_read_year and month <= last_read_month):
            break
        needed_data.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return needed_data

def get_start_end_from_needed_data(needed_data):
    if needed_data is None:
        today = datetime.today()
        end_year = today.year
        end_month = today.month - 1
        if end_month == 0:
            end_month = 12
            end_year -= 1
        start_str = "2015-01"
        end_str = f"{end_year}-{end_month:02d}"
        print(f"Fetching all data from {start_str} to {end_str}")
        return start_str, end_str
    if not needed_data:
        return None, None
    min_year, min_month = min(needed_data)
    max_year, max_month = max(needed_data)
    start_str = f"{min_year}-{min_month:02d}"
    end_str = f"{max_year}-{max_month:02d}"
    return start_str, end_str

def fetch_eia_data(series_id, start, end):
    params = {
        "api_key": _API_KEY,
        "frequency": "monthly",
        "data[0]": "value",
        "facets[seriesId][]": series_id,
        "start": start,
        "end": end
    }
    print(f"  Fetching {series_id}...")
    try:
        response = requests.get(_BASE_API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "response" in data and "data" in data["response"]:
            records = data["response"]["data"]
            print(f"Got {len(records)} records")
            return records
        else:
            print(f"No data found for {series_id}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {series_id}: {e}")
        return []

def transform_data_to_excel_format(all_data):
    period_data = {}
    for series_id, records in all_data.items():
        for record in records:
            period = record.get('period')
            value = record.get('value')
            if period and value and value != 'w':
                if period not in period_data:
                    period_data[period] = {}
                try:
                    period_data[period][series_id] = round(float(value), 2)
                except (ValueError, TypeError):
                    period_data[period][series_id] = None
    rows = []
    for period in sorted(period_data.keys()):
        year, month = period.split('-')
        year = int(year)
        month = int(month)
        world_total_prod = period_data[period].get('PAPR_WORLD')
        opec = period_data[period].get('PAPR_OPEC')
        non_opec = period_data[period].get('PAPR_NONOPEC')
        crude_oil = period_data[period].get('COPR_WORLD')
        world_total_cons = period_data[period].get('PATC_WORLD')
        oecd = period_data[period].get('PATC_OECD')
        
        world_total_prod = round(world_total_prod, 2) if world_total_prod is not None else None
        opec = round(opec, 2) if opec is not None else None
        non_opec = round(non_opec, 2) if non_opec is not None else None
        crude_oil = round(crude_oil, 2) if crude_oil is not None else None
        world_total_cons = round(world_total_cons, 2) if world_total_cons is not None else None
        oecd = round(oecd, 2) if oecd is not None else None
        
        other_liquids = None
        if world_total_prod is not None and crude_oil is not None:
            other_liquids = round(world_total_prod - crude_oil, 2)
        
        non_oecd = None
        if world_total_cons is not None and oecd is not None:
            non_oecd = round(world_total_cons - oecd, 2)
        
        row = {
            'Bulan': _NUMBER_TO_MONTH.get(month, f'Month-{month}'),
            'Tahun': year,
            'World Total Production': world_total_prod,
            'OPEC': opec,
            'Non-OPEC': non_opec,
            'Crude Oil': crude_oil,
            'Other Liquids': other_liquids,
            'World Total Consumption': world_total_cons,
            'OECD': oecd,
            'Non-OECD': non_oecd
        }
        rows.append(row)
    return pd.DataFrame(rows)

def save_to_excel(df, excel_path):
    print("Step 5: Saving to Excel...")
    if os.path.exists(excel_path):
        try:
            existing_df = pd.read_excel(excel_path, engine='openpyxl')
            df_combined = pd.concat([existing_df, df], ignore_index=True)
            df_combined.drop_duplicates(subset=['Bulan', 'Tahun'], keep='last', inplace=True)
            month_order = {
                'Januari': 1, 'Februari': 2, 'Maret': 3, 'April': 4,
                'Mei': 5, 'Juni': 6, 'Juli': 7, 'Agustus': 8,
                'September': 9, 'Oktober': 10, 'November': 11, 'Desember': 12
            }
            df_combined['Bulan_Order'] = df_combined['Bulan'].map(month_order)
            df_combined = df_combined.sort_values(['Tahun', 'Bulan_Order'])
            df_combined = df_combined.drop('Bulan_Order', axis=1)
            print(f"Merged with existing data. Total rows: {len(df_combined)}")  
        except Exception as e:
            print(f"Error reading existing file: {e}")
            print("Creating new file instead...")
            df_combined = df
    else:
        df_combined = df
    df_combined.to_excel(excel_path, index=False, engine='openpyxl')
    print(f"✅ Saved to {excel_path}")
    print(f"Total records: {len(df_combined)}")

def main():
    print("=" * 80)
    print("EIA STEO DATA SCRAPER")
    print("=" * 80)
    print()
    print("Step 1: Checking what data needs to be downloaded...")
    needed_data = get_migas_eia_needed_data()
    
    if needed_data is not None and len(needed_data) == 0:
        print("All data is up to date!")
        return
    if needed_data is None:
        print("Will download ALL available data from EIA STEO")
    else:
        print(f"Need to download data for {len(needed_data)} months")
        print(f"Periods: {needed_data[0]} to {needed_data[-1]}")
    print()
    start, end = get_start_end_from_needed_data(needed_data)
    print(f"Step 2: Date range: {start} to {end}")
    print()
    print("Step 3: Fetching data from EIA API...")
    all_data = {}
    for series_id in _SERIES_IDS.keys():
        records = fetch_eia_data(series_id, start, end)
        if records:
            all_data[series_id] = records
    if not all_data:
        print("\nNo data fetched. Please check your API key and internet connection.")
        return
    print()
    print("Step 4: Transforming data to Excel format...")
    df = transform_data_to_excel_format(all_data)
    if df.empty:
        print("No valid data to save.")
        return
    print(f"Transformed {len(df)} rows")
    print()
    print("Preview of data:")
    print(df.head(10).to_string(index=False))
    print()
    print("Step 5: Saving to Excel...")
    save_to_excel(df, _EXCEL_PATH)
    print()
    print("=" * 80)
    print("DONE!")
    print("=" * 80)

if __name__ == "__main__":
    main()