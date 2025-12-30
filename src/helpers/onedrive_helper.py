from io import BytesIO
import os
import requests
import pandas as pd
from dotenv import load_dotenv
import msal
from openpyxl import load_workbook

load_dotenv()

CLIENT_ID = os.getenv("MS_CLIENT_ID")
CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET")
TENANT_ID = os.getenv("MS_TENANT_ID")
USER_EMAIL = os.getenv("MS_USER_EMAIL")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["https://graph.microsoft.com/.default"]


def get_access_token():
    app = msal.ConfidentialClientApplication(
        client_id=CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )

    result = app.acquire_token_for_client(scopes=SCOPES)

    if "access_token" not in result:
        raise Exception(f"Gagal mendapatkan access token: {result}")

    return result["access_token"]


def download_excel_from_onedrive(access_token, file_path):
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://graph.microsoft.com/v1.0/users/{USER_EMAIL}/drive/root:{file_path}:/content"

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print(f"Berhasil download file: {file_path}")
        return BytesIO(response.content)
    elif response.status_code == 404:
        print(f"File tidak ditemukan: {file_path}")
        return None
    else:
        raise Exception(f"Download gagal: {response.status_code} - {response.text}")


def upload_excel_to_onedrive(access_token, file_path, excel_buffer):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }

    url = f"https://graph.microsoft.com/v1.0/users/{USER_EMAIL}/drive/root:{file_path}:/content"
    response = requests.put(url, headers=headers, data=excel_buffer.getvalue())

    if response.status_code in [200, 201]:
        print(f"Berhasil upload file: {file_path}")
        return True
    else:
        raise Exception(f"Upload gagal: {response.status_code} - {response.text}")


def read_excel_sheet_from_onedrive(access_token, file_path, sheet_name):
    excel_buffer = download_excel_from_onedrive(access_token, file_path)

    if excel_buffer is None:
        return pd.DataFrame()

    try:
        df = pd.read_excel(excel_buffer, sheet_name=sheet_name)
        print(f"Berhasil baca sheet '{sheet_name}', rows={len(df)}")
        return df
    except Exception as e:
        print(f"Gagal baca sheet '{sheet_name}': {e}")
        return pd.DataFrame()


def write_multiple_sheets_to_onedrive(access_token, file_path, sheets_dict):
    print(f"\nMenyiapkan file Excel dengan {len(sheets_dict)} sheets...")
    
    try:
        excel_buffer = download_excel_from_onedrive(access_token, file_path)
        
        if excel_buffer is not None:
            print("File sudah ada, mode update...")
            
            try:
                wb = load_workbook(excel_buffer)
                
                visible_sheets = [s for s in wb.worksheets if s.sheet_state == 'visible']
                
                if len(visible_sheets) == 0:
                    print("Semua sheets hidden! Meng-unhide sheet pertama...")
                    if len(wb.worksheets) > 0:
                        wb.worksheets[0].sheet_state = 'visible'
                        wb.active = 0
                
                for sheet in wb.worksheets:
                    if sheet.sheet_state != 'visible':
                        sheet.sheet_state = 'visible'
                
                temp_buffer = BytesIO()
                wb.save(temp_buffer)
                wb.close()
                temp_buffer.seek(0)
                
                output_buffer = BytesIO()
                
                with pd.ExcelWriter(temp_buffer, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                    for sheet_name, df in sheets_dict.items():
                        print(f"  Updating sheet: {sheet_name} ({len(df)} rows)")
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                output_buffer = temp_buffer
                
            except Exception as e:
                print(f"Error saat update existing file: {e}")
                print("Fallback: Membuat file baru...")
                
                output_buffer = BytesIO()
                with pd.ExcelWriter(output_buffer, engine='openpyxl', mode='w') as writer:
                    for sheet_name, df in sheets_dict.items():
                        print(f"  Writing sheet: {sheet_name} ({len(df)} rows)")
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        else:
            print("File belum ada, membuat file baru...")
            
            output_buffer = BytesIO()
            
            with pd.ExcelWriter(output_buffer, engine='openpyxl', mode='w') as writer:
                for sheet_name, df in sheets_dict.items():
                    print(f"  Writing sheet: {sheet_name} ({len(df)} rows)")
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        output_buffer.seek(0)
        
        print(f"\nUploading ke OneDrive: {file_path}")
        
        print("Mendapatkan fresh token untuk upload...")
        fresh_token = get_access_token()
        
        upload_excel_to_onedrive(fresh_token, file_path, output_buffer)
        
        print("Upload selesai!")
        
    except Exception as e:
        print(f"Error dalam write_multiple_sheets_to_onedrive: {e}")
        raise


def create_excel_writer_from_onedrive(access_token, file_path):
    excel_buffer = download_excel_from_onedrive(access_token, file_path)

    if excel_buffer is None:
        print("File belum ada, membuat file baru")
        return BytesIO(), "w"
    else:
        print("File sudah ada, mode update")
        
        try:
            wb = load_workbook(excel_buffer)
            visible_sheets = [s for s in wb.worksheets if s.sheet_state == 'visible']
            
            if len(visible_sheets) == 0:
                print("Fixing hidden sheets...")
                wb.worksheets[0].sheet_state = 'visible'
                wb.active = 0
                
                temp_buffer = BytesIO()
                wb.save(temp_buffer)
                wb.close()
                temp_buffer.seek(0)
                
                return temp_buffer, "a"
            
            wb.close()
        except Exception as e:
            print(f"Warning saat check file: {e}")
        
        return excel_buffer, "a"


def fix_hidden_sheets_onedrive(access_token, file_path):
    print(f"Memperbaiki hidden sheets di: {file_path}")
    
    try:
        excel_buffer = download_excel_from_onedrive(access_token, file_path)
        
        if excel_buffer is None:
            print("File tidak ditemukan!")
            return False
        
        wb = load_workbook(excel_buffer)
        
        print(f"Total sheets: {len(wb.worksheets)}")
        
        fixed_count = 0
        for idx, sheet in enumerate(wb.worksheets):
            if sheet.sheet_state != 'visible':
                sheet.sheet_state = 'visible'
                fixed_count += 1
                print(f"  Fixed: {sheet.title}")
            
            if idx == 0:
                wb.active = 0
        
        print(f"Fixed {fixed_count} sheets")
        
        output_buffer = BytesIO()
        wb.save(output_buffer)
        wb.close()
        output_buffer.seek(0)
        
        fresh_token = get_access_token()
        upload_excel_to_onedrive(fresh_token, file_path, output_buffer)
        
        print("File berhasil diperbaiki!")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False