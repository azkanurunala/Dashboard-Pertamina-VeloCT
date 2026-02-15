# Quick Function Status Check
# Monitors Azure Functions without log stream

param(
    [Parameter(Mandatory=$false)]
    [string]$FunctionAppName = "pei-dashboard",
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroupName = "PeiDashboard",
    
    [Parameter(Mandatory=$false)]
    [string]$AppInsightsId = "9db8826b-a342-44c5-973d-a045bac44ee2"
)

Write-Host "📊 Azure Functions Status Check" -ForegroundColor Cyan
Write-Host "Function App: $FunctionAppName" -ForegroundColor White
Write-Host "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor White
Write-Host ""
Write-Host "=" * 70 -ForegroundColor Gray
Write-Host ""

# 1. Check Function App Status
Write-Host "1️⃣  Function App Status" -ForegroundColor Yellow
Write-Host "-" * 70 -ForegroundColor Gray
try {
    $appStatus = az functionapp show --name $FunctionAppName --resource-group $ResourceGroupName --output json | ConvertFrom-Json
    
    if ($appStatus.state -eq "Running") {
        Write-Host "   ✅ Status: Running" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Status: $($appStatus.state)" -ForegroundColor Yellow
    }
    
    Write-Host "   Location: $($appStatus.location)" -ForegroundColor White
    Write-Host "   URL: https://$($appStatus.defaultHostName)" -ForegroundColor White
} catch {
    Write-Host "   ❌ Could not retrieve app status" -ForegroundColor Red
}

Write-Host ""

# 2. Check Timer Schedules
Write-Host "2️⃣  Timer Schedules Configuration" -ForegroundColor Yellow
Write-Host "-" * 70 -ForegroundColor Gray
try {
    $settings = az functionapp config appsettings list --name $FunctionAppName --resource-group $ResourceGroupName --output json | ConvertFrom-Json
    
    $morningSchedule = ($settings | Where-Object { $_.name -eq "MORNING_TIMER_SCHEDULE" }).value
    $afternoonSchedule = ($settings | Where-Object { $_.name -eq "AFTERNOON_TIMER_SCHEDULE" }).value
    $weeklySchedule = ($settings | Where-Object { $_.name -eq "WEEKLY_TIMER_SCHEDULE" }).value
    $monthlySchedule = ($settings | Where-Object { $_.name -eq "MONTHLY_TIMER_SCHEDULE" }).value
    
    if ($morningSchedule) {
        Write-Host "   ✅ MORNING_TIMER_SCHEDULE: $morningSchedule" -ForegroundColor Green
    } else {
        Write-Host "   ❌ MORNING_TIMER_SCHEDULE: NOT SET" -ForegroundColor Red
    }
    
    if ($afternoonSchedule) {
        Write-Host "   ✅ AFTERNOON_TIMER_SCHEDULE: $afternoonSchedule" -ForegroundColor Green
    } else {
        Write-Host "   ❌ AFTERNOON_TIMER_SCHEDULE: NOT SET" -ForegroundColor Red
    }
    
    if ($weeklySchedule) {
        Write-Host "   ✅ WEEKLY_TIMER_SCHEDULE: $weeklySchedule" -ForegroundColor Green
    } else {
        Write-Host "   ❌ WEEKLY_TIMER_SCHEDULE: NOT SET" -ForegroundColor Red
    }
    
    if ($monthlySchedule) {
        Write-Host "   ✅ MONTHLY_TIMER_SCHEDULE: $monthlySchedule" -ForegroundColor Green
    } else {
        Write-Host "   ❌ MONTHLY_TIMER_SCHEDULE: NOT SET" -ForegroundColor Red
    }
    
    # Convert UTC to WIB for display
    Write-Host ""
    Write-Host "   📅 Schedule in WIB (UTC+7):" -ForegroundColor Cyan
    if ($morningSchedule -match "0 0 22") {
        Write-Host "      Morning: 05:00 WIB (22:00 UTC)" -ForegroundColor White
    }
    if ($afternoonSchedule -match "0 10 22") {
        Write-Host "      Afternoon: 05:10 WIB (22:10 UTC)" -ForegroundColor White
    }
    if ($weeklySchedule -match "0 20 22") {
        Write-Host "      Weekly: 05:20 WIB (22:20 UTC)" -ForegroundColor White
    }
    if ($monthlySchedule -match "0 30 22") {
        Write-Host "      Monthly: 05:30 WIB (22:30 UTC)" -ForegroundColor White
    }
    
} catch {
    Write-Host "   ❌ Could not retrieve schedules" -ForegroundColor Red
}

Write-Host ""

