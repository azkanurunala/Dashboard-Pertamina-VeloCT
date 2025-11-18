import http.client

# Ganti 'reuters-api.p.rapidapi.com' dengan host yang benar jika berbeda
conn = http.client.HTTPSConnection("reuters-api.p.rapidapi.com") 

# --- BAGIAN INI YANG HARUS DIMODIFIKASI ---
# Ganti 'YOUR_RAPIDAPI_KEY_HERE' dengan kunci API RapidAPI Anda yang sebenarnya.
# Kunci ini diberikan saat Anda berlangganan API di RapidAPI.
headers = { 
    'x-rapidapi-host': "reuters-api.p.rapidapi.com",
    'x-rapidapi-key': "d2018568df559895fc0f7c06ced102274fe29c2276e18f1771955ffa2ff005dd"  
}
# --------------------------------------------

# Permintaan Anda
conn.request("GET", "/category?url=https%3A%2F%2Fwww.reuters.com%2Fworld%2Fafrica%2F", headers=headers)

res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))


