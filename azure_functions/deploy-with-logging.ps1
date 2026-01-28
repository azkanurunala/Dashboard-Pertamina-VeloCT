# Azure Functions Deployment Script - With Comprehensive Logging
# Deploy updated functions with comprehensive logging to Azure

param(
    [Parameter(Mandatory=$false)]
    [string]$FunctionAppName = "",
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroupName = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipTests = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$UseSlot = $false,
    
    [Parameter(Mandatory=$false)]
    [string]$SlotName = "staging"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   Azure Functions Deployment - Comprehensive Logging Update   ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "host.json")) {
    Write-Error "❌ host.json not found. Please run this script from the azure_functions directory."
    exit 1
}

# Check if Azure CLI is installed and logged in
Write-Host "🔍 Checking Azure CLI..." -ForegroundColor Blue
try {
    $account = az account show 2>$null | ConvertFrom-Json
    if (-not $account) {
        Write-Error "❌ Not logged in to Azure CLI. Please run: az login"
        exit 1
    }
    Write-Host "✅ Logged in as: $($account.user.name)" -ForegroundColor Green
    Write-Host "   Subscription: $($account.name)" -ForegroundColor White
} catch {
    Write-Error "❌ Azure CLI is not installed or not logged in."
    Write-Host "Install Azure CLI: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli" -ForegroundColor Yellow
    exit 1
}

# Check if Azure Functions Core Tools is installed
Write-Host "🔍 Checking Azure Functions Core Tools..." -ForegroundColor Blue
try {
    $funcVersion = func --version
    Write-Host "✅ Azure Functions Core Tools version: $funcVersion" -ForegroundColor Green
} catch {
    Write-Error "❌ Azure Functions Core Tools is not installed."
    Write-Host "Install with: npm install -g azure-functions-core-tools@4 --unsafe-perm true" -ForegroundColor Yellow
    exit 1
}

# If Function App name not provided, try to find it
if (-not $FunctionAppName) {
    Write-Host "🔍 Looking for Function Apps in subscription..." -ForegroundColor Blue
    $functionApps = az functionapp list --query "[?kind=='functionapp,linux'].{name:name, resourceGroup:resourceGroup}" | ConvertFrom-Json
    
    if ($functionApps.Count -eq 0) {
        Write-Error "❌ No Function Apps found in subscription."
        exit 1
    }
    
    if ($functionApps.Count -eq 1) {
        $FunctionAppName = $functionApps[0].name
        $ResourceGroupName = $functionApps[0].resourceGroup
        Write-Host "✅ Found Function App: $FunctionAppName" -ForegroundColor Green
    } else {
        Write-Host "📋 Multiple Function Apps found:" -ForegroundColor Yellow
        for ($i = 0; $i -lt $functionApps.Count; $i++) {
            Write-Host "  [$i] $($functionApps[$i].name) (Resource Group: $($functionApps[$i].resourceGroup))" -ForegroundColor White
        }
        $selection = Read-Host "Select Function App number (0-$($functionApps.Count - 1))"
        $FunctionAppName = $functionApps[$selection].name
        $ResourceGroupName = $functionApps[$selection].resourceGroup
    }
}

Write-Host ""
Write-Host "📦 Deployment Configuration:" -ForegroundColor Cyan
Write-Host "  Function App: $FunctionAppName" -ForegroundColor White
Write-Host "  Resource Group: $ResourceGroupName" -ForegroundColor White
if ($UseSlot) {
    Write-Host "  Deployment Slot: $SlotName" -ForegroundColor White
}
Write-Host ""

# Validate Function App exists
Write-Host "🔍 Validating Function App..." -ForegroundColor Blue
try {
    if ($ResourceGroupName) {
        $appInfo = az functionapp show --name $FunctionAppName --resource-group $ResourceGroupName --output json | ConvertFrom-Json
    } else {
        $appInfo = az functionapp show --name $FunctionAppName --output json | ConvertFrom-Json
        $ResourceGroupName = $appInfo.resourceGroup
    }
    
    if (-not $appInfo) {
        Write-Error "❌ Function App '$FunctionAppName' not found."
        exit 1
    }
    
    Write-Host "✅ Function App validated" -ForegroundColor Green
    Write-Host "   Location: $($appInfo.location)" -ForegroundColor White
    Write-Host "   Runtime: Python $($appInfo.siteConfig.linuxFxVersion -replace 'PYTHON\|', '')" -ForegroundColor White
    Write-Host "   State: $($appInfo.state)" -ForegroundColor White
} catch {
    Write-Error "❌ Failed to validate Function App: $($_.Exception.Message)"
    exit 1
}

