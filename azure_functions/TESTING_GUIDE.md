# Azure Functions Testing Guide

## Quick Start - Run Complete Test

To test everything in one go:

```powershell
cd azure_functions
.\RUN_COMPLETE_TEST.ps1
```

This will:
1. Configure direct database connection (bypass Key Vault for now)
2. Test the basic test_function
3. Test CNBC scraper function
4. Verify data was written to SQL Server database

---

## Individual Test Scripts

### 1. Configure Database Connection

```powershell
.\fix_and_test.ps1
```

This configures the direct database connection string and tests the basic function.

### 2. Test Basic Function

```powershell
python quick_test.py
```

Tests the `test_function` endpoint to verify basic connectivity.

### 3. Test Scraper Function

```powershell
python quick_test_scraper.py
```

Tests the CNBC scraper function to verify:
- Function execution
- Article scraping
- Database writes

### 4. Verify Database Data

```powershell
python verify_database_data.py
```

Connects directly to SQL Server and verifies:
- Total article count
- Recent articles
- Articles by source
- Today's scraped articles

---

## Current Configuration

- **Function App**: `pei-dashboard`
- **Resource Group**: `PeiDashboard`
- **Function App URL**: `https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net`
- **Function Key**: `QRn4YL31yW-bZBFHDlt8znrvRmlfbvD8owXwCBegfk7TAzFuLEZIFg==`
- **SQL Server**: `pei-dashboard.database.windows.net`
- **Database**: `pei-dashboard`

---

## Available Scraper Functions

All functions use the same URL pattern:
```
https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/{function_name}?code={function_key}
```

### International News Sources
1. `cnbc_scraper_function` - CNBC (US)
2. `cnn_scraper_function` - CNN (US)
3. `reuters_scraper_function` - Reuters (International)
4. `theguardian_scraper_function` - The Guardian (UK)
5. `oilprice_scraper_function` - OilPrice.com

### Indonesian News Sources
6. `bisnis_indonesia_scraper_function` - Bisnis Indonesia
7. `cnbc_indonesia_scraper_function` - CNBC Indonesia
8. `kompas_scraper_function` - Kompas
9. `kontan_scraper_function` - Kontan
10. `tempo_scraper_function` - Tempo

### Data Sources
11. `bps_scraper_function` - BPS (Indonesian Statistics)

### Utility Functions
12. `database_maintenance_function` - Database maintenance
13. `deduplication_function` - Remove duplicate articles
14. `test_function` - Basic connectivity test

---

## Testing Individual Scrapers

Example for testing any scraper:

```python
import requests
import json

url = "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/cnbc_scraper_function"
params = {"code": "QRn4YL31yW-bZBFHDlt8znrvRmlfbvD8owXwCBegfk7TAzFuLEZIFg=="}

payload = {
    "keywords": ["energy", "oil"],
    "start_date": "2026-01-27",
    "end_date": "2026-01-28",
    "save_to_db": True
}

response = requests.post(url, params=params, json=payload, timeout=120)
print(response.json())
```

---

## Troubleshooting

### Issue: "Database connection string not found"

**Solution**: Run `fix_and_test.ps1` to configure direct connection string.

### Issue: Function returns 500 error

**Possible causes**:
1. Missing dependencies - check deployment logs
2. Configuration error - verify app settings
3. Code error - check Application Insights logs

**Check logs**:
```powershell
az functionapp log tail --name pei-dashboard --resource-group PeiDashboard
```

### Issue: No articles saved to database

**Possible causes**:
1. No articles matched the search criteria (normal)
2. Database connection failed (check error message)
3. Scraper couldn't access the website (check error message)

**Verify database**:
```powershell
python verify_database_data.py
```

---

## Next Steps After Successful Testing

1. **Configure Copilot API** (for sentiment analysis):
   ```powershell
   az functionapp config appsettings set \
       --name pei-dashboard \
       --resource-group PeiDashboard \
       --settings "CopilotApiKey=YOUR_API_KEY" "CopilotEndpoint=YOUR_ENDPOINT"
   ```

2. **Set up Key Vault integration** (for production):
   - The code already supports Key Vault
   - RBAC permissions are configured
   - May need to wait for propagation or troubleshoot further

3. **Configure scheduled triggers**:
   - Edit function.json files to add timer triggers
   - Or use Azure Portal to configure schedules

4. **Monitor and optimize**:
   - Set up Application Insights alerts
   - Monitor function execution times
   - Optimize database queries if needed

---

## Key Vault Integration (Future)

The code is already prepared for Key Vault integration. Once RBAC propagates:

1. Secrets are stored in Key Vault:
   - `DatabaseConnectionString`
   - `StorageConnectionString`
   - `CopilotApiKey`
   - `CopilotEndpoint`

2. App Settings reference Key Vault:
   ```
   DatabaseConnectionString=@Microsoft.KeyVault(SecretUri=https://peidashboard.vault.azure.net/secrets/DatabaseConnectionString/)
   ```

3. Functions use Managed Identity to access secrets automatically

For now, we're using direct connection strings which work fine for testing.
