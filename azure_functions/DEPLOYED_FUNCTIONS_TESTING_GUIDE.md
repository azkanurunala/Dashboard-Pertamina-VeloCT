# Panduan Testing Azure Functions yang Sudah Di-Deploy

Dokumentasi lengkap untuk test Azure Functions yang sudah di-deploy via HTTP requests.

## 🎯 Prerequisites

1. **Azure Function App sudah di-deploy**
2. **curl** ter-install (biasanya sudah ada di Windows 10+)
3. **Python 3.11** dengan `requests` library:
   ```cmd
   pip install requests
   ```

## ⚙️ Konfigurasi

### Step 1: Dapatkan Function App URL

Dari Azure Portal:
1. Buka Azure Function App Anda
2. Copy URL: `https://your-function-app-name.azurewebsites.net`

### Step 2: Edit Konfigurasi

**Opsi A: Edit test_scrapers.bat** (line 6)
```batch
set FUNCTION_APP_NAME=your-actual-function-app-name
```

**Opsi B: Edit test_deployed_functions.py** (line 13)
```python
FUNCTION_APP_NAME = "your-actual-function-app-name"
```

## 🚀 Cara Menggunakan

### Opsi 1: Menu Interaktif (RECOMMENDED)

```cmd
cd azure_functions
test_scrapers.bat
```

Menu akan muncul:
```
========================================
AZURE FUNCTIONS TESTING MENU
========================================

Current Function App: your-function-app-name
Base URL: https://your-function-app-name.azurewebsites.net/api

1.  CNBC (International)
2.  OilPrice
3.  Reuters
4.  CNN
5.  The Guardian
6.  Kompas (Indonesia)
7.  Tempo (Indonesia)
8.  Kontan (Indonesia)
9.  CNBC Indonesia
10. Bisnis Indonesia
11. BPS (Data)
12. Test ALL Scrapers
13. Configure Function App URL
0.  Exit
```

### Opsi 2: Python Script - Test Semua

```cmd
cd azure_functions
python test_deployed_functions.py
```

### Opsi 3: Manual curl Commands

#### Test CNBC Function
```cmd
curl -X GET "https://your-app.azurewebsites.net/api/cnbc_scraper_function?keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28&save_to_db=false"
```

#### Test OilPrice Function
```cmd
curl -X GET "https://your-app.azurewebsites.net/api/oilprice_scraper_function?keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28&max_articles=10"
```

#### Test Kompas Function (Indonesian)
```cmd
curl -X GET "https://your-app.azurewebsites.net/api/kompas_scraper_function?keywords=energi,minyak&start_date=2025-01-21&end_date=2026-01-28&max_articles=10"
```

## 📋 Function Endpoints

### International News Scrapers

| Function | Endpoint | Parameters |
|----------|----------|------------|
| CNBC | `/cnbc_scraper_function` | keywords, start_date, end_date, save_to_db |
| OilPrice | `/oilprice_scraper_function` | keywords, start_date, end_date, max_articles |
| Reuters | `/reuters_scraper_function` | keywords, start_date, end_date, save_to_db |
| CNN | `/cnn_scraper_function` | keywords, start_date, end_date, max_articles |
| The Guardian | `/theguardian_scraper_function` | keywords, start_date, end_date, max_articles |

### Indonesian News Scrapers

| Function | Endpoint | Parameters |
|----------|----------|------------|
| Kompas | `/kompas_scraper_function` | keywords, start_date, end_date, max_articles |
| Tempo | `/tempo_scraper_function` | keywords, start_date, end_date, max_articles |
| Kontan | `/kontan_scraper_function` | keywords, start_date, end_date, max_articles |
| CNBC Indonesia | `/cnbc_indonesia_scraper_function` | keywords, start_date, end_date, max_articles |
| Bisnis Indonesia | `/bisnis_indonesia_scraper_function` | keywords, start_date, end_date, max_articles |

### Data Scrapers

| Function | Endpoint | Parameters |
|----------|----------|------------|
| BPS | `/bps_scraper_function` | indicators, start_date, end_date |

## 📊 Parameter Details

### Common Parameters

- **keywords**: Comma-separated keywords (e.g., `energy,oil,gas`)
  - English: `energy,oil,gas,petroleum`
  - Indonesian: `energi,minyak,gas,pertamina`

- **start_date**: Start date in `YYYY-MM-DD` format (e.g., `2026-01-21`)

- **end_date**: End date in `YYYY-MM-DD` format (e.g., `2026-01-28`)

- **max_articles**: Maximum number of articles to scrape (e.g., `10`, `20`, `50`)

- **save_to_db**: Whether to save to database (`true` or `false`)

### BPS Specific Parameters

- **indicators**: Comma-separated indicators (e.g., `inflation,gdp,unemployment`)

## ✅ Expected Response

