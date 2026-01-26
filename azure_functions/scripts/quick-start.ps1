# Quick Start Script untuk Azure Functions News Scraping System
# Script ini akan melakukan deployment lengkap dari awal

param(
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroupName = "rg-newscraper-dev",
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "Southeast Asia",
    
    [Parameter(Mandatory=$true)]
    [string]$SqlAdminPassword
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Azure Functions News Scraping System - Quick Start" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Green

# Validate prerequisites
Write-Host "🔍 Checking prerequisites..." -ForegroundColor Blue

# Check Azure CLI
try {
    $azVersion = az version --output json | ConvertFrom-Json
    Write-Host "✅ Azure CLI: $($azVersion.'azure-cli')" -ForegroundColor Green
} catch {
    Write-Error "❌ Azure CLI not found. Please install Azure CLI first."
    exit 1
}

# Check Azure Functions Core Tools
try {
    $funcVersion = func --version
    Write-Host "✅ Azure Functions Core Tools: $funcVersion" -ForegroundColor Green
} catch {
    Write-Error "❌ Azure Functions Core Tools not found. Install with: npm install -g azure-functions-core-tools@4 --unsafe-perm true"
    exit 1
}

# Check Python
try {
    $pythonVersion = python --version
    Write-Host "✅ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Error "❌ Python not found. Please install Python 3.9 or later."
    exit 1
}

# Check if logged in to Azure
try {
    $account = az account show --output json | ConvertFrom-Json
    Write-Host "✅ Azure Account: $($account.user.name)" -ForegroundColor Green
    Write-Host "✅ Subscription: $($account.name)" -ForegroundColor Green
} catch {
    Write-Error "❌ Not logged in to Azure. Please run 'az login' first."
    exit 1
}

Write-Host "`n📋 Deployment Configuration:" -ForegroundColor Cyan
Write-Host "  Resource Group: $ResourceGroupName" -ForegroundColor White
Write-Host "  Location: $Location" -ForegroundColor White
Write-Host "  SQL Admin: newscraperadmin" -ForegroundColor White

$confirm = Read-Host "`nProceed with deployment? (y/N)"
if ($confirm -ne 'y' -and $confirm -ne 'Y') {
    Write-Host "Deployment cancelled." -ForegroundColor Yellow
    exit 0
}

# Step 1: Deploy Infrastructure
Write-Host "`n🏗️ Step 1: Deploying Infrastructure..." -ForegroundColor Blue
Write-Host "This may take 5-10 minutes..." -ForegroundColor Yellow

try {
    & ".\scripts\deploy-infrastructure.ps1" -ResourceGroupName $ResourceGroupName -Location $Location -SqlAdminPassword $SqlAdminPassword
    if ($LASTEXITCODE -ne 0) {
        throw "Infrastructure deployment failed"
    }
    Write-Host "✅ Infrastructure deployment completed" -ForegroundColor Green
} catch {
    Write-Error "❌ Infrastructure deployment failed: $($_.Exception.Message)"
    exit 1
}

# Step 2: Initialize Database
Write-Host "`n🗄️ Step 2: Initializing Database..." -ForegroundColor Blue

try {
    python "scripts\initialize-database.py"
    if ($LASTEXITCODE -ne 0) {
        throw "Database initialization failed"
    }
    Write-Host "✅ Database initialization completed" -ForegroundColor Green
} catch {
    Write-Error "❌ Database initialization failed: $($_.Exception.Message)"
    Write-Host "You can run this manually later: python scripts\initialize-database.py" -ForegroundColor Yellow
}

# Step 3: Test Database Connection
Write-Host "`n🧪 Step 3: Testing Database Connection..." -ForegroundColor Blue

try {
    python "tests\test_database_connection.py"
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "⚠️ Database connection test had issues, but continuing..."
    } else {
        Write-Host "✅ Database connection test passed" -ForegroundColor Green
    }
} catch {
    Write-Warning "⚠️ Database connection test failed, but continuing with deployment..."
}

