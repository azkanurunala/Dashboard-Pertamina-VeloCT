# Manual Deployment Guide - Azure Functions

Jika Azure CLI bermasalah, Anda bisa deploy manual melalui Azure Portal dan VS Code.

## 📋 Prerequisites

✅ **Sudah Selesai:**
- Database setup complete
- SQL Server Authentication working
- Azure Functions Core Tools installed
- Code ready for deployment

## 🚀 Manual Deployment Steps

### **Step 1: Prepare Deployment Package**

1. **Buat ZIP file** dari folder `azure_functions`:
   - Select semua files di folder `azure_functions`
   - Right-click → Send to → Compressed folder
   - Nama: `azure-functions-deployment.zip`

### **Step 2: Deploy via Azure Portal**

1. **Buka Azure Portal:** https://portal.azure.com
2. **Navigate ke Function App:** `pei-dashboard`
3. **Go to Deployment Center:**
   - Di menu kiri, pilih **Deployment** → **Deployment Center**
4. **Upload ZIP:**
   - Pilih **ZIP Deploy**
   - Upload file `azure-functions-deployment.zip`
   - Click **Deploy**

### **Step 3: Configure Application Settings**

1. **Di Function App `pei-dashboard`:**
   - Go to **Settings** → **Configuration**
   - Click **New application setting**

2. **Add Connection String:**
   ```
   Name: SQL_SERVER_CONNECTION_STRING
   Value: Driver={ODBC Driver 17 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Uid=CloudSAa33fbc7c;Pwd=uRahcie3&105272;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;
   ```

3. **Add Other Settings:**
   ```
   FUNCTIONS_WORKER_RUNTIME: python
   FUNCTIONS_EXTENSION_VERSION: ~4
   ENVIRONMENT: production
   ```

4. **Click Save**

### **Step 4: Test Deployment**

1. **Test Function:**
   - Go to **Functions** → **test_function**
   - Click **Get Function URL**
   - Open URL in browser

2. **Expected Response:**
   ```json
   {
     "status": "success",
     "message": "Azure Functions News Scraping System is running",
     "database_status": "Database configuration loaded successfully",
     "timestamp": "2026-01-23 00:45:00"
   }
   ```

## 🔧 Alternative: VS Code Extension

### **Install Azure Functions Extension:**
1. Open VS Code
2. Install extension: **Azure Functions**
3. Sign in to Azure
4. Right-click project → **Deploy to Function App**
5. Select `pei-dashboard`

## 📊 Verification Steps

### **1. Check Function App Status:**
- Azure Portal → Function App `pei-dashboard` → **Overview**
- Status should be **Running**

### **2. Check Application Insights:**
- Go to **Application Insights** linked to your Function App
- Check **Live Metrics** for real-time data

### **3. Test Database Connection:**
- Use the test function URL
- Should return success with database status

## 🎯 Next Steps After Deployment

1. **Configure Timer Triggers** for scheduled scraping
2. **Setup Application Insights** monitoring
3. **Configure Key Vault** for secrets management
4. **Test end-to-end functionality**

## 🆘 Troubleshooting

### **Common Issues:**

1. **Deployment Failed:**
   - Check Function App logs in Azure Portal
   - Verify ZIP file contains all necessary files

2. **Database Connection Failed:**
   - Verify connection string in Application Settings
   - Check SQL Server firewall rules

3. **Function Not Working:**
   - Check Application Insights for errors
   - Verify Python runtime version

### **Support Commands:**
```bash
# If Azure CLI works later:
az functionapp logs tail --name pei-dashboard --resource-group PeiDashboard

# Check function status
az functionapp show --name pei-dashboard --resource-group PeiDashboard --query "state"
```