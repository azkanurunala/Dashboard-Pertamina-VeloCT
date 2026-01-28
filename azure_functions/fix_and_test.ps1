# Comprehensive fix and test script for Azure Functions

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Azure Functions Diagnostic and Fix Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check current app settings
Write-Host "Step 1: Checking current app settings..." -ForegroundColor Yellow
az functionapp config appsettings list --name pei-dashboard --resource-group PeiDashboard --query "[?name=='DatabaseConnectionString' || name=='SQL_SERVER_CONNECTION_STRING' || name=='KEY_VAULT_URL'].{Name:name, Value:value}" -o table

Write-Host ""
Write-Host "Step 2: Setting direct database connection (bypass Key Vault)..." -ForegroundColor Yellow

# Direct connection string
$connectionString = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Uid=CloudSAa33fbc7c;Pwd=uRahcie3&105272;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

az functionapp config appsettings set --name pei-dashboard --resource-group PeiDashboard --settings "SQL_SERVER_CONNECTION_STRING=$connectionString" --output none

Write-Host "Database connection string configured" -ForegroundColor Green

Write-Host ""
Write-Host "Step 3: Restarting function app..." -ForegroundColor Yellow
az functionapp restart --name pei-dashboard --resource-group PeiDashboard --output none
Start-Sleep -Seconds 10

Write-Host "Function app restarted" -ForegroundColor Green

Write-Host ""
Write-Host "Step 4: Testing function..." -ForegroundColor Yellow
Write-Host ""

# Test the function
$url = "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/test_function?code=QRn4YL31yW-bZBFHDlt8znrvRmlfbvD8owXwCBegfk7TAzFuLEZIFg=="

try {
    $response = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 30
    Write-Host "Test function responded successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor Cyan
    $response | ConvertTo-Json -Depth 10
    
    # Check if database test passed
    if ($response.tests.database.passed) {
        Write-Host ""
        Write-Host "DATABASE CONNECTION WORKING!" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "Database test failed. Details:" -ForegroundColor Yellow
        $response.tests.database | ConvertTo-Json -Depth 5
    }
} catch {
    Write-Host "Test failed: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Next: Test a scraper function" -ForegroundColor Cyan
Write-Host "Run: python quick_test_scraper.py" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
