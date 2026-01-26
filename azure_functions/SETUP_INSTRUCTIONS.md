# Azure Functions News Scraping System - Setup Instructions

## Current Status

✅ **Completed:**
- Database schema and handlers implemented
- Azure Functions code structure ready
- Configuration files prepared

❌ **Issues Found:**
1. **Firewall Rule**: IP address `180.252.80.182` needs to be added to Azure SQL Server firewall
2. **Azure CLI**: Not installed (required for deployment)
3. **Azure Functions Core Tools**: Not properly installed

## Required Actions

### 1. Add IP Address to SQL Server Firewall

**Option A: Using Azure Portal**
1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to your SQL Server: `pei-dashboard`
3. Go to **Security** > **Networking**
4. Add firewall rule:
   - **Rule name**: `LocalDevelopment`
   - **Start IP**: `180.252.80.182`
   - **End IP**: `180.252.80.182`
5. Click **Save**

**Option B: Using PowerShell (if you have Azure PowerShell)**
```powershell
# Login to Azure
Connect-AzAccount

# Add firewall rule
New-AzSqlServerFirewallRule -ResourceGroupName "PeiDashboard" -ServerName "pei-dashboard" -FirewallRuleName "LocalDevelopment" -StartIpAddress "180.252.80.182" -EndIpAddress "180.252.80.182"
```

### 2. Install Required Tools

**Install Azure CLI:**
1. Download from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-windows
2. Run the installer
3. Restart your command prompt
4. Login: `az login`

**Install Azure Functions Core Tools:**
```bash
# Install Node.js if not already installed
# Download from: https://nodejs.org/

# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4 --unsafe-perm true
```

### 3. Test Database Connection

After adding the firewall rule, test the connection:

```bash
cd azure_functions
python test_connection_methods.py
```

### 4. Initialize Database Schema

Once connection works:

```bash
cd azure_functions
python scripts/initialize-database.py
```

### 5. Deploy Function App

```bash
cd azure_functions
.\scripts\deploy-functions.ps1 -FunctionAppName "pei-dashboard"
```

## Alternative: Enable SQL Authentication

If you prefer to use SQL authentication instead of Azure AD:

1. Go to Azure Portal > SQL Server `pei-dashboard`
2. Go to **Security** > **Azure Active Directory**
3. Disable "Azure Active Directory only authentication"
4. Set SQL admin credentials
5. Update connection string in `.env.azure`

## Verification Steps

### 1. Database Connection Test
```bash
python azure_functions/tests/test_database_connection.py
```

### 2. Function App Test
After deployment, test the endpoint:
```
https://pei-dashboard.azurewebsites.net/api/test_function
```

### 3. Check Application Insights
- Go to Azure Portal
- Navigate to Application Insights for `pei-dashboard`
- Check logs and metrics

## Next Steps After Setup

1. **Configure Application Settings**
   - Add connection strings to Function App settings
   - Configure Key Vault access
   - Set up Application Insights

2. **Deploy Scraper Functions**
   - Implement timer-triggered functions
   - Configure scheduling
   - Test end-to-end functionality

3. **Setup Monitoring**
   - Configure alerts
   - Setup dashboards
   - Monitor performance

## Troubleshooting

### Common Issues

**Connection Timeout:**
- Check firewall rules
- Verify connection string
- Test network connectivity

**Authentication Failed:**
- Ensure proper Azure AD setup
- Check user permissions
- Verify connection string format

**Deployment Failed:**
- Check Azure CLI login status
- Verify Function App exists
- Check resource permissions

### Support Commands

```bash
# Check Azure CLI status
az account show

# List Function Apps
az functionapp list --output table

# Check SQL Server firewall rules
az sql server firewall-rule list --server pei-dashboard --resource-group PeiDashboard

# View Function App logs
func azure functionapp logstream pei-dashboard
```

## Contact Information

If you encounter issues:
1. Check the error logs in Application Insights
2. Verify all prerequisites are installed
3. Ensure proper Azure permissions
4. Test network connectivity to Azure services