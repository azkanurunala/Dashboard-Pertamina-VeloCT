# 🚀 Quick Start Guide - Migrasi ke Azure

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

## Untuk Yang Ingin Langsung Mulai!

Panduan singkat untuk memulai migrasi dalam 30 menit pertama.

---

## ⚡ 30 Menit Pertama

### 1. Install Tools (10 menit)
```powershell
# Install Azure CLI
winget install Microsoft.AzureCLI

# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4 --unsafe-perm true

# Verify
az --version
func --version
python --version
```

### 2. Login & Setup (5 menit)
```powershell
# Login
az login

# Pilih subscription
az account list --output table
az account set --subscription "NAMA_SUBSCRIPTION_ANDA"
```

### 3. Configure SQL Database Firewall (5 menit)
```powershell
# Allow Azure services
az sql server firewall-rule create `
  --resource-group PeiDashboard `
  --server pei-dashboard `
  --name AllowAzureServices `
  --start-ip-address 0.0.0.0 `
  --end-ip-address 0.0.0.0

# Allow your IP
az sql server firewall-rule create `
  --resource-group PeiDashboard `
  --server pei-dashboard `
  --name AllowMyIP `
  --start-ip-address [IP_ANDA] `
  --end-ip-address [IP_ANDA]
```

### 4. Get Connection String (5 menit)
```powershell
# Get connection string
az sql db show-connection-string `
  --client ado.net `
  --server pei-dashboard `
  --name pei-dashboard

# Simpan output ini! Akan digunakan nanti.
```

**✅ Checkpoint:** Database sudah ready!

---

## 🎯 Hari Pertama (2-3 jam)

### Setup Storage Account

```powershell
# 1. Buat Storage Account
az storage account create `
  --name stpeidashboard `
  --resource-group PeiDashboard `
  --location southeastasia `
  --sku Standard_LRS

# 2. Get Storage Connection String
az storage account show-connection-string `
  --name stpeidashboard `
  --resource-group PeiDashboard `
  --output tsv
```

### Simpan Secrets ke Key Vault

```powershell
# Simpan connection strings ke Key Vault
az keyvault secret set `
  --vault-name PeiDashboard `
  --name DatabaseConnectionString `
  --value "[CONNECTION_STRING_DATABASE]"

az keyvault secret set `
  --vault-name PeiDashboard `
  --name StorageConnectionString `
  --value "[CONNECTION_STRING_STORAGE]"
```

### Setup Database Schema

```powershell
# Jalankan schema SQL
az sql db query `
  --server pei-dashboard `
  --database pei-dashboard `
  --admin-user sqladmin `
  --admin-password "[PASSWORD_ANDA]" `
  --file azure_functions/shared/database_schema.sql
```

**✅ Checkpoint:** Database schema sudah siap!

---

## 📦 Hari Kedua (3-4 jam)

### Setup Azure OpenAI (untuk Copilot)

```powershell
# Buat Azure OpenAI resource
az cognitiveservices account create `
  --name openai-pei-dashboard `
  --resource-group PeiDashboard `
  --kind OpenAI `
  --sku S0 `
  --location eastus `
  --yes

# Get API key
az cognitiveservices account keys list `
  --name openai-pei-dashboard `
  --resource-group PeiDashboard

# Get endpoint
az cognitiveservices account show `
  --name openai-pei-dashboard `
  --resource-group PeiDashboard `
  --query properties.endpoint

# Deploy GPT-4 model
az cognitiveservices account deployment create `
  --name openai-pei-dashboard `
  --resource-group PeiDashboard `
  --deployment-name gpt-4 `
  --model-name gpt-4 `
  --model-version "0613" `
  --model-format OpenAI `
  --sku-capacity 10 `
  --sku-name "Standard"

# Simpan API key dan endpoint ke Key Vault
az keyvault secret set `
  --vault-name PeiDashboard `
  --name CopilotApiKey `
  --value "[API_KEY_DARI_OUTPUT_DI_ATAS]"

az keyvault secret set `
  --vault-name PeiDashboard `
  --name CopilotEndpoint `
  --value "[ENDPOINT_DARI_OUTPUT_DI_ATAS]"
```

### Migrasi Data Excel

```powershell
cd azure_functions

# Set environment variable
$env:DATABASE_CONNECTION_STRING = "[CONNECTION_STRING_DATABASE]"

# Install dependencies
pip install -r requirements.txt

# Jalankan migration
python shared/excel_migration.py

# Verifikasi
az sql db query `
  --server pei-dashboard `
  --database pei-dashboard `
  --admin-user sqladmin `
  --admin-password "[PASSWORD_ANDA]" `
  --query "SELECT COUNT(*) as total FROM news_articles"
```

**✅ Checkpoint:** Data sudah di Azure SQL Database!

---

## 🚀 Hari Ketiga (2-3 jam)

### Function App (Sudah Ada ✅)
Function App sudah ada:
- **Name:** `pei-dashboard`
- **URL:** `pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net`
- **Location:** Canada Central

### Configure Azure Functions

```powershell
# 1. Enable Managed Identity
az functionapp identity assign `
  --name pei-dashboard `
  --resource-group PeiDashboard

