from io import BytesIO
import os
import requests
import pandas as pd
from dotenv import load_dotenv
import msal

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
    
    output_buffer = BytesIO()
    
    with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
        for sheet_name, df in sheets_dict.items():
            print(f"  Writing sheet: {sheet_name} ({len(df)} rows)")
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    output_buffer.seek(0)
    
    print(f"\nUploading ke OneDrive: {file_path}")
    
    print("Mendapatkan fresh token untuk upload...")
    fresh_token = get_access_token()
    
    upload_excel_to_onedrive(fresh_token, file_path, output_buffer)
    
    print("Upload selesai!")


def create_excel_writer_from_onedrive(access_token, file_path):
    excel_buffer = download_excel_from_onedrive(access_token, file_path)

    if excel_buffer is None:
        print("File belum ada, membuat file baru")
        return BytesIO(), "w"
    else:
        print("File sudah ada, update file")
        return excel_buffer, "a"