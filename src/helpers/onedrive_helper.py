from io import BytesIO
import os
import requests
import pandas as pd
from dotenv import load_dotenv
import msal

load_dotenv()

CLIENT_ID = os.getenv("MS_CLIENT_ID")
CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET")
TENANT_ID = os.getenv("MS_TENANT_ID", "consumers")
REFRESH_TOKEN = os.getenv("MS_REFRESH_TOKEN")

# Personal Microsoft Account
AUTHORITY = "https://login.microsoftonline.com/consumers"

# SCOPES untuk refresh token - TANPA offline_access
SCOPES = [
    "Files.ReadWrite.All"
]


def get_access_token():
    """
    Menggunakan Refresh Token untuk personal Microsoft Account
    Cocok untuk automation dengan personal OneDrive
    """
    
    if not REFRESH_TOKEN:
        raise Exception(
            "\n❌ MS_REFRESH_TOKEN tidak ditemukan!\n"
            "Jalankan: python setup_personal_onedrive.py\n"
            "untuk mendapatkan refresh token terlebih dahulu."
        )
    
    # Untuk personal account, gunakan PublicClientApplication
    app = msal.PublicClientApplication(
        client_id=CLIENT_ID,
        authority=AUTHORITY
    )

    # Gunakan refresh token - TANPA offline_access di scopes
    result = app.acquire_token_by_refresh_token(
        refresh_token=REFRESH_TOKEN,
        scopes=SCOPES
    )

    if "access_token" not in result:
        error_desc = result.get('error_description', result.get('error', 'Unknown error'))
        
        # Jika refresh token expired, minta user login ulang
        if "invalid_grant" in str(error_desc).lower() or "AADSTS700082" in str(error_desc):
            raise Exception(
                "\n❌ Refresh token sudah expired atau invalid!\n"
                "Jalankan ulang: python setup_personal_onedrive.py\n"
                "untuk mendapatkan refresh token baru."
            )
        
        raise Exception(f"Gagal mendapatkan access token: {error_desc}")
    
    # Update refresh token jika ada yang baru
    if "refresh_token" in result:
        new_token = result["refresh_token"]
        if new_token != REFRESH_TOKEN:
            print(f"\n⚠️ REFRESH TOKEN BARU TERSEDIA!")
            print(f"Update .env dengan token baru (first 50 chars): {new_token[:50]}...")

    return result["access_token"]


def download_excel_from_onedrive(access_token, file_path):
    """
    Download file dari OneDrive personal menggunakan /me endpoint
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Encode path untuk handle special characters
    encoded_path = requests.utils.quote(file_path)
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:{encoded_path}:/content"

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print(f"✓ Berhasil download file: {file_path}")
        return BytesIO(response.content)
    elif response.status_code == 404:
        print(f"✗ File tidak ditemukan: {file_path}")
        return None
    elif response.status_code == 401:
        raise Exception("❌ Unauthorized: Token mungkin sudah expired, jalankan setup ulang")
    else:
        raise Exception(f"Download gagal: {response.status_code} - {response.text}")


def upload_excel_to_onedrive(access_token, file_path, excel_buffer):
    """
    Upload file ke OneDrive personal
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }

    encoded_path = requests.utils.quote(file_path)
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:{encoded_path}:/content"
    
    response = requests.put(url, headers=headers, data=excel_buffer.getvalue())

    if response.status_code in [200, 201]:
        print(f"✓ Berhasil upload file: {file_path}")
        return True
    else:
        raise Exception(f"Upload gagal: {response.status_code} - {response.text}")


def read_excel_sheet_from_onedrive(access_token, file_path, sheet_name):
    """
    Baca sheet tertentu dari Excel file di OneDrive
    """
    excel_buffer = download_excel_from_onedrive(access_token, file_path)

    if excel_buffer is None:
        return pd.DataFrame()

    try:
        df = pd.read_excel(excel_buffer, sheet_name=sheet_name)
        print(f"✓ Berhasil baca sheet '{sheet_name}', rows={len(df)}")
        return df
    except Exception as e:
        print(f"✗ Gagal baca sheet '{sheet_name}': {e}")
        return pd.DataFrame()


def create_excel_writer_from_onedrive(access_token, file_path):
    """
    Buat Excel writer dari file di OneDrive
    """
    excel_buffer = download_excel_from_onedrive(access_token, file_path)

    if excel_buffer is None:
        print("INFO: File belum ada, membuat file baru")
        return BytesIO(), "w"
    else:
        print("INFO: File sudah ada, akan di-update")
        return excel_buffer, "a"