# Quick Deployment Script for Azure Functions
# Simple one-command deployment

param(
    [Parameter(Mandatory=$false)]
    [string]$FunctionAppName = ""
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "🚀 Quick Deploy - Azure Functions with Comprehensive Logging" -ForegroundColor Cyan
Write-Host ""

# Check if in correct directory
if (-not (Test-Path "host.json")) {
    Write-Error "❌ Please run from azure_functions directory"
    exit 1
}

# Check Azure CLI
try {
    $account = az account show 2>$null | ConvertFrom-Json
    Write-Host "✅ Azure CLI: Logged in as $($account.user.name)" -ForegroundColor Green
} catch {
    Write-Error "❌ Not logged in. Run: az login"
    exit 1
}

# Check func tools
try {
    $funcVersion = func --version
    Write-Host "✅ Azure Functions Core Tools: $funcVersion" -ForegroundColor Green
} catch {
    Write-Error "❌ Install: npm install -g azure-functions-core-tools@4"
    exit 1
}

# Find or select Function App
if (-not $FunctionAppName) {
    $apps = az functionapp list --query "[?kind=='functionapp,linux'].{name:name, rg:resourceGroup}" | ConvertFrom-Json
    
    if ($apps.Count -eq 0) {
        Write-Error "❌ No Function Apps found"
        exit 1
    }
    
    if ($apps.Count -eq 1) {
        $FunctionAppName = $apps[0].name
        Write-Host "✅ Found: $FunctionAppName" -ForegroundColor Green
    } else {
        Write-Host "Select Function App:" -ForegroundColor Yellow
        for ($i = 0; $i -lt $apps.Count; $i++) {
            Write-Host "  [$i] $($apps[$i].name)" -ForegroundColor White
        }
        $sel = Read-Host "Number"
        $FunctionAppName = $apps[$sel].name
    }
}

Write-Host ""
Write-Host "📦 Deploying to: $FunctionAppName" -ForegroundColor Cyan
Write-Host ""

# Deploy
Write-Host "⏳ Deploying... (this takes 2-3 minutes)" -ForegroundColor Blue
func azure functionapp publish $FunctionAppName --build remote --python

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Deployment successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🔍 View logs:" -ForegroundColor Cyan
    Write-Host "   func azure functionapp logstream $FunctionAppName" -ForegroundColor White
    Write-Host ""
    Write-Host "🌐 Azure Portal:" -ForegroundColor Cyan
    Write-Host "   https://portal.azure.com" -ForegroundColor White
    Write-Host ""
} else {
    Write-Error "❌ Deployment failed"
    exit 1
}
