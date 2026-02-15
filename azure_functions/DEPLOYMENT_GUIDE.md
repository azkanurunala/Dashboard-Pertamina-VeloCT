# 🚀 Azure Functions Deployment Guide - PEI Dashboard

## 📋 Deployment Information

**Function App Name**: `pei-dashboard`  
**Resource Group**: `PeiDashboard`  
**Location**: Canada Central  
**Runtime**: Python 3.11  
**Deployment Date**: 16 Februari 2026

---

## ✅ Prerequisites Checklist

- [x] Azure Functions Core Tools v4.6.0 installed
- [x] Azure CLI installed and logged in
- [x] Python 3.11 virtual environment configured
- [x] Function App created in Azure Portal
- [x] All required files present (host.json, requirements.txt)

---

## 🔧 Deployment Methods

### Method 1: Simple Deployment (Direct to Production)

```bash
# Deploy with remote build (recommended)
func azure functionapp publish pei-dashboard --build remote

# Deploy with local build
func azure functionapp publish pei-dashboard --no-build
```

### Method 2: Using PowerShell Script

```powershell
# Simple deployment
.\scripts\deploy-functions.ps1 -FunctionAppName "pei-dashboard"

# With local build
.\scripts\deploy-functions.ps1 -FunctionAppName "pei-dashboard" -BuildLocally
```

### Method 3: Blue-Green Deployment (with Staging Slot)

```powershell
# Deploy to staging, validate, then promote
.\scripts\deploy-with-slots.ps1 -FunctionAppName "pei-dashboard" -DeploymentSlot "staging"

# Auto-promote after validation
.\scripts\deploy-with-slots.ps1 -FunctionAppName "pei-dashboard" -AutoPromote
```

---

## 📦 What Gets Deployed

### Core Files
- `host.json` - Function app configuration
- `requirements.txt` - Python dependencies
- `local.settings.json` - Environment variables (not deployed, for reference only)

### Function Directories
- **28 Scraper Functions**: All `*_scraper_function` directories
- **Processing Functions**: `processing/`, `deduplication_function/`
- **Orchestration**: `orchestration/`, timer functions
- **Shared Code**: `shared/` directory with utilities
- **Analysis**: `analysis/` directory
- **Backup**: `backup/` directory

### Dependencies (from requirements.txt)
- Azure Functions & SDK packages
- Database: pyodbc, sqlalchemy
- Web scraping: selenium, beautifulsoup4, requests
- Data processing: pandas, numpy
- PDF/OCR: pdfplumber, easyocr
- AI: openai, httpx

---

## 🌐 Deployment URLs

### Production
- **Base URL**: `https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net`
- **Test Endpoint**: `https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/test_function`
- **Health Check**: `https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/health_check_function`

### Staging (if configured)
- **Base URL**: `https://pei-dashboard-staging.azurewebsites.net`

---

## 🔍 Post-Deployment Verification

### 1. Check Deployment Status
```bash
# View deployment logs
func azure functionapp logstream pei-dashboard

# List all functions
func azure functionapp list-functions pei-dashboard

# Check function app status
az functionapp show --name pei-dashboard --resource-group PeiDashboard
```

### 2. Test Endpoints
```bash
# Test health check
curl https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/health_check_function

# Test with authentication
curl https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/test_function?code=<function-key>
```

### 3. Monitor Application Insights
- Open Azure Portal → Application Insights
- Check for errors, performance metrics
- Review function execution logs

---

## ⚙️ Configuration Management

### Environment Variables (Application Settings)

Key settings that need to be configured in Azure Portal:

```bash
# Database
SQL_SERVER_CONNECTION_STRING=<your-connection-string>

# AI/ML
AI_API_KEY=<your-api-key>
COPILOT_API_ENDPOINT=<endpoint-url>
AI_TYPE=GEMINI

# Storage
BLOB_STORAGE_CONNECTION_STRING=<storage-connection-string>
AzureWebJobsStorage=<storage-connection-string>

# Monitoring
APPLICATIONINSIGHTS_CONNECTION_STRING=<appinsights-connection-string>

# Schedules
SCHEDULE_DAILY_MORNING=0 10 6 * * *
SCHEDULE_DAILY_AFTERNOON=0 15 6 * * *
SCHEDULE_WEEKLY=0 20 6 * * *
SCHEDULE_MONTHLY=0 25 6 * * *
```

