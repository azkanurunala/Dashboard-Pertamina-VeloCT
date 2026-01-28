"""Quick test of deployed functions"""
import requests
import json

FUNCTION_APP_URL = "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net"
FUNCTION_KEY = "QRn4YL31yW-bZBFHDlt8znrvRmlfbvD8owXwCBegfk7TAzFuLEZIFg=="

print("Testing test_function...")
print("=" * 60)

url = f"{FUNCTION_APP_URL}/api/test_function?code={FUNCTION_KEY}"

try:
    response = requests.get(url, timeout=30)
    print(f"Status: {response.status_code}")
    
    if response.status_code in [200, 206]:
        result = response.json()
        print(json.dumps(result, indent=2))
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")
