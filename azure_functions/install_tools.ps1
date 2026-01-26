# Script to install Azure CLI and Azure Functions Core Tools
# Run this as Administrator

Write-Host "🔧 Installing Azure Development Tools..." -ForegroundColor Blue

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warning "⚠️ This script should be run as Administrator for best results"
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
}

# Install Chocolatey if not present
try {
    choco --version | Out-Null
    Write-Host "✅ Chocolatey already installed" -ForegroundColor Green
} catch {
    Write-Host "📦 Installing Chocolatey..." -ForegroundColor Blue
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
}

# Install Azure CLI
Write-Host "☁️ Installing Azure CLI..." -ForegroundColor Blue
try {
    choco install azure-cli -y
    Write-Host "✅ Azure CLI installed successfully" -ForegroundColor Green
} catch {
    Write-Warning "⚠️ Failed to install Azure CLI via Chocolatey"
    Write-Host "💡 Please download manually from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-windows" -ForegroundColor Yellow
}

# Install Node.js (required for Azure Functions Core Tools)
Write-Host "📦 Installing Node.js..." -ForegroundColor Blue
try {
    choco install nodejs -y
    Write-Host "✅ Node.js installed successfully" -ForegroundColor Green
} catch {
    Write-Warning "⚠️ Failed to install Node.js via Chocolatey"
    Write-Host "💡 Please download manually from: https://nodejs.org/" -ForegroundColor Yellow
}

# Refresh environment variables
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Install Azure Functions Core Tools
Write-Host "⚡ Installing Azure Functions Core Tools..." -ForegroundColor Blue
try {
    npm install -g azure-functions-core-tools@4 --unsafe-perm true
    Write-Host "✅ Azure Functions Core Tools installed successfully" -ForegroundColor Green
} catch {
    Write-Warning "⚠️ Failed to install Azure Functions Core Tools"
    Write-Host "💡 Try running: npm install -g azure-functions-core-tools@4 --unsafe-perm true" -ForegroundColor Yellow
}

Write-Host "`n🎉 Installation completed!" -ForegroundColor Green
Write-Host "💡 Please restart your command prompt to use the new tools" -ForegroundColor Yellow
Write-Host "`n📋 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Restart command prompt" -ForegroundColor White
Write-Host "2. Run: az login" -ForegroundColor White
Write-Host "3. Deploy functions: .\scripts\deploy-functions.ps1 -FunctionAppName 'pei-dashboard'" -ForegroundColor White