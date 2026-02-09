import requests
import os
import json

# Manually setting credentials from local.settings.json for direct test
username = "raden.aviandito@pertamina.com"
password = "Pertamina.Setup1S&P"

def test_sp_auth():
    print(f"Testing S&P Auth for {username}...")
    auth_url = "https://api.ci.spglobal.com/auth/api"
    
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {
        'username': username,
        'password': password
    }
    
    try:
        response = requests.post(auth_url, headers=headers, data=data, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Authentication Successful!")
            print(f"Token received: {response.json().get('access_token')[:10]}...")
        else:
            print("❌ Authentication Failed")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_sp_auth()
