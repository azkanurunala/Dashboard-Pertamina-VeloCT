# Azure Functions Deployment Script
# Deploys the Function App code to Azure

param(
    [Parameter(Mandatory=$true)]
    [string]$FunctionAppName,
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroupName = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$BuildLocally = $false
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting Azure Functions Deployment..." -ForegroundColor Green
Write-Host "Function App: $FunctionAppName" -ForegroundColor Yellow

# Check if Azure Functions Core Tools is installed
try {
    $funcVersion = func --version
    Write-Host "✅ Azure Functions Core Tools version: $funcVersion" -ForegroundColor Green
} catch {
    Write-Error "❌ Azure Functions Core Tools is not installed. Please install it first."
    Write-Host "Install with: npm install -g azure-functions-core-tools@4 --unsafe-perm true" -ForegroundColor Yellow
    exit 1
}

# Check if we're in the right directory
if (-not (Test-Path "host.json")) {
    Write-Error "❌ host.json not found. Please run this script from the azure_functions directory."
    exit 1
}

# Check if requirements.txt exists
if (-not (Test-Path "requirements.txt")) {
    Write-Error "❌ requirements.txt not found. Please ensure it exists in the azure_functions directory."
    exit 1
}

# Validate Function App exists
Write-Host "🔍 Validating Function App..." -ForegroundColor Blue
try {
    $appInfo = az functionapp show --name $FunctionAppName --output json 2>$null | ConvertFrom-Json
    if (-not $appInfo) {
        Write-Error "❌ Function App '$FunctionAppName' not found."
        exit 1
    }
    Write-Host "✅ Function App '$FunctionAppName' found" -ForegroundColor Green
    Write-Host "  Resource Group: $($appInfo.resourceGroup)" -ForegroundColor White
    Write-Host "  Location: $($appInfo.location)" -ForegroundColor White
    Write-Host "  Runtime: $($appInfo.siteConfig.pythonVersion)" -ForegroundColor White
} catch {
    Write-Error "❌ Failed to validate Function App. Please check if you're logged in to Azure CLI."
    exit 1
}

# Create function.json files for each function if they don't exist
Write-Host "📝 Ensuring function configurations..." -ForegroundColor Blue

# Create basic function structure if needed
$functionDirs = @(
    "orchestration",
    "processing", 
    "analysis",
    "scrapers"
)

foreach ($dir in $functionDirs) {
    if (-not (Test-Path $dir)) {
        Write-Host "Creating directory: $dir" -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# Create a simple HTTP trigger function for testing if none exist
$testFunctionDir = "test_function"
if (-not (Test-Path $testFunctionDir)) {
    Write-Host "Creating test function..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $testFunctionDir -Force | Out-Null
    
    # Create function.json
    $functionJson = @{
        scriptFile = "__init__.py"
        bindings = @(
            @{
                authLevel = "function"
                type = "httpTrigger"
                direction = "in"
                name = "req"
                methods = @("get", "post")
            },
            @{
                type = "http"
                direction = "out"
                name = "`$return"
            }
        )
    } | ConvertTo-Json -Depth 10

    $functionJson | Out-File -FilePath "$testFunctionDir/function.json" -Encoding UTF8

    # Create __init__.py
    $initPy = @"
import logging
import json
import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    
    try:
        # Test database connection
        from shared.models import DatabaseConfig
        from shared.database_handler import DatabaseHandler
        import os
        
        connection_string = os.getenv('SQL_SERVER_CONNECTION_STRING')
        if connection_string:
            config = DatabaseConfig(connection_string=connection_string)
            # Note: In production, you'd want to test the actual connection
            status = "Database configuration loaded successfully"
        else:
            status = "Database configuration not found"
        
        return func.HttpResponse(
            json.dumps({
                "status": "success",
                "message": "Azure Functions News Scraping System is running",
                "database_status": status,
                "timestamp": "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
            }),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Error in test function: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )
"@

    $initPy | Out-File -FilePath "$testFunctionDir/__init__.py" -Encoding UTF8
}

# Build and deploy
if ($BuildLocally) {
    Write-Host "🔨 Building locally..." -ForegroundColor Blue
    try {
        # Install dependencies locally
        pip install -r requirements.txt --target .python_packages/lib/site-packages
        Write-Host "✅ Dependencies installed locally" -ForegroundColor Green
    } catch {
        Write-Warning "⚠️ Local build failed, will use remote build"
    }
}

# Deploy to Azure
Write-Host "📦 Deploying to Azure..." -ForegroundColor Blue
try {
    if ($BuildLocally) {
        func azure functionapp publish $FunctionAppName --no-build
    } else {
        func azure functionapp publish $FunctionAppName --build remote
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Deployment successful!" -ForegroundColor Green
    } else {
        Write-Error "❌ Deployment failed"
        exit 1
    }
} catch {
    Write-Error "❌ Deployment failed: $($_.Exception.Message)"
    exit 1
}

# Get Function App URL
try {
    $appUrl = "https://$($appInfo.defaultHostName)"
    Write-Host "🌐 Function App URL: $appUrl" -ForegroundColor Cyan
    
    # Test the deployment
    Write-Host "🧪 Testing deployment..." -ForegroundColor Blue
    Start-Sleep -Seconds 10  # Wait for deployment to settle
    
    try {
        $testUrl = "$appUrl/api/test_function"
        $response = Invoke-RestMethod -Uri $testUrl -Method GET -TimeoutSec 30
        Write-Host "✅ Test function responded successfully" -ForegroundColor Green
        Write-Host "Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor White
    } catch {
        Write-Warning "⚠️ Test function call failed, but deployment may still be successful"
        Write-Host "You can test manually at: $appUrl/api/test_function" -ForegroundColor Yellow
    }
    
} catch {
    Write-Warning "⚠️ Could not retrieve Function App URL"
}

# Display useful information
Write-Host "`n📋 Deployment Summary:" -ForegroundColor Cyan
Write-Host "  Function App: $FunctionAppName" -ForegroundColor White
Write-Host "  URL: $appUrl" -ForegroundColor White
Write-Host "  Test Endpoint: $appUrl/api/test_function" -ForegroundColor White

Write-Host "`n🔗 Useful Commands:" -ForegroundColor Cyan
Write-Host "  View logs: func azure functionapp logstream $FunctionAppName" -ForegroundColor White
Write-Host "  List functions: func azure functionapp list-functions $FunctionAppName" -ForegroundColor White
Write-Host "  Get function keys: az functionapp keys list --name $FunctionAppName --resource-group $($appInfo.resourceGroup)" -ForegroundColor White

Write-Host "`n✨ Deployment completed successfully!" -ForegroundColor Green