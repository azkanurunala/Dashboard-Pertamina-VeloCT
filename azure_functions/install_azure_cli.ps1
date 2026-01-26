# Script to download and install Azure CLI
# Run this as Administrator for best results

Write-Host "☁️ Installing Azure CLI..." -ForegroundColor Blue

# Download URL for Azure CLI
$downloadUrl = "https://aka.ms/installazurecliwindows"
$installerPath = "$env:TEMP\AzureCLI.msi"

try {
    Write-Host "📥 Downloading Azure CLI installer..." -ForegroundColor Yellow
    Write-Host "   From: $downloadUrl" -ForegroundColor White
    
    # Download the installer
    Invoke-WebRequest -Uri $downloadUrl -OutFile $installerPath -UseBasicParsing
    
    Write-Host "✅ Download completed!" -ForegroundColor Green
    Write-Host "📦 Installer saved to: $installerPath" -ForegroundColor White
    
    # Install Azure CLI
    Write-Host "🔧 Installing Azure CLI..." -ForegroundColor Blue
    Write-Host "   This may take a few minutes..." -ForegroundColor Yellow
    
    Start-Process -FilePath "msiexec.exe" -ArgumentList "/i", $installerPath, "/quiet", "/norestart" -Wait
    
    Write-Host "✅ Azure CLI installation completed!" -ForegroundColor Green
    
    # Clean up
    Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
    
    Write-Host "`n💡 IMPORTANT: Please restart your command prompt!" -ForegroundColor Yellow
    Write-Host "   After restart, you can use: az login" -ForegroundColor White
    
    Write-Host "`n📋 Next Steps:" -ForegroundColor Cyan
    Write-Host "1. Close this command prompt" -ForegroundColor White
    Write-Host "2. Open a new command prompt" -ForegroundColor White
    Write-Host "3. Run: az login" -ForegroundColor White
    Write-Host "4. Run: .\scripts\deploy-functions.ps1 -FunctionAppName 'pei-dashboard'" -ForegroundColor White
    
} catch {
    Write-Error "❌ Failed to download or install Azure CLI: $($_.Exception.Message)"
    Write-Host "`n💡 Manual Installation:" -ForegroundColor Yellow
    Write-Host "1. Go to: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-windows" -ForegroundColor White
    Write-Host "2. Download and run the installer manually" -ForegroundColor White
}