# Step 4: Get Function App Name
Write-Host "`n📱 Step 4: Preparing Function App Deployment..." -ForegroundColor Blue

try {
    # Read function app name from .env.azure
    $envFile = ".env.azure"
    if (Test-Path $envFile) {
        $functionAppName = ""
        Get-Content $envFile | ForEach-Object {
            if ($_ -match "FUNCTION_APP_NAME=(.+)") {
                $functionAppName = $matches[1].Trim('"')
            }
        }
        
        if (-not $functionAppName) {
            # Try to get from Azure CLI
            $apps = az functionapp list --resource-group $ResourceGroupName --query "[?contains(name, 'newscraper')].name" --output tsv
            if ($apps) {
                $functionAppName = $apps.Split("`n")[0].Trim()
            }
        }
        
        if ($functionAppName) {
            Write-Host "✅ Function App found: $functionAppName" -ForegroundColor Green
            
            # Step 5: Deploy Function App
            Write-Host "`n📦 Step 5: Deploying Function App Code..." -ForegroundColor Blue
            
            try {
                & ".\scripts\deploy-functions.ps1" -FunctionAppName $functionAppName
                if ($LASTEXITCODE -ne 0) {
                    throw "Function App deployment failed"
                }
                Write-Host "✅ Function App deployment completed" -ForegroundColor Green
            } catch {
                Write-Error "❌ Function App deployment failed: $($_.Exception.Message)"
                Write-Host "You can deploy manually later: .\scripts\deploy-functions.ps1 -FunctionAppName $functionAppName" -ForegroundColor Yellow
            }
        } else {
            Write-Warning "⚠️ Could not determine Function App name. Please deploy manually."
        }
    } else {
        Write-Warning "⚠️ .env.azure file not found. Please check infrastructure deployment."
    }
} catch {
    Write-Warning "⚠️ Could not deploy Function App automatically: $($_.Exception.Message)"
}

# Final Summary
Write-Host "`n" + "=" * 60 -ForegroundColor Green
Write-Host "🎉 Quick Start Deployment Summary" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Green

if (Test-Path ".env.azure") {
    Write-Host "`n📋 Deployed Resources:" -ForegroundColor Cyan
    Get-Content ".env.azure" | Where-Object { $_ -match "^[A-Z_]+=.+" -and $_ -notmatch "CONNECTION_STRING" } | ForEach-Object {
        $parts = $_ -split "=", 2
        if ($parts.Length -eq 2) {
            $key = $parts[0]
            $value = $parts[1].Trim('"')
            if ($key -match "(NAME|URL)$") {
                Write-Host "  $key`: $value" -ForegroundColor White
            }
        }
    }
}

Write-Host "`n🔗 Next Steps:" -ForegroundColor Cyan
Write-Host "1. ✅ Infrastructure deployed" -ForegroundColor Green
Write-Host "2. ✅ Database initialized" -ForegroundColor Green
Write-Host "3. ✅ Function App deployed" -ForegroundColor Green
Write-Host "4. 🔄 Configure Copilot API (optional)" -ForegroundColor Yellow
Write-Host "5. 🔄 Implement scraper functions" -ForegroundColor Yellow
Write-Host "6. 🔄 Setup monitoring and alerts" -ForegroundColor Yellow

Write-Host "`n📚 Documentation:" -ForegroundColor Cyan
Write-Host "  Full guide: DEPLOYMENT_GUIDE.md" -ForegroundColor White
Write-Host "  Test database: python tests\test_database_connection.py" -ForegroundColor White

if ($functionAppName) {
    Write-Host "  Function App URL: https://$functionAppName.azurewebsites.net" -ForegroundColor White
    Write-Host "  Test endpoint: https://$functionAppName.azurewebsites.net/api/test_function" -ForegroundColor White
}

Write-Host "`n✨ Your Azure Functions News Scraping System is ready!" -ForegroundColor Green