# Check if comprehensive logging files exist
Write-Host ""
Write-Host "🔍 Verifying comprehensive logging files..." -ForegroundColor Blue
$requiredFiles = @(
    "shared/azure_logging.py",
    "cnbc_scraper_function/__init__.py",
    "kompas_scraper_function/__init__.py",
    "kontan_scraper_function/__init__.py"
)

$missingFiles = @()
foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Error "❌ Missing required files:"
    foreach ($file in $missingFiles) {
        Write-Host "   - $file" -ForegroundColor Red
    }
    exit 1
}

Write-Host "✅ All required logging files present" -ForegroundColor Green

# Verify azure_logging.py has AzureLoggingManager
$loggingContent = Get-Content "shared/azure_logging.py" -Raw
if ($loggingContent -notmatch "class AzureLoggingManager") {
    Write-Error "❌ AzureLoggingManager class not found in azure_logging.py"
    exit 1
}
Write-Host "✅ AzureLoggingManager class verified" -ForegroundColor Green

# Check requirements.txt
Write-Host ""
Write-Host "🔍 Checking requirements.txt..." -ForegroundColor Blue
if (-not (Test-Path "requirements.txt")) {
    Write-Error "❌ requirements.txt not found."
    exit 1
}
Write-Host "✅ requirements.txt found" -ForegroundColor Green

# Confirm deployment
Write-Host ""
Write-Host "⚠️  Ready to deploy with comprehensive logging updates" -ForegroundColor Yellow
Write-Host ""
Write-Host "This will deploy the following updates:" -ForegroundColor White
Write-Host "  ✓ New azure_logging.py module" -ForegroundColor Green
Write-Host "  ✓ Updated 11 scraper functions with comprehensive logging" -ForegroundColor Green
Write-Host "  ✓ Correlation tracking and performance metrics" -ForegroundColor Green
Write-Host "  ✓ Enhanced error logging with stack traces" -ForegroundColor Green
Write-Host ""

$confirm = Read-Host "Continue with deployment? (Y/N)"
if ($confirm -ne "Y" -and $confirm -ne "y") {
    Write-Host "❌ Deployment cancelled by user" -ForegroundColor Yellow
    exit 0
}

# Deploy to Azure
Write-Host ""
Write-Host "📦 Deploying to Azure..." -ForegroundColor Blue
Write-Host "   This may take several minutes..." -ForegroundColor White
Write-Host ""

try {
    $deployTarget = $FunctionAppName
    if ($UseSlot) {
        $deployTarget = "$FunctionAppName/$SlotName"
        Write-Host "🎯 Deploying to slot: $SlotName" -ForegroundColor Cyan
    }
    
    # Deploy with remote build (recommended for Python)
    func azure functionapp publish $deployTarget --build remote --python
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Deployment successful!" -ForegroundColor Green
    } else {
        Write-Error "❌ Deployment failed with exit code: $LASTEXITCODE"
        exit 1
    }
} catch {
    Write-Error "❌ Deployment failed: $($_.Exception.Message)"
    exit 1
}

# Wait for deployment to settle
Write-Host ""
Write-Host "⏳ Waiting for deployment to settle..." -ForegroundColor Blue
Start-Sleep -Seconds 15

# Get Function App URL
$appUrl = "https://$($appInfo.defaultHostName)"
if ($UseSlot) {
    $slotInfo = az functionapp deployment slot show --name $FunctionAppName --slot $SlotName --resource-group $ResourceGroupName | ConvertFrom-Json
    $appUrl = "https://$($slotInfo.defaultHostName)"
}

Write-Host "✅ Deployment settled" -ForegroundColor Green

