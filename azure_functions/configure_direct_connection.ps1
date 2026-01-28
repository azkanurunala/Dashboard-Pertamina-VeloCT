# Configure direct database connection string (bypass Key Vault for testing)

$connectionString = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;Uid=CloudSAa33fbc7c;Pwd=uRahcie3&105272;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

Write-Host "Configuring direct database connection string..." -ForegroundColor Cyan

az functionapp config appsettings set `
    --name pei-dashboard `
    --resource-group PeiDashboard `
    --settings "SQL_SERVER_CONNECTION_STRING=$connectionString"

Write-Host "`nRestarting function app..." -ForegroundColor Cyan
az functionapp restart --name pei-dashboard --resource-group PeiDashboard

Write-Host "`nConfiguration complete!" -ForegroundColor Green
Write-Host "You can now test the functions."
