# Script to download and install ODBC Driver 18 for SQL Server
# Run this as Administrator

Write-Host "🔽 Downloading ODBC Driver 18 for SQL Server..." -ForegroundColor Blue

# Download URL for ODBC Driver 18
$downloadUrl = "https://go.microsoft.com/fwlink/?linkid=2249006"
$installerPath = "$env:TEMP\msodbcsql.msi"

try {
    # Download the installer
    Write-Host "Downloading from: $downloadUrl" -ForegroundColor Yellow
    Invoke-WebRequest -Uri $downloadUrl -OutFile $installerPath -UseBasicParsing
    
    Write-Host "✅ Download completed!" -ForegroundColor Green
    
    # Install the driver
    Write-Host "🔧 Installing ODBC Driver 18..." -ForegroundColor Blue
    Start-Process -FilePath "msiexec.exe" -ArgumentList "/i", $installerPath, "/quiet", "/norestart" -Wait
    
    Write-Host "✅ ODBC Driver 18 installation completed!" -ForegroundColor Green
    Write-Host "💡 Please restart your command prompt and try again." -ForegroundColor Yellow
    
    # Clean up
    Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
    
}
catch {
    Write-Error "❌ Failed to download or install ODBC Driver 18: $($_.Exception.Message)"
    Write-Host "💡 Please download manually from: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server" -ForegroundColor Yellow
}