# 3. Check Recent Executions (via Application Insights)
Write-Host "3️⃣  Recent Function Executions (Last 1 Hour)" -ForegroundColor Yellow
Write-Host "-" * 70 -ForegroundColor Gray
try {
    $query = "requests | where timestamp > ago(1h) | where name contains 'timer' or name contains 'scraper' | project timestamp, name, success, duration | order by timestamp desc | take 10"
    
    Write-Host "   Querying Application Insights..." -ForegroundColor Gray
    $executions = az monitor app-insights query --app $AppInsightsId --analytics-query $query --output json 2>$null | ConvertFrom-Json
    
    if ($executions.tables[0].rows.Count -gt 0) {
        Write-Host "   ✅ Found $($executions.tables[0].rows.Count) executions" -ForegroundColor Green
        Write-Host ""
        
        foreach ($row in $executions.tables[0].rows | Select-Object -First 5) {
            $timestamp = $row[0]
            $name = $row[1]
            $success = $row[2]
            $duration = [math]::Round($row[3], 2)
            
            $statusIcon = if ($success) { "✅" } else { "❌" }
            $statusColor = if ($success) { "Green" } else { "Red" }
            
            Write-Host "   $statusIcon $timestamp - $name ($duration ms)" -ForegroundColor $statusColor
        }
    } else {
        Write-Host "   ℹ️  No executions found in last hour" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ⚠️  Could not query Application Insights" -ForegroundColor Yellow
    Write-Host "   Use Azure Portal for detailed monitoring" -ForegroundColor Gray
}

Write-Host ""

# 4. Check for Recent Errors
Write-Host "4️⃣  Recent Errors (Last 24 Hours)" -ForegroundColor Yellow
Write-Host "-" * 70 -ForegroundColor Gray
try {
    $errorQuery = "exceptions | where timestamp > ago(24h) | project timestamp, operation_Name, outerMessage | order by timestamp desc | take 5"
    
    $errors = az monitor app-insights query --app $AppInsightsId --analytics-query $errorQuery --output json 2>$null | ConvertFrom-Json
    
    if ($errors.tables[0].rows.Count -gt 0) {
        Write-Host "   ⚠️  Found $($errors.tables[0].rows.Count) errors" -ForegroundColor Red
        Write-Host ""
        
        foreach ($row in $errors.tables[0].rows) {
            $timestamp = $row[0]
            $operation = $row[1]
            $message = $row[2]
            
            Write-Host "   ❌ $timestamp" -ForegroundColor Red
            Write-Host "      Function: $operation" -ForegroundColor White
            Write-Host "      Error: $message" -ForegroundColor Gray
            Write-Host ""
        }
    } else {
        Write-Host "   ✅ No errors found in last 24 hours" -ForegroundColor Green
    }
} catch {
    Write-Host "   ⚠️  Could not query errors" -ForegroundColor Yellow
}

Write-Host ""

# 5. Function Count
Write-Host "5️⃣  Deployed Functions" -ForegroundColor Yellow
Write-Host "-" * 70 -ForegroundColor Gray
try {
    $functions = az functionapp function list --name $FunctionAppName --resource-group $ResourceGroupName --output json | ConvertFrom-Json
    
    $scrapers = ($functions | Where-Object { $_.name -like "*scraper*" }).Count
    $timers = ($functions | Where-Object { $_.name -like "*timer*" }).Count
    $utilities = $functions.Count - $scrapers - $timers
    
    Write-Host "   ✅ Total Functions: $($functions.Count)" -ForegroundColor Green
    Write-Host "      - Scrapers: $scrapers" -ForegroundColor White
    Write-Host "      - Timers: $timers" -ForegroundColor White
    Write-Host "      - Utilities: $utilities" -ForegroundColor White
} catch {
    Write-Host "   ❌ Could not list functions" -ForegroundColor Red
}

Write-Host ""
Write-Host "=" * 70 -ForegroundColor Gray
Write-Host ""

# Summary
Write-Host "📋 Summary" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Quick monitoring completed!" -ForegroundColor Green
Write-Host ""
Write-Host "🔗 For detailed monitoring, visit:" -ForegroundColor Yellow
Write-Host "   Azure Portal: https://portal.azure.com" -ForegroundColor White
Write-Host "   Function App: https://portal.azure.com/#@/resource/subscriptions/5e4ecee4-ce42-47f4-b953-7f29ad625c53/resourceGroups/PeiDashboard/providers/Microsoft.Web/sites/pei-dashboard" -ForegroundColor White
Write-Host ""
Write-Host "📊 Monitoring Options:" -ForegroundColor Yellow
Write-Host "   1. Azure Portal → pei-dashboard → Functions → [function] → Monitor" -ForegroundColor White
Write-Host "   2. Azure Portal → Application Insights → Logs" -ForegroundColor White
Write-Host "   3. Azure Portal → pei-dashboard → Metrics" -ForegroundColor White
Write-Host ""
