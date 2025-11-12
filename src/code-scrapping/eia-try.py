import requests
import pandas as pd
from datetime import datetime
API_KEY = "kODFA7mKVrNKWrGyFiIk5fIdlC1AKGXzba5lJxzY"
import requests
import json
import pandas as pd

import requests
import pandas as pd
import json

import requests
import pandas as pd
import json

# ============================================================================
# CONFIGURATION
# ============================================================================
BASE_URL = "https://api.eia.gov/v2/steo/data/"

# ============================================================================
# STEP 1: EXPLORE STEO DATA - CEK APA AJA YANG TERSEDIA
# ============================================================================
def explore_steo_data():
    print("=" * 80)
    print("🔍 STEP 1: EXPLORING STEO DATA")
    print("=" * 80)
    print()
    
    params = {
        "api_key": API_KEY,
        "frequency": "monthly",
        "length": 5000  # Ambil banyak untuk lihat semua data
    }
    
    print("📡 Fetching STEO data...")
    print(f"URL: {BASE_URL}")
    print(f"Params: {json.dumps(params, indent=2)}")
    print()
    
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Response Status: {response.status_code}")
        print()
        
        # Check structure
        print("📋 Response Structure:")
        print(f"Keys: {list(data.keys())}")
        print()
        
        if "response" in data:
            print("Response metadata:")
            response_data = data["response"]
            print(f"  Total records: {response_data.get('total', 'N/A')}")
            print()
            
            if "data" in response_data and len(response_data["data"]) > 0:
                df = pd.DataFrame(response_data["data"])
                
                print(f"✅ Got {len(df)} records")
                print()
                
                # Show columns
                print("=" * 80)
                print("📊 DATA STRUCTURE")
                print("=" * 80)
                print(f"Columns: {list(df.columns)}")
                print()
                
                # Show sample data
                print("=" * 80)
                print("👀 SAMPLE DATA (first 10 rows)")
                print("=" * 80)
                print(df.head(10).to_string(index=False))
                print()
                
                # Analyze unique values
                print("=" * 80)
                print("🔍 UNIQUE VALUES ANALYSIS")
                print("=" * 80)
                print()
                
                for col in df.columns:
                    unique_count = df[col].nunique()
                    print(f"{col}:")
                    print(f"  - Unique values: {unique_count}")
                    
                    if unique_count <= 30:
                        unique_vals = sorted([str(v) for v in df[col].unique() if v is not None])
                        print(f"  - Values: {', '.join(unique_vals[:20])}")
                        if len(unique_vals) > 20:
                            print(f"    ... and {len(unique_vals) - 20} more")
                    else:
                        sample_vals = sorted([str(v) for v in df[col].unique() if v is not None])[:10]
                        print(f"  - Sample: {', '.join(sample_vals)} ...")
                    print()
                
                # Look for series IDs
                if 'seriesId' in df.columns or 'series_id' in df.columns or 'series-id' in df.columns:
                    series_col = 'seriesId' if 'seriesId' in df.columns else ('series_id' if 'series_id' in df.columns else 'series-id')
                    
                    print("=" * 80)
                    print("📌 AVAILABLE SERIES")
                    print("=" * 80)
                    
                    series_list = df[series_col].unique()
                    print(f"\nTotal unique series: {len(series_list)}")
                    print()
                    
                    # Look for petroleum-related series
                    petroleum_series = [s for s in series_list if s and any(keyword in str(s).upper() for keyword in ['PAPR', 'PASC', 'PETRO', 'OIL', 'PROD', 'CONS'])]
                    
                    if petroleum_series:
                        print("🛢️  PETROLEUM-RELATED SERIES:")
                        for series in sorted(petroleum_series)[:20]:
                            series_data = df[df[series_col] == series]
                            name = series_data['seriesDescription'].iloc[0] if 'seriesDescription' in df.columns else 'N/A'
                            print(f"  - {series}: {name}")
                        
                        if len(petroleum_series) > 20:
                            print(f"  ... and {len(petroleum_series) - 20} more petroleum series")
                    
                    print()
                    print("All series (first 30):")
                    for series in sorted(series_list)[:30]:
                        series_data = df[df[series_col] == series]
                        if 'seriesDescription' in df.columns:
                            name = series_data['seriesDescription'].iloc[0]
                            print(f"  - {series}: {name}")
                        else:
                            print(f"  - {series}")
                    
                    if len(series_list) > 30:
                        print(f"  ... and {len(series_list) - 30} more")
                
                return df
            else:
                print("❌ No data found in response")
                print(f"Response: {json.dumps(data, indent=2)}")
                return None
        else:
            print("❌ Unexpected response structure")
            print(f"Response: {json.dumps(data, indent=2)}")
            return None
            
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        print(f"Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

# ============================================================================
# STEP 2: GET SPECIFIC SERIES DATA
# ============================================================================
def get_specific_series(series_id, start_date="2024-11", end_date="2025-11"):
    print()
    print("=" * 80)
    print(f"📊 STEP 2: GETTING SPECIFIC SERIES - {series_id}")
    print("=" * 80)
    print()
    
    params = {
        "api_key": API_KEY,
        "frequency": "monthly",
        "data[0]": "value",
        "facets[seriesId][]": series_id,
        "start": start_date,
        "end": end_date,
        "sort[0][column]": "period",
        "sort[0][direction]": "desc"
    }
    
    print(f"📡 Fetching data for series: {series_id}")
    print(f"Period: {start_date} to {end_date}")
    print()
    
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "response" in data and "data" in data["response"]:
            records = data["response"]["data"]
            df = pd.DataFrame(records)
            
            print(f"✅ Got {len(df)} records")
            print()
            
            if len(df) > 0:
                print("📋 Data Preview:")
                print("-" * 80)
                display_cols = ['period', 'value', 'unit']
                available_cols = [col for col in display_cols if col in df.columns]
                
                if 'seriesDescription' in df.columns:
                    print(f"Series Description: {df['seriesDescription'].iloc[0]}")
                    print()
                
                print(df[available_cols].head(20).to_string(index=False))
                print()
                
                # Statistics
                if 'value' in df.columns:
                    df_numeric = df[df['value'].notna()].copy()
                    df_numeric['value_num'] = pd.to_numeric(df_numeric['value'], errors='coerce')
                    df_numeric = df_numeric.dropna(subset=['value_num'])
                    
                    if len(df_numeric) > 0:
                        print("📊 Statistics:")
                        print(f"  Mean: {df_numeric['value_num'].mean():.2f}")
                        print(f"  Min: {df_numeric['value_num'].min():.2f} (period: {df_numeric.loc[df_numeric['value_num'].idxmin(), 'period']})")
                        print(f"  Max: {df_numeric['value_num'].max():.2f} (period: {df_numeric.loc[df_numeric['value_num'].idxmax(), 'period']})")
                        print()
                
                return df
            else:
                print("⚠️  No data returned for this series")
                return None
        else:
            print("❌ No data found")
            print(f"Response: {json.dumps(data, indent=2)}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

# ============================================================================
# STEP 3: GET PETROLEUM PRODUCTION & CONSUMPTION
# ============================================================================
def get_petroleum_data():
    print()
    print("=" * 80)
    print("🛢️  STEP 3: PETROLEUM PRODUCTION & CONSUMPTION DATA")
    print("=" * 80)
    print()
    
    # Common STEO petroleum series IDs
    series_to_fetch = {
        "PAPR_WORLD": "World Petroleum Production",
        "PASC_WORLD": "World Petroleum Consumption",
        "PAPR_OPEC": "OPEC Petroleum Production",
        "PAPR_NONOPEC": "Non-OPEC Petroleum Production",
    }
    
    results = {}
    
    for series_id, description in series_to_fetch.items():
        print(f"Fetching: {description} ({series_id})")
        df = get_specific_series(series_id, "2024-01", "2025-11")
        
        if df is not None:
            results[series_id] = df
            
            # Export to CSV
            filename = f"steo_{series_id.lower()}.csv"
            df.to_csv(filename, index=False)
            print(f"✅ Saved to: {filename}")
        else:
            print(f"⚠️  Could not fetch {series_id}")
        
        print()
    
    return results

# ============================================================================
# MAIN EXECUTION
# ============================================================================
if __name__ == "__main__":
    print()
    print("🛢️  EIA STEO (Short-Term Energy Outlook) DATA EXPLORER")
    print()
    
    # Step 1: Explore to see what's available
    all_data = explore_steo_data()
    
    # Step 2: Get petroleum-specific data
    if all_data is not None:
        petroleum_data = get_petroleum_data()
        
        print()
        print("=" * 80)
        print("💡 HOW TO USE THIS DATA")
        print("=" * 80)
        print("""
The STEO API provides Short-Term Energy Outlook data.

Common Petroleum Series IDs:
- PAPR_WORLD: World Petroleum Production
- PASC_WORLD: World Petroleum Consumption  
- PAPR_OPEC: OPEC Production
- PAPR_NONOPEC: Non-OPEC Production
- PAPR_OECD: OECD Production
- PASC_OECD: OECD Consumption

To get specific series:
1. Find the series ID from Step 1 output
2. Use get_specific_series(series_id, start, end)
3. Data is automatically saved to CSV

Example API call:
https://api.eia.gov/v2/steo/data/?api_key=YOUR_KEY&frequency=monthly&facets[seriesId][]=PAPR_WORLD&start=2024-01&end=2025-11
        """)
    
    print()
    print("=" * 80)
    print("✨ DONE!")
    print("=" * 80)
    print()