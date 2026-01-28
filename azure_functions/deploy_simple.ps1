# Simple deployment script using zip

Write-Host "Creating deployment package..." -ForegroundColor Cyan

# Create a temporary directory for deployment
$tempDir = "deploy_temp"
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

# Copy necessary files
Write-Host "Copying files..." -ForegroundColor Yellow

# Copy function directories
$functionDirs = @(
    "cnbc_scraper_function",
    "cnn_scraper_function", 
    "reuters_scraper_function",
    "theguardian_scraper_function",
    "oilprice_scraper_function",
    "bisnis_indonesia_scraper_function",
    "cnbc_indonesia_scraper_function",
    "kompas_scraper_function",
    "kontan_scraper_function",
    "tempo_scraper_function",
    "bps_scraper_function",
    "database_maintenance_function",
    "deduplication_function",
    "test_function"
)

foreach ($dir in $functionDirs) {
    if (Test-Path $dir) {
        Copy-Item -Path $dir -Destination "$tempDir\$dir" -Recurse
    }
}

# Copy shared modules
Copy-Item -Path "shared" -Destination "$tempDir\shared" -Recurse
Copy-Item -Path "scrapers" -Destination "$tempDir\scrapers" -Recurse
Copy-Item -Path "processing" -Destination "$tempDir\processing" -Recurse

# Copy config files
Copy-Item -Path "host.json" -Destination "$tempDir\host.json"
Copy-Item -Path "requirements.txt" -Destination "$tempDir\requirements.txt"

Write-Host "Creating zip file..." -ForegroundColor Yellow
$zipPath = "deploy.zip"
if (Test-Path $zipPath) {
    Remove-Item $zipPath
}

Compress-Archive -Path "$tempDir\*" -DestinationPath $zipPath

Write-Host "Deploying to Azure..." -ForegroundColor Yellow
az functionapp deployment source config-zip `
    --resource-group PeiDashboard `
    --name pei-dashboard `
    --src $zipPath

# Cleanup
Remove-Item -Recurse -Force $tempDir
Remove-Item $zipPath

Write-Host ""
Write-Host "Deployment complete!" -ForegroundColor Green
Write-Host "Waiting for function app to restart..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host "Testing function..." -ForegroundColor Cyan
python quick_test.py
