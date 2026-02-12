# Azure Functions News Scraping System - Deployment Guide

## 🚨 URGENT: Current Setup Status

### ✅ Completed
- Database schema and handlers implemented
- Azure Functions code structure ready  
- Configuration files prepared (.env.azure)
- Test scripts created

### ❌ Required Actions (Priority Order)

#### 1. 🔥 CRITICAL: Add IP to SQL Server Firewall
**Your IP `180.252.80.182` is blocked by Azure SQL Server firewall**

**Option A: Azure Portal (Recommended)**
1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to SQL Server: `pei-dashboard`
3. Go to **Security** > **Networking**
4. Click **Add client IP** or manually add:
   - Rule name: `LocalDevelopment`
   - Start IP: `180.252.80.182`
   - End IP: `180.252.80.182`
5. Click **Save**

#### 2. 📥 Install Missing Tools
- **Azure CLI**: Download from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-windows
- **Azure Functions Core Tools**: `npm install -g azure-functions-core-tools@4 --unsafe-perm true`

#### 3. 🧪 Test & Deploy
After fixing firewall:
```bash
# Test database connection
python scripts/local-test.py

# Initialize database schema  
python scripts/initialize-database.py

# Deploy to Azure (after installing tools)
.\scripts\deploy-functions.ps1 -FunctionAppName "pei-dashboard"
```

## Quick Commands Created

The following batch files have been created for easy execution:
- `test-connection.bat` - Test database connection
- `init-database.bat` - Initialize database schema
- `deploy-functions.bat` - Deploy to Azure Functions

---

## Original Deployment Guide

Panduan lengkap untuk deploy dan setup Azure resources untuk sistem news scraping.

## Prerequisites

### 1. Install Required Tools

```bash
# Azure CLI
# Download dari: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

# Azure Functions Core Tools
npm install -g azure-functions-core-tools@4 --unsafe-perm true

# Python dependencies
pip install -r requirements.txt

# SQL Server Command Line Tools (untuk Windows)
# Download dari: https://docs.microsoft.com/en-us/sql/tools/sqlcmd-utility
```

### 2. Login ke Azure

```bash
az login
az account set --subscription "Your-Subscription-ID"
```

## Deployment Steps

### Step 1: Deploy Infrastructure

1. **Edit parameter file** (opsional):
   ```bash
   # Edit infrastructure/parameters.dev.json
   # Ganti password SQL Server dengan password yang kuat
   ```

2. **Run deployment script**:
   ```powershell
   # Dari directory azure_functions
   .\scripts\deploy-infrastructure.ps1 -ResourceGroupName "rg-newscraper-dev" -SqlAdminPassword "YourSecurePassword123!"
   ```

   Script ini akan:
   - Membuat Resource Group
   - Deploy semua Azure resources (SQL Server, Function App, Key Vault, Storage)
   - Membuat file `.env.azure` dengan konfigurasi

### Step 2: Initialize Database

1. **Set environment variable**:
   ```bash
   # Copy connection string dari .env.azure
   export SQL_SERVER_CONNECTION_STRING="Driver={ODBC Driver 17 for SQL Server};Server=tcp:..."
   ```

2. **Run database initialization**:
   ```bash
   python scripts/initialize-database.py
   ```

### Step 3: Test Database Connection

```bash
python tests/test_database_connection.py
```

### Step 4: Deploy Function App Code

```powershell
# Ganti dengan nama Function App Anda
.\scripts\deploy-functions.ps1 -FunctionAppName "newscraper-dev-func-xxxxx"
```

### Step 5: Configure Copilot API (Opsional)

1. **Add Copilot API key ke Key Vault**:
   ```bash
   az keyvault secret set --vault-name "newscraper-dev-kv-xxxxx" --name "copilot-api-key" --value "your-copilot-api-key"
   ```

2. **Update Function App settings**:
   ```bash
   az functionapp config appsettings set --name "newscraper-dev-func-xxxxx" --resource-group "rg-newscraper-dev" --settings "AI_API_KEY=@Microsoft.KeyVault(VaultName=newscraper-dev-kv-xxxxx;SecretName=copilot-api-key)"
   ```

## Verification

### 1. Test Function App

