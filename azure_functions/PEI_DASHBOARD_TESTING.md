# PEI Dashboard Function App - Testing Guide

## 📋 Function App Information

- **Name**: PeiDashboard
- **URL**: `pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net`
- **Region**: Canada Central
- **Resource Group**: PeiDashboard
- **Subscription**: Azure subscription 1
- **Runtime**: Python (Azure Functions v4)
- **Plan**: Consumption (Y1)

## 🚀 Quick Start

### Test 1 Function (Fastest)

```cmd
cd azure_functions
test_pei_dashboard.bat
```

Ini akan test CNBC scraper function dan menampilkan response.

### Test dengan Menu

```cmd
cd azure_functions
test_scrapers.bat
```

### Test Semua Functions

```cmd
cd azure_functions
python test_deployed_functions.py
```

## 🔗 Function Endpoints

Base URL: `https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api`

### International News Scrapers

1. **CNBC**
   ```
   GET /cnbc_scraper_function?keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28&save_to_db=false
   ```

2. **OilPrice**
   ```
   GET /oilprice_scraper_function?keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28&max_articles=10
   ```

3. **Reuters**
   ```
   GET /reuters_scraper_function?keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28&save_to_db=false
   ```

4. **CNN**
   ```
   GET /cnn_scraper_function?keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28&max_articles=10
   ```

5. **The Guardian**
   ```
   GET /theguardian_scraper_function?keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28&max_articles=10
   ```

### Indonesian News Scrapers

6. **Kompas**
   ```
   GET /kompas_scraper_function?keywords=energi,minyak&start_date=2025-01-21&end_date=2026-01-28&max_articles=10
   ```

7. **Tempo**
   ```
   GET /tempo_scraper_function?keywords=energi,minyak&start_date=2025-01-21&end_date=2026-01-28&max_articles=10
   ```

8. **Kontan**
   ```
   GET /kontan_scraper_function?keywords=energi,minyak&start_date=2025-01-21&end_date=2026-01-28&max_articles=10
   ```

9. **CNBC Indonesia**
   ```
   GET /cnbc_indonesia_scraper_function?keywords=energi,minyak&start_date=2025-01-21&end_date=2026-01-28&max_articles=10
   ```

10. **Bisnis Indonesia**
    ```
    GET /bisnis_indonesia_scraper_function?keywords=energi,minyak&start_date=2025-01-21&end_date=2026-01-28&max_articles=10
    ```

### Data Scrapers

11. **BPS**
    ```
    GET /bps_scraper_function?indicators=inflation,gdp&start_date=2025-01-21&end_date=2026-01-28
    ```

## 📝 Example curl Commands

### Test CNBC (Copy-Paste Ready)

```cmd
curl -X GET "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/cnbc_scraper_function?keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28&save_to_db=false"
```

### Test OilPrice

```cmd
curl -X GET "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/oilprice_scraper_function?keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28&max_articles=10"
```

### Test Kompas (Indonesian)

```cmd
curl -X GET "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/kompas_scraper_function?keywords=energi,minyak&start_date=2025-01-21&end_date=2026-01-28&max_articles=10"
```

## ✅ Expected Response

### Success (200 OK)

```json
{
  "status": "success",
  "source": "CNBC",
  "execution_time_seconds": 12.45,
  "execution_id": "abc123",
  "correlation_id": "xyz789",
  "parameters": {
    "keywords": ["energy", "oil"],
    "start_date": "2026-01-21",
    "end_date": "2026-01-28",
    "save_to_db": false
  },
  "results": {
    "articles_found": 18,
    "articles_saved": 0,
    "articles": [...]
  },
  "timestamp": "2026-01-28T10:30:00Z"
}
```

### Error (400/500)

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

## 🔍 Monitoring & Logs

### Azure Portal
1. Go to: https://portal.azure.com
2. Navigate to: PeiDashboard Function App
3. Click: Functions → Select function → Monitor
4. View: Invocations, Success Rate, Errors

### Application Insights
1. Go to: PeiDashboard Function App
2. Click: Application Insights
3. View: Live Metrics, Failures, Performance

### Check Logs
```cmd
# Using Azure CLI
az functionapp log tail --name pei-dashboard-f5eebmdhe2a9dfgs --resource-group PeiDashboard
```

## 🎯 Testing Checklist

- [ ] Run `test_pei_dashboard.bat` untuk quick test
- [ ] Verify response = 200 OK
- [ ] Check articles_found > 0
- [ ] Verify execution_time < 60 seconds
- [ ] Test dengan keywords berbeda
- [ ] Test dengan date range berbeda
- [ ] Check Application Insights untuk errors
- [ ] Verify database saving (jika enabled)

## 🔧 Troubleshooting

### Function Returns 1ms / Immediate Failure
**Cause**: Import path issues
**Solution**: Import path fixes sudah di-apply, redeploy jika perlu

### Function Times Out
**Cause**: Scraping terlalu banyak artikel
**Solution**: 
- Reduce date range
- Reduce max_articles
- Check website availability

### 500 Internal Server Error
**Cause**: Error di dalam function
**Solution**:
- Check Application Insights logs
- Verify database connection
- Check import errors

### No Articles Found
**Cause**: Keywords tidak match atau date range salah
**Solution**:
- Try different keywords
- Expand date range
- Check website availability

## 📊 Performance Expectations

| Scraper | Expected Time | Expected Articles (7 days) |
|---------|--------------|---------------------------|
| CNBC | 10-30s | 10-30 |
| OilPrice | 15-45s | 10-20 |
| Reuters | 10-30s | 15-40 |
| CNN | 10-30s | 10-25 |
| The Guardian | 15-45s | 15-35 |
| Kompas | 10-30s | 10-25 |
| Tempo | 10-30s | 10-25 |
| Kontan | 10-30s | 10-20 |
| CNBC Indonesia | 10-30s | 10-20 |
| Bisnis Indonesia | 10-30s | 10-20 |
| BPS | 5-15s | 5-15 data points |

## 🔐 Security

Function App menggunakan:
- HTTPS only
- Managed Identity (jika configured)
- Key Vault untuk secrets (jika configured)
- Function keys untuk authentication (jika enabled)

## 📞 Support

Jika ada masalah:
1. Check error message di response
2. Check Application Insights
3. Verify function deployment status
4. Check this guide
5. Review import path fixes

## 🔗 Related Files

- `test_pei_dashboard.bat` - Quick test script
- `test_scrapers.bat` - Menu interaktif
- `test_deployed_functions.py` - Test semua functions
- `DEPLOYED_FUNCTIONS_TESTING_GUIDE.md` - Detailed guide

---

**Function App**: PeiDashboard  
**Region**: Canada Central  
**Status**: Running ✅  
**Last Updated**: January 28, 2026
