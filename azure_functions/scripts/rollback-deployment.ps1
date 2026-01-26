# Automated Rollback Script for Azure Functions
# Provides quick rollback capabilities for failed deployments

param(
    [Parameter(Mandatory=$true)]
    [string]$FunctionAppName,
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroupName = "",
    
    [Parameter(Mandatory=$false)]
    [string]$TargetSlot = "staging",
    
    [Parameter(Mandatory=$false)]
    [switch]$Force = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipValidation = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$WhatIf = $false
)

$ErrorActionPreference = "Stop"

Write-Host "🔄 Starting Deployment Rollback..." -ForegroundColor Yellow
Write-Host "Function App: $FunctionAppName" -ForegroundColor White
Write-Host "Target Slot: $TargetSlot" -ForegroundColor White

# Function to write colored output
function Write-Status {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

# Function to confirm action
function Confirm-Action {
    param([string]$Message)
    
    if ($Force) {
        return $true
    }
    
    Write-Host $Message -ForegroundColor Yellow
    $response = Read-Host "Continue? (y/N)"
    return $response -eq "y" -or $response -eq "Y"
}

# Function to test endpoint health
function Test-EndpointHealth {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 30
    )
    
    try {
        $response = Invoke-RestMethod -Uri "$Url/api/test_function" -Method GET -TimeoutSec $TimeoutSeconds
        return $response -and $response.status -eq "success"
    } catch {
        return $false
    }
}

# Check if Azure CLI is installed and user is logged in
try {
    $account = az account show --output json | ConvertFrom-Json
    Write-Status "✅ Logged in as: $($account.user.name)" "Green"
} catch {
    Write-Error "❌ Not logged in to Azure. Please run 'az login' first."
    exit 1
}

# Get Function App information
Write-Status "🔍 Retrieving Function App information..." "Blue"
try {
    $appInfo = az functionapp show --name $FunctionAppName --output json | ConvertFrom-Json
    if (-not $appInfo) {
        Write-Error "❌ Function App '$FunctionAppName' not found."
        exit 1
    }
    
    if (-not $ResourceGroupName) {
        $ResourceGroupName = $appInfo.resourceGroup
    }
    
    Write-Status "✅ Function App found in resource group: $ResourceGroupName" "Green"
} catch {
    Write-Error "❌ Failed to retrieve Function App information: $($_.Exception.Message)"
    exit 1
}

# Check current deployment status
Write-Status "🔍 Checking current deployment status..." "Blue"
try {
    $slots = az functionapp deployment slot list --name $FunctionAppName --resource-group $ResourceGroupName --output json | ConvertFrom-Json
    
    $targetSlotExists = $slots | Where-Object { $_.name -eq $TargetSlot }
    if (-not $targetSlotExists) {
        Write-Error "❌ Target slot '$TargetSlot' not found."
        exit 1
    }
    
    Write-Status "✅ Target slot '$TargetSlot' found" "Green"
} catch {
    Write-Error "❌ Failed to check deployment slots: $($_.Exception.Message)"
    exit 1
}

# Get URLs
$productionUrl = "https://$($appInfo.defaultHostName)"
$targetSlotUrl = "https://$FunctionAppName-$TargetSlot.azurewebsites.net"

Write-Status "Production URL: $productionUrl" "White"
Write-Status "Target Slot URL: $targetSlotUrl" "White"

# Pre-rollback validation
if (-not $SkipValidation) {
    Write-Status "🧪 Pre-rollback validation..." "Blue"
    
    # Check current production health
    Write-Status "Checking current production health..." "Blue"
    $productionHealthy = Test-EndpointHealth -Url $productionUrl
    
    if ($productionHealthy) {
        Write-Status "⚠️ Current production appears to be healthy" "Yellow"
        if (-not (Confirm-Action "Production seems healthy. Are you sure you want to rollback?")) {
            Write-Status "Rollback cancelled by user" "Yellow"
            exit 0
        }
    } else {
        Write-Status "❌ Current production appears unhealthy - rollback justified" "Red"
    }
    
    # Check target slot health
    Write-Status "Checking target slot health..." "Blue"
    $targetHealthy = Test-EndpointHealth -Url $targetSlotUrl
    
    if (-not $targetHealthy) {
        Write-Status "❌ Target slot appears unhealthy" "Red"
        if (-not (Confirm-Action "Target slot may be unhealthy. Continue with rollback?")) {
            Write-Status "Rollback cancelled by user" "Yellow"
            exit 0
        }
    } else {
        Write-Status "✅ Target slot appears healthy" "Green"
    }
}

