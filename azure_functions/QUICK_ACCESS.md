# 🚀 Quick Access Guide - PEI Dashboard Functions

## 🔑 Get Your Function Keys

```bash
az functionapp keys list --name pei-dashboard --resource-group PeiDashboard
```

Simpan output ini - Anda akan memerlukan `masterKey` atau function-specific keys.

---

## 🧪 Test Functions

### 1. Health Check (No Auth Required)
```bash
curl https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/health
```

### 2. Test Function (Requires Auth)
```bash
# Replace YOUR_KEY with actual key
curl "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/test_function?code=YOUR_KEY"
```

### 3. Test Scraper (Example: Reuters)
```bash
curl "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/reuters_scraper_function?code=YOUR_KEY"
```

---

## 📋 All Function URLs

### Base URL
```
https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net
```

### Indonesian News Scrapers
```
/api/bisnis_indonesia_scraper_function
/api/cnbc_indonesia_scraper_function
/api/kompas_scraper_function
/api/kontan_scraper_function
/api/kontan_bbm_scraper_function
/api/kontan_biodiesel_scraper_function
/api/tempo_scraper_function
/api/bloomberg_technoz_scraper_function
/api/energiesmedia_scraper_function
```

### International News Scrapers
```
/api/cnn_scraper_function
/api/cnbc_scraper_function
/api/reuters_scraper_function
/api/theguardian_scraper_function
/api/scmp_scraper_function
```

### Energy & Commodity Data
```
/api/oilprice_scraper_function
/api/cpo_scraper_function
/api/biodiesel_esdm_scraper_function
/api/bioetanol_esdm_scraper_function
/api/migas_esdm_scraper_function
/api/migas_eia_scraper_function
/api/bioenergytimes_scraper_function
/api/sipsn_scraper_function
```

### Government & Market Data
```
/api/bank_indonesia_scraper_function
/api/bps_scraper_function
/api/iaea_pris_scraper_function
/api/sandp_data_scraper_function
/api/sandp_news_scraper_function
/api/google_news_scraper_function
```

### Utility Functions
```
/api/health (no auth required)
/api/maintenance
/api/deduplicate
/api/test_function
/api/test_env_function
/api/test_imports_function
/api/test_new_deploy_function
```

---

## 🔧 Management Commands

### View Live Logs
```bash
func azure functionapp logstream pei-dashboard
```

### Restart Function App
```bash
az functionapp restart --name pei-dashboard --resource-group PeiDashboard
```

### Stop Function App
```bash
az functionapp stop --name pei-dashboard --resource-group PeiDashboard
```

### Start Function App
```bash
az functionapp start --name pei-dashboard --resource-group PeiDashboard
```

### List All Functions
```bash
az functionapp function list --name pei-dashboard --resource-group PeiDashboard --output table
```

---

## 🌐 Azure Portal Quick Links

### Function App Dashboard
```
https://portal.azure.com/#@/resource/subscriptions/5e4ecee4-ce42-47f4-b953-7f29ad625c53/resourceGroups/PeiDashboard/providers/Microsoft.Web/sites/pei-dashboard
```

### Deployment Center
```
https://portal.azure.com/#@/resource/subscriptions/5e4ecee4-ce42-47f4-b953-7f29ad625c53/resourceGroups/PeiDashboard/providers/Microsoft.Web/sites/pei-dashboard/vstscd
```

### Application Insights
```
https://portal.azure.com → Search "pei-dashboard" → Application Insights
```

---

## 📊 Monitoring Queries (Application Insights)

### Failed Requests (Last 24h)
```kusto
requests
| where timestamp > ago(24h)
| where success == false
| summarize count() by name, resultCode
| order by count_ desc
```

### Function Performance
```kusto
requests
| where timestamp > ago(1h)
| summarize avg(duration), max(duration), count() by name
| order by avg_duration desc
```

### Recent Exceptions
```kusto
exceptions
| where timestamp > ago(24h)
| project timestamp, type, outerMessage, operation_Name
| order by timestamp desc
```

---

## 🎯 Quick Test Script

Save as `test_functions.sh` (Linux/Mac) or `test_functions.ps1` (Windows):

### PowerShell Version
```powershell
# Get function key
$keys = az functionapp keys list --name pei-dashboard --resource-group PeiDashboard | ConvertFrom-Json
$masterKey = $keys.masterKey

# Test health check
Write-Host "Testing Health Check..."
Invoke-RestMethod -Uri "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/health"

# Test authenticated function
Write-Host "Testing Reuters Scraper..."
Invoke-RestMethod -Uri "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/reuters_scraper_function?code=$masterKey"
```

### Bash Version
```bash
#!/bin/bash

# Get function key
MASTER_KEY=$(az functionapp keys list --name pei-dashboard --resource-group PeiDashboard --query masterKey -o tsv)

# Test health check
echo "Testing Health Check..."
curl https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/health

# Test authenticated function
echo "Testing Reuters Scraper..."
curl "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/reuters_scraper_function?code=$MASTER_KEY"
```

---

## 📱 Postman Collection

Import this into Postman for easy testing:

```json
{
  "info": {
    "name": "PEI Dashboard Functions",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "baseUrl",
      "value": "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net"
    },
    {
      "key": "functionKey",
      "value": "YOUR_FUNCTION_KEY_HERE"
    }
  ],
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "url": "{{baseUrl}}/api/health"
      }
    },
    {
      "name": "Reuters Scraper",
      "request": {
        "method": "GET",
        "url": "{{baseUrl}}/api/reuters_scraper_function?code={{functionKey}}"
      }
    }
  ]
}
```

---

**Pro Tip**: Bookmark this page for quick access to all your function URLs and commands!
