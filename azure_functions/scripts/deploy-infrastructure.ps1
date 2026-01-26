# Azure Infrastructure Deployment Script
# Deploys all required Azure resources for the News Scraping System

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "Southeast Asia",
    
    [Parameter(Mandatory=$false)]
    [string]$Environment = "dev",
    
    [Parameter(Mandatory=$false)]
    [string]$SqlAdminLogin = "newscraperadmin",
    
    [Parameter(Mandatory=$true)]
    [string]$SqlAdminPassword
)

# Set error action preference
$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting Azure Infrastructure Deployment..." -ForegroundColor Green
Write-Host "Resource Group: $ResourceGroupName" -ForegroundColor Yellow
Write-Host "Location: $Location" -ForegroundColor Yellow
Write-Host "Environment: $Environment" -ForegroundColor Yellow

# Check if Azure CLI is installed
try {
    $azVersion = az version --output json | ConvertFrom-Json
    Write-Host "✅ Azure CLI version: $($azVersion.'azure-cli')" -ForegroundColor Green
} catch {
    Write-Error "❌ Azure CLI is not installed or not in PATH. Please install Azure CLI first."
    exit 1
}

# Check if logged in to Azure
try {
    $account = az account show --output json | ConvertFrom-Json
    Write-Host "✅ Logged in as: $($account.user.name)" -ForegroundColor Green
    Write-Host "✅ Subscription: $($account.name) ($($account.id))" -ForegroundColor Green
} catch {
    Write-Error "❌ Not logged in to Azure. Please run 'az login' first."
    exit 1
}

# Create resource group if it doesn't exist
Write-Host "📦 Creating resource group..." -ForegroundColor Blue
try {
    $rg = az group show --name $ResourceGroupName --output json 2>$null | ConvertFrom-Json
    if ($rg) {
        Write-Host "✅ Resource group '$ResourceGroupName' already exists" -ForegroundColor Green
    }
} catch {
    Write-Host "Creating new resource group '$ResourceGroupName'..." -ForegroundColor Yellow
    az group create --name $ResourceGroupName --location $Location --output table
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Failed to create resource group"
        exit 1
    }
    Write-Host "✅ Resource group created successfully" -ForegroundColor Green
}

# Deploy infrastructure using Bicep
Write-Host "🏗️ Deploying infrastructure..." -ForegroundColor Blue
$deploymentName = "newscraper-deployment-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

try {
    $deployment = az deployment group create `
        --resource-group $ResourceGroupName `
        --template-file "infrastructure/main.bicep" `
        --parameters environment=$Environment sqlAdminLogin=$SqlAdminLogin sqlAdminPassword=$SqlAdminPassword `
        --name $deploymentName `
        --output json | ConvertFrom-Json
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Infrastructure deployment failed"
        exit 1
    }
    
    Write-Host "✅ Infrastructure deployed successfully!" -ForegroundColor Green
    
    # Extract outputs
    $outputs = $deployment.properties.outputs
    $functionAppName = $outputs.functionAppName.value
    $sqlServerName = $outputs.sqlServerName.value
    $sqlDatabaseName = $outputs.sqlDatabaseName.value
    $keyVaultName = $outputs.keyVaultName.value
    $storageAccountName = $outputs.storageAccountName.value
    $sqlConnectionString = $outputs.sqlConnectionString.value
    
    Write-Host "📋 Deployment Summary:" -ForegroundColor Cyan
    Write-Host "  Function App: $functionAppName" -ForegroundColor White
    Write-Host "  SQL Server: $sqlServerName" -ForegroundColor White
    Write-Host "  SQL Database: $sqlDatabaseName" -ForegroundColor White
    Write-Host "  Key Vault: $keyVaultName" -ForegroundColor White
    Write-Host "  Storage Account: $storageAccountName" -ForegroundColor White
    
} catch {
    Write-Error "❌ Deployment failed: $($_.Exception.Message)"
    exit 1
}

# Initialize database schema
Write-Host "🗄️ Initializing database schema..." -ForegroundColor Blue
try {
    # Create a temporary SQL script with connection info
    $tempSqlScript = "temp_schema_deploy.sql"
    $schemaContent = Get-Content "shared/database_schema.sql" -Raw
    
    # Use sqlcmd to execute the schema
    Write-Host "Executing database schema..." -ForegroundColor Yellow
    sqlcmd -S "$sqlServerName.database.windows.net" -d $sqlDatabaseName -U $SqlAdminLogin -P $SqlAdminPassword -i "shared/database_schema.sql" -l 60
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Database schema initialized successfully" -ForegroundColor Green
    } else {
        Write-Warning "⚠️ Database schema initialization may have had issues. Please check manually."
    }
} catch {
    Write-Warning "⚠️ Could not initialize database schema automatically: $($_.Exception.Message)"
    Write-Host "Please run the SQL script manually: shared/database_schema.sql" -ForegroundColor Yellow
}

# Create environment configuration file
Write-Host "⚙️ Creating environment configuration..." -ForegroundColor Blue
$envConfig = @"
# Azure Functions News Scraping System - Environment Configuration
# Generated on $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

# SQL Server Configuration
SQL_SERVER_CONNECTION_STRING="$sqlConnectionString"

# Azure Services
AZURE_KEY_VAULT_URL="https://$keyVaultName.vault.azure.net/"
BLOB_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=$storageAccountName;EndpointSuffix=core.windows.net;AccountKey=<will-be-retrieved-from-keyvault>"

# Function App Configuration
FUNCTIONS_WORKER_RUNTIME="python"
FUNCTIONS_EXTENSION_VERSION="~4"
ENVIRONMENT="$Environment"

# Application Insights
APPINSIGHTS_INSTRUMENTATIONKEY="<will-be-set-automatically>"
APPLICATIONINSIGHTS_CONNECTION_STRING="<will-be-set-automatically>"

# Resource Names (for reference)
RESOURCE_GROUP_NAME="$ResourceGroupName"
FUNCTION_APP_NAME="$functionAppName"
SQL_SERVER_NAME="$sqlServerName"
SQL_DATABASE_NAME="$sqlDatabaseName"
KEY_VAULT_NAME="$keyVaultName"
STORAGE_ACCOUNT_NAME="$storageAccountName"
"@

$envConfig | Out-File -FilePath ".env.azure" -Encoding UTF8
Write-Host "✅ Environment configuration saved to .env.azure" -ForegroundColor Green

# Display next steps
Write-Host "`n🎉 Deployment completed successfully!" -ForegroundColor Green
Write-Host "`n📝 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Review the generated .env.azure file" -ForegroundColor White
Write-Host "2. Test database connection using the test scripts" -ForegroundColor White
Write-Host "3. Deploy your Function App code" -ForegroundColor White
Write-Host "4. Configure Copilot API credentials in Key Vault" -ForegroundColor White

Write-Host "`n🔗 Useful Commands:" -ForegroundColor Cyan
Write-Host "  Test database: python tests/test_database_connection.py" -ForegroundColor White
Write-Host "  Deploy functions: func azure functionapp publish $functionAppName" -ForegroundColor White
Write-Host "  View logs: func azure functionapp logstream $functionAppName" -ForegroundColor White

Write-Host "`n✨ Infrastructure is ready for use!" -ForegroundColor Green