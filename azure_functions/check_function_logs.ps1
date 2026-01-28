# Check Azure Function logs for errors

Write-Host "Fetching recent function logs..." -ForegroundColor Cyan
Write-Host ""

az functionapp log tail --name pei-dashboard --resource-group PeiDashboard --timeout 5