# Test deployment (if not skipped)
if (-not $SkipTests) {
    Write-Host ""
    Write-Host "🧪 Testing deployment..." -ForegroundColor Blue
    
    # Test CNBC scraper function
    try {
        Write-Host "   Testing CNBC scraper..." -ForegroundColor White
        
        # Get function key
        $keys = az functionapp keys list --name $FunctionAppName --resource-group $ResourceGroupName | ConvertFrom-Json
        $masterKey = $keys.masterKey
        
        # Test with simple parameters
        $testUrl = "$appUrl/api/cnbc_scraper_function?code=$masterKey&keywords=energy&start_date=2024-01-01&end_date=2024-01-02"
        
        Write-Host "   Calling: $testUrl" -ForegroundColor Gray
        $response = Invoke-RestMethod -Uri $testUrl -Method GET -TimeoutSec 60 -ErrorAction Stop
        
        if ($response.status -eq "success" -or $response.execution_id) {
            Write-Host "   ✅ CNBC scraper responded successfully" -ForegroundColor Green
            Write-Host "   Execution ID: $($response.execution_id)" -ForegroundColor White
            Write-Host "   Correlation ID: $($response.correlation_id)" -ForegroundColor White
        } else {
            Write-Warning "   ⚠️ CNBC scraper responded but status unclear"
        }
    } catch {
        Write-Warning "   ⚠️ Test function call failed: $($_.Exception.Message)"
        Write-Host "   You can test manually at: $appUrl/api/cnbc_scraper_function" -ForegroundColor Yellow
    }
}

# Display deployment summary
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                    Deployment Summary                          ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Deployment Details:" -ForegroundColor Cyan
Write-Host "  Function App: $FunctionAppName" -ForegroundColor White
Write-Host "  Resource Group: $ResourceGroupName" -ForegroundColor White
Write-Host "  URL: $appUrl" -ForegroundColor White
if ($UseSlot) {
    Write-Host "  Slot: $SlotName" -ForegroundColor White
}
Write-Host ""

Write-Host "🔗 Useful Links:" -ForegroundColor Cyan
Write-Host "  Azure Portal: https://portal.azure.com/#@/resource/subscriptions/$($account.id)/resourceGroups/$ResourceGroupName/providers/Microsoft.Web/sites/$FunctionAppName" -ForegroundColor White
Write-Host "  Log Stream: https://portal.azure.com/#@/resource/subscriptions/$($account.id)/resourceGroups/$ResourceGroupName/providers/Microsoft.Web/sites/$FunctionAppName/logStream" -ForegroundColor White
Write-Host "  Application Insights: https://portal.azure.com/#@/resource/subscriptions/$($account.id)/resourceGroups/$ResourceGroupName/providers/microsoft.insights/components/$FunctionAppName" -ForegroundColor White
Write-Host ""

Write-Host "📊 Monitoring Commands:" -ForegroundColor Cyan
Write-Host "  View live logs:" -ForegroundColor White
Write-Host "    func azure functionapp logstream $FunctionAppName" -ForegroundColor Gray
Write-Host ""
Write-Host "  List all functions:" -ForegroundColor White
Write-Host "    func azure functionapp list-functions $FunctionAppName" -ForegroundColor Gray
Write-Host ""
Write-Host "  Get function keys:" -ForegroundColor White
Write-Host "    az functionapp keys list --name $FunctionAppName --resource-group $ResourceGroupName" -ForegroundColor Gray
Write-Host ""

Write-Host "🔍 Verify Logging:" -ForegroundColor Cyan
Write-Host "  1. Open Azure Portal → Function App → Log Stream" -ForegroundColor White
Write-Host "  2. Trigger a scraper function" -ForegroundColor White
Write-Host "  3. Look for emoji logs: 🚀 FUNCTION_START, ✅ FUNCTION_END, etc." -ForegroundColor White
Write-Host "  4. Check Application Insights for custom dimensions" -ForegroundColor White
Write-Host ""

Write-Host "📝 Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Test each scraper function" -ForegroundColor White
Write-Host "  2. Verify logs in Azure Log Stream" -ForegroundColor White
Write-Host "  3. Check Application Insights for metrics" -ForegroundColor White
Write-Host "  4. Run Application Insights queries from COMPREHENSIVE_LOGGING_GUIDE.md" -ForegroundColor White
Write-Host ""

if ($UseSlot) {
    Write-Host "🔄 Slot Swap:" -ForegroundColor Cyan
    Write-Host "  To swap $SlotName to production:" -ForegroundColor White
    Write-Host "    az functionapp deployment slot swap --name $FunctionAppName --resource-group $ResourceGroupName --slot $SlotName" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "✨ Deployment completed successfully!" -ForegroundColor Green
Write-Host ""
