import pandas as pd
import time
from datetime import datetime, timedelta
import sys
import os
import re
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import json


from main import (
    get_gspread_client,
    read_worksheet_gsheet,
    write_worksheet_gsheet,
    get_or_create_worksheet,
    scrape_keyword,
    sheet_to_keyword
)

def generate_date_range(start_date, end_date):
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    return dates

def batch_scrape():
    print("\n" + "=" * 80)
    print("BATCH NEWS SCRAPER TO GOOGLE SHEETS")
    print("=" * 80)
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    start_date = os.getenv('START_DATE', '2025-12-02')
    end_date = os.getenv('END_DATE', '2025-12-17')
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    print(f"\nConfiguration:")
    print(f"   Spreadsheet ID: {spreadsheet_id[:20]}..." if spreadsheet_id else "   ❌ SPREADSHEET_ID not found!")
    print(f"   Date Range: {start_date} to {end_date}")
    print(f"   Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if not spreadsheet_id:
        print("\nERROR: SPREADSHEET_ID not found in .env!")
        return
    date_list = generate_date_range(start_date, end_date)
    print(f"\nProcessing {len(date_list)} dates:")
    for date in date_list:
        print(f"   • {date}")
    try:
        print("\nConnecting to Google Sheets...")
        client = get_gspread_client()
        spreadsheet = client.open_by_key(spreadsheet_id)
        print(f"Connected to: {spreadsheet.title}")
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        return

    sheet_names = [
        "(News)indeks risiko geopolitik",
        "(News)indeks volatilitas",
        "(News)Kurs",
        "(News)IHSG",
        "(News)Inflasi",
        "(News)BI Rate",
        "(News)JIBOR",
        "(News)indeks sales retail",
        "(News)indeks kepercayaan knsmn",
        "(News)indeks kinerja manufaktur",
        "(News)indeks kinerja jasa",
        "(News)neraca perdagangan",
        "(News)PDB",
        "(News)Bioenergi",
        "(News)Harga Minyak",
        "(News)Volume Minyak",
        "(News)Harga Produk Kilang", 
        "(News)Volume Produk Kilang"
    ]
    
    total_sheets = len(sheet_names)
    total_dates = len(date_list)
    total_tasks = total_sheets * total_dates
    completed_tasks = 0
    failed_tasks = 0
    total_articles = 0
    start_time = datetime.now()
    for date_idx, tanggal in enumerate(date_list, 1):
        print(f"\n" + "=" * 80)
        print(f"DATE {date_idx}/{total_dates}: {tanggal}")
        print(f"=" * 80)
        for sheet_idx, sheet_name in enumerate(sheet_names, 1):
            keyword_asli = sheet_to_keyword.get(sheet_name)
            if not keyword_asli:
                print(f"\nKeyword not found for '{sheet_name}'. Skipping.")
                continue
            
            print(f"\n[{date_idx}/{total_dates}] [{sheet_idx}/{total_sheets}] {sheet_name}")
            print(f"Keyword: {keyword_asli.upper()}")
            print(f"Date: {tanggal}")
            
            try:
                hasil_df = scrape_keyword(keyword_asli, tanggal)
                articles_found = len(hasil_df)
                print(f"Found: {articles_found} articles")
                worksheet = get_or_create_worksheet(spreadsheet, sheet_name)
                existing_df = read_worksheet_gsheet(worksheet)
                if not existing_df.empty:
                    combined_df = pd.concat([existing_df, hasil_df], ignore_index=True)
                    combined_df = combined_df.drop_duplicates(subset=['url'], keep='first')
                    new_articles = len(combined_df) - len(existing_df)
                    print(f"Combined: {len(combined_df)} total ({new_articles} new)")
                else:
                    combined_df = hasil_df
                    new_articles = articles_found
                    print(f"New worksheet: {len(combined_df)} articles")
                success = write_worksheet_gsheet(worksheet, combined_df)
                if success:
                    completed_tasks += 1
                    total_articles += new_articles
                    print(f"SUCCESS!")
                else:
                    raise Exception("Write failed")
            except Exception as e:
                failed_tasks += 1
                print(f"Error: {e}")
                backup_filename = f"backup_{sheet_name}_{tanggal}.xlsx"
                if 'combined_df' in locals() and not combined_df.empty:
                    combined_df.to_excel(backup_filename, index=False)
                    print(f"Backup saved: {backup_filename}")
            progress = ((date_idx - 1) * total_sheets + sheet_idx) / total_tasks * 100
            print(f"Overall Progress: {progress:.1f}% ({completed_tasks}/{total_tasks} tasks)")
            time.sleep(3)  
        if date_idx < total_dates:
            print(f"\nWaiting 10 seconds before next date...")
            time.sleep(10)
    end_time = datetime.now()
    duration = end_time - start_time
    
    print(f"\n" + "=" * 80)
    print(f"BATCH SCRAPING COMPLETE!")
    print(f"=" * 80)
    print(f"Dates processed: {total_dates} ({start_date} to {end_date})")
    print(f"Sheets processed: {total_sheets}")
    print(f"Successful tasks: {completed_tasks}/{total_tasks}")
    print(f"Failed tasks: {failed_tasks}/{total_tasks}")
    print(f"Total new articles: {total_articles}")
    print(f"Duration: {duration}")
    print(f"Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"End: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nNext steps:")
    print(f"   1. Open your Google Sheet to verify data")
    print(f"   2. Check for any backup files if there were errors")
    print(f"   3. Review the logs above for any issues")
    print(f"=" * 80 + "\n")
    
    # Create summary log
    log_filename = f"batch_scraper_{start_date}_to_{end_date}.log"
    with open(log_filename, 'w') as f:
        f.write(f"Batch Scraper Summary\n")
        f.write(f"====================\n\n")
        f.write(f"Date Range: {start_date} to {end_date}\n")
        f.write(f"Total Dates: {total_dates}\n")
        f.write(f"Total Sheets: {total_sheets}\n")
        f.write(f"Total Tasks: {total_tasks}\n")
        f.write(f"Successful: {completed_tasks}\n")
        f.write(f"Failed: {failed_tasks}\n")
        f.write(f"New Articles: {total_articles}\n")
        f.write(f"Duration: {duration}\n")
        f.write(f"Start Time: {start_time}\n")
        f.write(f"End Time: {end_time}\n")
    
    print(f"Summary saved to: {log_filename}")

if __name__ == "__main__":
    batch_scrape()
