# Update Production Schedules for Azure Functions
# This script updates timer schedules from testing to production values

param(
    [Parameter(Mandatory=$false)]
    [string]$FunctionAppName = "pei-dashboard",
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroupName = "PeiDashboard"
)

Write-Host "🔧 Updating Production Schedules for Azure Functions..." -ForegroundColor Cyan
Write-Host ""

# Current schedules (TESTING - runs at 6:10, 6:15, 6:20, 6:25 AM)
Write-Host "❌ Current Testing Schedules:" -ForegroundColor Red
Write-Host "   MORNING_TIMER_SCHEDULE: 0 10 6 * * * (6:10 AM daily)" -ForegroundColor Yellow
Write-Host "   AFTERNOON_TIMER_SCHEDULE: 0 15 6 * * * (6:15 AM daily)" -ForegroundColor Yellow
Write-Host "   WEEKLY_TIMER_SCHEDULE: 0 20 6 * * * (6:20 AM daily)" -ForegroundColor Yellow
Write-Host "   MONTHLY_TIMER_SCHEDULE: 0 25 6 * * * (6:25 AM daily)" -ForegroundColor Yellow
Write-Host ""

# Proposed production schedules
Write-Host "✅ Schedules to be Applied:" -ForegroundColor Green
Write-Host "   MORNING_TIMER_SCHEDULE: 0 50 6 * * * (6:50 AM daily)" -ForegroundColor Cyan
Write-Host "   AFTERNOON_TIMER_SCHEDULE: 0 55 6 * * * (6:55 AM daily)" -ForegroundColor Cyan
Write-Host "   WEEKLY_TIMER_SCHEDULE: 0 0 7 * * * (7:00 AM daily)" -ForegroundColor Cyan
Write-Host "   MONTHLY_TIMER_SCHEDULE: 0 5 7 * * * (7:05 AM daily)" -ForegroundColor Cyan
Write-Host ""

Write-Host "⚠️  IMPORTANT: Please confirm these schedules are correct!" -ForegroundColor Yellow
Write-Host ""
Write-Host "Cron Format: second minute hour day month dayOfWeek" -ForegroundColor Gray
Write-Host "Example: '0 0 6 * * *' = 6:00 AM every day" -ForegroundColor Gray
Write-Host "Example: '0 0 14 * * *' = 2:00 PM every day" -ForegroundColor Gray
Write-Host "Example: '0 0 8 * * 1' = 8:00 AM every Monday" -ForegroundColor Gray
Write-Host "Example: '0 0 9 1 * *' = 9:00 AM on 1st of every month" -ForegroundColor Gray
Write-Host ""

$response = Read-Host "Do you want to proceed with these schedules? (y/N)"

if ($response -ne "y" -and $response -ne "Y") {
    Write-Host "❌ Update cancelled. Please edit this script with correct schedules." -ForegroundColor Red
    Write-Host ""
    Write-Host "To customize schedules, edit the variables below in this script:" -ForegroundColor Yellow
    Write-Host "   `$morningSchedule = '0 0 6 * * *'" -ForegroundColor White
    Write-Host "   `$afternoonSchedule = '0 0 14 * * *'" -ForegroundColor White
    Write-Host "   `$weeklySchedule = '0 0 8 * * 1'" -ForegroundColor White
    Write-Host "   `$monthlySchedule = '0 0 9 1 * *'" -ForegroundColor White
    exit 0
}

Write-Host ""
Write-Host "🚀 Updating schedules in Azure..." -ForegroundColor Blue

# Production schedules
# CUSTOMIZE THESE VALUES IF NEEDED:
$morningSchedule = "0 50 6 * * *"     # 6:50 AM daily
$afternoonSchedule = "0 55 6 * * *"   # 6:55 AM daily
$weeklySchedule = "0 0 7 * * *"       # 7:00 AM daily (runs every day for testing)
$monthlySchedule = "0 5 7 * * *"      # 7:05 AM daily (runs every day for testing)

