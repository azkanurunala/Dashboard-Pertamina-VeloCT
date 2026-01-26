Write-Host "Downloading ODBC Driver 18 for SQL Server..." -ForegroundColor Blue

$downloadUrl = "https://go.microsoft.com/fwlink/?linkid=2249006"
$installerPath = "$env:TEMP\msodbcsql.msi"

Invoke-WebRequest -Uri $downloadUrl -OutFile $installerPath -UseBasicParsing

Write-Host "Download completed. Starting installation..." -ForegroundColor Green
Write-Host "Installer saved to: $installerPath" -ForegroundColor Yellow
Write-Host "Please run the installer manually or use: msiexec /i $installerPath /quiet" -ForegroundColor Yellow