
import pandas as pd
import sys
import os

# Add parent directory
sys.path.append(os.path.join(os.getcwd(), 'azure_functions'))

from scrapers.sandp_data_scraper import SAndPDataScraper

def test_pivot_bbm_forecast():
    scraper = SAndPDataScraper()
    
    # Mock DataFrame matching API output structure
    data = [
        {'year': 2024, 'month': 1, 'price': 80.0, 'priceSymbol': 'PCAAS00'}, # Brent
        {'year': 2024, 'month': 1, 'price': 90.0, 'priceSymbol': 'PGAEY00'}, # RON92
        {'year': 2024, 'month': 1, 'price': 100.0, 'priceSymbol': 'PJABF00'}, # JetKero
    ]
    df = pd.DataFrame(data)
    
    print("Testing pivot_bbm_forecast...")
    result = scraper.pivot_bbm_forecast(df, is_short_term=True)
    
    print("Columns:", result.columns.tolist())
    
    expected_cols = ['year', 'month', 'brent', 'price_brent', 'price_ron92', 'price_jetkero']
    for col in expected_cols:
        if col in result.columns:
            print(f"✅ Found {col}")
        else:
            # check for alternative name
            if col == 'brent' and 'price_brent' in result.columns: 
                 # brent is mapped from price_brent
                 pass
            elif col != 'brent': # brent is optional in my logic check
                 print(f"❌ Missing {col}")

    # Check snake_case conversion
    if 'price_ron92' in result.columns:
        print("✅ Column is snake_case (price_ron92)")
    else:
        print("❌ Column is NOT snake_case")
        
    # Check crackspread calculation
    if 'ron92_cs' in result.columns:
        print("✅ Found ron92_cs")
        print(f"Value: {result.iloc[0]['ron92_cs']} (Expected 10.0)")
    else:
        print("❌ Missing ron92_cs")

def test_pivot_saf_uco():
    scraper = SAndPDataScraper()
    
    data = [
        {'assessDate': '2024-01-01', 'value': 100, 'symbol': 'UCFCC00', 'modDate': '2024-01-02'},
        {'assessDate': '2024-01-01', 'value': 200, 'symbol': 'SFSMR00', 'modDate': '2024-01-02'},
    ]
    df = pd.DataFrame(data)
    
    print("\nTesting pivot_saf_uco_data...")
    result = scraper.pivot_saf_uco_data(df)
    
    print("Columns:", result.columns.tolist())
    
    expected = ['assess_date', 'value_uco', 'value_saf', 'mod_date_uco', 'mod_date_saf']
    for col in expected:
        if col in result.columns:
            print(f"✅ Found {col}")
        else:
            print(f"❌ Missing {col}")

if __name__ == "__main__":
    try:
        test_pivot_bbm_forecast()
        test_pivot_saf_uco()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
