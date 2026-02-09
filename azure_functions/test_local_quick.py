import requests
import json
import time

url = "http://localhost:7071/api/health_check_function"
print(f"Testing {url}...")

result = {}
try:
    response = requests.get(url, timeout=5)
    result = {
        "status": "SUCCESS",
        "code": response.status_code,
        "content": str(response.content)
    }
except Exception as e:
    result = {
        "status": "ERROR",
        "error": str(e)
    }

print(result)

with open("test_quick_result.json", "w") as f:
    json.dump(result, f)
