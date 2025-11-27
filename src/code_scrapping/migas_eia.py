import requests
import pandas as pd
from datetime import datetime
import os

_API_KEY = "kODFA7mKVrNKWrGyFiIk5fIdlC1AKGXzba5lJxzY"
_BASE_API_URL = "https://api.eia.gov/v2/steo/data/"
_EXCEL_PATH = "../results/Terstruktur(Data Scrapping).xlsx"

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

_QUARTER_TO_NUMBER = {
    'q1': 1, 'q2': 2, 'q3': 3, 'q4': 4
}
_NUMBER_TO_QUARTER = {
    1: 'Q1', 2: 'Q2', 3: 'Q3', 4: 'Q4'
}

_SERIES_IDS = {
    'PAPR_WORLD': 'World Total Production',
    'PAPR_OPEC': 'OPEC Production',
    'PAPR_NONOPEC': 'Non-OPEC Production',
    'COPR_WORLD': 'Crude Oil',
    'PATC_WORLD': 'World Total Consumption',
    'PATC_OECD': 'OECD Consumption'
}

_FREQUENCY_CONFIG = {
    'monthly': {
        'sheet_name': '(Data)eia_monthly',
        'period_column': 'Bulan',
        'start_date': '2015-01'
    },
    'quarterly': {
        'sheet_name': '(Data)eia_quarterly',
        'period_column': 'Quarter',
        'start_date': '2015-Q1'
    },
    'annual': {
        'sheet_name': '(Data)eia_annual',
        'period_column': 'Tahun',
        'start_date': '2015'
    }
}

def read_last_entry_from_excel(excel_path: str, sheet_name: str, frequency: str):
    """Membaca entry terakhir dari Excel berdasarkan frequency"""
    if not os.path.exists(excel_path):
        print(f"  File Excel belum ada untuk {frequency}")
        return None, None
    
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name, engine='openpyxl')
        if df.empty or "Tahun" not in df.columns:
            print(f"  Sheet kosong atau format salah untuk {frequency}")
            return None, None
        
        if frequency == 'monthly':
            if "Bulan" not in df.columns:
                return None, None
            df["Bulan"] = df["Bulan"].astype(str).str.lower()
            df["Bulan_Angka"] = df["Bulan"].map(_MONTH_TO_NUMBER)
            df = df.dropna(subset=["Bulan_Angka"])
            if df.empty:
                return None, None
            df_sorted = df.sort_values(["Tahun", "Bulan_Angka"])
            last_row = df_sorted.iloc[-1]
            print(f"  Data terakhir ({frequency}): {last_row['Bulan'].capitalize()} {int(last_row['Tahun'])}")
            return int(last_row["Tahun"]), int(last_row["Bulan_Angka"])
        
        elif frequency == 'quarterly':
            if "Quarter" not in df.columns:
                return None, None
            df["Quarter"] = df["Quarter"].astype(str).str.lower()
            df["Quarter_Angka"] = df["Quarter"].map(_QUARTER_TO_NUMBER)
            df = df.dropna(subset=["Quarter_Angka"])
            if df.empty:
                return None, None
            df_sorted = df.sort_values(["Tahun", "Quarter_Angka"])
            last_row = df_sorted.iloc[-1]
            print(f"  Data terakhir ({frequency}): {last_row['Quarter'].upper()} {int(last_row['Tahun'])}")
            return int(last_row["Tahun"]), int(last_row["Quarter_Angka"])
        
        elif frequency == 'annual':
            df_sorted = df.sort_values(["Tahun"])
            last_row = df_sorted.iloc[-1]
            print(f"  Data terakhir ({frequency}): {int(last_row['Tahun'])}")
            return int(last_row["Tahun"]), None
        
    except ValueError:
        print(f"  Sheet '{sheet_name}' tidak ditemukan untuk {frequency}")
        return None, None
    except Exception as e:
        print(f"  Error membaca Excel ({frequency}): {e}")
        return None, None

