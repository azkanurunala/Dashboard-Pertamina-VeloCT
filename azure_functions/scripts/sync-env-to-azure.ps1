# Sync .env -> Azure Function App App Settings
#
# Reads ../.env and pushes every KEY=VALUE entry to the live Function App
# via `az functionapp config appsettings set`. Skips comments, blank lines,
# and any keys you list in $Skip. Run from azure_functions/ or pass -EnvFile.
#
# Usage:
#   .\scripts\sync-env-to-azure.ps1
#   .\scripts\sync-env-to-azure.ps1 -FunctionAppName pei-dashboard -ResourceGroupName PeiDashboard
#   .\scripts\sync-env-to-azure.ps1 -DryRun
#
# Prereqs: az CLI logged in (`az login`).

param(
    [string]$FunctionAppName  = "pei-dashboard",
    [string]$ResourceGroupName = "PeiDashboard",
    [string]$EnvFile          = ".env",
    [string[]]$Skip           = @(
        "TEST_MODE", "USE_MOCK_SERVICES", "DEBUG_MODE",
        "MOCK_EXTERNAL_SERVICES", "FUNCTIONS_WORKER_PYTHON_PATH",
        "PROPERTY_TEST_ITERATIONS",
        # App Insights settings must come from azure_settings.json or the portal,
        # never from .env (which holds test-only mock values that would break
        # production telemetry). See AZURE_OPENAI_MIGRATION.md for the incident.
        "APPINSIGHTS_INSTRUMENTATIONKEY",
        "APPLICATIONINSIGHTS_CONNECTION_STRING"
    ),
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $EnvFile)) {
    Write-Error "Env file not found: $EnvFile"
    exit 1
}

Write-Host "Reading $EnvFile ..." -ForegroundColor Cyan

$pairs = @()
Get-Content $EnvFile | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $eq = $line.IndexOf("=")
    if ($eq -lt 1) { return }

    $key   = $line.Substring(0, $eq).Trim()
    $value = $line.Substring($eq + 1).Trim()

    # Strip wrapping quotes if present
    if (($value.StartsWith('"') -and $value.EndsWith('"')) -or
        ($value.StartsWith("'") -and $value.EndsWith("'"))) {
        $value = $value.Substring(1, $value.Length - 2)
    }

    if ($Skip -contains $key) {
        Write-Host "  skip   $key" -ForegroundColor DarkGray
        return
    }

    $pairs += "$key=$value"
    $shown = if ($value.Length -gt 0) { "($($value.Length) chars)" } else { "(empty)" }
    Write-Host "  stage  $key $shown" -ForegroundColor Green
}

if ($pairs.Count -eq 0) {
    Write-Warning "No settings to push."
    exit 0
}

Write-Host ""
Write-Host "Target: $FunctionAppName / $ResourceGroupName" -ForegroundColor Yellow
Write-Host "Pushing $($pairs.Count) settings ..." -ForegroundColor Yellow

if ($DryRun) {
    Write-Host "[DRY RUN] would call: az functionapp config appsettings set --name $FunctionAppName --resource-group $ResourceGroupName --settings <$($pairs.Count) pairs>" -ForegroundColor Magenta
    exit 0
}

# Pass settings via a temp JSON file. Going through `az.cmd` with KEY=VALUE
# args breaks for values containing CMD metacharacters (e.g. `&` in passwords),
# because the batch wrapper re-parses arguments before az ever sees them.
$jsonObjects = $pairs | ForEach-Object {
    $eq2 = $_.IndexOf("=")
    @{ name = $_.Substring(0, $eq2); value = $_.Substring($eq2 + 1); slotSetting = $false }
}
$tmpJson = [System.IO.Path]::GetTempFileName() + ".json"
$jsonObjects | ConvertTo-Json -Depth 5 -Compress | Set-Content -Path $tmpJson -Encoding UTF8

try {
    & az functionapp config appsettings set `
        --name $FunctionAppName `
        --resource-group $ResourceGroupName `
        --settings "@$tmpJson" `
        --output none

    if ($LASTEXITCODE -ne 0) {
        Write-Error "az functionapp config appsettings set failed (exit $LASTEXITCODE)"
        exit $LASTEXITCODE
    }
} finally {
    Remove-Item $tmpJson -ErrorAction SilentlyContinue
}

Write-Host "Done." -ForegroundColor Green
