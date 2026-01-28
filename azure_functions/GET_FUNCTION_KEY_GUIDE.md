# Cara Mendapatkan Function Key

Function App Anda memerlukan authentication key. Ikuti langkah berikut:

## 📋 Langkah-langkah:

### 1. Buka Azure Portal
- Go to: https://portal.azure.com
- Login dengan akun Azure Anda

### 2. Navigate ke Function App
- Search: "PeiDashboard" atau "pei-dashboard"
- Click: Function App Anda

### 3. Get Function Key

**Opsi A: Host Keys (Recommended - Works for all functions)**
1. Di sidebar kiri, click: **App Keys**
2. Scroll ke section: **Host keys**
3. Click: **Show values** pada key `default`
4. Click: **Copy** icon
5. Paste key ke file konfigurasi

**Opsi B: Function-specific Key**
1. Di sidebar kiri, click: **Functions**
2. Click: Function yang ingin di-test (e.g., `cnbc_scraper_function`)
3. Click: **Function Keys**
4. Click: **Show values** pada key `default`
5. Click: **Copy** icon
6. Paste key ke file konfigurasi

### 4. Update Script dengan Function Key

Edit file: `test_scrapers.bat` (line 9)
```batch
set FUNCTION_KEY=YOUR_FUNCTION_KEY_HERE
```

Atau edit file: `test_deployed_functions.py` (line 16)
```python
FUNCTION_KEY = "YOUR_FUNCTION_KEY_HERE"
```

## 🔐 Function Key Format

Function key biasanya terlihat seperti:
```
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx==
```

Panjang sekitar 50-60 karakter dengan `==` di akhir.

## ✅ Test dengan Function Key

### Menggunakan curl:
```cmd
curl -X GET "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/cnbc_scraper_function?code=YOUR_FUNCTION_KEY&keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28"
```

### Atau menggunakan header:
```cmd
curl -H "x-functions-key: YOUR_FUNCTION_KEY" -X GET "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/cnbc_scraper_function?keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28"
```

## 🎯 Quick Test

Setelah mendapatkan function key:

```cmd
# Set function key
set FUNCTION_KEY=your_actual_key_here

# Test CNBC function
curl -X GET "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/cnbc_scraper_function?code=%FUNCTION_KEY%&keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28"
```

## 🔒 Security Notes

- **JANGAN commit function key ke Git!**
- Function key memberikan akses penuh ke functions
- Simpan di environment variable atau secure storage
- Rotate key secara berkala untuk security

## 📝 Alternative: Disable Authentication (Not Recommended for Production)

Jika ini untuk testing saja, Anda bisa disable authentication:

1. Go to Function App → Configuration
2. Set: `AzureWebJobsDisableHomepage` = `false`
3. Atau edit `function.json` untuk setiap function:
   ```json
   {
     "authLevel": "anonymous"
   }
   ```

**WARNING**: Ini membuat function bisa diakses siapa saja tanpa authentication!

## 🆘 Troubleshooting

### Masih 401 setelah add key?
- Verify key di-copy dengan benar (no extra spaces)
- Try host key instead of function key
- Check key belum expired atau di-revoke

### Key tidak muncul di portal?
- Verify Anda punya permission yang cukup
- Contact Azure admin untuk access

### Lupa dimana simpan key?
- Check Azure Portal → Function App → App Keys
- Regenerate key jika perlu (old key akan invalid)

---

**Next Step**: Setelah dapat function key, update script dan test lagi!
