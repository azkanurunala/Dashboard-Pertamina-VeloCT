# 📘 Panduan Migrasi ke Azure - Step by Step

## 📌 Resource Yang Sudah Ada

| Resource | Nama |
|----------|------|
| Resource Group | `PeiDashboard` |
| Key Vault | `PeiDashboard` |
| SQL Server | `pei-dashboard` |
| SQL Database | `pei-dashboard` |
| Function App | `pei-dashboard` |
| Function URL | `pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net` |
| Location | Canada Central |

---

## Daftar Isi
1. [Persiapan Awal](#1-persiapan-awal)
2. [Setup Azure Accounts](#2-setup-azure-accounts)
3. [Setup Azure SQL Database](#3-setup-azure-sql-database)
4. [Setup Azure Storage Account](#4-setup-azure-storage-account)
5. [Setup Azure Key Vault](#5-setup-azure-key-vault)
6. [Setup Microsoft Copilot API](#6-setup-microsoft-copilot-api)
7. [Setup Azure Functions](#7-setup-azure-functions)
8. [Migrasi Data dari Excel](#8-migrasi-data-dari-excel)
9. [Deploy Functions](#9-deploy-functions)
10. [Testing & Validation](#10-testing--validation)
11. [Monitoring Setup](#11-monitoring-setup)
12. [Go Live](#12-go-live)

---

## 1. Persiapan Awal

### 1.1 Checklist Kebutuhan
- [ ] Azure Subscription
- [ ] Azure CLI installed di komputer
- [ ] Python 3.9+ installed
- [ ] Azure Functions Core Tools installed
- [ ] Git installed
- [ ] Visual Studio Code (recommended)
- [ ] Access ke data Excel yang ada

### 1.2 Install Azure CLI
```bash
# Windows (PowerShell as Administrator)
winget install Microsoft.AzureCLI

# Atau download dari: https://aka.ms/installazurecliwindows

# Verify installation
az --version
```

### 1.3 Install Azure Functions Core Tools
```bash
# Windows
npm install -g azure-functions-core-tools@4 --unsafe-perm true

# Verify installation
func --version
```

### 1.4 Login ke Azure
```bash
# Login ke Azure
az login

# Pilih subscription yang akan digunakan
az account list --output table
az account set --subscription "SUBSCRIPTION_ID"
```

### 1.5 Install Python Dependencies
```bash
cd azure_functions
pip install -r requirements.txt
```

---

## 2. Setup Azure Accounts

### 2.1 Resource Group (Sudah Ada ✅)
Resource Group sudah dibuat dengan nama: `PeiDashboard`

### 2.2 Catat Informasi Penting
Buat file `deployment-info.txt` dan catat:
```
Subscription ID: [ISI_DISINI]
Resource Group: PeiDashboard
Key Vault: PeiDashboard
SQL Server: pei-dashboard
SQL Database: pei-dashboard
Location: [ISI_LOCATION_ANDA]
```

---

## 3. Setup Azure SQL Database

### 3.1 SQL Server (Sudah Ada ✅)
SQL Server sudah ada dengan nama: `pei-dashboard`

### 3.2 Configure Firewall
```bash
# Allow Azure services
az sql server firewall-rule create \
  --resource-group PeiDashboard \
  --server pei-dashboard \
  --name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

# Allow your IP (untuk testing dari komputer lokal)
az sql server firewall-rule create \
  --resource-group PeiDashboard \
  --server pei-dashboard \
  --name AllowMyIP \
  --start-ip-address [IP_ANDA] \
  --end-ip-address [IP_ANDA]
```

Cek IP Anda di: https://whatismyipaddress.com/

### 3.3 Database (Sudah Ada ✅)
Database sudah ada dengan nama: `pei-dashboard`

### 3.4 Get Connection String
```bash
az sql db show-connection-string \
  --client ado.net \
  --server pei-dashboard \
  --name pei-dashboard
```

Simpan connection string ini, akan digunakan nanti.

### 3.5 Jalankan Database Schema
```bash
# Connect ke database menggunakan Azure Data Studio atau SQL Server Management Studio
# Jalankan file: azure_functions/shared/database_schema.sql
```

**Atau via Azure CLI:**
```bash
az sql db query \
  --server pei-dashboard \
  --database pei-dashboard \
  --admin-user sqladmin \
  --admin-password "[PASSWORD_ANDA]" \
  --file azure_functions/shared/database_schema.sql
```

---

## 4. Setup Azure Storage Account

### 4.1 Buat Storage Account
```bash
az storage account create \
  --name stpeidashboard \
  --resource-group PeiDashboard \
  --location southeastasia \
  --sku Standard_LRS \
  --kind StorageV2
```

**Note:** Nama storage account harus lowercase dan tanpa special characters.

### 4.2 Buat Containers
```bash
# Get storage account key
STORAGE_KEY=$(az storage account keys list \
  --resource-group PeiDashboard \
  --account-name stpeidashboard \
  --query '[0].value' -o tsv)

# Buat containers
az storage container create \
  --name temp-files \
  --account-name stpeidashboard \
  --account-key $STORAGE_KEY

az storage container create \
  --name processing \
  --account-name stpeidashboard \
  --account-key $STORAGE_KEY

az storage container create \
  --name backups \
  --account-name stpeidashboard \
  --account-key $STORAGE_KEY

az storage container create \
  --name archive \
  --account-name stpeidashboard \
  --account-key $STORAGE_KEY
```

### 4.3 Get Connection String
```bash
az storage account show-connection-string \
  --name stpeidashboard \
  --resource-group PeiDashboard \
  --output tsv
```

Simpan connection string ini.

---

## 5. Setup Azure Key Vault

### 5.1 Key Vault (Sudah Ada ✅)
Key Vault sudah ada dengan nama: `PeiDashboard`

### 5.2 Simpan Secrets
```bash
# Database connection string
az keyvault secret set \
  --vault-name PeiDashboard \
  --name DatabaseConnectionString \
  --value "[CONNECTION_STRING_DATABASE]"

# Storage connection string
az keyvault secret set \
  --vault-name PeiDashboard \
  --name StorageConnectionString \
  --value "[CONNECTION_STRING_STORAGE]"

# Copilot API Key (akan diisi nanti)
az keyvault secret set \
  --vault-name PeiDashboard \
  --name CopilotApiKey \
  --value "[COPILOT_API_KEY]"

# Copilot Endpoint (akan diisi nanti)
az keyvault secret set \
  --vault-name PeiDashboard \
  --name CopilotEndpoint \
  --value "[COPILOT_ENDPOINT]"
```

---

## 6. Setup Microsoft Copilot API

### 6.1 Daftar Microsoft Copilot
1. Buka: https://www.microsoft.com/en-us/microsoft-365/copilot
2. Atau gunakan Azure OpenAI Service sebagai alternatif

### 6.2 Untuk Azure OpenAI (Alternatif)
```bash
# Buat Azure OpenAI resource
az cognitiveservices account create \
  --name openai-pei-dashboard \
  --resource-group PeiDashboard \
  --kind OpenAI \
  --sku S0 \
  --location eastus \
  --yes

# Get API key
az cognitiveservices account keys list \
  --name openai-pei-dashboard \
  --resource-group PeiDashboard

# Get endpoint
az cognitiveservices account show \
  --name openai-pei-dashboard \
  --resource-group PeiDashboard \
  --query properties.endpoint
```

### 6.3 Deploy Model (untuk Azure OpenAI)
```bash
# Deploy GPT-4 model
az cognitiveservices account deployment create \
  --name openai-pei-dashboard \
  --resource-group PeiDashboard \
  --deployment-name gpt-4 \
  --model-name gpt-4 \
  --model-version "0613" \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name "Standard"
```

### 6.4 Update Key Vault dengan Copilot Info
```bash
# Update secrets dengan info yang didapat
az keyvault secret set \
  --vault-name PeiDashboard \
  --name CopilotApiKey \
  --value "[API_KEY_DARI_STEP_6.2]"

az keyvault secret set \
  --vault-name PeiDashboard \
  --name CopilotEndpoint \
  --value "[ENDPOINT_DARI_STEP_6.2]"
```

---

## 7. Setup Azure Functions

### 7.1 Function App (Sudah Ada ✅)
Function App sudah ada dengan info:
- **Name:** `pei-dashboard`
- **URL:** `pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net`
- **Location:** Canada Central
- **OS:** Linux
- **Runtime:** Python (Functions v4)

### 7.2 Enable Managed Identity
```bash
az functionapp identity assign \
  --name pei-dashboard \
  --resource-group PeiDashboard
```

Catat `principalId` yang muncul.

### 7.3 Grant Key Vault Access
```bash
# Get principal ID
PRINCIPAL_ID=$(az functionapp identity show \
  --name pei-dashboard \
  --resource-group PeiDashboard \
  --query principalId -o tsv)

# Grant access
az keyvault set-policy \
  --name PeiDashboard \
  --object-id $PRINCIPAL_ID \
  --secret-permissions get list
```

### 7.4 Configure Application Settings
```bash
# Key Vault reference
az functionapp config appsettings set \
  --name pei-dashboard \
  --resource-group PeiDashboard \
  --settings \
    "KEY_VAULT_URL=https://PeiDashboard.vault.azure.net/" \
    "DatabaseConnectionString=@Microsoft.KeyVault(SecretUri=https://PeiDashboard.vault.azure.net/secrets/DatabaseConnectionString/)" \
    "StorageConnectionString=@Microsoft.KeyVault(SecretUri=https://PeiDashboard.vault.azure.net/secrets/StorageConnectionString/)" \
    "CopilotApiKey=@Microsoft.KeyVault(SecretUri=https://PeiDashboard.vault.azure.net/secrets/CopilotApiKey/)" \
    "CopilotEndpoint=@Microsoft.KeyVault(SecretUri=https://PeiDashboard.vault.azure.net/secrets/CopilotEndpoint/)"
```

### 7.5 Enable Application Insights
```bash
# Buat Application Insights
az monitor app-insights component create \
  --app appinsights-pei-dashboard \
  --location southeastasia \
  --resource-group PeiDashboard

# Get instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app appinsights-pei-dashboard \
  --resource-group PeiDashboard \
  --query instrumentationKey -o tsv)

# Configure Function App
az functionapp config appsettings set \
  --name func-pei-dashboard \
  --resource-group PeiDashboard \
  --settings "APPINSIGHTS_INSTRUMENTATIONKEY=$INSTRUMENTATION_KEY"
```

---

## 8. Migrasi Data dari Excel

### 8.1 Persiapkan Data Excel
1. Pastikan file Excel ada di folder `src/results/`
2. File yang perlu dimigrasi:
   - `(News)Scrapping.xlsx`
   - `(News)Sentiment.xlsx`
   - Data lainnya

### 8.2 Jalankan Migration Script
```bash
cd azure_functions

# Set environment variables untuk testing lokal
$env:DATABASE_CONNECTION_STRING="[CONNECTION_STRING_DATABASE]"

# Jalankan migration
python shared/excel_migration.py
```

### 8.3 Verifikasi Data
```bash
# Connect ke database dan check
az sql db query \
  --server pei-dashboard \
  --database pei-dashboard \
  --admin-user sqladmin \
  --admin-password "[PASSWORD_ANDA]" \
  --query "SELECT COUNT(*) as total_articles FROM news_articles"
```

---

## 9. Deploy Functions

### 9.1 Persiapkan Deployment
```bash
cd azure_functions

# Pastikan semua dependencies ada
pip install -r requirements.txt

# Test functions locally (optional)
func start
```

### 9.2 Deploy ke Azure
```bash
# Deploy semua functions
func azure functionapp publish func-pei-dashboard --python
```

**Note:** Proses ini akan memakan waktu 5-10 menit.

### 9.3 Verifikasi Deployment
```bash
# List functions yang ter-deploy
az functionapp function list \
  --name func-pei-dashboard \
  --resource-group PeiDashboard \
  --output table
```

### 9.4 Test Individual Function
```bash
# Get function URL
az functionapp function show \
  --name func-pei-dashboard \
  --resource-group PeiDashboard \
  --function-name cnbc_scraper_function \
  --query invokeUrlTemplate -o tsv

# Test dengan curl atau Postman
curl -X POST "[FUNCTION_URL]" \
  -H "Content-Type: application/json" \
  -d '{"keywords": ["energy"], "start_date": "2024-01-01", "end_date": "2024-01-31"}'
```

---

## 10. Testing & Validation

### 10.1 Test Scraper Functions
```bash
# Test CNBC scraper
curl -X POST "https://func-pei-dashboard.azurewebsites.net/api/cnbc_scraper_function" \
  -H "Content-Type: application/json" \
  -d '{"keywords": ["oil"], "start_date": "2024-01-01", "end_date": "2024-01-31"}'

# Test CNN scraper
curl -X POST "https://func-pei-dashboard.azurewebsites.net/api/cnn_scraper_function" \
  -H "Content-Type: application/json" \
  -d '{"keywords": ["energy"], "start_date": "2024-01-01", "end_date": "2024-01-31"}'
```

### 10.2 Test Database Connection
```bash
# Check articles in database
az sql db query \
  --server pei-dashboard \
  --database pei-dashboard \
  --admin-user sqladmin \
  --admin-password "[PASSWORD_ANDA]" \
  --query "SELECT TOP 10 title, source, published_date FROM news_articles ORDER BY scraped_date DESC"
```

### 10.3 Test Sentiment Analysis
```bash
# Trigger sentiment analysis
curl -X POST "https://func-pei-dashboard.azurewebsites.net/api/sentiment_analysis_function" \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2024-01-01", "end_date": "2024-01-31"}'
```

### 10.4 Test Backup Function
```bash
# Trigger manual backup
curl -X POST "https://func-pei-dashboard.azurewebsites.net/api/backup_function" \
  -H "Content-Type: application/json" \
  -d '{"database_name": "pei-dashboard"}'
```

### 10.5 Run Unit Tests
```bash
cd azure_functions
pytest tests/ -v
```

---

## 11. Monitoring Setup

### 11.1 Configure Alerts
```bash
# Alert untuk function failures
az monitor metrics alert create \
  --name "High Function Failure Rate" \
  --resource-group PeiDashboard \
  --scopes "/subscriptions/[SUBSCRIPTION_ID]/resourceGroups/PeiDashboard/providers/Microsoft.Web/sites/func-pei-dashboard" \
  --condition "count FunctionExecutionCount > 100" \
  --window-size 5m \
  --evaluation-frequency 1m
```

### 11.2 Setup Dashboard
1. Buka Azure Portal
2. Go to Application Insights > appinsights-pei-dashboard
3. Create custom dashboard dengan:
   - Function execution count
   - Success rate
   - Response time
   - Error rate
   - Database query performance

### 11.3 Configure Log Analytics
```bash
# Enable diagnostic logs
az monitor diagnostic-settings create \
  --name func-diagnostics \
  --resource "/subscriptions/[SUBSCRIPTION_ID]/resourceGroups/PeiDashboard/providers/Microsoft.Web/sites/func-pei-dashboard" \
  --logs '[{"category": "FunctionAppLogs", "enabled": true}]' \
  --workspace "/subscriptions/[SUBSCRIPTION_ID]/resourceGroups/PeiDashboard/providers/Microsoft.OperationalInsights/workspaces/[WORKSPACE_NAME]"
```

---

## 12. Go Live

### 12.1 Pre-Launch Checklist
- [ ] Semua functions ter-deploy dengan sukses
- [ ] Database schema sudah dijalankan
- [ ] Data Excel sudah dimigrasi
- [ ] Semua tests passing
- [ ] Monitoring dan alerts sudah setup
- [ ] Backup schedule sudah dikonfigurasi
- [ ] Documentation sudah lengkap
- [ ] Team sudah di-training

### 12.2 Enable Schedulers
```bash
# Schedulers akan otomatis berjalan sesuai CRON schedule
# Verify timer triggers
az functionapp function show \
  --name func-pei-dashboard \
  --resource-group PeiDashboard \
  --function-name daily_morning_timer
```

### 12.3 Monitor First 24 Hours
1. Check Application Insights setiap 2 jam
2. Monitor error logs
3. Verify data collection
4. Check database growth
5. Monitor costs

### 12.4 Parallel Running (Optional)
Untuk safety, jalankan sistem lama dan baru secara parallel selama 1-2 minggu:
- Compare results
- Validate data accuracy
- Monitor performance
- Identify issues

### 12.5 Cutover
Setelah yakin sistem baru berjalan dengan baik:
1. Stop sistem lama
2. Update documentation
3. Notify stakeholders
4. Archive old system

---

## 📊 Monitoring Checklist Harian

### Hari 1-7
- [ ] Check Application Insights dashboard
- [ ] Review error logs
- [ ] Verify data collection
- [ ] Check database size
- [ ] Monitor costs
- [ ] Test backup restore

### Hari 8-30
- [ ] Weekly review of metrics
- [ ] Performance optimization
- [ ] Cost optimization
- [ ] Update documentation
- [ ] Team feedback

---

## 🆘 Troubleshooting

### Function Tidak Berjalan
```bash
# Check function logs
az functionapp log tail \
  --name func-pei-dashboard \
  --resource-group PeiDashboard

# Check function status
az functionapp show \
  --name func-pei-dashboard \
  --resource-group PeiDashboard \
  --query state
```

### Database Connection Issues
```bash
# Test connection
az sql db show \
  --server pei-dashboard \
  --name pei-dashboard \
  --resource-group PeiDashboard

# Check firewall rules
az sql server firewall-rule list \
  --server pei-dashboard \
  --resource-group PeiDashboard
```

### Key Vault Access Issues
```bash
# Check access policies
az keyvault show \
  --name PeiDashboard \
  --query properties.accessPolicies
```

---

## 💰 Estimasi Biaya Bulanan

### Azure Functions (Consumption Plan)
- Executions: ~1 juta/bulan = $0.20
- Execution time: ~400,000 GB-s = $8.00
- **Total: ~$8.20/bulan**

### Azure SQL Database (S0)
- **~$15/bulan**

### Azure Storage (Standard LRS)
- Storage: 100 GB = $2.00
- Transactions: 1 juta = $0.05
- **Total: ~$2.05/bulan**

### Azure OpenAI (GPT-4)
- Tergantung usage
- **Estimasi: $50-200/bulan**

### **TOTAL ESTIMASI: $75-225/bulan**

---

## 📞 Support & Resources

### Documentation
- Azure Functions: https://docs.microsoft.com/azure/azure-functions/
- Azure SQL: https://docs.microsoft.com/azure/azure-sql/
- Azure Storage: https://docs.microsoft.com/azure/storage/
- Azure OpenAI: https://docs.microsoft.com/azure/cognitive-services/openai/

### Monitoring
- Application Insights: https://portal.azure.com
- Function App Logs: Azure Portal > Function App > Monitor

### Backup & Recovery
- Lihat: `azure_functions/backup/database_recovery.py`
- Recovery procedures documented

---

## ✅ Kesimpulan

Dengan mengikuti panduan ini step-by-step, sistem akan berhasil dimigrasi ke Azure dengan:
- ✅ Scalable architecture
- ✅ Automated backups
- ✅ Comprehensive monitoring
- ✅ Security best practices
- ✅ Cost-effective solution

**Selamat! Sistem Azure Functions PEI Dashboard Anda siap production! 🎉**

---

*Panduan ini dibuat: 27 Januari 2026*
*Versi: 1.0*
