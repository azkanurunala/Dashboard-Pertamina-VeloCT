# CNBC Scraper Error Analysis

## Task 2.2: Trigger CNBC Scraper Function and Capture Error Logs

**Date**: January 28, 2026  
**Function**: cnbc_scraper_function  
**Status**: ❌ FAILED - HTTP 500 with Empty Response Body

---

## Executive Summary

The CNBC scraper function was triggered and returned an **HTTP 500 Internal Server Error** with an **empty response body**. This indicates the function is crashing during execution without proper error handling to return error details.

### Key Findings

- ✅ Function is reachable (not a deployment issue)
- ❌ Function crashes during execution (HTTP 500)
- ❌ No error message returned in response body
- ❌ Application Insights not capturing error details
- ⚠️ Azure CLI not available for real-time log capture

---

## Test Execution Details

### HTTP Request

**URL**: `https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/cnbc_scraper_function`

**Method**: POST

**Payload**:
```json
{
  "keywords": ["energy", "oil", "gas"],
  "start_date": "2026-01-27",
  "end_date": "2026-01-28",
  "save_to_db": true
}
```

### HTTP Response

**Status Code**: 500 (Internal Server Error)

**Execution Time**: 13.5 seconds

**Response Body**: Empty (0 bytes)

**Response Headers**:
```
Content-Length: 0
Date: Wed, 28 Jan 2026 08:55:10 GMT
Server: Kestrel
Request-Context: appId=cid-v1:9db8826b-a342-44c5-973d-a045bac44ee2
```

### Application Insights Query Results

**Errors**: 0 entries found  
**Exceptions**: 0 entries found  
**Failed Requests**: 0 entries found

**Analysis**: Application Insights is either:
1. Not properly configured to capture function errors
2. Has a delay in processing logs (>5 minutes)
3. Function is crashing before logging can occur

---

## Error Classification

Based on the symptoms, this is likely one of the following error types:

### 1. Import Error (Most Likely)
**Symptoms**:
- Function crashes immediately on invocation
- No error message returned
- Fast failure (13.5 seconds includes network time)

**Possible Causes**:
- Missing Python package in requirements.txt
- Incorrect import paths (e.g., `from shared.config` instead of `from ..shared.config`)
- Module not found during function initialization

**Example Error**:
```python
ModuleNotFoundError: No module named 'requests'
ImportError: cannot import name 'CNBCNewsScraper' from 'scrapers.cnbc_scraper'
```

### 2. Configuration Error (Possible)
**Symptoms**:
- Function starts but crashes during initialization
- Configuration values not found

**Possible Causes**:
- Database connection string not configured
- Key Vault reference not resolved
- Missing environment variables

**Example Error**:
```python
ConfigurationError: Database connection string not found
KeyError: 'DatabaseConnectionString'
```

### 3. Dependency Error (Possible)
**Symptoms**:
- Function deploys but crashes on first import
- Package version incompatibility

**Possible Causes**:
- requirements.txt not deployed with function
- Package version conflicts
- Missing system dependencies

---

## Validation Against Requirements

### Requirement 1.2: Capture Error Messages and Stack Traces
**Status**: ❌ FAILED

**Issue**: Function returns empty response body, no error message captured.

**Expected**: Error message and stack trace should be in response body or logs.

**Actual**: Empty response body, no logs in Application Insights.

### Requirement 1.4: Include Import Errors and Runtime Exceptions
**Status**: ❌ FAILED

**Issue**: No error details captured anywhere.

**Expected**: Import errors and exceptions should be logged to Application Insights.

**Actual**: No errors found in Application Insights queries.

### Requirement 9.4: HTTP 500 Errors Should Include Error Message
**Status**: ❌ FAILED

**Issue**: Response body is empty (0 bytes).

**Expected**: JSON response with error details:
```json
{
  "status": "error",
  "error": "ErrorType",
  "message": "Detailed error description",
  "timestamp": "2026-01-28T08:55:10Z"
}
```

**Actual**: Empty response body.

### Requirement 9.5: Never Return Empty Response Bodies
**Status**: ❌ FAILED

**Issue**: Response body is completely empty.

**Expected**: All responses should contain JSON with status and details.

**Actual**: 0-byte response body.

---

## Manual Log Access Required

Since Azure CLI is not installed and Application Insights is not showing errors, **manual log access via Azure Portal is required**.

### Step-by-Step Instructions

#### 1. Access Azure Portal Log Stream

1. **Open Azure Portal**
   - Navigate to: https://portal.azure.com
   - Sign in with your Azure credentials

