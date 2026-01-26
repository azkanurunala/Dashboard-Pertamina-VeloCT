# Script to reset SQL Server admin password
# Requires Azure CLI to be installed and logged in

param(
    [Parameter(Mandatory=$true)]
    [string]$NewPassword
)

Write-Host "🔧 Resetting SQL Server admin password..." -ForegroundColor Blue

try {
    # Reset the password
    az sql server update `
        --name "pei-dashboard" `
        --resource-group "PeiDashboard" `
        --admin-password $NewPassword
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Password reset successfully!" -ForegroundColor Green
        Write-Host "💡 New password: $NewPassword" -ForegroundColor Yellow
        Write-Host "⚠️ Please update your connection strings" -ForegroundColor Yellow
    } else {
        Write-Error "❌ Failed to reset password"
    }
} catch {
    Write-Error "❌ Error: $($_.Exception.Message)"
    Write-Host "💡 Make sure Azure CLI is installed and you're logged in: az login" -ForegroundColor Yellow
}