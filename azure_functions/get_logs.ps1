# Get Azure Function App logs

Write-Host "Fetching Application Insights logs..." -ForegroundColor Cyan
Write-Host ""

# Get the most recent logs
az monitor app-insights query `
    --app pei-dashboard `
    --resource-group PeiDashboard `
    --analytics-query "traces | where timestamp > ago(30m) | order by timestamp desc | take 50 | project timestamp, message, severityLevel" `
    --output table

Write-Host ""
Write-Host "If no logs appear above, check the Azure Portal:" -ForegroundColor Yellow
Write-Host "https://portal.azure.com -> pei-dashboard -> Log stream" -ForegroundColor White
