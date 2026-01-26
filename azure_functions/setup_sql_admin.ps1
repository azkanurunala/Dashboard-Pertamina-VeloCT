# Script to setup SQL Server admin user
# This will enable SQL authentication and set admin password

param(
    [Parameter(Mandatory=$true)]
    [string]$AdminPassword
)

Write-Host "🔧 Setting up SQL Server admin user..." -ForegroundColor Blue

try {
    # First, check if Azure CLI is available
    $azVersion = az --version 2>$null
    if (-not $azVersion) {
        Write-Error "❌ Azure CLI not found. Please install Azure CLI first."
        Write-Host "Download from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli" -ForegroundColor Yellow
        exit 1
    }
    
    Write-Host "✅ Azure CLI found" -ForegroundColor Green
    
    # Check if logged in
    $account = az account show 2>$null
    if (-not $account) {
        Write-Host "🔐 Please login to Azure..." -ForegroundColor Yellow
        az login
    }
    
    Write-Host "✅ Azure login verified" -ForegroundColor Green
    
    # Enable SQL authentication and set admin password
    Write-Host "🔧 Enabling SQL authentication..." -ForegroundColor Blue
    
    az sql server update `
        --name "pei-dashboard" `
        --resource-group "PeiDashboard" `
        --admin-password $AdminPassword `
        --enable-ad-only-auth false
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ SQL Server admin setup completed!" -ForegroundColor Green
        Write-Host "📋 Configuration:" -ForegroundColor Cyan
        Write-Host "   Server: pei-dashboard.database.windows.net" -ForegroundColor White
        Write-Host "   Admin User: CloudSAa33fbc7c" -ForegroundColor White
        Write-Host "   Password: $AdminPassword" -ForegroundColor White
        Write-Host "   Database: pei-dashboard" -ForegroundColor White
        
        Write-Host "`n💡 Connection string:" -ForegroundColor Yellow
        Write-Host "Driver={ODBC Driver 17 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Uid=CloudSAa33fbc7c;Pwd=$AdminPassword;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;" -ForegroundColor White
        
    } else {
        Write-Error "❌ Failed to setup SQL Server admin"
        Write-Host "💡 You may need to:" -ForegroundColor Yellow
        Write-Host "   1. Check your permissions in Azure" -ForegroundColor White
        Write-Host "   2. Verify the resource group and server names" -ForegroundColor White
        Write-Host "   3. Try setting up through Azure Portal manually" -ForegroundColor White
    }
    
} catch {
    Write-Error "❌ Error: $($_.Exception.Message)"
    Write-Host "💡 Please try setting up SQL admin through Azure Portal" -ForegroundColor Yellow
}