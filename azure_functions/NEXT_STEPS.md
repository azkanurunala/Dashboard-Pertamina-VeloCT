# Next Steps - Azure Functions Migration

## Current Status

### ✅ What's Working
1. **Database connection** - Test function successfully connects to SQL Server
2. **Database schema** - All tables created correctly
3. **Basic function execution** - Test function returns 200 status
4. **Configuration** - Direct connection string configured and working

### ❌ What's Not Working
1. **CNBC Scraper Function** - Returns 500 error with no response body
2. **No articles scraped yet** - Only 1 test article in database

## Problem Analysis

The scraper function is returning HTTP 500 with an empty response. This suggests:
1. The function is crashing during execution
2. The error is not being caught and returned properly
3. Likely causes:
   - Missing dependencies in Azure
   - Import errors
   - Scraper code issues
   - The updated config.py code hasn't been deployed yet

## Solution: Redeploy Functions

The updated `config.py` with Key Vault SDK integration was created locally but **NOT deployed to Azure yet**. The functions running in Azure still have the old code.

### Option 1: Deploy via Azure CLI (Recommended)

```powershell
# Navigate to azure_functions directory
cd C:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions

# Deploy using func tools
func azure functionapp publish pei-dashboard --python
```

**Note**: This may fail due to remote build issues we saw earlier.

### Option 2: Deploy via Zip (Alternative)

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy_simple.ps1
```

### Option 3: Check Logs First

Before redeploying, check what's actually failing:

```powershell
# View logs in Azure Portal
# Go to: https://portal.azure.com
# Navigate to: pei-dashboard Function App -> Log stream
# Then trigger the scraper again and watch the logs
```

Or use Azure CLI:

```powershell
az webapp log tail --name pei-dashboard --resource-group PeiDashboard
```

## Immediate Actions

### 1. Check Azure Portal Logs

1. Open Azure Portal: https://portal.azure.com
2. Navigate to Resource Groups -> PeiDashboard -> pei-dashboard (Function App)
3. Click "Log stream" in the left menu
4. In another window, run: `python test_scraper_simple.py`
5. Watch the logs to see the actual error

### 2. Once You See the Error

Based on the error, we can:
- Fix missing dependencies
- Fix code issues
- Redeploy with corrections

### 3. Alternative: Test with a Simpler Scraper

Instead of CNBC (which might have complex scraping logic), let's test with a simpler function first.

Create a minimal test scraper:

```powershell
# Test the test_function (already working)
python quick_test.py

# If that works, the infrastructure is fine
# The issue is specifically with the scraper code
```

## Why This Happened

1. We updated `shared/config.py` locally to add Key Vault SDK support
2. We updated `test_function/__init__.py` to test Key Vault access
3. **But we didn't redeploy these changes to Azure**
4. The functions in Azure are still running the old code
5. The old code doesn't have the fallback to `SQL_SERVER_CONNECTION_STRING`

## Quick Fix

The fastest solution is to redeploy. But the deployment keeps failing due to remote build issues.

### Workaround: Manual File Update

If deployment continues to fail, we can:
1. Use Azure Portal to edit files directly (not recommended for production)
2. Use VS Code Azure Functions extension
3. Fix the remote build issue

## Recommended Next Step

**Run this command and share the output**:

```powershell
func azure functionapp publish pei-dashboard --python --build remote
```

This will attempt deployment with remote build. If it fails, we'll see the exact error and can fix it.

Alternatively, check the logs first to understand what's actually failing in the scraper.
