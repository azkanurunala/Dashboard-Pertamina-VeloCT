# 🚀 Quick Start Guide - Migrasi ke Azure

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

# Buat resource groups
az group create --name rg-functions-newscraper --location southeastasia
az group create --name rg-database-newscraper --location southeastasia
```

### 3. Buat SQL Database (10 menit)
```powershell
# Ganti [NAMA_UNIK] dengan nama Anda (contoh: pertamina01)
$UNIQUE_NAME = "pertamina01"

# Buat SQL Server
az sql server create `
  --name "sql-newscraper-$UNIQUE_NAME" `
  --resource-group rg-database-newscraper `
  --location southeastasia `
  --admin-user sqladmin `
  --admin-password "P@ssw0rd123!Strong"

# Buat Database
az sql db create `
  --resource-group rg-database-newscraper `
  --server "sql-newscraper-$UNIQUE_NAME" `
  --name NewsScraperDB `
  --service-objective S0

# Allow Azure services
az sql server firewall-rule create `
  --resource-group rg-database-newscraper `
  --server "sql-newscraper-$UNIQUE_NAME" `
  --name AllowAzureServices `
  --start-ip-address 0.0.0.0 `
  --end-ip-address 0.0.0.0
```

### 4. Get Connection String (5 menit)
```powershell
# Get connection string
az sql db show-connection-string `
  --client ado.net `
  --server "sql-newscraper-$UNIQUE_NAME" `
  --name NewsScraperDB

# Simpan output ini! Akan digunakan nanti.
```

**✅ Checkpoint:** Anda sudah punya database Azure SQL yang siap digunakan!

---

## 🎯 Hari Pertama (2-3 jam)

### Setup Storage & Key Vault

```powershell
$UNIQUE_NAME = "pertamina01"  # Ganti dengan nama Anda

# 1. Buat Storage Account
az storage account create `
  --name "stnewscraper$UNIQUE_NAME" `
  --resource-group rg-functions-newscraper `
  --location southeastasia `
  --sku Standard_LRS

# 2. Buat Key Vault
az keyvault create `
  --name "kv-newscraper-$UNIQUE_NAME" `
  --resource-group rg-functions-newscraper `
  --location southeastasia

# 3. Simpan connection strings ke Key Vault
# (Ganti [CONNECTION_STRING] dengan yang didapat sebelumnya)
az keyvault secret set `
  --vault-name "kv-newscraper-$UNIQUE_NAME" `
  --name DatabaseConnectionString `
  --value "[CONNECTION_STRING_DATABASE]"

az keyvault secret set `
  --vault-name "kv-newscraper-$UNIQUE_NAME" `
  --name StorageConnectionString `
  --value "[CONNECTION_STRING_STORAGE]"
```

### Setup Database Schema

```powershell
# Download Azure Data Studio atau SQL Server Management Studio
# Atau gunakan Azure CLI:

az sql db query `
  --server "sql-newscraper-$UNIQUE_NAME" `
  --database NewsScraperDB `
  --admin-user sqladmin `
  --admin-password "P@ssw0rd123!Strong" `
  --file azure_functions/shared/database_schema.sql
```

**✅ Checkpoint:** Database schema sudah siap!

---

## 📦 Hari Kedua (3-4 jam)

### Setup Azure OpenAI (untuk Copilot)

```powershell
$UNIQUE_NAME = "pertamina01"

# Buat Azure OpenAI resource
az cognitiveservices account create `
  --name "openai-newscraper-$UNIQUE_NAME" `
  --resource-group rg-functions-newscraper `
  --kind OpenAI `
  --sku S0 `
  --location eastus `
  --yes

# Get API key
az cognitiveservices account keys list `
  --name "openai-newscraper-$UNIQUE_NAME" `
  --resource-group rg-functions-newscraper

# Get endpoint
az cognitiveservices account show `
  --name "openai-newscraper-$UNIQUE_NAME" `
  --resource-group rg-functions-newscraper `
  --query properties.endpoint

# Deploy GPT-4 model
az cognitiveservices account deployment create `
  --name "openai-newscraper-$UNIQUE_NAME" `
  --resource-group rg-functions-newscraper `
  --deployment-name gpt-4 `
  --model-name gpt-4 `
  --model-version "0613" `
  --model-format OpenAI `
  --sku-capacity 10 `
  --sku-name "Standard"

# Simpan API key dan endpoint ke Key Vault
az keyvault secret set `
  --vault-name "kv-newscraper-$UNIQUE_NAME" `
  --name CopilotApiKey `
  --value "[API_KEY_DARI_OUTPUT_DI_ATAS]"

az keyvault secret set `
  --vault-name "kv-newscraper-$UNIQUE_NAME" `
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
  --server "sql-newscraper-$UNIQUE_NAME" `
  --database NewsScraperDB `
  --admin-user sqladmin `
  --admin-password "P@ssw0rd123!Strong" `
  --query "SELECT COUNT(*) as total FROM news_articles"
```

**✅ Checkpoint:** Data sudah di Azure SQL Database!

---

## 🚀 Hari Ketiga (2-3 jam)

### Deploy Azure Functions