### Update Application Settings
```bash
# Set a single setting
az functionapp config appsettings set --name pei-dashboard --resource-group PeiDashboard --settings "ENVIRONMENT=production"

# Set multiple settings from file
az functionapp config appsettings set --name pei-dashboard --resource-group PeiDashboard --settings @appsettings.json
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. ModuleNotFoundError
**Problem**: Missing Python packages  
**Solution**: 
```bash
# Redeploy with remote build
func azure functionapp publish pei-dashboard --build remote
```

#### 2. Timeout During Upload
**Problem**: Large file size (443 MB)  
**Solution**:
- Use remote build instead of local
- Check internet connection
- Consider excluding unnecessary files in `.funcignore`

#### 3. Function Not Responding
**Problem**: Function returns 500 or timeout  
**Solution**:
```bash
# Check logs
func azure functionapp logstream pei-dashboard

# Restart function app
az functionapp restart --name pei-dashboard --resource-group PeiDashboard
```

#### 4. Database Connection Issues
**Problem**: Cannot connect to SQL Server  
**Solution**:
- Verify connection string in Application Settings
- Check firewall rules in Azure SQL
- Ensure ODBC Driver 17 is available in Azure

---

## 📊 Monitoring & Logs

### View Live Logs
```bash
# Stream logs in real-time
func azure functionapp logstream pei-dashboard

# View logs in Azure Portal
# Portal → Function App → Monitoring → Log Stream
```

### Application Insights Queries

```kusto
// Failed requests in last 24 hours
requests
| where timestamp > ago(24h)
| where success == false
| summarize count() by name, resultCode

// Function execution duration
requests
| where timestamp > ago(1h)
| summarize avg(duration), max(duration) by name
| order by avg_duration desc

// Exception tracking
exceptions
| where timestamp > ago(24h)
| summarize count() by type, outerMessage
```

---

## 🔄 Rollback Procedure

### If Deployment Fails

```bash
# Option 1: Redeploy previous version
# (if you have the previous code)
git checkout <previous-commit>
func azure functionapp publish pei-dashboard --build remote

# Option 2: Use Azure Portal
# Portal → Function App → Deployment Center → Redeploy previous deployment

# Option 3: Use deployment slots (if configured)
az functionapp deployment slot swap --name pei-dashboard --resource-group PeiDashboard --slot staging --target-slot production
```

---

## 📝 Deployment Checklist

Before deploying to production:

- [ ] All tests passing locally
- [ ] Database migration completed
- [ ] Environment variables configured in Azure
- [ ] Application Insights enabled
- [ ] Backup of current production version
- [ ] Stakeholders notified of deployment
- [ ] Monitoring dashboard ready
- [ ] Rollback plan prepared

After deployment:

- [ ] Verify all functions are running
- [ ] Test critical endpoints
- [ ] Check Application Insights for errors
- [ ] Monitor for 30 minutes
- [ ] Verify scheduled functions trigger correctly
- [ ] Test database connectivity
- [ ] Confirm scraper functions work

---

## 🔗 Useful Commands

```bash
# Get function keys
az functionapp keys list --name pei-dashboard --resource-group PeiDashboard

# List all functions
az functionapp function list --name pei-dashboard --resource-group PeiDashboard

# Restart function app
az functionapp restart --name pei-dashboard --resource-group PeiDashboard

# Stop function app
az functionapp stop --name pei-dashboard --resource-group PeiDashboard

# Start function app
az functionapp start --name pei-dashboard --resource-group PeiDashboard

# View configuration
az functionapp config show --name pei-dashboard --resource-group PeiDashboard

# Scale function app
az functionapp plan update --name ASP-PeiDashboard-a455 --resource-group PeiDashboard --sku P1V2
```

---

## 📞 Support & Resources

### Documentation
- [Azure Functions Python Developer Guide](https://docs.microsoft.com/azure/azure-functions/functions-reference-python)
- [Azure Functions Core Tools](https://docs.microsoft.com/azure/azure-functions/functions-run-local)
- [Deployment Best Practices](https://docs.microsoft.com/azure/azure-functions/functions-best-practices)

### Internal Documentation
- [Database Schema](docs/database/FINAL_VERIFICATION_REPORT.md)
- [Migration Guide](UNIFIED_MIGRATION.sql)
- [Project README](README.md)

---

**Last Updated**: 16 Februari 2026  
**Deployment Status**: ✅ COMPLETED SUCCESSFULLY  
**Deployment Time**: 15 Feb 2026, 21:15 UTC  
**Functions Deployed**: 35 (28 scrapers + 7 utilities)  
**Health Check**: ✅ All systems operational  
**Python Version**: 3.11.13  
**All Imports**: ✅ 19/19 modules loaded successfully