### Success Response (200 OK)
```json
{
  "status": "success",
  "source": "CNBC",
  "execution_time_seconds": 15.23,
  "execution_id": "abc123",
  "correlation_id": "xyz789",
  "parameters": {
    "keywords": ["energy", "oil"],
    "start_date": "2026-01-21",
    "end_date": "2026-01-28",
    "save_to_db": false
  },
  "results": {
    "articles_found": 25,
    "articles_saved": 0,
    "articles": [...]
  },
  "timestamp": "2026-01-28T10:30:00Z"
}
```

### Error Response (400/500)
```json
{
  "status": "error",
  "error": "Invalid parameters",
  "message": "Missing required parameter: keywords",
  "error_type": "ValueError",
  "execution_id": "abc123",
  "timestamp": "2026-01-28T10:30:00Z"
}
```

## 🔍 Troubleshooting

### Error: Connection Refused
**Problem**: Tidak bisa connect ke Azure Function
**Solution**:
- Verify Function App URL benar
- Check Function App status di Azure Portal (harus Running)
- Verify firewall/network settings

### Error: 401 Unauthorized
**Problem**: Function memerlukan authentication
**Solution**:
- Get Function Key dari Azure Portal
- Add ke URL: `?code=YOUR_FUNCTION_KEY`
- Atau add header: `-H "x-functions-key: YOUR_KEY"`

### Error: 404 Not Found
**Problem**: Function endpoint tidak ditemukan
**Solution**:
- Verify function name benar (case-sensitive)
- Check deployment status di Azure Portal
- Verify function sudah di-deploy

### Error: 500 Internal Server Error
**Problem**: Error di dalam function
**Solution**:
- Check Application Insights logs
- Check function logs di Azure Portal
- Verify import path issues sudah di-fix
- Check database connection string

### Error: Timeout
**Problem**: Function execution terlalu lama
**Solution**:
- Normal untuk scraping banyak artikel
- Increase timeout di script (default 5 minutes)
- Reduce `max_articles` parameter
- Check function performance di Azure Portal

## 📈 Performance Monitoring

### Check Execution Time
```cmd
curl -w "\nTime: %{time_total}s\n" -X GET "https://your-app.azurewebsites.net/api/cnbc_scraper_function?keywords=energy&start_date=2025-01-21&end_date=2026-01-28"
```

### Check Response Size
```cmd
curl -w "\nSize: %{size_download} bytes\n" -X GET "https://your-app.azurewebsites.net/api/cnbc_scraper_function?keywords=energy&start_date=2025-01-21&end_date=2026-01-28"
```

## 🎯 Testing Checklist

Before production deployment:

- [ ] All functions return 200 OK
- [ ] Response contains expected data structure
- [ ] Articles are being scraped correctly
- [ ] Execution time is acceptable (< 5 minutes)
- [ ] No import errors in logs
- [ ] Database saving works (if enabled)
- [ ] Error handling works correctly
- [ ] Logging is comprehensive

## 📝 Example Test Session

```cmd
C:\> cd azure_functions
C:\azure_functions> test_scrapers.bat

========================================
AZURE FUNCTIONS TESTING MENU
========================================

Current Function App: pertamina-news-scraper
Base URL: https://pertamina-news-scraper.azurewebsites.net/api

Enter your choice (0-13): 1

========================================
Testing CNBC Scraper Function
========================================
URL: https://pertamina-news-scraper.azurewebsites.net/api/cnbc_scraper_function

{
  "status": "success",
  "source": "CNBC",
  "execution_time_seconds": 12.45,
  "results": {
    "articles_found": 18,
    "articles_saved": 0
  }
}

✓ CNBC: PASSED
```

## 🔗 Related Documentation

- **Import Path Fix**: `IMPORT_PATH_FIX_SUMMARY.md`
- **Python 3.11 Compatibility**: `PYTHON_311_COMPATIBILITY_STATUS.md`
- **Comprehensive Logging**: `COMPREHENSIVE_LOGGING_GUIDE.md`
- **Local Testing**: `SCRAPER_TESTING_GUIDE.md`

## 💡 Tips

1. **Test lokal dulu** sebelum test deployed version
2. **Start dengan 1 function** untuk verify setup
3. **Use small date ranges** untuk testing cepat
4. **Monitor Application Insights** untuk detailed logs
5. **Check function logs** jika ada error
6. **Use save_to_db=false** untuk testing tanpa save ke database

## 🔐 Security Notes

### Function Keys
Jika function memerlukan authentication:

```cmd
# Add function key to URL
curl "https://your-app.azurewebsites.net/api/cnbc_scraper_function?code=YOUR_FUNCTION_KEY&keywords=energy"

# Or use header
curl -H "x-functions-key: YOUR_FUNCTION_KEY" "https://your-app.azurewebsites.net/api/cnbc_scraper_function?keywords=energy"
```

### Get Function Key
1. Azure Portal → Function App
2. Functions → Your Function
3. Function Keys → Copy key

## 📞 Support

Jika ada masalah:
1. Check error message di response
2. Check Application Insights logs
3. Verify function deployment status
4. Check this troubleshooting guide
5. Verify Python 3.11 compatibility fixes applied

---

**Last Updated**: January 28, 2026
**Python Version**: 3.11.0
**Status**: Ready for deployment testing ✅