# What-if mode
if ($WhatIf) {
    Write-Status "🔍 What-If Mode - No actual rollback will occur" "Cyan"
    Write-Status "Would swap production with slot: $TargetSlot" "White"
    Write-Status "Production URL would remain: $productionUrl" "White"
    Write-Status "Previous production code would move to slot: $TargetSlot" "White"
    exit 0
}

# Final confirmation
if (-not (Confirm-Action "⚠️ This will rollback production to the code in '$TargetSlot' slot. Continue?")) {
    Write-Status "Rollback cancelled by user" "Yellow"
    exit 0
}

# Record rollback information
$rollbackInfo = @{
    Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    FunctionAppName = $FunctionAppName
    ResourceGroupName = $ResourceGroupName
    TargetSlot = $TargetSlot
    ProductionUrl = $productionUrl
    InitiatedBy = $account.user.name
}

Write-Status "💾 Recording rollback information..." "Blue"
$rollbackInfo | ConvertTo-Json | Out-File -FilePath "rollback-log-$(Get-Date -Format 'yyyyMMdd-HHmmss').json" -Encoding UTF8

# Perform the rollback (slot swap)
Write-Status "🔄 Performing rollback..." "Red"
try {
    Write-Status "Swapping production with $TargetSlot slot..." "Yellow"
    az functionapp deployment slot swap --name $FunctionAppName --resource-group $ResourceGroupName --slot $TargetSlot --target-slot production --output table
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Rollback failed"
        exit 1
    }
    
    Write-Status "✅ Rollback swap completed" "Green"
} catch {
    Write-Error "❌ Rollback failed: $($_.Exception.Message)"
    exit 1
}

# Post-rollback validation
Write-Status "🧪 Post-rollback validation..." "Blue"
Start-Sleep -Seconds 30  # Wait for swap to settle

if (-not $SkipValidation) {
    $postRollbackHealthy = Test-EndpointHealth -Url $productionUrl -TimeoutSeconds 60
    
    if ($postRollbackHealthy) {
        Write-Status "✅ Post-rollback validation passed" "Green"
    } else {
        Write-Status "❌ Post-rollback validation failed" "Red"
        Write-Status "⚠️ Production may still be unhealthy after rollback" "Yellow"
        Write-Status "Manual investigation required" "Yellow"
    }
} else {
    Write-Status "⚠️ Post-rollback validation skipped" "Yellow"
}

# Rollback completed
Write-Status "🎉 Rollback completed!" "Green"

# Display rollback summary
Write-Status "`n📋 Rollback Summary:" "Cyan"
Write-Status "  Function App: $FunctionAppName" "White"
Write-Status "  Resource Group: $ResourceGroupName" "White"
Write-Status "  Rollback Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" "White"
Write-Status "  Rolled back from: production" "White"
Write-Status "  Rolled back to: $TargetSlot slot content" "White"
Write-Status "  Production URL: $productionUrl" "White"
Write-Status "  Initiated by: $($account.user.name)" "White"

# Display next steps
Write-Status "`n📝 Next Steps:" "Cyan"
Write-Status "1. Verify production functionality at: $productionUrl" "White"
Write-Status "2. Investigate the root cause of the original deployment issue" "White"
Write-Status "3. Fix the issues in the development/staging environment" "White"
Write-Status "4. Test thoroughly before the next deployment" "White"
Write-Status "5. Review rollback log: rollback-log-$(Get-Date -Format 'yyyyMMdd-HHmmss').json" "White"

# Display useful commands
Write-Status "`n🔗 Useful Commands:" "Cyan"
Write-Status "  View logs: func azure functionapp logstream $FunctionAppName" "White"
Write-Status "  List slots: az functionapp deployment slot list --name $FunctionAppName --resource-group $ResourceGroupName" "White"
Write-Status "  Validate deployment: .\deployment-validation.ps1 -FunctionAppName $FunctionAppName" "White"

Write-Status "`n✅ Rollback process completed!" "Green"