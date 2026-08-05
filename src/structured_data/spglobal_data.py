import os
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
import requests
import tqdm
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers.storage_backend import storage

load_dotenv()


# Constants

ONEDRIVE_FILE_PATH = os.getenv("ONEDRIVE_DATA_PATH", "/results/(Terstruktur)Data_Scraping_final.xlsx")

SP_USERNAME = os.getenv("SPGLOBAL_USERNAME")
SP_PASSWORD = os.getenv("SPGLOBAL_PASSWORD")

SHEET_NAME_SAF               = "(Data)SAF"
SHEET_NAME_FORECAST_BBM_LONG  = "(Data)Crackspread_BBM_YEAR"
SHEET_NAME_FORECAST_BBM_SHORT = "(Data)Crackspread_BBM"
SHEET_NAME_PETROCHEMICAL      = "(Data)Crackspread_NON_BBM"
SHEET_NAME_CRACKSPEED_BBM     = "(Data)Crackspeed_BBM"
SHEET_NAME_CRACKSPEED_NON_BBM = "(Data)Crackspeed_NonBBM"

SP_AUTH_URL          = "https://api.ci.spglobal.com/auth/api"
SP_HISTORY_URL       = "https://api.ci.spglobal.com/market-data/v3/value/history/symbol"
SP_CURRENT_URL       = "https://api.ci.spglobal.com/market-data/v3/value/current/symbol"
SP_PETCHEM_URL       = "https://api.ci.spglobal.com/odata/petchem-analytics/v1.2/Prices"
SP_FORECAST_LT_URL   = "https://api.ci.spglobal.com/energy-price-forecast/v1/prices-long-term"
SP_FORECAST_ST_URL   = "https://api.ci.spglobal.com/energy-price-forecast/v1/prices-short-term"

# Symbol maps
SYMBOL_MAP_SAF = {
    "UCFCC00": "UCO",
    "SFSMR00": "SAF",
}
SYMBOL_MAP_BBM = {
    "PGAEY00": "RON92",
    "PGAEZ00": "RON95",
    "PGAMS00": "RON97",
    "AMFSA00": "FO05",
    "PJABF00": "JetKero",
    "AAPPF00": "GO50",
    "AACUE00": "GO2500",
    "PCAAS00": "Brent",
}
SYMBOL_MAP_NON_BBM = {
    "PCAAS00": "Brent",
    "PTAAF10": "Butane",
    "PTAAM10": "Propane",
}

# Unit conversion factors (BBL to MT)
BBL_TO_MT = {
    "RON92":   0.120,
    "RON95":   0.120,
    "RON97":   0.120,
    "FO05":    0.15748,
    "JetKero": 0.127,
    "GO50":    0.134,
    "GO2500":  0.134,
    "Brent":   0.134,
}

BBM_PRODUCTS    = ["RON92", "RON95", "RON97", "FO05", "JetKero", "GO50", "GO2500"]
BBM_SYMBOLS_ST  = ["PGAEY00", "PGAEZ00", "PGAMS00", "AMFSA00", "PJABF00", "AAPPF00", "AACUE00", "PCAAS00"]
BBM_SYMBOLS_LT  = ["PGAEY00", "PGAEZ00", "PGAMS00", "AMFSA00", "PJABF00", "AAPPF00", "AACUE00", "PCAAS00"]
NON_BBM_SYMBOLS = ["PCAAS00", "PTAAF10", "PTAAM10"]
SAF_SYMBOLS     = ["SFSMR00", "UCFCC00"]

PETCHEM_PRODUCTS = [
    {"name": "Paraxylene", "basis": "Spot CFR China"},
    {"name": "Propylene",  "basis": "CFR SE Asia"},
    {"name": "Benzene",    "basis": "Spot FOB Korea"},
]


# Authentication

