# Azure Portal Log Stream Access Guide

## Overview

This guide documents how to access real-time log streams for the **pei-dashboard** Function App using the Azure Portal web interface. This is one of three methods for accessing Azure Function logs (Portal UI, Azure CLI, Application Insights).

**Validates Requirement 1.1**: Access Azure Portal log stream for real-time function execution logs.

## Prerequisites

- Azure account with access to the PeiDashboard resource group
- Web browser (Chrome, Edge, Firefox, or Safari)
- Appropriate permissions (Reader or Contributor role on the Function App)

## Step-by-Step Instructions

### Method 1: Direct Navigation

1. **Open Azure Portal**
   - Navigate to: https://portal.azure.com
   - Sign in with your Azure credentials

2. **Navigate to Function App**
   - In the search bar at the top, type: `pei-dashboard`
   - Click on the **pei-dashboard** Function App from the search results
   - Alternatively: Home → Resource Groups → PeiDashboard → pei-dashboard

3. **Access Log Stream**
   - In the left sidebar, scroll down to the **Monitoring** section
   - Click on **Log stream**
   - The log stream will automatically start displaying real-time logs

4. **View Logs**
   - Logs appear in real-time as functions execute
   - Each log entry shows:
     - Timestamp
     - Log level (Information, Warning, Error)
     - Function name
     - Message content
     - Stack traces (for errors)

### Method 2: Direct URL

You can bookmark this URL for quick access:

```
https://portal.azure.com/#@/resource/subscriptions/{subscription-id}/resourceGroups/PeiDashboard/providers/Microsoft.Web/sites/pei-dashboard/logStream
```

**Note**: Replace `{subscription-id}` with your actual Azure subscription ID.

To find your subscription ID:
1. Go to Azure Portal → Subscriptions
2. Copy the Subscription ID for your subscription

### Method 3: Using Diagnostic Tool

The diagnostic tool can provide the portal URL:

```bash
python diagnostic_tool.py check-access
```

This will display the portal URL along with other access methods.

## Log Stream Features

### Real-Time Monitoring

The log stream provides:
- **Live Updates**: Logs appear as they are generated
- **Auto-Scroll**: Automatically scrolls to show latest logs
- **Color Coding**: Different colors for log levels (Info, Warning, Error)
- **Function Filtering**: Can filter by specific function name

### Log Levels

| Level | Color | Description |
|-------|-------|-------------|
| Information | Blue | Normal execution logs, function invocations |
| Warning | Yellow | Non-critical issues, deprecation warnings |
| Error | Red | Exceptions, failures, critical issues |

### What You'll See

**Successful Function Execution:**
```
2024-01-28T10:30:15.123 [Information] Executing 'cnbc_scraper_function' (Reason='This function was programmatically called via the host APIs.', Id=abc-123)
2024-01-28T10:30:15.456 [Information] Starting CNBC news scraper...
2024-01-28T10:30:16.789 [Information] Found 15 articles
2024-01-28T10:30:17.012 [Information] Executed 'cnbc_scraper_function' (Succeeded, Id=abc-123, Duration=1889ms)
```

**Function with Errors:**
```
2024-01-28T10:31:20.123 [Information] Executing 'cnbc_scraper_function' (Reason='This function was programmatically called via the host APIs.', Id=def-456)
2024-01-28T10:31:20.456 [Error] Exception while executing function: cnbc_scraper_function
2024-01-28T10:31:20.457 [Error] ModuleNotFoundError: No module named 'requests'
2024-01-28T10:31:20.458 [Error] Stack trace:
  File "/home/site/wwwroot/cnbc_scraper_function/__init__.py", line 5, in <module>
    import requests
2024-01-28T10:31:20.789 [Error] Executed 'cnbc_scraper_function' (Failed, Id=def-456, Duration=666ms)
```

## Triggering Functions to Generate Logs

To see logs in the stream, you need to invoke functions:

### Option 1: HTTP Request (Recommended)

```bash
# Using curl
curl -X POST "https://pei-dashboard.azurewebsites.net/api/cnbc_scraper_function?code={function-key}" \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2024-01-01", "end_date": "2024-01-07"}'

# Using PowerShell
Invoke-RestMethod -Uri "https://pei-dashboard.azurewebsites.net/api/cnbc_scraper_function?code={function-key}" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"start_date": "2024-01-01", "end_date": "2024-01-07"}'
```

