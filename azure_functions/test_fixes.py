import requests
import json
import time

functions_to_test = [
    "bps_scraper_function",
    "bioetanol_esdm_scraper_function",
    "bisnis_indonesia_scraper_function"
]

results = {}

print("Testing fixed functions...")
for func_name in functions_to_test:
    url = f"http://localhost:7071/api/{func_name}"
    print(f"Testing {url}...")
    try:
        # Short timeout because we just want to see if it starts successfully or returns a different error
        # Although scrapers can take time, we hope for a quick failure if it's broken, or a success.
        # However, these run for 10-20s. Let's give 30s.
        response = requests.get(url, timeout=45) 
        try:
             json_content = response.json()
        except:
             json_content = str(response.content)

        results[func_name] = {
            "status": "SUCCESS" if response.status_code == 200 else "FAILED",
            "code": response.status_code,
            "content": json_content
        }
    except Exception as e:
        results[func_name] = {
            "status": "ERROR",
            "error": str(e)
        }

print("Testing complete.")
with open("test_fixes_result.json", "w") as f:
    json.dump(results, f, indent=2)
