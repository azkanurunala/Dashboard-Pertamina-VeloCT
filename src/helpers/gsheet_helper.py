import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json
import os


def get_gspread_client(credentials_json=None, credentials_path=None):
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    if credentials_json:
        if isinstance(credentials_json, str):
            creds_dict = json.loads(credentials_json)
        else:
            creds_dict = credentials_json
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    elif credentials_path and os.path.exists(credentials_path):
        credentials = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    elif os.getenv('GOOGLE_CREDENTIALS'):
        creds_dict = json.loads(os.getenv('GOOGLE_CREDENTIALS'))
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        possible_paths = [
            'credentials.json',
            os.path.join(os.path.dirname(__file__), 'credentials.json'),
            os.path.join(os.path.dirname(__file__), '..', 'credentials.json'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'credentials.json')
        ]
        creds_file = None
        for path in possible_paths:
            if os.path.exists(path):
                creds_file = path
                break
        if not creds_file:
            raise Exception("Credentials tidak ditemukan")
        credentials = Credentials.from_service_account_file(creds_file, scopes=scopes)
    client = gspread.authorize(credentials)
    print("Connected to Google Sheets")
    return client

def open_spreadsheet(client, spreadsheet_id):
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        print(f"Connected to: {spreadsheet.title}")
        return spreadsheet
    except Exception as e:
        print(f"Error opening spreadsheet: {e}")
        raise

def get_or_create_worksheet(spreadsheet, sheet_name, rows=1000, cols=26):
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        print(f"Found existing sheet: {sheet_name}")
        return worksheet
    except gspread.exceptions.WorksheetNotFound:
        print(f"Creating new sheet: {sheet_name}")
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=rows, cols=cols)
        return worksheet

def read_worksheet(worksheet):
    try:
        data = worksheet.get_all_values()
        if not data or len(data) <= 1:
            return pd.DataFrame()
        headers = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=headers)
        print(f"Read {len(df)} rows from {worksheet.title}")
        return df 
    except Exception as e:
        print(f"Error reading worksheet: {e}")
        return pd.DataFrame()


def write_worksheet(worksheet, df, clear_first=True):
    try:
        if clear_first:
            worksheet.clear()
        headers = df.columns.tolist()
        values = [headers] + df.values.tolist()
        values = [[str(cell) if pd.notna(cell) else "" for cell in row] for row in values]
        worksheet.update('A1', values)
        print(f"Wrote {len(df)} rows to {worksheet.title}")
        return True
    except Exception as e:
        print(f"Error writing to worksheet: {e}")
        return False


def append_to_worksheet(worksheet, df):
    try:
        existing_df = read_worksheet(worksheet)
        if not existing_df.empty:
            combined_df = pd.concat([existing_df, df], ignore_index=True)
        else:
            combined_df = df
        return write_worksheet(worksheet, combined_df)  
    except Exception as e:
        print(f"Error appending to worksheet: {e}")
        return False


def quick_read_sheet(spreadsheet_id, sheet_name, credentials_json=None):
    client = get_gspread_client(credentials_json=credentials_json)
    spreadsheet = open_spreadsheet(client, spreadsheet_id)
    worksheet = spreadsheet.worksheet(sheet_name)
    return read_worksheet(worksheet)


def quick_write_sheet(spreadsheet_id, sheet_name, df, credentials_json=None):
    client = get_gspread_client(credentials_json=credentials_json)
    spreadsheet = open_spreadsheet(client, spreadsheet_id)
    worksheet = get_or_create_worksheet(spreadsheet, sheet_name)
    return write_worksheet(worksheet, df)


def batch_update_multiple_sheets(spreadsheet_id, sheets_data, credentials_json=None):
    results = {}
    client = get_gspread_client(credentials_json=credentials_json)
    spreadsheet = open_spreadsheet(client, spreadsheet_id)
    
    for sheet_name, df in sheets_data.items():
        print(f"\nProcessing sheet: {sheet_name}")
        try:
            worksheet = get_or_create_worksheet(spreadsheet, sheet_name)
            success = write_worksheet(worksheet, df)
            results[sheet_name] = "Success" if success else "Failed"
        except Exception as e:
            results[sheet_name] = f"Error: {str(e)}"
    
    return results