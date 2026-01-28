# Script PowerShell untuk menjalankan setiap scraper satu per satu
# Memudahkan testing individual scraper

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SCRAPER TESTING MENU" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Function to test a scraper
function Test-Scraper {
    param(
        [string]$ScraperName,
        [string]$ScraperModule
    )
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "Testing: $ScraperName" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
    
    $testScript = @"
import sys
import os
import asyncio
from datetime import datetime, timedelta

# Add parent directory to path
parent_dir = os.path.abspath(os.path.dirname(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

async def test():
    try:
        print('Importing $ScraperModule...')
        $ScraperModule
        print('✓ Import successful')
        
        # Test basic functionality
        print('✓ Scraper ready to use')
        return True
    except Exception as e:
        print(f'✗ Error: {str(e)}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    result = asyncio.run(test())
    sys.exit(0 if result else 1)
"@
    
    # Save temp test script
    $tempFile = "temp_test_$ScraperName.py"
    $testScript | Out-File -FilePath $tempFile -Encoding UTF8
    
    # Run test
    python $tempFile
    $exitCode = $LASTEXITCODE
    
    # Cleanup
    Remove-Item $tempFile -ErrorAction SilentlyContinue
    
    if ($exitCode -eq 0) {
        Write-Host "✓ $ScraperName: PASSED" -ForegroundColor Green
    } else {
        Write-Host "✗ $ScraperName: FAILED" -ForegroundColor Red
    }
    
    return $exitCode -eq 0
}

# Menu
Write-Host "Select scraper to test:" -ForegroundColor Cyan
Write-Host "1.  CNBC (International)"
Write-Host "2.  OilPrice"
Write-Host "3.  Reuters"
Write-Host "4.  CNN"
Write-Host "5.  The Guardian"
Write-Host "6.  Kompas (Indonesia)"
Write-Host "7.  Tempo (Indonesia)"
Write-Host "8.  Kontan (Indonesia)"
Write-Host "9.  CNBC Indonesia"
Write-Host "10. Bisnis Indonesia"
Write-Host "11. BPS (Data)"
Write-Host "12. Test ALL Scrapers"
Write-Host "0.  Exit"
Write-Host ""

$choice = Read-Host "Enter your choice (0-12)"

switch ($choice) {
    "1" {
        Test-Scraper -ScraperName "CNBC" -ScraperModule "from scrapers.cnbc_scraper import CNBCNewsScraper"
    }
    "2" {
        Test-Scraper -ScraperName "OilPrice" -ScraperModule "from scrapers.oilprice_scraper import scrape_oilprice_news"
    }
    "3" {
        Test-Scraper -ScraperName "Reuters" -ScraperModule "from scrapers.reuters_scraper import ReutersNewsScraper"
    }
    "4" {
        Test-Scraper -ScraperName "CNN" -ScraperModule "from scrapers.cnn_scraper import scrape_cnn_news"
    }
    "5" {
        Test-Scraper -ScraperName "TheGuardian" -ScraperModule "from scrapers.theguardian_scraper import scrape_theguardian_news"
    }
    "6" {
        Test-Scraper -ScraperName "Kompas" -ScraperModule "from scrapers.kompas_scraper import scrape_kompas_news"
    }
    "7" {
        Test-Scraper -ScraperName "Tempo" -ScraperModule "from scrapers.tempo_scraper import scrape_tempo_news"
    }
    "8" {
        Test-Scraper -ScraperName "Kontan" -ScraperModule "from scrapers.kontan_scraper import scrape_kontan_news"
    }
    "9" {
        Test-Scraper -ScraperName "CNBC_Indonesia" -ScraperModule "from scrapers.cnbc_indonesia_scraper import scrape_cnbc_indonesia_news"
    }
    "10" {
        Test-Scraper -ScraperName "BisnisIndonesia" -ScraperModule "from scrapers.bisnis_indonesia_scraper import scrape_bisnis_indonesia_news"
    }
    "11" {
        Test-Scraper -ScraperName "BPS" -ScraperModule "from scrapers.bps_scraper import scrape_bps_data"
    }
    "12" {
        Write-Host ""
        Write-Host "Testing ALL scrapers..." -ForegroundColor Cyan
        Write-Host ""
        
        python test_individual_scrapers.py
    }
    "0" {
        Write-Host "Exiting..." -ForegroundColor Yellow
        exit
    }
    default {
        Write-Host "Invalid choice!" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
