import requests

api_key = '8199b1a60c76d284ee3d2228a51b3743'
url = f"https://webapi.bps.go.id/v1/api/list/model/news/domain/0000/page/0/key/{api_key}"

r = requests.get(url, timeout=15)
print(f"Status: {r.status_code}")
print(f"Content-Type: {r.headers.get('Content-Type','')}")
print(r.text[:800])
