@echo off
REM Script untuk test Azure Functions yang sudah di-deploy via HTTP

REM ========================================
REM KONFIGURASI - AZURE FUNCTION APP
REM ========================================
set FUNCTION_APP_NAME=pei-dashboard-f5eebmdhe2a9dfgs
set AZURE_REGION=canadacentral-01
set BASE_URL=https://%FUNCTION_APP_NAME%.canadacentral-01.azurewebsites.net/api

REM FUNCTION KEY - SUDAH DIKONFIGURASI!
set FUNCTION_KEY=QRn4YL31yW-bZBFHDlt8znrvRmlfbvD8owXwCBegfk7TAzFuLEZIFg==

REM Jika URL berubah, edit line di atas atau uncomment dan edit line di bawah:
REM set BASE_URL=https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api

echo.
echo ========================================
echo AZURE FUNCTIONS TESTING MENU
echo ========================================
echo.
echo Current Function App: %FUNCTION_APP_NAME%
echo Base URL: %BASE_URL%
echo Function Key: %FUNCTION_KEY:~0,10%... (hidden)
echo.
if "%FUNCTION_KEY%"=="YOUR_FUNCTION_KEY_HERE" (
    echo ========================================
    echo WARNING: Function Key Not Configured!
    echo ========================================
    echo.
    echo Functions memerlukan authentication key.
    echo Lihat GET_FUNCTION_KEY_GUIDE.md untuk cara mendapatkan key.
    echo.
    echo Quick steps:
    echo 1. Azure Portal -^> PeiDashboard Function App
    echo 2. App Keys -^> Host keys -^> default -^> Copy
    echo 3. Edit test_scrapers.bat line 9
    echo.
    pause
)
echo.

:MENU
echo ========================================
echo Select scraper to test:
echo.
echo 1.  CNBC (International)
echo 2.  OilPrice
echo 3.  Reuters
echo 4.  CNN
echo 5.  The Guardian
echo 6.  Kompas (Indonesia)
echo 7.  Tempo (Indonesia)
echo 8.  Kontan (Indonesia)
echo 9.  CNBC Indonesia
echo 10. Bisnis Indonesia
echo 11. BPS (Data)
echo 12. Test ALL Scrapers
echo 13. Configure Function App URL
echo 0.  Exit
echo.

set /p choice="Enter your choice (0-13): "

if "%choice%"=="1" goto TEST_CNBC
if "%choice%"=="2" goto TEST_OILPRICE
if "%choice%"=="3" goto TEST_REUTERS
if "%choice%"=="4" goto TEST_CNN
if "%choice%"=="5" goto TEST_GUARDIAN
if "%choice%"=="6" goto TEST_KOMPAS
if "%choice%"=="7" goto TEST_TEMPO
if "%choice%"=="8" goto TEST_KONTAN
if "%choice%"=="9" goto TEST_CNBC_ID
if "%choice%"=="10" goto TEST_BISNIS
if "%choice%"=="11" goto TEST_BPS
if "%choice%"=="12" goto TEST_ALL
if "%choice%"=="13" goto CONFIGURE
if "%choice%"=="0" goto EXIT

echo Invalid choice!
pause
goto MENU

:TEST_CNBC
echo.
echo ========================================
echo Testing CNBC Scraper Function
echo ========================================
echo URL: %BASE_URL%/cnbc_scraper_function
echo.
curl -X GET "%BASE_URL%/cnbc_scraper_function?code=%FUNCTION_KEY%&keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28&save_to_db=true" -H "Content-Type: application/json"
echo.
echo.
pause
goto MENU

:TEST_OILPRICE
echo.
echo ========================================
echo Testing OilPrice Scraper Function
echo ========================================
echo URL: %BASE_URL%/oilprice_scraper_function
echo.
curl -X GET "%BASE_URL%/oilprice_scraper_function?code=%FUNCTION_KEY%&keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28&max_articles=10" -H "Content-Type: application/json"
echo.
echo.
pause
goto MENU

:TEST_REUTERS
echo.
echo ========================================
echo Testing Reuters Scraper Function
echo ========================================
echo URL: %BASE_URL%/reuters_scraper_function
echo.
curl -X GET "%BASE_URL%/reuters_scraper_function?code=%FUNCTION_KEY%&keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28&save_to_db=true" -H "Content-Type: application/json"
echo.
echo.
pause
goto MENU

