# Test Deployment Script
# Tests deployed Azure Functions

$baseUrl = "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net"

Write-Host "🧪 Testing Azure Functions Deployment..." -ForegroundColor Cyan
Write-Host ""

# Test 1: Health Check
Write-Host "1. Testing Health Check Function..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/health" -Method GET -TimeoutSec 30
    Write-Host "   ✅ Health Check: OK" -ForegroundColor Green
    Write-Host "   Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor White
} catch {
    Write-Host "   ⚠️ Health Check: Failed or requires authentication" -ForegroundColor Yellow
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Gray
}

Write-Host ""

# Test 2: Test Function
Write-Host "2. Testing Test Function..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/test_function" -Method GET -TimeoutSec 30
    Write-Host "   ✅ Test Function: OK" -ForegroundColor Green
    Write-Host "   Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor White
} catch {
    Write-Host "   ⚠️ Test Function: Failed or requires authentication" -ForegroundColor Yellow
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Gray
}

Write-Host ""

# Test 3: Get Function Keys
Write-Host "3. Getting Function Keys..." -ForegroundColor Yellow
try {
    $keys = az functionapp keys list --name pei-dashboard --resource-group PeiDashboard --output json | ConvertFrom-Json
    Write-Host "   ✅ Function Keys Retrieved" -ForegroundColor Green
    Write-Host "   Master Key: $($keys.masterKey.Substring(0,10))..." -ForegroundColor White
} catch {
    Write-Host "   ⚠️ Could not retrieve keys" -ForegroundColor Yellow
}

Write-Host ""

# Test 4: List All Functions
Write-Host "4. Listing All Deployed Functions..." -ForegroundColor Yellow
try {
    $functions = az functionapp function list --name pei-dashboard --resource-group PeiDashboard --output json | ConvertFrom-Json
    Write-Host "   ✅ Total Functions: $($functions.Count)" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "   Scraper Functions:" -ForegroundColor Cyan
    $scrapers = $functions | Where-Object { $_.name -like "*scraper*" }
    Write-Host "   - Count: $($scrapers.Count)" -ForegroundColor White
    
    Write-Host ""
    Write-Host "   Utility Functions:" -ForegroundColor Cyan
    $utilities = $functions | Where-Object { $_.name -notlike "*scraper*" }
    Write-Host "   - Count: $($utilities.Count)" -ForegroundColor White
} catch {
    Write-Host "   ⚠️ Could not list functions" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "📋 Deployment Summary:" -ForegroundColor Cyan
Write-Host "   Base URL: $baseUrl" -ForegroundColor White
Write-Host "   Resource Group: PeiDashboard" -ForegroundColor White
Write-Host "   Location: Canada Central" -ForegroundColor White
Write-Host "   Runtime: Python 3.11" -ForegroundColor White

Write-Host ""
Write-Host "🔗 Useful Links:" -ForegroundColor Cyan
Write-Host "   Azure Portal: https://portal.azure.com" -ForegroundColor White
Write-Host "   Function App: https://portal.azure.com/#@/resource/subscriptions/5e4ecee4-ce42-47f4-b953-7f29ad625c53/resourceGroups/PeiDashboard/providers/Microsoft.Web/sites/pei-dashboard" -ForegroundColor White
Write-Host "   Deployment Center: https://portal.azure.com/#@/resource/subscriptions/5e4ecee4-ce42-47f4-b953-7f29ad625c53/resourceGroups/PeiDashboard/providers/Microsoft.Web/sites/pei-dashboard/vstscd" -ForegroundColor White

Write-Host ""
Write-Host "✨ Testing Complete!" -ForegroundColor Green