### Option 2: Azure Portal Test

1. In the Function App, click on **Functions** in the left sidebar
2. Select a function (e.g., `cnbc_scraper_function`)
3. Click **Code + Test**
4. Click **Test/Run**
5. Enter test parameters in the request body
6. Click **Run**
7. Switch to the **Log stream** tab to see execution logs

### Option 3: Using Test Scripts

```bash
# Run existing test script
cd azure_functions
python test_scraper.py cnbc
```

## Capturing Logs for Analysis

### Manual Copy-Paste

1. Let the log stream run for desired duration (e.g., 30 seconds)
2. Select all log text (Ctrl+A or Cmd+A)
3. Copy to clipboard (Ctrl+C or Cmd+C)
4. Paste into a text file for analysis

### Save to File

```bash
# Create logs directory if it doesn't exist
mkdir -p azure_functions/logs

# Save logs with timestamp
# (Paste copied logs into file)
notepad azure_functions/logs/portal_logs_2024-01-28.txt
```

### Analyze Captured Logs

```bash
# Use diagnostic tool to classify errors
python diagnostic_tool.py classify-error logs/portal_logs_2024-01-28.txt
```

## Filtering and Searching

### Filter by Function Name

In the log stream interface:
1. Look for the filter/search box (usually at the top)
2. Enter function name: `cnbc_scraper_function`
3. Only logs from that function will be displayed

### Filter by Log Level

Some portal versions allow filtering by severity:
- Click the filter icon
- Select log levels to display (Information, Warning, Error)
- Uncheck levels you want to hide

### Search for Keywords

Use browser search (Ctrl+F or Cmd+F) to find:
- Error messages: Search for "Error", "Exception", "Failed"
- Specific functions: Search for function name
- Specific operations: Search for "database", "scraping", etc.

## Troubleshooting

### No Logs Appearing

**Problem**: Log stream is open but no logs are displayed.

**Solutions**:
1. **Invoke a function**: Logs only appear when functions execute
   - Use HTTP request to trigger a function
   - Use Azure Portal Test/Run feature
2. **Check Application Insights**: Ensure it's enabled
   - Function App → Application Insights → Verify it's connected
3. **Refresh the page**: Sometimes the stream connection drops
   - Press F5 to reload the page
   - Reopen the Log stream tab
4. **Check permissions**: Ensure you have Reader or Contributor role
   - Resource Group → Access control (IAM) → Check your role

### Connection Timeout

**Problem**: "Connection timed out" or "Stream disconnected" message.

**Solutions**:
1. **Refresh the page**: Reload the Azure Portal page
2. **Check network**: Ensure stable internet connection
3. **Try different browser**: Some browsers handle streaming better
4. **Use Azure CLI instead**: Fallback to `az functionapp log tail`

### Logs Are Truncated

**Problem**: Long error messages or stack traces are cut off.

**Solutions**:
1. **Use Application Insights**: Query for full logs
   ```bash
   python diagnostic_tool.py get-errors 30
   ```
2. **Use Azure CLI**: Provides complete log output
   ```bash
   az functionapp log tail --name pei-dashboard --resource-group PeiDashboard
   ```
3. **Download logs**: Use Azure CLI to save complete logs to file

### Permission Denied

**Problem**: "You do not have permission to view this resource" error.

**Solutions**:
1. **Check role assignment**: 
   - Go to Resource Group → Access control (IAM)
   - Verify you have Reader or Contributor role
2. **Request access**: Contact Azure subscription administrator
3. **Use different account**: Try signing in with account that has access

## Comparison with Other Methods

### Azure Portal vs Azure CLI vs Application Insights

| Feature | Azure Portal | Azure CLI | Application Insights |
|---------|--------------|-----------|---------------------|
| **Real-time** | ✅ Yes | ✅ Yes | ❌ No (slight delay) |
| **Historical** | ❌ No | ❌ No | ✅ Yes (up to 90 days) |
| **Filtering** | ⚠️ Limited | ⚠️ Limited | ✅ Advanced (Kusto) |
| **Copy/Save** | ⚠️ Manual | ✅ Easy | ✅ Export |
| **Setup** | ✅ None | ⚠️ Requires CLI | ✅ None |
| **Offline** | ❌ No | ❌ No | ✅ Yes (query results) |
| **Automation** | ❌ No | ✅ Yes | ✅ Yes |

