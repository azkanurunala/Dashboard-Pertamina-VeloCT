from io import BytesIO
import msal
import requests
import os
from dotenv import load_dotenv
import pandas as pd
import json

load_dotenv()

CLIENT_ID = os.getenv("MS_CLIENT_ID") or os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET") or os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("MS_TENANT_ID") or os.getenv("TENANT_ID")
REFRESH_TOKEN = os.getenv("MS_REFRESH_TOKEN")

TOKEN_CACHE_FILE = "token_cache.json"


def load_token_cache():
    cache = msal.SerializableTokenCache()
    if os.path.exists(TOKEN_CACHE_FILE):
        with open(TOKEN_CACHE_FILE, "r") as f:
            cache.deserialize(f.read())
    return cache


def save_token_cache(cache):
    if cache.has_state_changed:
        with open(TOKEN_CACHE_FILE, "w") as f:
            f.write(cache.serialize())


def extract_refresh_token_from_cache():
    if os.path.exists(TOKEN_CACHE_FILE):
        with open(TOKEN_CACHE_FILE, "r") as f:
            cache_data = json.load(f)
            refresh_tokens = cache_data.get("RefreshToken", {})
            if refresh_tokens:
                for token_data in refresh_tokens.values():
                    print("\n" + "="*60)
                    print("REFRESH TOKEN DITEMUKAN!")
                    print("Copy token ini ke .env sebagai MS_REFRESH_TOKEN:")
                    print("="*60)
                    print(f"MS_REFRESH_TOKEN={token_data.get('secret')}")
                    print("="*60)
                    return token_data.get('secret')
    return None


def get_access_token(client_id=None, client_secret=None, tenant_id=None):
    client_id = client_id or CLIENT_ID
    authority = "https://login.microsoftonline.com/consumers"
    
    cache = load_token_cache()
    app = msal.PublicClientApplication(
        client_id,
        authority=authority,
        token_cache=cache
    )
    
    scopes = ["Files.ReadWrite.All", "User.Read"]
    
    if REFRESH_TOKEN:
        print("Mencoba autentikasi dengan refresh token dari .env...")
        cache_dict = json.loads(cache.serialize()) if cache.serialize() else {}
        if "RefreshToken" not in cache_dict:
            cache_dict["RefreshToken"] = {}
        
        token_key = f"{client_id}-consumers-RefreshToken-Files.ReadWrite.All User.Read--"
        cache_dict["RefreshToken"][token_key] = {
            "secret": REFRESH_TOKEN,
            "client_id": client_id,
            "home_account_id": "",
            "environment": "login.microsoftonline.com",
            "realm": "consumers",
            "target": "Files.ReadWrite.All User.Read"
        }
        cache.deserialize(json.dumps(cache_dict))
    
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])
        if result and "access_token" in result:
            print("Berhasil autentikasi menggunakan cached/refresh token")
            save_token_cache(cache)
            return result["access_token"]
    
    print("\n⚠️ Token expired atau tidak valid. Perlu login manual.")
    flow = app.initiate_device_flow(scopes=scopes)
    if "user_code" not in flow:
        raise Exception(f"Gagal membuat device flow: {flow.get('error_description')}")
    
    print("\n" + "="*60)
    print("AUTENTIKASI DIPERLUKAN")
    print("="*60)
    print(flow["message"])
    print("="*60)
    print("\nSetelah login, tekan Enter untuk melanjutkan...")
    input()
    
    result = app.acquire_token_by_device_flow(flow)
    
    if "access_token" in result:
        print("\nBerhasil autentikasi ke Microsoft Graph API")
        save_token_cache(cache)
        extract_refresh_token_from_cache()
        return result["access_token"]
    else:
        raise Exception(f"Gagal autentikasi: {result.get('error_description')}")


def download_excel_from_onedrive(access_token, file_path):
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:{file_path}:/content"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print(f"Berhasil download file dari OneDrive: {file_path}")
        return BytesIO(response.content)
    elif response.status_code == 404:
        print(f"File tidak ditemukan di OneDrive: {file_path}")
        return None
    else:
        raise Exception(f"Gagal download file: {response.status_code} - {response.text}")


def upload_excel_to_onedrive(access_token, file_path, excel_buffer):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }
    
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:{file_path}:/content"
    response = requests.put(url, headers=headers, data=excel_buffer.getvalue())
    if response.status_code in [200, 201]:
        print(f"Berhasil upload file ke OneDrive: {file_path}")
        return True
    else:
        raise Exception(f"Gagal upload file: {response.status_code} - {response.text}")


def read_excel_sheet_from_onedrive(access_token, file_path, sheet_name):
    excel_buffer = download_excel_from_onedrive(access_token, file_path)
    if excel_buffer is None:
        return pd.DataFrame()
    try:
        df = pd.read_excel(excel_buffer, sheet_name=sheet_name)
        print(f"Berhasil baca sheet '{sheet_name}': {len(df)} baris")
        return df
    except Exception as e:
        print(f"Gagal baca sheet '{sheet_name}': {e}")
        return pd.DataFrame()


def create_excel_writer_from_onedrive(access_token, file_path):
    excel_buffer = download_excel_from_onedrive(access_token, file_path)
    if excel_buffer is None:
        print("File tidak ada, akan membuat file baru")
        return BytesIO(), 'w'
    else:
        print("File sudah ada, akan update")
        return excel_buffer, 'a'