```bash
# Test endpoint
curl https://newscraper-dev-func-xxxxx.azurewebsites.net/api/test_function
```

### 2. Check Application Insights

1. Go to Azure Portal
2. Navigate to your Application Insights resource
3. Check "Live Metrics" and "Logs"

### 3. Verify Database

```bash
# Run comprehensive database tests
python tests/test_database_connection.py
```

## Configuration

### Environment Variables

File `.env.azure` berisi semua konfigurasi yang diperlukan:

```bash
# SQL Server
SQL_SERVER_CONNECTION_STRING="Driver={ODBC Driver 17 for SQL Server};..."

# Azure Services
AZURE_KEY_VAULT_URL="https://newscraper-dev-kv-xxxxx.vault.azure.net/"
BLOB_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."

# Function App
FUNCTIONS_WORKER_RUNTIME="python"
FUNCTIONS_EXTENSION_VERSION="~4"
ENVIRONMENT="dev"
```

### Key Vault Secrets

Secrets yang perlu dikonfigurasi di Key Vault:

- `sql-connection-string`: Connection string untuk SQL Server
- `storage-connection-string`: Connection string untuk Blob Storage
- `copilot-api-key`: API key untuk Microsoft Copilot (opsional)

## Monitoring

### Application Insights

- **Live Metrics**: Real-time monitoring
- **Logs**: Query logs dengan KQL
- **Failures**: Track errors dan exceptions
- **Performance**: Monitor response times

### SQL Server

- **Query Performance Insight**: Monitor database performance
- **Alerts**: Set up alerts untuk high CPU, storage, dll
- **Backup**: Automated backup sudah dikonfigurasi

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check firewall rules
   az sql server firewall-rule list --server "newscraper-dev-sql-xxxxx" --resource-group "rg-newscraper-dev"
   
   # Add your IP if needed
   az sql server firewall-rule create --server "newscraper-dev-sql-xxxxx" --resource-group "rg-newscraper-dev" --name "MyIP" --start-ip-address "YOUR_IP" --end-ip-address "YOUR_IP"
   ```

2. **Function App Deployment Failed**
   ```bash
   # Check deployment logs
   func azure functionapp logstream "newscraper-dev-func-xxxxx"
   
   # Redeploy with verbose logging
   func azure functionapp publish "newscraper-dev-func-xxxxx" --build remote --verbose
   ```

3. **Key Vault Access Denied**
   ```bash
   # Check access policies
   az keyvault show --name "newscraper-dev-kv-xxxxx" --query "properties.accessPolicies"
   
   # Add access policy for Function App
   az keyvault set-policy --name "newscraper-dev-kv-xxxxx" --object-id "FUNCTION_APP_PRINCIPAL_ID" --secret-permissions get list
   ```

### Logs and Diagnostics

```bash
# Function App logs
func azure functionapp logstream "newscraper-dev-func-xxxxx"

# Application Insights logs (KQL)
# Go to Azure Portal > Application Insights > Logs
traces
| where timestamp > ago(1h)
| order by timestamp desc

# SQL Server logs
# Go to Azure Portal > SQL Database > Query Performance Insight
```

## Security Best Practices

1. **Use Managed Identity** untuk akses ke Azure services
2. **Store secrets** di Key Vault, bukan di environment variables
3. **Enable firewall rules** untuk SQL Server
4. **Use HTTPS only** untuk Function App
5. **Regular security updates** untuk dependencies

## Cost Optimization

1. **Function App**: Gunakan Consumption plan untuk development
2. **SQL Server**: Gunakan Basic tier untuk development
3. **Storage**: Gunakan Standard LRS untuk development
4. **Monitor costs** dengan Azure Cost Management

## Next Steps

Setelah deployment berhasil:

1. **Implement scrapers**: Buat Azure Functions untuk scraping news
2. **Setup scheduling**: Konfigurasi timer triggers
3. **Add monitoring**: Setup alerts dan dashboards
4. **Performance tuning**: Optimize database queries dan function performance
5. **Production deployment**: Deploy ke production environment

## Support

Jika ada masalah:

1. Check logs di Application Insights
2. Run diagnostic tests: `python tests/test_database_connection.py`
3. Verify Azure resources di Azure Portal
4. Check firewall rules dan network connectivity