def get_needed_data(frequency: str, excel_path: str, sheet_name: str):
    """Menentukan data apa saja yang perlu diunduh"""
    last_read_year, last_read_period = read_last_entry_from_excel(excel_path, sheet_name, frequency)
    today = datetime.today()
    
    if frequency == 'monthly':
        month = today.month - 1
        year = today.year
        if month == 0:
            month = 12
            year -= 1
        
        needed_data = []
        if last_read_year is None or last_read_period is None:
            return None
        
        while True:
            if year < last_read_year or (year == last_read_year and month <= last_read_period):
                break
            needed_data.append((year, month))
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        return needed_data
    
    elif frequency == 'quarterly':
        current_month = today.month
        current_quarter = (current_month - 1) // 3 + 1
        if current_month in [1, 2, 3]:
            quarter = 4
            year = today.year - 1
        else:
            quarter = current_quarter - 1
            year = today.year
        
        needed_data = []
        if last_read_year is None or last_read_period is None:
            return None
        
        while True:
            if year < last_read_year or (year == last_read_year and quarter <= last_read_period):
                break
            needed_data.append((year, quarter))
            quarter -= 1
            if quarter == 0:
                quarter = 4
                year -= 1
        return needed_data
    
    elif frequency == 'annual':
        year = today.year - 1
        
        needed_data = []
        if last_read_year is None:
            return None
        
        while year > last_read_year:
            needed_data.append((year, None))
            year -= 1
        return needed_data

def get_start_end_from_needed_data(needed_data, frequency: str):
    """Menentukan start dan end date untuk API call"""
    config = _FREQUENCY_CONFIG[frequency]
    
    if needed_data is None:
        today = datetime.today()
        
        if frequency == 'monthly':
            end_year = today.year
            end_month = today.month - 1
            if end_month == 0:
                end_month = 12
                end_year -= 1
            end_str = f"{end_year}-{end_month:02d}"
        elif frequency == 'quarterly':
            current_month = today.month
            if current_month in [1, 2, 3]:
                end_str = f"{today.year - 1}-Q4"
            else:
                current_quarter = (current_month - 1) // 3
                end_str = f"{today.year}-Q{current_quarter}"
        elif frequency == 'annual':
            end_str = str(today.year - 1)
        
        print(f"  Fetching all data from {config['start_date']} to {end_str}")
        return config['start_date'], end_str
    
    if not needed_data:
        return None, None
    
    if frequency == 'monthly':
        min_year, min_month = min(needed_data)
        max_year, max_month = max(needed_data)
        start_str = f"{min_year}-{min_month:02d}"
        end_str = f"{max_year}-{max_month:02d}"
    elif frequency == 'quarterly':
        min_year, min_quarter = min(needed_data)
        max_year, max_quarter = max(needed_data)
        start_str = f"{min_year}-Q{min_quarter}"
        end_str = f"{max_year}-Q{max_quarter}"
    elif frequency == 'annual':
        years = [y for y, _ in needed_data]
        start_str = str(min(years))
        end_str = str(max(years))
    
    return start_str, end_str

