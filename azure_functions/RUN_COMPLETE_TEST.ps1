# Complete test workflow for Azure Functions migration

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Azure Functions Migration - Complete Test Workflow" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Configure and test basic function
Write-Host "STEP 1: Configure Database Connection and Test Basic Function" -ForegroundColor Yellow
Write-Host "-------------------------------------------------------------" -ForegroundColor Gray
Write-Host ""

& .\fix_and_test.ps1

Write-Host ""
Write-Host "Press Enter to continue to scraper test..." -ForegroundColor Cyan
Read-Host

# Step 2: Test scraper function
Write-Host ""
Write-Host "STEP 2: Test CNBC Scraper Function" -ForegroundColor Yellow
Write-Host "-------------------------------------------------------------" -ForegroundColor Gray
Write-Host ""

python quick_test_scraper.py

Write-Host ""
Write-Host "Press Enter to verify database data..." -ForegroundColor Cyan
Read-Host

# Step 3: Verify database
Write-Host ""
Write-Host "STEP 3: Verify Data in SQL Server Database" -ForegroundColor Yellow
Write-Host "-------------------------------------------------------------" -ForegroundColor Gray
Write-Host ""

python verify_database_data.py

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Test Workflow Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. If all tests passed, you can test other scraper functions" -ForegroundColor White
Write-Host "  2. Configure Copilot API credentials for sentiment analysis" -ForegroundColor White
Write-Host "  3. Set up scheduled triggers for automated scraping" -ForegroundColor White
Write-Host ""
