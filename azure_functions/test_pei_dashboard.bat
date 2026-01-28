@echo off
REM Quick test script untuk PEI Dashboard Function App

set BASE_URL=https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api
set FUNCTION_KEY=QRn4YL31yW-bZBFHDlt8znrvRmlfbvD8owXwCBegfk7TAzFuLEZIFg==

echo ========================================
echo PEI DASHBOARD FUNCTION APP TESTER
echo ========================================
echo.
echo Base URL: %BASE_URL%
echo Function Key: Configured ✓
echo.
echo Testing CNBC Scraper Function...
echo.

curl -X GET "%BASE_URL%/cnbc_scraper_function?code=%FUNCTION_KEY%&keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28&save_to_db=false" -H "Content-Type: application/json"

echo.
echo.
echo ========================================
echo Test Complete!
echo ========================================
echo.
echo If you see JSON response above, the function is working!
echo.
echo To test other scrapers, run: test_scrapers.bat
echo.
pause