def fetch_eia_data(series_id, start, end, frequency):
    """Mengambil data dari EIA API"""
    params = {
        "api_key": _API_KEY,
        "frequency": frequency,
        "data[0]": "value",
        "facets[seriesId][]": series_id,
        "start": start,
        "end": end
    }
    print(f"    Fetching {series_id}...")
    try:
        response = requests.get(_BASE_API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "response" in data and "data" in data["response"]:
            records = data["response"]["data"]
            print(f"    Got {len(records)} records")
            return records
        else:
            print(f"    No data found for {series_id}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"    Error fetching {series_id}: {e}")
        return []

def transform_data_to_excel_format(all_data, frequency):
    """Transform data ke format Excel sesuai frequency"""
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
        if frequency == 'monthly':
            year, month = period.split('-')
            year = int(year)
            month = int(month)
            period_name = _NUMBER_TO_MONTH.get(month, f'Month-{month}')
        elif frequency == 'quarterly':
            year, quarter = period.split('-Q')
            year = int(year)
            quarter = int(quarter)
            period_name = f'Q{quarter}'
        elif frequency == 'annual':
            year = int(period)
            period_name = None
        
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
        
        if frequency == 'monthly':
            row = {'Bulan': period_name, **row}
        elif frequency == 'quarterly':
            row = {'Quarter': period_name, **row}
        
        rows.append(row)
    
    return pd.DataFrame(rows)

def save_to_excel(df, excel_path, sheet_name, frequency):
    """Menyimpan data ke Excel"""
    print(f"  Saving {frequency} data to Excel...")
    
    if os.path.exists(excel_path):
        try:
            existing_df = pd.read_excel(excel_path, sheet_name=sheet_name, engine='openpyxl')
            df_combined = pd.concat([existing_df, df], ignore_index=True)
            
            if frequency == 'monthly':
                df_combined.drop_duplicates(subset=['Bulan', 'Tahun'], keep='last', inplace=True)
                month_order = {
                    'Januari': 1, 'Februari': 2, 'Maret': 3, 'April': 4,
                    'Mei': 5, 'Juni': 6, 'Juli': 7, 'Agustus': 8,
                    'September': 9, 'Oktober': 10, 'November': 11, 'Desember': 12
                }
                df_combined['Bulan_Order'] = df_combined['Bulan'].map(month_order)
                df_combined = df_combined.sort_values(['Tahun', 'Bulan_Order'])
                df_combined = df_combined.drop('Bulan_Order', axis=1)
            elif frequency == 'quarterly':
                df_combined.drop_duplicates(subset=['Quarter', 'Tahun'], keep='last', inplace=True)
                quarter_order = {'Q1': 1, 'Q2': 2, 'Q3': 3, 'Q4': 4}
                df_combined['Quarter_Order'] = df_combined['Quarter'].map(quarter_order)
                df_combined = df_combined.sort_values(['Tahun', 'Quarter_Order'])
                df_combined = df_combined.drop('Quarter_Order', axis=1)
            elif frequency == 'annual':
                df_combined.drop_duplicates(subset=['Tahun'], keep='last', inplace=True)
                df_combined = df_combined.sort_values(['Tahun'])
            
            print(f"  Merged with existing data. Total rows: {len(df_combined)}")
        except ValueError:
            print(f"  Sheet '{sheet_name}' tidak ditemukan, membuat sheet baru")
            df_combined = df
        except Exception as e:
            print(f"  Error reading existing file: {e}")
            df_combined = df
    else:
        df_combined = df
    
    try:
        if os.path.exists(excel_path):
            with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                df_combined.to_excel(writer, sheet_name=sheet_name, index=False)
        else:
            with pd.ExcelWriter(excel_path, engine='openpyxl', mode='w') as writer:
                df_combined.to_excel(writer, sheet_name=sheet_name, index=False)
        
        print(f"  Saved to {excel_path}")
        print(f"  Sheet: {sheet_name}")
        print(f"  Total records: {len(df_combined)}")
    except Exception as e:
        print(f"  Error saving to Excel: {e}")

def process_frequency(frequency: str):
    """Process data untuk satu frequency"""
    print(f"\n{'='*80}")
    print(f"PROCESSING {frequency.upper()} DATA")
    print(f"{'='*80}")
    
    config = _FREQUENCY_CONFIG[frequency]
    sheet_name = config['sheet_name']
    
    print(f"\nStep 1: Checking what {frequency} data needs to be downloaded...")
    needed_data = get_needed_data(frequency, _EXCEL_PATH, sheet_name)
    
    if needed_data is not None and len(needed_data) == 0:
        print(f"  All {frequency} data is up to date!")
        return
    
    if needed_data is None:
        print(f"  Will download ALL available {frequency} data from EIA STEO")
    else:
        print(f"  Need to download data for {len(needed_data)} periods")
    
    start, end = get_start_end_from_needed_data(needed_data, frequency)
    if start is None or end is None:
        print(f"  No new {frequency} data to fetch")
        return
    
    print(f"\nStep 2: Date range: {start} to {end}")
    
    print(f"\nStep 3: Fetching {frequency} data from EIA API...")
    all_data = {}
    for series_id in _SERIES_IDS.keys():
        records = fetch_eia_data(series_id, start, end, frequency)
        if records:
            all_data[series_id] = records
    
    if not all_data:
        print(f"\n  No {frequency} data fetched. Please check your API key and internet connection.")
        return
    
    print(f"\nStep 4: Transforming {frequency} data to Excel format...")
    df = transform_data_to_excel_format(all_data, frequency)
    if df.empty:
        print(f"  No valid {frequency} data to save.")
        return
    print(f"  Transformed {len(df)} rows")
    
    print(f"\nStep 5: Preview of {frequency} data:")
    print(df.head(10).to_string(index=False))
    
    print(f"\nStep 6: Saving {frequency} data...")
    save_to_excel(df, _EXCEL_PATH, sheet_name, frequency)

def main_eia():
    """Main function untuk menjalankan scraping untuk semua frequency"""
    print("=" * 80)
    print("EIA STEO DATA SCRAPER - MULTI FREQUENCY")
    print("=" * 80)
    print("\nWill process data for: MONTHLY, QUARTERLY, and ANNUAL frequencies")
    
    frequencies = ['monthly', 'quarterly', 'annual']
    
    for frequency in frequencies:
        try:
            process_frequency(frequency)
        except Exception as e:
            print(f"\nError processing {frequency} data: {e}")
            continue
    
    print("\n" + "=" * 80)
    print("ALL FREQUENCIES PROCESSED!")
    print("=" * 80)
    print("\nSheets created:")
    for freq in frequencies:
        print(f"  - {_FREQUENCY_CONFIG[freq]['sheet_name']}")

if __name__ == "__main__":
    main_eia()