try {
    # Update MORNING_TIMER_SCHEDULE
    Write-Host "Updating MORNING_TIMER_SCHEDULE..." -ForegroundColor Yellow
    az functionapp config appsettings set --name $FunctionAppName --resource-group $ResourceGroupName --settings "MORNING_TIMER_SCHEDULE=$morningSchedule" --output none
    Write-Host "✅ MORNING_TIMER_SCHEDULE updated" -ForegroundColor Green
    
    # Update AFTERNOON_TIMER_SCHEDULE
    Write-Host "Updating AFTERNOON_TIMER_SCHEDULE..." -ForegroundColor Yellow
    az functionapp config appsettings set --name $FunctionAppName --resource-group $ResourceGroupName --settings "AFTERNOON_TIMER_SCHEDULE=$afternoonSchedule" --output none
    Write-Host "✅ AFTERNOON_TIMER_SCHEDULE updated" -ForegroundColor Green
    
    # Update WEEKLY_TIMER_SCHEDULE
    Write-Host "Updating WEEKLY_TIMER_SCHEDULE..." -ForegroundColor Yellow
    az functionapp config appsettings set --name $FunctionAppName --resource-group $ResourceGroupName --settings "WEEKLY_TIMER_SCHEDULE=$weeklySchedule" --output none
    Write-Host "✅ WEEKLY_TIMER_SCHEDULE updated" -ForegroundColor Green
    
    # Update MONTHLY_TIMER_SCHEDULE
    Write-Host "Updating MONTHLY_TIMER_SCHEDULE..." -ForegroundColor Yellow
    az functionapp config appsettings set --name $FunctionAppName --resource-group $ResourceGroupName --settings "MONTHLY_TIMER_SCHEDULE=$monthlySchedule" --output none
    Write-Host "✅ MONTHLY_TIMER_SCHEDULE updated" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "🎉 All schedules updated successfully!" -ForegroundColor Green
    
} catch {
    Write-Host "❌ Error updating schedules: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🔍 Verifying updated schedules..." -ForegroundColor Blue

try {
    $settings = az functionapp config appsettings list --name $FunctionAppName --resource-group $ResourceGroupName --output json | ConvertFrom-Json
    
    $morningValue = ($settings | Where-Object { $_.name -eq "MORNING_TIMER_SCHEDULE" }).value
    $afternoonValue = ($settings | Where-Object { $_.name -eq "AFTERNOON_TIMER_SCHEDULE" }).value
    $weeklyValue = ($settings | Where-Object { $_.name -eq "WEEKLY_TIMER_SCHEDULE" }).value
    $monthlyValue = ($settings | Where-Object { $_.name -eq "MONTHLY_TIMER_SCHEDULE" }).value
    
    Write-Host ""
    Write-Host "✅ Current Schedules in Azure:" -ForegroundColor Green
    Write-Host "   MORNING_TIMER_SCHEDULE: $morningValue" -ForegroundColor White
    Write-Host "   AFTERNOON_TIMER_SCHEDULE: $afternoonValue" -ForegroundColor White
    Write-Host "   WEEKLY_TIMER_SCHEDULE: $weeklyValue" -ForegroundColor White
    Write-Host "   MONTHLY_TIMER_SCHEDULE: $monthlyValue" -ForegroundColor White
    
} catch {
    Write-Host "⚠️  Could not verify schedules, but update was successful" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "📝 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Restart the Function App to apply changes:" -ForegroundColor White
Write-Host "   az functionapp restart --name $FunctionAppName --resource-group $ResourceGroupName" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Monitor timer functions in Azure Portal:" -ForegroundColor White
Write-Host "   Portal → Function App → Functions → [timer function] → Monitor" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Check next scheduled run:" -ForegroundColor White
Write-Host "   Portal → Function App → Functions → [timer function] → Code + Test → Logs" -ForegroundColor Gray

Write-Host ""
Write-Host "✨ Schedule update completed!" -ForegroundColor Green