def login_spglobal(username=None, password=None):
    """
    Authenticate with S&P Global API and return a Bearer access token.

    Returns the token string, or None on failure.
    """
    username = username or SP_USERNAME
    password = password or SP_PASSWORD

    if not username or not password:
        print("[Auth] Error: SPGLOBAL_USERNAME atau SPGLOBAL_PASSWORD tidak ditemukan di environment.")
        return None

    try:
        print("[Auth] Login ke S&P Global API...")
        print(f"[Auth] Username: {username}")
        response = requests.post(
            SP_AUTH_URL,
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        print(f"[Auth] Status code: {response.status_code}")
        response.raise_for_status()

        access_token = response.json().get("access_token")
        if access_token:
            print("[Auth] Login berhasil! Access token diperoleh.")
            return access_token

        print(f"[Auth] Login gagal: access_token tidak ditemukan. Response: {response.json()}")
        return None

    except requests.exceptions.RequestException as exc:
        print(f"[Auth] Error saat login: {exc}")
        if hasattr(exc, "response") and exc.response is not None:
            print(f"[Auth] Response status: {exc.response.status_code}")
            print(f"[Auth] Response body  : {exc.response.text}")
        return None


# Market Data — Historical & Current

def get_historical_data(access_token, symbols, start_date, end_date, fields=None, page_size=2000):
    """
    Fetch historical market data for the given symbols and date range.

    Returns a DataFrame or None on failure.
    """
    if fields is None:
        fields = ["UOM", "Currency", "description"]

    symbols_str  = ",".join([f'"{s}"' for s in symbols])
    filter_query = f'symbol IN ({symbols_str}) AND assessDate>"{start_date}" AND assessDate<"{end_date}"'
    params = {
        "Field":    ",".join(fields),
        "Filter":   filter_query,
        "PageSize": page_size,
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/json",
    }

    try:
        print(f"[Historical] Mengambil data dari {start_date} hingga {end_date}...")
        print(f"\nDEBUG - Request details:")
        print(f"  URL   : {SP_HISTORY_URL}")
        print(f"  Params: {params}")
        print(f"  Filter: {filter_query}")

        response = requests.get(SP_HISTORY_URL, params=params, headers=headers, timeout=60)

        print(f"\nDEBUG - Response:")
        print(f"  Status  : {response.status_code}")
        print(f"  Full URL: {response.url}")
        response.raise_for_status()

        data      = response.json()
        flat_data = []

        if data and isinstance(data, dict) and "results" in data:
            results = data["results"]
            print(f"[Historical] Total symbols ditemukan: {len(results)}")
            if results:
                first = results[0]
                print(f"\nDEBUG - Item pertama:")
                print(f"  Symbol       : {first.get('symbol')}")
                print(f"  Keys         : {list(first.keys())}")
                print(f"  referenceData: {first.get('referenceData')}")

            for item in results:
                symbol    = item.get("symbol", "")
                for dp in item.get("data", []):
                    bate = dp.get("bate", "")
                    if bate != "c" and symbol not in ["PTAAF10", "PTAAM10"]:
                        continue
                    assess_date = dp.get("assessDate", "")
                    if assess_date and "T" in assess_date:
                        assess_date = assess_date.split("T")[0]
                    flat_data.append({
                        "symbol":     symbol,
                        "assessDate": assess_date,
                        "value":      dp.get("value", ""),
                        "modDate":    dp.get("modDate", ""),
                    })

        if not flat_data:
            print("[Historical] Tidak ada data yang ditemukan.")
            return None

        df = pd.DataFrame(flat_data)
        if "value" in df.columns:
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
        print(f"[Historical] Berhasil mengambil {len(df)} baris data.")
        return df

    except requests.exceptions.RequestException as exc:
        print(f"[Historical] Error: {exc}")
        if hasattr(exc, "response") and exc.response is not None:
            print(f"[Historical] Response: {exc.response.text}")
        return None

def get_current_data(access_token, symbols, fields=None):
    """
    Fetch the latest (current) market data for the given symbols.

    Returns a deduplicated DataFrame or None on failure.
    """
    if fields is None:
        fields = ["UOM", "Currency", "description"]

    symbols_str  = ",".join([f'"{s}"' for s in symbols])
    filter_query = f"symbol IN ({symbols_str})"
    params = {
        "Field":  ",".join(fields),
        "Filter": filter_query,
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/json",
    }

    try:
        print(f"[Current] Mengambil data current untuk symbols: {symbols}")
        print(f"\nDEBUG - Request details:")
        print(f"  URL   : {SP_CURRENT_URL}")
        print(f"  Params: {params}")
        print(f"  Filter: {filter_query}")

        response = requests.get(SP_CURRENT_URL, params=params, headers=headers, timeout=60)

        print(f"\nDEBUG - Response:")
        print(f"  Status  : {response.status_code}")
        print(f"  Full URL: {response.url}")
        response.raise_for_status()

        data      = response.json()
        flat_data = []

        if data and isinstance(data, dict) and "results" in data:
            results = data["results"]
            print(f"[Current] Total symbols ditemukan: {len(results)}")
            for item in results:
                symbol = item.get("symbol", "")
                for dp in item.get("data", []):
                    bate = dp.get("bate", "")
                    if bate != "c" and symbol not in ["PTAAF10", "PTAAM10"]:
                        continue
                    assess_date = dp.get("assessDate", "")
                    if assess_date and "T" in assess_date:
                        assess_date = assess_date.split("T")[0]
                    flat_data.append({
                        "symbol":     symbol,
                        "assessDate": assess_date,
                        "value":      dp.get("value", ""),
                        "modDate":    dp.get("modDate", ""),
                    })

        if not flat_data:
            print("[Current] Tidak ada data yang ditemukan.")
            return None

        df = pd.DataFrame(flat_data)
        if "value" in df.columns:
            df["value"] = pd.to_numeric(df["value"], errors="coerce")

        print(f"[Current] Berhasil mengambil {len(df)} baris data (sebelum drop duplicate).")

        if "assessDate" in df.columns and "modDate" in df.columns:
            df = df.sort_values("modDate", ascending=False)
            df = df.drop_duplicates(subset=["symbol", "assessDate"], keep="first")
            print(f"[Current] Setelah drop duplicate: {len(df)} baris data.")

        print("\n[Current] Sample data:")
        print(df.head(3))
        return df

    except requests.exceptions.RequestException as exc:
        print(f"[Current] Error: {exc}")
        if hasattr(exc, "response") and exc.response is not None:
            print(f"[Current] Response: {exc.response.text}")
        return None


# Petrochemical Data

def get_historical_price_petrochemical_short_term(
    access_token, productName, Basis, Year, Month=1, pageSize=1000, selects=None
):
    """
    Fetch short-term petrochemical prices for a single product, year, and month.

    Returns a list of flat dicts.
    """
    if selects is None:
        selects = ["Product", "Value", "DateMonth", "DateYear"]

    filter_str = (
        f"Product eq '{productName}' and DateYear eq {Year} "
        f"and DateMonth eq {Month} and Basis eq '{Basis}'"
    )
    params = {
        "$select": ",".join(selects),
        "$filter": filter_str,
        "$top":    pageSize,
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/json",
    }

    try:
        print(f"[Petchem] Mengambil data {productName} tahun {Year} bulan {Month}...")
        response = requests.get(SP_PETCHEM_URL, params=params, headers=headers, timeout=60)
        print(f"[Petchem] Status: {response.status_code}")
        response.raise_for_status()

        data      = response.json()
        flat_data = []

        if data and isinstance(data, dict):
            results = data.get("value", [])
            print(f"[Petchem] Total data untuk {productName}: {len(results)}")
            for item in results:
                flat_data.append({
                    "Year":               item.get("DateYear"),
                    "Month":              item.get("DateMonth"),
                    f"Price_{productName}": item.get("Value"),
                })

        return flat_data

    except requests.exceptions.RequestException as exc:
        print(f"[Petchem] Error {productName}: {exc}")
        if hasattr(exc, "response") and exc.response is not None:
            print(f"[Petchem] Response status: {exc.response.status_code}")
            print(f"[Petchem] Response text  : {exc.response.text}")
        return []

def pivot_data_petrochemical(all_data):
    """Pivot a list of petrochemical data lists into a single wide DataFrame."""
    if not all_data:
        return pd.DataFrame()

    df_combined = pd.DataFrame()
    for data in all_data:
        if data:
            df_temp = pd.DataFrame(data)
            if df_combined.empty:
                df_combined = df_temp
            else:
                df_combined = df_combined.merge(df_temp, on=["Year", "Month"], how="outer")

    if not df_combined.empty:
        df_combined = df_combined.sort_values(["Year", "Month"]).reset_index(drop=True)
    return df_combined

def get_non_bbm_price_from_bbm_forecast(access_token, year, month, unitName="MT"):
    """
    Fetch Brent, Butane, and Propane prices from the S&P short-term forecast API.

    Returns a dict with keys 'Brent', 'Butane', 'Propane'.
    """
    symbols_str  = ",".join([f'"{s}"' for s in NON_BBM_SYMBOLS])
    filter_query = (
        f'priceSymbol IN ({symbols_str}) AND year={year} '
        f'AND month={month} AND unitName="{unitName}"'
    )
    params = {
        "field":    ",".join(["year", "month", "price", "priceSymbol"]),
        "filter":   filter_query,
        "pageSize": 100,
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/json",
    }

    prices = {"Brent": None, "Butane": None, "Propane": None}
    symbol_to_name = {"PCAAS00": "Brent", "PTAAF10": "Butane", "PTAAM10": "Propane"}

    try:
        print(f"[NonBBM] Mengambil harga Brent, Butane, Propane untuk year={year}, month={month}...")
        response = requests.get(SP_FORECAST_ST_URL, params=params, headers=headers, timeout=60)
        print(f"[NonBBM] Status: {response.status_code}")
        response.raise_for_status()

        data = response.json()
        if data and isinstance(data, dict):
            results = data.get("results", [])
            print(f"[NonBBM] Total symbols ditemukan: {len(results)}")
            for item in results:
                symbol = item.get("priceSymbol")
                price  = item.get("price")
                if symbol in symbol_to_name and price is not None:
                    name         = symbol_to_name[symbol]
                    prices[name] = float(price)
                    print(f"[NonBBM]   {name}: ${price}")

        for name, price in prices.items():
            if price is None:
                print(f"[NonBBM]   WARNING: {name} tidak ditemukan.")
        return prices

    except requests.exceptions.RequestException as exc:
        print(f"[NonBBM] Error: {exc}")
        if hasattr(exc, "response") and exc.response is not None:
            print(f"[NonBBM] Response status: {exc.response.status_code}")
        return prices


# Energy Price Forecast — Long Term & Short Term

def get_historical_price_energy_forecast_long_term(
    access_token, priceSymbols, start_date, end_date, unitName, fields=None, page_size=1000
):
    """
    Fetch long-term annual energy price forecast for the given symbols and year range.

    Returns a sorted DataFrame or None on failure.
    """
    if fields is None:
        fields = ["year", "price", "priceSymbol"]

    symbols_str  = ",".join([f'"{s}"' for s in priceSymbols])
    filter_query = (
        f'priceSymbol IN ({symbols_str}) AND year>={start_date} '
        f'AND year<={end_date} AND unitName="{unitName}"'
    )
    params = {
        "field":    ",".join(fields),
        "filter":   filter_query,
        "pageSize": page_size,
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/json",
    }

    try:
        print(f"[LT Forecast] Mengambil data dari {start_date} hingga {end_date}...")
        print(f"\nDEBUG - Request details:")
        print(f"  URL   : {SP_FORECAST_LT_URL}")
        print(f"  Params: {params}")
        print(f"  Filter: {filter_query}")

        response = requests.get(SP_FORECAST_LT_URL, params=params, headers=headers, timeout=60)

        print(f"\nDEBUG - Response:")
        print(f"  Status  : {response.status_code}")
        print(f"  Full URL: {response.url}")
        response.raise_for_status()

        data      = response.json()
        flat_data = []

        if data and isinstance(data, dict):
            count   = data.get("metadata", {}).get("count", 0)
            results = data.get("results", [])
            print(f"\n[LT Forecast] Total records ditemukan: {count}")

            if results:
                first = results[0]
                print(f"\nDEBUG - Item pertama:")
                print(f"  Year         : {first.get('year')}")
                print(f"  Price        : {first.get('price')}")
                print(f"  Price Symbol : {first.get('priceSymbol')}")
                print(f"  Keys         : {list(first.keys())}")

            for item in results:
                flat_item = {
                    "year":        item.get("year"),
                    "price":       item.get("price"),
                    "priceSymbol": item.get("priceSymbol"),
                }
                for field in fields:
                    if field not in flat_item and field in item:
                        flat_item[field] = item.get(field)
                flat_data.append(flat_item)

        if not flat_data:
            print("[LT Forecast] Tidak ada data yang ditemukan.")
            return None

        df = pd.DataFrame(flat_data)
        if "price" in df.columns:
            df["price"] = pd.to_numeric(df["price"], errors="coerce")
        if "year" in df.columns:
            df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

        df = df.sort_values(["year", "priceSymbol"], ascending=True)
        print(f"\n[LT Forecast] Berhasil mengambil {len(df)} baris data.")
        print(f"[LT Forecast] Price symbols: {df['priceSymbol'].unique().tolist()}")
        print(f"[LT Forecast] Year range   : {df['year'].min()} - {df['year'].max()}")
        return df

    except requests.exceptions.RequestException as exc:
        print(f"[LT Forecast] Error: {exc}")
        if hasattr(exc, "response") and exc.response is not None:
            print(f"[LT Forecast] Response status: {exc.response.status_code}")
            print(f"[LT Forecast] Response text  : {exc.response.text}")
        return None

def get_historical_price_energy_forecast_short_term(
    access_token, priceSymbols, year, month, unitName, fields=None, page_size=1000
):
    """
    Fetch short-term monthly energy price forecast for the given symbols, year, and month.

    Returns a sorted DataFrame or None on failure.
    """
    if fields is None:
        fields = ["year", "month", "price", "priceSymbol"]

    symbols_str  = ",".join([f'"{s}"' for s in priceSymbols])
    filter_query = (
        f'priceSymbol IN ({symbols_str}) AND year={year} '
        f'AND month={month} AND unitName="{unitName}"'
    )
    params = {
        "field":    ",".join(fields),
        "filter":   filter_query,
        "pageSize": page_size,
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/json",
    }

    try:
        print(f"[ST Forecast] Mengambil data untuk year={year}, month={month}...")
        print(f"\nDEBUG - Request details:")
        print(f"  URL   : {SP_FORECAST_ST_URL}")
        print(f"  Params: {params}")
        print(f"  Filter: {filter_query}")

        response = requests.get(SP_FORECAST_ST_URL, params=params, headers=headers, timeout=60)

        print(f"\nDEBUG - Response:")
        print(f"  Status  : {response.status_code}")
        print(f"  Full URL: {response.url}")
        response.raise_for_status()

        data      = response.json()
        flat_data = []

        if data and isinstance(data, dict):
            count   = data.get("metadata", {}).get("count", 0)
            results = data.get("results", [])
            print(f"\n[ST Forecast] Total records ditemukan: {count}")

            if results:
                first = results[0]
                print(f"\nDEBUG - Item pertama:")
                print(f"  Year         : {first.get('year')}")
                print(f"  Month        : {first.get('month')}")
                print(f"  Price        : {first.get('price')}")
                print(f"  Price Symbol : {first.get('priceSymbol')}")
                print(f"  Keys         : {list(first.keys())}")

            for item in results:
                flat_item = {
                    "year":        item.get("year"),
                    "month":       item.get("month"),
                    "price":       item.get("price"),
                    "priceSymbol": item.get("priceSymbol"),
                }
                for field in fields:
                    if field not in flat_item and field in item:
                        flat_item[field] = item.get(field)
                flat_data.append(flat_item)

        if not flat_data:
            print("[ST Forecast] Tidak ada data yang ditemukan.")
            return None

        df = pd.DataFrame(flat_data)
        if "price" in df.columns:
            df["price"] = pd.to_numeric(df["price"], errors="coerce")
        if "year" in df.columns:
            df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
        if "month" in df.columns:
            df["month"] = pd.to_numeric(df["month"], errors="coerce").astype("Int64")

        df = df.sort_values(["year", "month", "priceSymbol"], ascending=True)
        print(f"\n[ST Forecast] Berhasil mengambil {len(df)} baris data.")
        print(f"[ST Forecast] Price symbols: {df['priceSymbol'].unique().tolist()}")
        print(f"[ST Forecast] Year range   : {df['year'].min()} - {df['year'].max()}")
        if "month" in df.columns:
            print(f"[ST Forecast] Month range  : {df['month'].min()} - {df['month'].max()}")
        return df

    except requests.exceptions.RequestException as exc:
        print(f"[ST Forecast] Error: {exc}")
        if hasattr(exc, "response") and exc.response is not None:
            print(f"[ST Forecast] Response status: {exc.response.status_code}")
            print(f"[ST Forecast] Response text  : {exc.response.text}")
        return None


# Data Pivot

def pivot_data_to_columns_saf(df):
    """Pivot SAF and UCO symbol data into wide format with value and modDate columns."""
    df["suffix"] = df["symbol"].map(SYMBOL_MAP_SAF)

    df_value = df.pivot_table(
        index="assessDate", columns="suffix", values="value", aggfunc="first"
    ).reset_index()
    df_value.columns = ["assessDate"] + [
        f"value_{c}" for c in df_value.columns if c != "assessDate"
    ]

    df_moddate = df.pivot_table(
        index="assessDate", columns="suffix", values="modDate", aggfunc="first"
    ).reset_index()
    df_moddate.columns = ["assessDate"] + [
        f"modDate_{c}" for c in df_moddate.columns if c != "assessDate"
    ]

    df_final     = df_value.merge(df_moddate, on="assessDate", how="outer")
    column_order = ["assessDate", "value_UCO", "value_SAF", "modDate_UCO", "modDate_SAF"]
    for col in column_order:
        if col not in df_final.columns:
            df_final[col] = None
    return df_final[column_order].sort_values("assessDate")

def pivot_data_to_columns_bbm(df):
    """
    Pivot BBM symbol data into wide format with BBL/MT values and crackspreads.
    """
    df["suffix"] = df["symbol"].map(SYMBOL_MAP_BBM)

    df_value = df.pivot_table(
        index="assessDate", columns="suffix", values="value", aggfunc="first"
    ).reset_index()
    df_value.columns = ["assessDate"] + [
        f"value_{c}" for c in df_value.columns if c != "assessDate"
    ]

    df_moddate = df.pivot_table(
        index="assessDate", columns="suffix", values="modDate", aggfunc="first"
    ).reset_index()
    df_moddate.columns = ["assessDate"] + [
        f"modDate_{c}" for c in df_moddate.columns if c != "assessDate"
    ]

    df_final = df_value.merge(df_moddate, on="assessDate", how="outer")

    # FO05: raw value is in MT, convert to BBL
    if "value_FO05" in df_final.columns:
        df_final["value_FO05_MT"] = df_final["value_FO05"]
        df_final["value_FO05"]    = df_final["value_FO05"] * BBL_TO_MT["FO05"]
    else:
        df_final["value_FO05_MT"] = None
        df_final["value_FO05"]    = None

    # MT conversion for all products
    for product, factor in BBL_TO_MT.items():
        col    = f"value_{product}"
        col_mt = f"value_{product}_MT"
        if product == "FO05":
            continue  # already handled above
        if col in df_final.columns:
            df_final[col_mt] = df_final[col] * factor
        else:
            df_final[col_mt] = None

    # Crackspread BBL
    for product in BBM_PRODUCTS:
        col       = f"value_{product}"
        final_col = f"value_{product}_final"
        if col in df_final.columns and "value_Brent" in df_final.columns:
            df_final[final_col] = df_final[col] - df_final["value_Brent"]
        else:
            df_final[final_col] = None

    # Crackspread MT
    for product in BBM_PRODUCTS:
        col_mt       = f"value_{product}_MT"
        final_col_mt = f"value_{product}_MT_final"
        if col_mt in df_final.columns and "value_Brent_MT" in df_final.columns:
            df_final[final_col_mt] = df_final[col_mt] - df_final["value_Brent_MT"]
        else:
            df_final[final_col_mt] = None

    column_order = (
        ["assessDate"]
        + [f"value_{p}" for p in BBM_PRODUCTS] + ["value_Brent"]
        + [f"value_{p}_MT" for p in BBM_PRODUCTS] + ["value_Brent_MT"]
        + [f"value_{p}_final" for p in BBM_PRODUCTS]
        + [f"value_{p}_MT_final" for p in BBM_PRODUCTS]
        + [f"modDate_{p}" for p in BBM_PRODUCTS] + ["modDate_Brent"]
    )
    for col in column_order:
        if col not in df_final.columns:
            df_final[col] = None
    return df_final[column_order].sort_values("assessDate")

def pivot_data_to_columns_non_bbm(df):
    """Pivot non-BBM (LPG/petrochemical) historical symbol data into wide format with crackspreads."""
    symbol_map = {
        "PTAAF10": "Butane",
        "PTAAM10": "Propane",
        "PHABV00": "Paraxylene",
        "PHAKR00": "Propylene",
        "PHASM05": "Benzene",
        "PCAAS00": "Brent",
    }
    df["suffix"] = df["symbol"].map(symbol_map)

    df_value = df.pivot_table(
        index="assessDate", columns="suffix", values="value", aggfunc="first"
    ).reset_index()
    df_value.columns = ["assessDate"] + [f"value_{c}" for c in df_value.columns if c != "assessDate"]

    df_moddate = df.pivot_table(
        index="assessDate", columns="suffix", values="modDate", aggfunc="first"
    ).reset_index()
    df_moddate.columns = ["assessDate"] + [f"modDate_{c}" for c in df_moddate.columns if c != "assessDate"]

    df_final = df_value.merge(df_moddate, on="assessDate", how="outer")

    if "value_Butane" in df_final.columns and "value_Propane" in df_final.columns:
        df_final["value_LPG"] = df_final["value_Butane"] * 0.5 + df_final["value_Propane"] * 0.5
    else:
        df_final["value_LPG"] = None

    for product in ["LPG", "Paraxylene", "Propylene", "Benzene"]:
        value_col = f"value_{product}"
        final_col = f"value_{product}_final"
        if value_col in df_final.columns and "value_Brent" in df_final.columns:
            df_final[final_col] = df_final[value_col] - df_final["value_Brent"]
        else:
            df_final[final_col] = None

    column_order = [
        "assessDate",
        "value_Butane", "value_Propane", "value_LPG",
        "value_Paraxylene", "value_Propylene", "value_Benzene", "value_Brent",
        "value_LPG_final", "value_Paraxylene_final", "value_Propylene_final", "value_Benzene_final",
        "modDate_Butane", "modDate_Propane",
        "modDate_Paraxylene", "modDate_Propylene", "modDate_Benzene",
    ]
    for col in column_order:
        if col not in df_final.columns:
            df_final[col] = None
    return df_final[column_order].sort_values("assessDate")

def pivot_data_to_columns_price_forecast_bbm_short_term(df):
    """
    Pivot short-term BBM price forecast into wide format with crackspreads.
    """
    df["suffix"] = df["priceSymbol"].map(SYMBOL_MAP_BBM)

    df_price = df.pivot_table(
        index=["year", "month"], columns="suffix", values="price", aggfunc="first"
    ).reset_index()
    df_price.columns = ["year", "month"] + [
        f"price_{c}" for c in df_price.columns if c not in ["year", "month"]
    ]

    if "price_Brent" not in df_price.columns:
        print("[ST BBM Pivot] WARNING: Tidak ada data Brent ditemukan!")
        for product in BBM_PRODUCTS:
            df_price[f"price_{product}_crackspread"] = None
        return df_price.sort_values(["year", "month"])

    print("[ST BBM Pivot] Brent data found, calculating crackspreads...")
    for product in BBM_PRODUCTS:
        price_col      = f"price_{product}"
        crackspread_col = f"price_{product}_crackspread"
        df_price[crackspread_col] = (
            df_price[price_col] - df_price["price_Brent"]
            if price_col in df_price.columns else None
        )

    column_order = (
        ["year", "month"]
        + [f"price_{p}" for p in BBM_PRODUCTS]
        + ["price_Brent"]
        + [f"price_{p}_crackspread" for p in BBM_PRODUCTS]
    )
    for col in column_order:
        if col not in df_price.columns:
            df_price[col] = None
    return df_price[column_order].sort_values(["year", "month"])

def pivot_data_to_columns_price_forecast_bbm(df):
    """
    Pivot long-term BBM price forecast into wide annual format with crackspreads.
    """
    df["suffix"] = df["priceSymbol"].map(SYMBOL_MAP_BBM)

    df_price = df.pivot_table(
        index="year", columns="suffix", values="price", aggfunc="first"
    ).reset_index()
    df_price.columns = ["year"] + [
        f"price_{c}" for c in df_price.columns if c != "year"
    ]

    if "price_Brent" not in df_price.columns:
        print("[LT BBM Pivot] WARNING: Tidak ada data Brent ditemukan!")
        for product in BBM_PRODUCTS:
            df_price[f"price_{product}_crackspread"] = None
        return df_price.sort_values("year")

    print("[LT BBM Pivot] Brent data found, calculating crackspreads...")
    for product in BBM_PRODUCTS:
        price_col       = f"price_{product}"
        crackspread_col = f"price_{product}_crackspread"
        df_price[crackspread_col] = (
            df_price[price_col] - df_price["price_Brent"]
            if price_col in df_price.columns else None
        )

    column_order = (
        ["year"]
        + [f"price_{p}" for p in BBM_PRODUCTS]
        + ["price_Brent"]
        + [f"price_{p}_crackspread" for p in BBM_PRODUCTS]
    )
    for col in column_order:
        if col not in df_price.columns:
            df_price[col] = None
    return df_price[column_order].sort_values("year")


# Data Merge

def _merge_suffix_columns(df_merged):
    """Resolve _old/_new suffix columns after an outer merge, preferring _new values."""
    for col in list(df_merged.columns):
        if col.endswith("_old"):
            base    = col.replace("_old", "")
            new_col = f"{base}_new"
            if new_col in df_merged.columns:
                df_merged[base] = df_merged[new_col].fillna(df_merged[col])
            else:
                df_merged[base] = df_merged[col]
        elif col.endswith("_new") and f'{col.replace("_new", "")}_old' not in df_merged.columns:
            df_merged[col.replace("_new", "")] = df_merged[col]

    drop_cols = [c for c in df_merged.columns if c.endswith("_old") or c.endswith("_new")]
    return df_merged.drop(columns=drop_cols)

def merge_with_existing_data(df_old, df_new):
    """Merge SAF/BBM DataFrames on assessDate, preferring new values on conflict."""
    if df_old.empty:
        return df_new
    if df_new.empty:
        return df_old

    # Neon returns datetime.date objects; API returns strings — normalize both to str
    df_old["assessDate"] = df_old["assessDate"].astype(str)
    df_new["assessDate"] = df_new["assessDate"].astype(str)

    for col in set(df_old.columns) | set(df_new.columns):
        if col not in df_old.columns:
            df_old[col] = None
        if col not in df_new.columns:
            df_new[col] = None

    df_merged = df_old.merge(df_new, on="assessDate", how="outer", suffixes=("_old", "_new"))
    df_merged = _merge_suffix_columns(df_merged)

    print(f"[Merge] Data sebelum deduplikasi: {len(df_merged)} baris.")
    value_cols  = [c for c in df_merged.columns if c.startswith("value_")]
    df_merged   = df_merged.drop_duplicates(subset=["assessDate"] + value_cols, keep="last")
    df_merged   = df_merged.sort_values("assessDate", ascending=True).reset_index(drop=True)

    print(f"[Merge] Data setelah deduplikasi: {len(df_merged)} baris.")
    print(f"[Merge] Data lama: {len(df_old)} | Data baru: {len(df_new)} | Final: {len(df_merged)}")
    return df_merged

def merge_with_existing_data_forecast(df_old, df_new):
    """Merge long-term forecast DataFrames on year, preferring new values on conflict."""
    if df_old.empty:
        return df_new
    if df_new.empty:
        return df_old

    for col in set(df_old.columns) | set(df_new.columns):
        if col not in df_old.columns:
            df_old[col] = None
        if col not in df_new.columns:
            df_new[col] = None

    df_merged = df_old.merge(df_new, on="year", how="outer", suffixes=("_old", "_new"))
    df_merged = _merge_suffix_columns(df_merged)

    print(f"[Merge] Data sebelum deduplikasi: {len(df_merged)} baris.")
    price_cols = [c for c in df_merged.columns if c.startswith("price_")]
    df_merged  = df_merged.drop_duplicates(subset=["year"] + price_cols, keep="last")
    df_merged  = df_merged.sort_values("year", ascending=True).reset_index(drop=True)

    print(f"[Merge] Data setelah deduplikasi: {len(df_merged)} baris.")
    print(f"[Merge] Data lama: {len(df_old)} | Data baru: {len(df_new)} | Final: {len(df_merged)}")
    return df_merged

def merge_with_existing_data_forecast_short_term(df_old, df_new):
    """Merge short-term forecast DataFrames on year+month, preferring new values."""
    if df_old.empty:
        return df_new
    if df_new.empty:
        return df_old

    for col in set(df_old.columns) | set(df_new.columns):
        if col not in df_old.columns:
            df_old[col] = None
        if col not in df_new.columns:
            df_new[col] = None

    df_merged = df_old.merge(
        df_new, on=["year", "month"], how="outer", suffixes=("_old", "_new")
    )
    df_merged = _merge_suffix_columns(df_merged)

    print(f"[Merge] Data sebelum deduplikasi: {len(df_merged)} baris.")
    price_cols = [c for c in df_merged.columns if c.startswith("price_")]
    df_merged  = df_merged.drop_duplicates(subset=["year", "month"] + price_cols, keep="last")
    df_merged  = df_merged.sort_values(["year", "month"], ascending=True).reset_index(drop=True)

    print(f"[Merge] Data setelah deduplikasi: {len(df_merged)} baris.")
    print(f"[Merge] Data lama: {len(df_old)} | Data baru: {len(df_new)} | Final: {len(df_merged)}")
    return df_merged

def merge_with_existing_data_petrochemical(df_old, df_new):
    """Merge petrochemical DataFrames on Year+Month, preferring new values."""
    if df_old.empty:
        return df_new
    if df_new.empty:
        return df_old

    for col in set(df_old.columns) | set(df_new.columns):
        if col not in df_old.columns:
            df_old[col] = None
        if col not in df_new.columns:
            df_new[col] = None

    df_merged = df_old.merge(
        df_new, on=["Year", "Month"], how="outer", suffixes=("_old", "_new")
    )
    df_merged = _merge_suffix_columns(df_merged)

    print(f"[Merge] Data sebelum deduplikasi: {len(df_merged)} baris.")
    price_cols = [c for c in df_merged.columns if c.startswith("Price_")]
    df_merged  = df_merged.drop_duplicates(subset=["Year", "Month"] + price_cols, keep="last")
    df_merged  = df_merged.sort_values(["Year", "Month"], ascending=True).reset_index(drop=True)

    print(f"[Merge] Data setelah deduplikasi: {len(df_merged)} baris.")
    print(f"[Merge] Data lama: {len(df_old)} | Data baru: {len(df_new)} | Final: {len(df_merged)}")
    return df_merged


# Storage Read / Write

def _last_saved_date(sheet_name, date_col="assessDate"):
    """Return the latest date_col value already in storage, or None if empty/missing.

    Used to self-heal: resume from the day after the last saved row instead of
    a fixed trailing window, so a missed scheduled run doesn't create a
    permanent gap.
    """
    df = storage.read_structured_sheet(sheet_name)
    if df.empty or date_col not in df.columns:
        return None
    dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
    return dates.max().date() if not dates.empty else None


def _write_sheet_to_storage(sheet_name, df_new, merge_key="assessDate"):
    """
    Merge df_new with the existing storage sheet and write the result.

    merge_key determines which merge strategy is used.
    """
    print(f"\n[Write] Menyiapkan sheet '{sheet_name}'...")

    df_old = storage.read_structured_sheet(sheet_name)

    if merge_key == "year":
        df_final = merge_with_existing_data_forecast(df_old, df_new)
    elif isinstance(merge_key, list) and "month" in merge_key:
        df_final = merge_with_existing_data_forecast_short_term(df_old, df_new)
    elif isinstance(merge_key, list) and "Month" in merge_key:
        df_final = merge_with_existing_data_petrochemical(df_old, df_new)
    else:
        df_final = merge_with_existing_data(df_old, df_new)

    storage.write_structured_sheet(sheet_name, df_final)
    print(f"[Write] Sheet '{sheet_name}' berhasil disimpan ({len(df_final)} rows).")


# Public Entry Points

def main_saf_daily():
    """Scrape and save current SAF and UCO prices from S&P Global."""
    print(f"\n{'='*60}")
    print("SCRAPER SAF — CURRENT (DAILY)")
    print(f"{'='*60}")

    sp_token = login_spglobal()
    if not sp_token:
        print("[Main] Gagal login ke S&P Global API.")
        return

    df_current = get_current_data(sp_token, SAF_SYMBOLS)
    if df_current is None:
        print("\n[Main] Gagal mengambil data current.")
        return

    df_pivoted = pivot_data_to_columns_saf(df_current)
    _write_sheet_to_storage(SHEET_NAME_SAF, df_pivoted)

    print(f"\n{'='*60}")
    print("[Main] DATA BERHASIL DISIMPAN")
    print(f"{'='*60}")
    print(f"[Main] Sheet : {SHEET_NAME_SAF}")
    print(f"[Main] Format: assessDate | value_UCO | value_SAF | modDate_UCO | modDate_SAF")
    print(f"[Main] Rows  : {len(df_pivoted)}")
    print(f"\n{'='*60}\n[Main] SELESAI\n{'='*60}")

def main_saf_weekly(start_date: str | None = None, end_date: str | None = None):
    """Scrape and save historical SAF and UCO prices from S&P Global.

    Without arguments, self-heals: resumes from the day after the last saved
    assessDate (falling back to a 7-day window if the sheet is empty), so a
    missed scheduled run gets caught up automatically. Pass start_date/end_date
    for an explicit backfill range.
    """
    print(f"\n{'='*60}")
    print("SCRAPER SAF — HISTORICAL (WEEKLY)")
    print(f"{'='*60}")

    end_date = end_date or datetime.today().strftime("%Y-%m-%d")
    if start_date is None:
        last_date  = _last_saved_date(SHEET_NAME_SAF)
        start_date = ((last_date + timedelta(days=1)) if last_date
                      else (datetime.today() - timedelta(days=7)).date()).strftime("%Y-%m-%d")
    if start_date > end_date:
        print(f"[Main] Sudah up-to-date (data terakhir: {start_date}) — skip.")
        return

    sp_token = login_spglobal()
    if not sp_token:
        print("[Main] Gagal login ke S&P Global API.")
        return

    print(f"\n[Main] Period: {start_date} to {end_date}")
    df_historical = get_historical_data(sp_token, SAF_SYMBOLS, start_date, end_date)
    if df_historical is None:
        print("\n[Main] Gagal mengambil data historical.")
        return

    df_pivoted = pivot_data_to_columns_saf(df_historical)
    _write_sheet_to_storage(SHEET_NAME_SAF, df_pivoted)

    print(f"\n{'='*60}")
    print("[Main] DATA BERHASIL DISIMPAN")
    print(f"{'='*60}")
    print(f"[Main] Sheet : {SHEET_NAME_SAF}")
    print(f"[Main] Rows  : {len(df_pivoted)}")
    print(f"\n{'='*60}\n[Main] SELESAI\n{'='*60}")

def _prev_month(today=None):
    """Return (year, month) of the calendar month before today."""
    today = today or datetime.today()
    return (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)


def _month_range(start_year, start_month, end_year, end_month):
    """Inclusive list of (year, month) tuples from start to end."""
    months = []
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def _missing_months(sheet_name, year_col, month_col):
    """Months from (last saved +1) through last calendar month.

    Returns None if the sheet has no usable data yet (caller should default
    to just the last calendar month, matching the original single-month
    behavior). Returns [] if already up-to-date.
    """
    end_year, end_month = _prev_month()

    df = storage.read_structured_sheet(sheet_name)
    if df.empty or year_col not in df.columns or month_col not in df.columns:
        return None
    df = df.dropna(subset=[year_col, month_col])
    if df.empty:
        return None

    last_year  = int(df[year_col].max())
    last_month = int(df.loc[df[year_col] == last_year, month_col].max())

    start_month = last_month + 1
    start_year  = last_year
    if start_month > 12:
        start_month = 1
        start_year += 1

    if (start_year, start_month) > (end_year, end_month):
        return []
    return _month_range(start_year, start_month, end_year, end_month)


def _fetch_petrochemical_month(sp_token, year, month):
    """Fetch and pivot one month of short-term petrochemical + crackspread data.

    Returns a 1-row DataFrame, or None if nothing could be fetched.
    """
    all_data = []
    for product in PETCHEM_PRODUCTS:
        data = get_historical_price_petrochemical_short_term(
            sp_token, product["name"], product["basis"], year, month
        )
        if data:
            print(f"[Main] Berhasil: {len(data)} records untuk {product['name']}.")
            all_data.append(data)
        else:
            print(f"[Main] Gagal mengambil data untuk {product['name']}.")

    if not all_data:
        print("\n[Main] Tidak ada data yang berhasil diambil.")
        return None

    df_pivoted = pivot_data_petrochemical(all_data)
    prices     = get_non_bbm_price_from_bbm_forecast(sp_token, year, month)

    df_pivoted["Price_Brent"]   = prices["Brent"]
    df_pivoted["Price_Butane"]  = prices["Butane"]
    df_pivoted["Price_Propane"] = prices["Propane"]

    if prices["Butane"] is not None and prices["Propane"] is not None:
        lpg = 0.5 * prices["Butane"] + 0.5 * prices["Propane"]
        df_pivoted["Price_LPG"] = lpg
        print(f"\n[Main] Harga LPG (0.5*Butane + 0.5*Propane): ${lpg}/MT")
    else:
        df_pivoted["Price_LPG"] = None
        print("\n[Main] WARNING: Harga Butane atau Propane tidak tersedia — LPG tidak dihitung.")

    if prices["Brent"] is not None:
        print(f"\n[Main] Menghitung crackspread dengan Brent = ${prices['Brent']}/MT")
        for product in PETCHEM_PRODUCTS:
            name           = product["name"]
            price_col      = f"Price_{name}"
            crackspread_col = f"Price_{name}_crackspread"
            if price_col in df_pivoted.columns:
                df_pivoted[crackspread_col] = df_pivoted[price_col] - prices["Brent"]
                print(f"[Main] Crackspread {name}: {price_col} - Brent")
            else:
                df_pivoted[crackspread_col] = None
                print(f"[Main] Data {name} tidak tersedia.")
    else:
        print("\n[Main] WARNING: Harga Brent tidak tersedia — crackspread tidak dihitung.")
        for product in PETCHEM_PRODUCTS:
            df_pivoted[f'Price_{product["name"]}_crackspread'] = None

    if prices["Brent"] is not None and df_pivoted.get("Price_LPG", [None]).iloc[0] is not None:
        df_pivoted["Price_LPG_crackspread"] = df_pivoted["Price_LPG"] - prices["Brent"]
        print("[Main] Crackspread LPG: LPG - Brent")
    else:
        df_pivoted["Price_LPG_crackspread"] = None
        print("[Main] Crackspread LPG tidak dapat dihitung.")

    return df_pivoted


def main_petrochemical_short_term(start_year=None, start_month=None, end_year=None, end_month=None):
    """Scrape and save short-term petrochemical prices with crackspreads.

    Without arguments, self-heals: catches up every month between the last
    saved row and last calendar month, so a missed day-12 scheduled run
    doesn't create a permanent gap. Pass start_year/start_month (and
    optionally end_year/end_month) for an explicit backfill range.
    """
    print(f"\n{'='*60}")
    print("SCRAPER PETROCHEMICAL — SHORT TERM")
    print(f"{'='*60}")

    if start_year is None:
        missing = _missing_months(SHEET_NAME_PETROCHEMICAL, "Year", "Month")
        months  = missing if missing is not None else [_prev_month()]
    else:
        end_year, end_month = end_year or start_year, end_month or start_month
        months = _month_range(start_year, start_month, end_year, end_month)

    if not months:
        print("[Main] Sudah up-to-date — skip.")
        return

    sp_token = login_spglobal()
    if not sp_token:
        print("[Main] Gagal login ke S&P Global API.")
        return

    frames = []
    for year, month in months:
        print(f"\n[Main] Period : {year}-{month:02d}")
        df_month = _fetch_petrochemical_month(sp_token, year, month)
        if df_month is not None:
            frames.append(df_month)

    if not frames:
        print("\n[Main] Tidak ada data yang berhasil diambil.")
        # exit(1)
        return

    df_pivoted = pd.concat(frames, ignore_index=True)

    column_order = ["Year", "Month"]
    for product in PETCHEM_PRODUCTS:
        col = f'Price_{product["name"]}'
        if col in df_pivoted.columns:
            column_order.append(col)
    column_order.extend(["Price_Butane", "Price_Propane", "Price_LPG", "Price_Brent"])
    for product in PETCHEM_PRODUCTS:
        col = f'Price_{product["name"]}_crackspread'
        if col in df_pivoted.columns:
            column_order.append(col)
    column_order.append("Price_LPG_crackspread")
    for col in column_order:
        if col not in df_pivoted.columns:
            df_pivoted[col] = None
    df_pivoted = df_pivoted[column_order]

    _write_sheet_to_storage(SHEET_NAME_PETROCHEMICAL, df_pivoted, merge_key=["Year", "Month"])
    print(f"\n{'='*60}\n[Main] SELESAI\n{'='*60}")

def main_price_forecast_short_term_bbm(start_year=None, start_month=None, end_year=None, end_month=None):
    """Scrape and save short-term BBM price forecast with crackspreads.

    Without arguments, self-heals: catches up every month between the last
    saved row and last calendar month, so a missed day-12 scheduled run
    doesn't create a permanent gap. Pass start_year/start_month (and
    optionally end_year/end_month) for an explicit backfill range.
    """
    print(f"\n{'='*60}")
    print("SCRAPER PRICE FORECAST BBM — SHORT TERM")
    print(f"{'='*60}")

    if start_year is None:
        missing = _missing_months(SHEET_NAME_FORECAST_BBM_SHORT, "year", "month")
        months  = missing if missing is not None else [_prev_month()]
    else:
        end_year, end_month = end_year or start_year, end_month or start_month
        months = _month_range(start_year, start_month, end_year, end_month)

    if not months:
        print("[Main] Sudah up-to-date — skip.")
        return

    sp_token = login_spglobal()
    if not sp_token:
        print("[Main] Gagal login ke S&P Global API.")
        return

    frames = []
    for year, month in months:
        print(f"\n[Main] Period  : {year}-{month:02d}")
        print(f"[Main] Symbols : {', '.join(BBM_SYMBOLS_ST)}")
        df_month = get_historical_price_energy_forecast_short_term(
            sp_token, BBM_SYMBOLS_ST, year, month, unitName="BBL",
            fields=["year", "month", "price", "priceSymbol"]
        )
        if df_month is not None and not df_month.empty:
            frames.append(df_month)
        else:
            print(f"[Main] Gagal mengambil data forecast untuk {year}-{month:02d}.")

    if not frames:
        print("\n[Main] Tidak ada data yang berhasil diambil.")
        # exit(1)
        return

    df_forecast = pd.concat(frames, ignore_index=True)
    df_pivoted  = pivot_data_to_columns_price_forecast_bbm_short_term(df_forecast)
    _write_sheet_to_storage(SHEET_NAME_FORECAST_BBM_SHORT, df_pivoted, merge_key=["year", "month"])

    print(f"\n{'='*60}")
    print("[Main] DATA BERHASIL DISIMPAN")
    print(f"{'='*60}")
    print(f"[Main] Sheet : {SHEET_NAME_FORECAST_BBM_SHORT}")
    print(f"[Main] Rows  : {len(df_pivoted)}")
    print(f"\n{'='*60}\n[Main] SELESAI\n{'='*60}")

def main_price_forecast_long_term_bbm(start_year=None, end_year=None):
    """Scrape and save long-term BBM price forecast with crackspreads.

    Without arguments, refreshes the current year's forecast (idempotent
    upsert keyed on year). Pass start_year/end_year for an explicit backfill
    range of past forecast years.
    """
    print(f"\n{'='*60}")
    print("SCRAPER PRICE FORECAST BBM — LONG TERM")
    print(f"{'='*60}")

    start_year = start_year or datetime.today().year
    end_year   = end_year or start_year

    sp_token = login_spglobal()
    if not sp_token:
        print("[Main] Gagal login ke S&P Global API.")
        return

    print(f"\n[Main] Period  : {start_year}-{end_year}")
    print(f"[Main] Symbols : {', '.join(BBM_SYMBOLS_LT)}")

    df_forecast = get_historical_price_energy_forecast_long_term(
        sp_token, BBM_SYMBOLS_LT, start_year, end_year, unitName="BBL",
        fields=["year", "price", "priceSymbol"]
    )
    if df_forecast is None or df_forecast.empty:
        print("\n[Main] Gagal mengambil data forecast.")
        # exit(1)
        return

    df_pivoted = pivot_data_to_columns_price_forecast_bbm(df_forecast)
    _write_sheet_to_storage(SHEET_NAME_FORECAST_BBM_LONG, df_pivoted, merge_key="year")

    print(f"\n{'='*60}")
    print("[Main] DATA BERHASIL DISIMPAN")
    print(f"{'='*60}")
    print(f"[Main] Sheet : {SHEET_NAME_FORECAST_BBM_LONG}")
    print(f"[Main] Rows  : {len(df_pivoted)}")
    print(f"\n{'='*60}\n[Main] SELESAI\n{'='*60}")


def main_crackspeed_bbm_weekly(start_date: str | None = None, end_date: str | None = None):
    """Scrape and save historical BBM crackspeed prices from S&P Global.

    Without arguments, self-heals: resumes from the day after the last saved
    assessDate (falling back to a 7-day window if the sheet is empty), so a
    missed scheduled run gets caught up automatically. Pass start_date/end_date
    for an explicit backfill range.
    """
    print(f"\n{'='*60}")
    print("SCRAPER CRACKSPEED BBM — HISTORICAL (WEEKLY)")
    print(f"{'='*60}")

    end_date = end_date or datetime.today().strftime("%Y-%m-%d")
    if start_date is None:
        last_date  = _last_saved_date(SHEET_NAME_CRACKSPEED_BBM)
        start_date = ((last_date + timedelta(days=1)) if last_date
                      else (datetime.today() - timedelta(days=7)).date()).strftime("%Y-%m-%d")
    if start_date > end_date:
        print(f"[Main] Sudah up-to-date (data terakhir: {start_date}) — skip.")
        return

    sp_token = login_spglobal()
    if not sp_token:
        print("[Main] Gagal login ke S&P Global API.")
        return

    bbm_symbols = ["PGAEY00", "PGAEZ00", "PGAMS00", "AMFSA00", "PJABF00", "AAPPF00", "AACUE00", "PCAAS00"]
    print(f"\n[Main] Period : {start_date} to {end_date}")
    print(f"[Main] Symbols: {', '.join(bbm_symbols)}")

    df_historical = get_historical_data(sp_token, bbm_symbols, start_date, end_date)
    if df_historical is None:
        print("\n[Main] Gagal mengambil data historical.")
        return

    df_pivoted = pivot_data_to_columns_bbm(df_historical)
    _write_sheet_to_storage(SHEET_NAME_CRACKSPEED_BBM, df_pivoted)

    print(f"\n{'='*60}")
    print("[Main] DATA BERHASIL DISIMPAN")
    print(f"{'='*60}")
    print(f"[Main] Sheet : {SHEET_NAME_CRACKSPEED_BBM}")
    print(f"[Main] Rows  : {len(df_pivoted)}")
    print(f"\n{'='*60}\n[Main] SELESAI\n{'='*60}")


def main_crackspeed_non_bbm_weekly(start_date: str | None = None, end_date: str | None = None):
    """Scrape and save historical non-BBM crackspeed prices from S&P Global.

    Without arguments, self-heals: resumes from the day after the last saved
    assessDate (falling back to a 7-day window if the sheet is empty), so a
    missed scheduled run gets caught up automatically. Pass start_date/end_date
    for an explicit backfill range.
    """
    print(f"\n{'='*60}")
    print("SCRAPER CRACKSPEED NON BBM — HISTORICAL (WEEKLY)")
    print(f"{'='*60}")

    end_date = end_date or datetime.today().strftime("%Y-%m-%d")
    if start_date is None:
        last_date  = _last_saved_date(SHEET_NAME_CRACKSPEED_NON_BBM)
        start_date = ((last_date + timedelta(days=1)) if last_date
                      else (datetime.today() - timedelta(days=7)).date()).strftime("%Y-%m-%d")
    if start_date > end_date:
        print(f"[Main] Sudah up-to-date (data terakhir: {start_date}) — skip.")
        return

    sp_token = login_spglobal()
    if not sp_token:
        print("[Main] Gagal login ke S&P Global API.")
        return

    non_bbm_symbols = ["PTAAF10", "PTAAM10", "PHABV00", "PHAKR00", "PHASM05", "PCAAS00"]
    print(f"\n[Main] Period : {start_date} to {end_date}")
    print(f"[Main] Symbols: {', '.join(non_bbm_symbols)}")

    df_historical = get_historical_data(sp_token, non_bbm_symbols, start_date, end_date)
    if df_historical is None:
        print("\n[Main] Gagal mengambil data historical.")
        return

    df_pivoted = pivot_data_to_columns_non_bbm(df_historical)
    _write_sheet_to_storage(SHEET_NAME_CRACKSPEED_NON_BBM, df_pivoted)

    print(f"\n{'='*60}")
    print("[Main] DATA BERHASIL DISIMPAN")
    print(f"{'='*60}")
    print(f"[Main] Sheet : {SHEET_NAME_CRACKSPEED_NON_BBM}")
    print(f"[Main] Rows  : {len(df_pivoted)}")
    print(f"\n{'='*60}\n[Main] SELESAI\n{'='*60}")


# # Script Entry Point

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("MENJALANKAN SEMUA SCRAPER S&P GLOBAL")
    print(f"{'='*60}")

    functions = [
        ("SAF Daily",                     main_saf_daily),
        ("SAF Weekly",                    main_saf_weekly),
        ("Crackspeed BBM Weekly",         main_crackspeed_bbm_weekly),
        ("Crackspeed Non-BBM Weekly",     main_crackspeed_non_bbm_weekly),
        ("Petrochemical Short Term",      main_petrochemical_short_term),
        ("Price Forecast BBM Short Term", main_price_forecast_short_term_bbm),
        ("Price Forecast BBM Long Term",  main_price_forecast_long_term_bbm),
    ]

    for name, func in functions:
        print(f"\n{'='*60}")
        print(f"MENJALANKAN: {name}")
        print(f"{'='*60}")
        try:
            func()
        except SystemExit:
            print(f"[Main] {name} keluar lebih awal (exit dipanggil).")
        except Exception as exc:
            print(f"[Main] Error pada {name}: {exc}")
            import traceback
            traceback.print_exc()
            print(f"[Main] Melanjutkan ke scraper berikutnya...")

    print(f"\n{'='*60}")
    print("SEMUA SCRAPER SELESAI")
    print(f"{'='*60}")