**Recommendation**: 
- Use **Azure Portal** for quick real-time monitoring
- Use **Azure CLI** for capturing logs to files
- Use **Application Insights** for historical analysis and advanced queries

## Best Practices

### 1. Keep Log Stream Open During Testing

When testing fixes:
1. Open log stream in one browser tab
2. Invoke functions from another tab or terminal
3. Watch logs in real-time to see results immediately

### 2. Capture Logs Before and After Fixes

```bash
# Before fix
# 1. Open log stream
# 2. Invoke function
# 3. Copy logs to: logs/before_fix_2024-01-28.txt

# After fix
# 1. Deploy changes
# 2. Open log stream
# 3. Invoke function
# 4. Copy logs to: logs/after_fix_2024-01-28.txt

# Compare
diff logs/before_fix_2024-01-28.txt logs/after_fix_2024-01-28.txt
```

### 3. Use Multiple Monitoring Methods

For comprehensive debugging:
1. **Portal log stream**: Real-time monitoring
2. **Azure CLI**: Capture to files for analysis
3. **Application Insights**: Historical trends and patterns
4. **Diagnostic tool**: Automatic classification and suggestions

### 4. Document Error Patterns

When you see errors:
1. Copy the full error message and stack trace
2. Note the timestamp
3. Note what triggered the error (which function, what parameters)
4. Save to diagnostic session for tracking

### 5. Monitor During Deployment

When deploying fixes:
1. Open log stream before deployment
2. Watch for deployment messages
3. Test function immediately after deployment
4. Verify logs show updated code behavior

## Integration with Diagnostic System

The Azure Portal log stream integrates with the diagnostic system:

### Capture and Classify

```bash
# 1. Capture logs from portal (copy-paste to file)
# 2. Classify errors
python diagnostic_tool.py classify-error logs/portal_logs.txt

# Output shows:
# - Error types identified
# - Suggested fixes
# - Missing packages or configurations
```

### Track in Diagnostic Session

```python
from diagnostics import DiagnosticSession, AzureLogAccess
from datetime import datetime

# Start session
session = DiagnosticSession(
    session_id="portal-debug-2024-01-28",
    start_time=datetime.utcnow()
)

# Add note about portal access
session.add_note("Accessed Azure Portal log stream")
session.add_note("Captured logs during CNBC scraper test")

# ... add errors, fixes, test results ...

# Export report
session.export_to_markdown("diagnostic_sessions/portal-debug-2024-01-28.md")
```

## Quick Reference

### Access URLs

- **Azure Portal Home**: https://portal.azure.com
- **Function App**: Search for "pei-dashboard"
- **Log Stream**: Function App → Monitoring → Log stream

### Common Log Patterns

**Import Error:**
```
[Error] ModuleNotFoundError: No module named 'requests'
```

**Configuration Error:**
```
[Error] ConfigurationError: Database connection string not found
```

**Network Error:**
```
[Error] NetworkError: Connection timeout after 30 seconds
```

**Database Error:**
```
[Error] pyodbc.OperationalError: Unable to connect to database
```

### Next Steps After Viewing Logs

1. **Classify errors**: Use diagnostic tool to identify error types
2. **Apply fixes**: Based on error classification
3. **Deploy**: Push fixes to Azure
4. **Verify**: Check log stream again to confirm fixes work
5. **Document**: Record results in diagnostic session

## Summary

The Azure Portal log stream provides:

- ✅ **Real-time monitoring** of function execution
- ✅ **Visual interface** with color-coded log levels
- ✅ **No setup required** - works immediately in browser
- ✅ **Easy access** - just a few clicks from portal home
- ✅ **Integration** with diagnostic system for analysis

**When to use**:
- Quick health checks
- Real-time monitoring during testing
- Visual confirmation of function execution
- Immediate feedback when testing fixes

**Limitations**:
- No historical logs (only real-time)
- Manual copy-paste to save logs
- Limited filtering capabilities
- Requires browser and internet connection

For comprehensive debugging, combine portal log stream with Azure CLI and Application Insights queries.

---

**Task 2.1 Complete**: Azure Portal log stream access documented.
**Validates**: Requirement 1.1 - Access Azure Portal log stream for real-time function execution logs.