2. **Navigate to Function App**
   - Search for: `pei-dashboard`
   - Click on the Function App from search results

3. **Open Log Stream**
   - In left sidebar, scroll to **Monitoring** section
   - Click **Log stream**
   - Log stream will start automatically

#### 2. Trigger Function While Watching Logs

1. **Keep Log Stream Open** in one browser tab

2. **Trigger Function** using one of these methods:

   **Option A: Using PowerShell**
   ```powershell
   $url = "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/cnbc_scraper_function?code=QRn4YL31yW-bZBFHDlt8znrvRmlfbvD8owXwCBegfk7TAzFuLEZIFg=="
   
   $body = @{
       keywords = @("energy", "oil", "gas")
       start_date = "2026-01-27"
       end_date = "2026-01-28"
       save_to_db = $true
   } | ConvertTo-Json
   
   Invoke-RestMethod -Uri $url -Method POST -Body $body -ContentType "application/json"
   ```

   **Option B: Using Python**
   ```python
   python capture_cnbc_error.py
   ```

   **Option C: Using Azure Portal Test**
   - Go to Function App → Functions → cnbc_scraper_function
   - Click **Code + Test**
   - Click **Test/Run**
   - Enter test parameters
   - Click **Run**

3. **Watch Log Stream** for error messages

4. **Capture Error Details**
   - Look for lines with `[Error]` prefix
   - Copy full error message
   - Copy complete stack trace
   - Note the timestamp

#### 3. Save Captured Logs

1. **Select All Logs** (Ctrl+A or Cmd+A)
2. **Copy to Clipboard** (Ctrl+C or Cmd+C)
3. **Save to File**:
   ```
   azure_functions/diagnostic_logs/portal_logs_cnbc_YYYYMMDD_HHMMSS.txt
   ```

#### 4. Classify Errors

Once logs are captured, classify the error type:

```bash
# If you have the diagnostic tool
python diagnostic_tool.py classify-error diagnostic_logs/portal_logs_cnbc_*.txt

# Manual classification
# Look for these patterns in the logs:
# - "ModuleNotFoundError" or "ImportError" → Import Error
# - "ConfigurationError" or "not found" → Configuration Error
# - "NetworkError" or "timeout" → Network Error
# - "database" or "sql" → Database Error
```

---

## Alternative: Application Insights Portal Query

If log stream doesn't work, try querying Application Insights directly:

### Access Application Insights

1. **Navigate to Application Insights**
   - Azure Portal → Search "pei-dashboard"
   - Click on the Application Insights resource (not Function App)
   - Or: Function App → Application Insights → View Application Insights data

2. **Open Logs Query**
   - Click **Logs** in left sidebar
   - Close any tutorial popups

3. **Run Error Query**

   **Query for Traces (Errors)**:
   ```kusto
   traces
   | where timestamp > ago(1h)
   | where severityLevel >= 3
   | where cloud_RoleName == "cnbc_scraper_function" or message contains "cnbc"
   | order by timestamp desc
   | project timestamp, severityLevel, message, operation_Name
   ```

   **Query for Exceptions**:
   ```kusto
   exceptions
   | where timestamp > ago(1h)
   | where cloud_RoleName == "cnbc_scraper_function" or outerMessage contains "cnbc"
   | order by timestamp desc
   | project timestamp, type, outerMessage, innermostMessage, details
   ```

   **Query for Failed Requests**:
   ```kusto
   requests
   | where timestamp > ago(1h)
   | where success == false
   | where name == "cnbc_scraper_function" or url contains "cnbc"
   | order by timestamp desc
   | project timestamp, name, resultCode, duration, url
   ```

4. **Export Results**
   - Click **Export** button
   - Choose **Export to CSV** or **Export to Excel**
   - Save to: `diagnostic_logs/appinsights_query_results.csv`

---

## Expected Error Patterns

Based on similar Azure Functions issues, here are the most likely errors:

### Pattern 1: Import Error
```
[Error] Exception while executing function: cnbc_scraper_function
[Error] ModuleNotFoundError: No module named 'requests'
[Error] Stack trace:
  File "/home/site/wwwroot/cnbc_scraper_function/__init__.py", line 5, in <module>
    import requests
```

**Fix**: Add `requests` to requirements.txt

### Pattern 2: Relative Import Error
```
[Error] ImportError: attempted relative import with no known parent package
[Error] Stack trace:
  File "/home/site/wwwroot/cnbc_scraper_function/__init__.py", line 3, in <module>
    from ..scrapers.cnbc_scraper import CNBCNewsScraper
```

**Fix**: Verify import paths use correct relative imports