```powershell
$UNIQUE_NAME = "pertamina01"

# 1. Buat Function App
az functionapp create `
  --resource-group rg-functions-newscraper `
  --consumption-plan-location southeastasia `
  --runtime python `
  --runtime-version 3.9 `
  --functions-version 4 `
  --name "func-newscraper-$UNIQUE_NAME" `
  --storage-account "stnewscraper$UNIQUE_NAME" `
  --os-type Linux

# 2. Enable Managed Identity
az functionapp identity assign `
  --name "func-newscraper-$UNIQUE_NAME" `
  --resource-group rg-functions-newscraper

# 3. Grant Key Vault access
$PRINCIPAL_ID = az functionapp identity show `
  --name "func-newscraper-$UNIQUE_NAME" `
  --resource-group rg-functions-newscraper `
  --query principalId -o tsv

az keyvault set-policy `
  --name "kv-newscraper-$UNIQUE_NAME" `
  --object-id $PRINCIPAL_ID `
  --secret-permissions get list

# 4. Configure app settings
az functionapp config appsettings set `
  --name "func-newscraper-$UNIQUE_NAME" `
  --resource-group rg-functions-newscraper `
  --settings `
    "KEY_VAULT_URL=https://kv-newscraper-$UNIQUE_NAME.vault.azure.net/" `
    "DatabaseConnectionString=@Microsoft.KeyVault(SecretUri=https://kv-newscraper-$UNIQUE_NAME.vault.azure.net/secrets/DatabaseConnectionString/)" `
    "StorageConnectionString=@Microsoft.KeyVault(SecretUri=https://kv-newscraper-$UNIQUE_NAME.vault.azure.net/secrets/StorageConnectionString/)" `
    "CopilotApiKey=@Microsoft.KeyVault(SecretUri=https://kv-newscraper-$UNIQUE_NAME.vault.azure.net/secrets/CopilotApiKey/)" `
    "CopilotEndpoint=@Microsoft.KeyVault(SecretUri=https://kv-newscraper-$UNIQUE_NAME.vault.azure.net/secrets/CopilotEndpoint/)"

# 5. Deploy functions
cd azure_functions
func azure functionapp publish "func-newscraper-$UNIQUE_NAME" --python
```

**⏳ Tunggu 5-10 menit untuk deployment selesai...**

**✅ Checkpoint:** Functions sudah ter-deploy!

---

## 🧪 Testing (1 jam)

### Test Scraper Function

```powershell
$UNIQUE_NAME = "pertamina01"

# Test CNBC scraper
$FUNCTION_URL = "https://func-newscraper-$UNIQUE_NAME.azurewebsites.net/api/cnbc_scraper_function"

curl -X POST $FUNCTION_URL `
  -H "Content-Type: application/json" `
  -d '{"keywords": ["oil"], "start_date": "2024-01-01", "end_date": "2024-01-31"}'
```

### Verify Data in Database

```powershell
az sql db query `
  --server "sql-newscraper-$UNIQUE_NAME" `
  --database NewsScraperDB `
  --admin-user sqladmin `
  --admin-password "P@ssw0rd123!Strong" `
  --query "SELECT TOP 10 title, source, published_date FROM news_articles ORDER BY scraped_date DESC"
```

**✅ Checkpoint:** System working end-to-end!

---

## 📊 Monitoring Setup (30 menit)

### Enable Application Insights

```powershell
$UNIQUE_NAME = "pertamina01"

# Buat Application Insights
az monitor app-insights component create `
  --app "appinsights-newscraper" `
  --location southeastasia `
  --resource-group rg-functions-newscraper

# Get instrumentation key
$INSTRUMENTATION_KEY = az monitor app-insights component show `
  --app "appinsights-newscraper" `
  --resource-group rg-functions-newscraper `
  --query instrumentationKey -o tsv

# Configure Function App
az functionapp config appsettings set `
  --name "func-newscraper-$UNIQUE_NAME" `
  --resource-group rg-functions-newscraper `
  --settings "APPINSIGHTS_INSTRUMENTATIONKEY=$INSTRUMENTATION_KEY"
```

### View Logs

1. Buka Azure Portal: https://portal.azure.com
2. Go to Function App > func-newscraper-[NAMA_ANDA]
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
  --name "func-newscraper-$UNIQUE_NAME" `
  --resource-group rg-functions-newscraper
```

**Issue: Database connection failed**
```powershell
# Check firewall rules
az sql server firewall-rule list `
  --server "sql-newscraper-$UNIQUE_NAME" `
  --resource-group rg-database-newscraper
```

**Issue: Key Vault access denied**
```powershell
# Re-grant access
az keyvault set-policy `
  --name "kv-newscraper-$UNIQUE_NAME" `
  --object-id $PRINCIPAL_ID `
  --secret-permissions get list
```

---

## 💡 Pro Tips

1. **Use Unique Names**: Ganti `pertamina01` dengan nama unik Anda
2. **Save Passwords**: Simpan semua passwords di password manager
3. **Document Everything**: Catat semua resource names
4. **Test Incrementally**: Test setiap step sebelum lanjut
5. **Monitor Costs**: Setup cost alerts dari awal

---

## 📞 Support

- Azure Documentation: https://docs.microsoft.com/azure/
- Azure Support: https://portal.azure.com/#blade/Microsoft_Azure_Support/HelpAndSupportBlade
- Team Lead: [ISI_NAMA_DAN_KONTAK]

---

**🚀 Happy Migrating!**

*Quick Start Guide ini dibuat: 27 Januari 2026*
*Versi: 1.0*
