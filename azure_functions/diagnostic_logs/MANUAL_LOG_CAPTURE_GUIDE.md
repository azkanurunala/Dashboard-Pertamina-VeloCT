# Manual Log Capture Guide - Quick Start

## 🎯 Goal
Capture the error logs from the CNBC scraper function that's returning HTTP 500.

## ⚡ Quick Steps (5 minutes)

### Step 1: Open Azure Portal Log Stream
1. Go to: https://portal.azure.com
2. Search: `pei-dashboard`
3. Click: **Monitoring** → **Log stream**

### Step 2: Trigger the Function

**Option A: PowerShell (Recommended)**
```powershell
$url = "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/cnbc_scraper_function?code=QRn4YL31yW-bZBFHDlt8znrvRmlfbvD8owXwCBegfk7TAzFuLEZIFg=="

$body = @{
    keywords = @("energy")
    start_date = "2026-01-27"
    end_date = "2026-01-28"
    save_to_db = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri $url -Method POST -Body $body -ContentType "application/json"
```

**Option B: Python**
```bash
cd azure_functions
python capture_cnbc_error.py
```

### Step 3: Watch for Errors

Look for lines like:
```
[Error] Exception while executing function: cnbc_scraper_function
[Error] ModuleNotFoundError: No module named 'requests'
[Error] Stack trace:
  File "/home/site/wwwroot/cnbc_scraper_function/__init__.py", line 5
```

### Step 4: Copy the Logs

1. **Select all** (Ctrl+A)
2. **Copy** (Ctrl+C)
3. **Paste into file**: `diagnostic_logs/portal_logs_cnbc.txt`

### Step 5: Share the Logs

Send the captured logs file so we can:
- Identify the exact error
- Classify the error type
- Apply the appropriate fix

---

## 🔍 What to Look For

### Import Errors (Most Common)
```
ModuleNotFoundError: No module named 'requests'
ImportError: cannot import name 'CNBCNewsScraper'
```

### Configuration Errors
```
ConfigurationError: Database connection string not found
KeyError: 'DatabaseConnectionString'
```

### Dependency Errors
```
No module named 'beautifulsoup4'
No module named 'aiohttp'
```

---

## 📋 Alternative: Application Insights Query

If log stream doesn't work:

1. **Go to**: Azure Portal → pei-dashboard → Application Insights
2. **Click**: Logs
3. **Run this query**:
```kusto
traces
| where timestamp > ago(1h)
| where severityLevel >= 3
| order by timestamp desc
```

4. **Export**: Click Export → CSV
5. **Save**: `diagnostic_logs/appinsights_traces.csv`

---

## ❓ Troubleshooting

### "No logs appearing"
- ✅ Make sure you triggered the function
- ✅ Refresh the log stream page
- ✅ Try Application Insights query instead

### "Permission denied"
- ✅ Check you have Reader role on the Function App
- ✅ Contact Azure admin for access

### "Log stream disconnected"
- ✅ Refresh the page
- ✅ Try a different browser
- ✅ Use Application Insights as backup

---

## 📞 Need Help?

If you're stuck:
1. Share a screenshot of what you see in the log stream
2. Share any error messages you encounter
3. We'll help troubleshoot the access issue

---

## ✅ Success Criteria

You've successfully captured logs when you have:
- ✅ Full error message (e.g., "ModuleNotFoundError: No module named 'X'")
- ✅ Stack trace showing which file and line number
- ✅ Function name (cnbc_scraper_function)
- ✅ Timestamp of the error

---

## 🚀 After Capturing Logs

Once you have the logs:
1. We'll classify the error type
2. Apply the appropriate fix
3. Redeploy the function
4. Test again to verify it works

**Expected outcome**: HTTP 200 with articles data instead of HTTP 500 with empty body.

---

## 📚 Full Documentation

For detailed information, see:
- **Full Analysis**: `CNBC_ERROR_ANALYSIS.md`
- **Portal Guide**: `../diagnostics/AZURE_PORTAL_LOG_ACCESS.md`
- **Quick Reference**: `../diagnostics/LOG_ACCESS_QUICK_REFERENCE.md`