### Pattern 3: Configuration Error
```
[Error] Exception while executing function: cnbc_scraper_function
[Error] ConfigurationError: Database connection string not found
[Error] Stack trace:
  File "/home/site/wwwroot/shared/config.py", line 45, in get_database_connection_string
    raise ConfigurationError("Database connection string not found")
```

**Fix**: Add database connection string to Function App settings

### Pattern 4: Missing Scraper Module
```
[Error] ModuleNotFoundError: No module named 'scrapers.cnbc_scraper'
[Error] Stack trace:
  File "/home/site/wwwroot/cnbc_scraper_function/__init__.py", line 4, in <module>
    from ..scrapers.cnbc_scraper import CNBCNewsScraper
```

**Fix**: Verify scraper file is deployed and in correct location

---

## Recommended Next Steps

### Immediate Actions (Required)

1. **Access Azure Portal Log Stream** (see instructions above)
2. **Trigger CNBC scraper** while watching logs
3. **Capture full error message and stack trace**
4. **Save logs to file** for analysis
5. **Classify error type** (import, config, dependency, etc.)

### After Capturing Logs

1. **Analyze error details** to identify root cause
2. **Apply appropriate fix** based on error classification:
   - Import Error → Fix import statements
   - Dependency Error → Update requirements.txt
   - Configuration Error → Add environment variables
   - Runtime Error → Fix code logic

3. **Redeploy function** with fixes
4. **Test again** and verify HTTP 200 response
5. **Document results** in diagnostic session

### If Manual Access Fails

If you cannot access Azure Portal or logs are not appearing:

1. **Check Azure permissions**
   - Verify you have Reader or Contributor role
   - Contact Azure admin if needed

2. **Enable Application Insights**
   - Function App → Application Insights
   - Verify it's enabled and connected

3. **Check Function App status**
   - Function App → Overview
   - Verify status is "Running"
   - Check for any platform issues

4. **Try alternative function**
   - Test a different scraper (e.g., CNN)
   - See if error is specific to CNBC or affects all functions

---

## Files Generated

This error capture session generated the following files:

1. **cnbc_response_20260128_155514.json**
   - HTTP response details
   - Status code: 500
   - Empty response body
   - Response headers

2. **cnbc_appinsights_20260128_155519.json**
   - Application Insights query results
   - No errors found
   - No exceptions found
   - No failed requests found

3. **CNBC_ERROR_ANALYSIS.md** (this file)
   - Comprehensive error analysis
   - Manual log access instructions
   - Expected error patterns
   - Next steps and recommendations

---

## Summary

### What We Know

✅ Function is deployed and reachable  
✅ Function accepts HTTP requests  
❌ Function crashes with HTTP 500  
❌ No error message in response body  
❌ Application Insights not capturing errors  
⚠️ Azure CLI not available for log capture  

### What We Need

🔍 **Full error message and stack trace** from Azure Portal log stream  
🔍 **Error type classification** (import, config, dependency, runtime)  
🔍 **Specific missing package or configuration** causing the crash  

### How to Get It

📋 Follow the **Manual Log Access Required** section above  
📋 Access Azure Portal → pei-dashboard → Log stream  
📋 Trigger function while watching logs  
📋 Capture and save error details  

### Once We Have Logs

🔧 Classify error type  
🔧 Apply appropriate fix  
🔧 Redeploy function  
🔧 Test and verify  

---

## Validation Against Design Document

### Property 1: Comprehensive Error Logging
**Status**: ❌ FAILED

**Expected**: Error message and stack trace captured in logs.

**Actual**: No errors captured in Application Insights, manual access required.

### Property 29: HTTP 500 Error Body
**Status**: ❌ FAILED

**Expected**: Response body contains JSON with error details.

**Actual**: Response body is empty (0 bytes).

**Requirement**: 9.4, 9.5 - HTTP 500 errors must include error message in response body.

---

## References

- **Azure Portal Log Access Guide**: `diagnostics/AZURE_PORTAL_LOG_ACCESS.md`
- **Log Access Quick Reference**: `diagnostics/LOG_ACCESS_QUICK_REFERENCE.md`
- **Application Insights Queries**: `diagnostics/appinsights_queries.md`
- **Diagnostic Tool**: `diagnostic_tool.py`
- **Capture Script**: `capture_cnbc_error.py`

---

**Task Status**: ⏸️ PAUSED - Awaiting manual log capture from Azure Portal

**Next Task**: Capture error logs from Azure Portal log stream and classify error type

**Blocked By**: Azure CLI not installed, Application Insights not showing errors

**Workaround**: Manual log access via Azure Portal web interface (instructions provided above)