# 2. Grant Key Vault access
$PRINCIPAL_ID = az functionapp identity show `
  --name pei-dashboard `
  --resource-group PeiDashboard `
  --query principalId -o tsv

az keyvault set-policy `
  --name PeiDashboard `
  --object-id $PRINCIPAL_ID `
  --secret-permissions get list

# 3. Configure app settings
az functionapp config appsettings set `
  --name pei-dashboard `
  --resource-group PeiDashboard `
  --settings `
    "KEY_VAULT_URL=https://PeiDashboard.vault.azure.net/" `
    "DatabaseConnectionString=@Microsoft.KeyVault(SecretUri=https://PeiDashboard.vault.azure.net/secrets/DatabaseConnectionString/)" `
    "StorageConnectionString=@Microsoft.KeyVault(SecretUri=https://PeiDashboard.vault.azure.net/secrets/StorageConnectionString/)" `
    "CopilotApiKey=@Microsoft.KeyVault(SecretUri=https://PeiDashboard.vault.azure.net/secrets/CopilotApiKey/)" `
    "CopilotEndpoint=@Microsoft.KeyVault(SecretUri=https://PeiDashboard.vault.azure.net/secrets/CopilotEndpoint/)"

# 4. Deploy functions
cd azure_functions
func azure functionapp publish pei-dashboard --python
```

**⏳ Tunggu 5-10 menit untuk deployment selesai...**

**✅ Checkpoint:** Functions sudah ter-deploy!

---

## 🧪 Testing (1 jam)

### Test Scraper Function

```powershell
# Test CNBC scraper
$FUNCTION_URL = "https://func-pei-dashboard.azurewebsites.net/api/cnbc_scraper_function"

curl -X POST $FUNCTION_URL `
  -H "Content-Type: application/json" `
  -d '{"keywords": ["oil"], "start_date": "2024-01-01", "end_date": "2024-01-31"}'
```

### Verify Data in Database

```powershell
az sql db query `
  --server pei-dashboard `
  --database pei-dashboard `
  --admin-user sqladmin `
  --admin-password "[PASSWORD_ANDA]" `
  --query "SELECT TOP 10 title, source, published_date FROM news_articles ORDER BY scraped_date DESC"
```

**✅ Checkpoint:** System working end-to-end!

---

## 📊 Monitoring Setup (30 menit)

### Enable Application Insights

```powershell
# Buat Application Insights
az monitor app-insights component create `
  --app appinsights-pei-dashboard `
  --location southeastasia `
  --resource-group PeiDashboard

# Get instrumentation key
$INSTRUMENTATION_KEY = az monitor app-insights component show `
  --app appinsights-pei-dashboard `
  --resource-group PeiDashboard `
  --query instrumentationKey -o tsv

# Configure Function App
az functionapp config appsettings set `
  --name func-pei-dashboard `
  --resource-group PeiDashboard `
  --settings "APPINSIGHTS_INSTRUMENTATIONKEY=$INSTRUMENTATION_KEY"
```

### View Logs

1. Buka Azure Portal: https://portal.azure.com
2. Go to Function App > func-pei-dashboard
3. Click "Monitor" > "Logs"
4. View real-time logs

**✅ Checkpoint:** Monitoring active!

---

## 🎉 You're Live!

### What's Next?

1. **Monitor First 24 Hours**
   - Check logs setiap 2 jam
   - Verify data collection
   - Monitor costs

2. **Setup Alerts**
   - Function failures
   - High latency
   - Cost alerts

3. **Documentation**
   - Update team wiki
   - Create runbooks
   - Train team members

4. **Optimization**
   - Review performance
   - Optimize costs
   - Fine-tune settings

---

## 📚 Full Documentation

Untuk detail lengkap, lihat:
- **MIGRATION_GUIDE.md** - Panduan lengkap step-by-step
- **MIGRATION_CHECKLIST.md** - Checklist tracking
- **IMPLEMENTATION_COMPLETE.md** - Dokumentasi implementasi

---

## 🆘 Need Help?

### Common Issues

**Issue: Function deployment failed**
```powershell
# Check logs
az functionapp log tail `
  --name func-pei-dashboard `
  --resource-group PeiDashboard
```

**Issue: Database connection failed**
```powershell
# Check firewall rules
az sql server firewall-rule list `
  --server pei-dashboard `
  --resource-group PeiDashboard
```

**Issue: Key Vault access denied**
```powershell
# Re-grant access
az keyvault set-policy `
  --name PeiDashboard `
  --object-id $PRINCIPAL_ID `
  --secret-permissions get list
```

---

## 💡 Pro Tips

1. **Save Passwords**: Simpan semua passwords di password manager
2. **Document Everything**: Catat semua resource names
3. **Test Incrementally**: Test setiap step sebelum lanjut
4. **Monitor Costs**: Setup cost alerts dari awal

---

## 📞 Support

- Azure Documentation: https://docs.microsoft.com/azure/
- Azure Support: https://portal.azure.com/#blade/Microsoft_Azure_Support/HelpAndSupportBlade
- Team Lead: [ISI_NAMA_DAN_KONTAK]

---

**🚀 Happy Migrating!**

*Quick Start Guide ini dibuat: 27 Januari 2026*
*Versi: 1.0*