:TEST_CNN
echo.
echo ========================================
echo Testing CNN Scraper Function
echo ========================================
echo URL: %BASE_URL%/cnn_scraper_function
echo.
curl -X GET "%BASE_URL%/cnn_scraper_function?code=%FUNCTION_KEY%&keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28&max_articles=10&save_to_db=true" -H "Content-Type: application/json"
echo.
echo.
pause
goto MENU

:TEST_GUARDIAN
echo.
echo ========================================
echo Testing The Guardian Scraper Function
echo ========================================
echo URL: %BASE_URL%/theguardian_scraper_function
echo.
curl -X GET "%BASE_URL%/theguardian_scraper_function?code=%FUNCTION_KEY%&keywords=energy,oil&start_date=2025-01-21&end_date=2026-01-28&max_articles=10&save_to_db=true" -H "Content-Type: application/json"
echo.
echo.
pause
goto MENU

:TEST_KOMPAS
echo.
echo ========================================
echo Testing Kompas Scraper Function
echo ========================================
echo URL: %BASE_URL%/kompas_scraper_function
echo.
curl -X GET "%BASE_URL%/kompas_scraper_function?code=%FUNCTION_KEY%&keywords=energi,minyak&start_date=2025-01-21&end_date=2026-01-28&max_articles=10&save_to_db=true" -H "Content-Type: application/json"
echo.
echo.
pause
goto MENU

:TEST_TEMPO
echo.
echo ========================================
echo Testing Tempo Scraper Function
echo ========================================
echo URL: %BASE_URL%/tempo_scraper_function
echo.
curl -X GET "%BASE_URL%/tempo_scraper_function?code=%FUNCTION_KEY%&keywords=energi,minyak&start_date=2025-01-21&end_date=2026-01-28&max_articles=10&save_to_db=true" -H "Content-Type: application/json"
echo.
echo.
pause
goto MENU

:TEST_KONTAN
echo.
echo ========================================
echo Testing Kontan Scraper Function
echo ========================================
echo URL: %BASE_URL%/kontan_scraper_function
echo.
curl -X GET "%BASE_URL%/kontan_scraper_function?code=%FUNCTION_KEY%&keywords=energi,minyak&start_date=2025-01-21&end_date=2026-01-28&max_articles=10&save_to_db=true" -H "Content-Type: application/json"
echo.
echo.
pause
goto MENU

:TEST_CNBC_ID
echo.
echo ========================================
echo Testing CNBC Indonesia Scraper Function
echo ========================================
echo URL: %BASE_URL%/cnbc_indonesia_scraper_function
echo.
curl -X GET "%BASE_URL%/cnbc_indonesia_scraper_function?code=%FUNCTION_KEY%&keywords=energi,minyak&start_date=2025-01-21&end_date=2026-01-28&max_articles=10&save_to_db=true" -H "Content-Type: application/json"
echo.
echo.
pause
goto MENU

:TEST_BISNIS
echo.
echo ========================================
echo Testing Bisnis Indonesia Scraper Function
echo ========================================
echo URL: %BASE_URL%/bisnis_indonesia_scraper_function
echo.
curl -X GET "%BASE_URL%/bisnis_indonesia_scraper_function?code=%FUNCTION_KEY%&keywords=energi,minyak&start_date=2025-01-21&end_date=2026-01-28&max_articles=10&save_to_db=true" -H "Content-Type: application/json"
echo.
echo.
pause
goto MENU

:TEST_BPS
echo.
echo ========================================
echo Testing BPS Scraper Function
echo ========================================
echo URL: %BASE_URL%/bps_scraper_function
echo.
curl -X GET "%BASE_URL%/bps_scraper_function?code=%FUNCTION_KEY%&indicators=inflation,gdp&start_date=2025-01-21&end_date=2026-01-28&save_to_db=true" -H "Content-Type: application/json"
echo.
echo.
pause
goto MENU

:TEST_ALL
echo.
echo ========================================
echo Testing ALL Scraper Functions
echo ========================================
echo.
python test_deployed_functions.py
pause
goto MENU

:CONFIGURE
echo.
echo ========================================
echo Configure Function App URL
echo ========================================
echo.
echo Current: %BASE_URL%
echo.
set /p NEW_APP_NAME="Enter Function App Name (without .azurewebsites.net): "
set FUNCTION_APP_NAME=%NEW_APP_NAME%
set BASE_URL=https://%FUNCTION_APP_NAME%.azurewebsites.net/api
echo.
echo Updated to: %BASE_URL%
echo.
pause
goto MENU

:EXIT
echo.
echo Exiting...
exit /b 0
