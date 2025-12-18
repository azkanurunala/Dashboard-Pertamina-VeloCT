import pandas as pd
import time
from datetime import datetime
import sys
import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import json

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from code_scrapping.kontan import scrape_kontan

def get_gspread_client():
    creds_json = os.getenv('GOOGLE_CREDENTIALS')
    if creds_json:
        print("Using GOOGLE_CREDENTIALS from environment")
        creds_dict = json.loads(creds_json)
        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
    else:
        possible_paths = [
            'credentials.json',
            os.path.join(os.path.dirname(__file__), 'credentials.json'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'credentials.json')
        ]
        
        creds_file = None
        for path in possible_paths:
            if os.path.exists(path):
                creds_file = path
                break
        
        if not creds_file:
            raise Exception(
                "\n❌ No credentials.json found!\n"
                "\n📝 Make sure credentials.json is in one of:\n"
                "   - Project root folder\n"
                "   - scrapper/main_scrapper/ folder\n"
            )
        
        print(f"📋 Using credentials from: {creds_file}")
        credentials = Credentials.from_service_account_file(
            creds_file,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
    
    client = gspread.authorize(credentials)
    print("✅ Connected to Google Sheets")
    return client

def read_worksheet_gsheet(worksheet):
    """Read data from Google Sheets worksheet"""
    try:
        data = worksheet.get_all_values()
        if not data or len(data) <= 1:
            return pd.DataFrame()
        
        headers = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=headers)
        return df
    except Exception as e:
        print(f"⚠️  Error reading worksheet: {e}")
        return pd.DataFrame()

def write_worksheet_gsheet(worksheet, df):
    """Write data to Google Sheets worksheet"""
    try:
        worksheet.clear()
        
        headers = df.columns.tolist()
        values = [headers] + df.values.tolist()
        
        values = [[str(cell) if pd.notna(cell) else "" for cell in row] for row in values]
        
        worksheet.update('A1', values)
        
        print(f"✅ Successfully wrote {len(df)} rows")
        return True
    except Exception as e:
        print(f"❌ Error writing to worksheet: {e}")
        return False

def get_or_create_worksheet(spreadsheet, sheet_name):
    """Get existing worksheet or create new one"""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        print(f"📄 Found existing sheet: {sheet_name}")
        return worksheet
    except gspread.exceptions.WorksheetNotFound:
        print(f"📝 Creating new sheet: {sheet_name}")
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
        return worksheet

def test_kontan_to_gsheet():
    print("\n" + "=" * 80)
    print("🧪 TEST KONTAN SCRAPER TO GOOGLE SHEETS")
    print("=" * 80)
    
    # Load environment
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    
    # Test configuration - bisa dari env atau default
    keyword = os.getenv('KEYWORD', 'ekonomi')
    tanggal_filter = os.getenv('TANGGAL_FILTER', '2024-12-18')
    sheet_name = f"(Test)Kontan {keyword.title()}"
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    
    print(f"\n📋 Test Configuration:")
    print(f"   Keyword: {keyword}")
    print(f"   Date: {tanggal_filter if tanggal_filter else 'No filter'}")
    print(f"   Sheet Name: {sheet_name}")
    print(f"   Spreadsheet ID: {spreadsheet_id[:20]}..." if spreadsheet_id else "   ❌ SPREADSHEET_ID not found!")
    print(f"   Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not spreadsheet_id:
        print("\n❌ ERROR: SPREADSHEET_ID not found in .env!")
        return
    
    # Connect to Google Sheets
    try:
        print("\n🔗 Connecting to Google Sheets...")
        client = get_gspread_client()
        spreadsheet = client.open_by_key(spreadsheet_id)
        print(f"✅ Connected to: {spreadsheet.title}")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return
    
    # Scrape data
    print(f"\n🚀 Starting Kontan scraper...")
    print("=" * 80)
    
    try:
        hasil = scrape_kontan(keyword, tanggal_filter)
        
        print(f"\n📊 Scraping result: {len(hasil)} articles")
        
        if not hasil:
            print("⚠️  No articles found!")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(hasil)
        df['source'] = 'KONTAN'
        df['keyword'] = keyword
        
        # Reorder columns
        column_order = ['title', 'date', 'url', 'content', 'source', 'keyword']
        df = df[[col for col in column_order if col in df.columns]]
        
        print(f"\n📄 Sample data (first 3 rows):")
        for i, row in df.head(3).iterrows():
            print(f"\n   [{i+1}] {row['title'][:70]}...")
            print(f"       Date: {row['date']}")
            print(f"       Content: {len(str(row['content']))} chars")
            print(f"       Status: {'✅' if row['content'] != 'N/A' else '⚠️'}")
        
        # Get or create worksheet
        worksheet = get_or_create_worksheet(spreadsheet, sheet_name)
        
        # Read existing data
        print(f"\n📖 Reading existing data...")
        existing_df = read_worksheet_gsheet(worksheet)
        
        if not existing_df.empty:
            print(f"   Found {len(existing_df)} existing rows")
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            combined_df = combined_df.drop_duplicates(subset=['url'], keep='first')
            new_articles = len(combined_df) - len(existing_df)
            print(f"   Combined: {len(combined_df)} total rows ({new_articles} new)")
        else:
            combined_df = df
            new_articles = len(df)
            print(f"   New worksheet, no existing data")
        
        # Write to Google Sheets
        print(f"\n💾 Writing data to Google Sheets...")
        success = write_worksheet_gsheet(worksheet, combined_df)
        
        if success:
            # Statistics
            success_scrape = sum(1 for _, row in df.iterrows() if row['content'] != 'N/A')
            failed_scrape = len(df) - success_scrape
            
            print(f"\n" + "=" * 80)
            print(f"✅ TEST COMPLETE!")
            print(f"=" * 80)
            print(f"   Total scraped: {len(df)} articles")
            print(f"   Successful scrapes: {success_scrape}/{len(df)} ({success_scrape/len(df)*100:.1f}%)")
            print(f"   Failed scrapes: {failed_scrape}/{len(df)}")
            print(f"   New articles added: {new_articles}")
            print(f"   Total in sheet: {len(combined_df)}")
            print(f"   End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"\n🔗 Open your Google Sheet to verify!")
            print(f"=" * 80 + "\n")
        else:
            raise Exception("Write to Google Sheets failed")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        
        # Save backup locally
        if 'df' in locals() and not df.empty:
            backup_filename = f"backup_kontan_test_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
            df.to_excel(backup_filename, index=False)
            print(f"💾 Backup saved: {backup_filename}")
        
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_kontan_to_gsheet()