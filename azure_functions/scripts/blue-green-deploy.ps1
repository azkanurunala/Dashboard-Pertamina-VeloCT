# Blue-Green Deployment Script for Azure Functions
# Implements zero-downtime deployment using deployment slots

param(
    [Parameter(Mandatory=$true)]
    [string]$FunctionAppName,
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroupName = "",
    
    [Parameter(Mandatory=$false)]
    [string]$SourceSlot = "staging",
    
    [Parameter(Mandatory=$false)]
    [string]$TargetSlot = "production",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipValidation = $false,
    
    [Parameter(Mandatory=$false)]
    [int]$ValidationTimeoutSeconds = 300,
    
    [Parameter(Mandatory=$false)]
    [switch]$AutoRollback = $true,
    
    [Parameter(Mandatory=$false)]
    [switch]$WhatIf = $false
)

$ErrorActionPreference = "Stop"

Write-Host "🔄 Starting Blue-Green Deployment..." -ForegroundColor Green
Write-Host "Function App: $FunctionAppName" -ForegroundColor Yellow
Write-Host "Source Slot: $SourceSlot" -ForegroundColor Yellow
Write-Host "Target Slot: $TargetSlot" -ForegroundColor Yellow

# Function to write colored output
function Write-Status {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

# Function to test endpoint health
function Test-EndpointHealth {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 30,
        [int]$MaxRetries = 3
    )
    
    $retryCount = 0
    while ($retryCount -lt $MaxRetries) {
        try {
            Write-Status "Testing endpoint: $Url" "Blue"
            $response = Invoke-RestMethod -Uri "$Url/api/test_function" -Method GET -TimeoutSec $TimeoutSeconds
            
            if ($response -and $response.status -eq "success") {
                Write-Status "✅ Endpoint health check passed" "Green"
                return $true
            } else {
                Write-Status "⚠️ Endpoint returned unexpected response" "Yellow"
                Write-Status "Response: $($response | ConvertTo-Json -Compress)" "White"
            }
        } catch {
            Write-Status "❌ Endpoint health check failed: $($_.Exception.Message)" "Red"
        }
        
        $retryCount++
        if ($retryCount -lt $MaxRetries) {
            Write-Status "Retrying in 10 seconds... ($retryCount/$MaxRetries)" "Yellow"
            Start-Sleep -Seconds 10
        }
    }
    
    return $false
}

# Function to validate deployment
function Test-DeploymentValidation {
    param(
        [string]$SlotUrl,
        [int]$TimeoutSeconds = 300
    )
    
    Write-Status "🧪 Running deployment validation..." "Blue"
    
    # Basic health check
    if (-not (Test-EndpointHealth -Url $SlotUrl -TimeoutSeconds 30)) {
        Write-Status "❌ Basic health check failed" "Red"
        return $false
    }
    
    # Extended validation tests
    $validationTests = @(
        @{
            Name = "Database Connection Test"
            Endpoint = "/api/test_function"
            ExpectedStatus = "success"
        }
        # Add more validation tests as needed
    )
    
    foreach ($test in $validationTests) {
        try {
            Write-Status "Running test: $($test.Name)" "Blue"
            $testUrl = "$SlotUrl$($test.Endpoint)"
            $response = Invoke-RestMethod -Uri $testUrl -Method GET -TimeoutSec 30
            
            if ($response.status -eq $test.ExpectedStatus) {
                Write-Status "✅ $($test.Name) passed" "Green"
            } else {
                Write-Status "❌ $($test.Name) failed" "Red"
                Write-Status "Expected: $($test.ExpectedStatus), Got: $($response.status)" "White"
                return $false
            }
        } catch {
            Write-Status "❌ $($test.Name) failed with exception: $($_.Exception.Message)" "Red"
            return $false
        }
    }
    
    Write-Status "✅ All validation tests passed" "Green"
    return $true
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
    
    $ResourceGroupName = $appInfo.resourceGroup
    Write-Status "✅ Function App found in resource group: $ResourceGroupName" "Green"
} catch {
    Write-Error "❌ Failed to retrieve Function App information: $($_.Exception.Message)"
    exit 1
}

# Check if deployment slots exist
Write-Status "🔍 Checking deployment slots..." "Blue"
try {
    $slots = az functionapp deployment slot list --name $FunctionAppName --resource-group $ResourceGroupName --output json | ConvertFrom-Json
    
    $sourceSlotExists = $slots | Where-Object { $_.name -eq $SourceSlot }
    if (-not $sourceSlotExists -and $SourceSlot -ne "production") {
        Write-Error "❌ Source slot '$SourceSlot' not found."
        exit 1
    }
    
    Write-Status "✅ Deployment slots verified" "Green"
} catch {
    Write-Error "❌ Failed to check deployment slots: $($_.Exception.Message)"
    exit 1
}

# Get slot URLs
$productionUrl = "https://$($appInfo.defaultHostName)"
$sourceSlotUrl = if ($SourceSlot -eq "production") { 
    $productionUrl 
} else { 
    "https://$FunctionAppName-$SourceSlot.azurewebsites.net" 
}

Write-Status "Production URL: $productionUrl" "White"
Write-Status "Source Slot URL: $sourceSlotUrl" "White"

# Pre-deployment validation
if (-not $SkipValidation) {
    Write-Status "🔍 Pre-deployment validation..." "Blue"
    
    # Validate source slot
    if (-not (Test-DeploymentValidation -SlotUrl $sourceSlotUrl -TimeoutSeconds $ValidationTimeoutSeconds)) {
        Write-Error "❌ Pre-deployment validation failed for source slot"
        exit 1
    }
    
    Write-Status "✅ Pre-deployment validation passed" "Green"
}

# What-if mode
if ($WhatIf) {
    Write-Status "🔍 What-If Mode - No actual deployment will occur" "Cyan"
    Write-Status "Would swap slots: $SourceSlot -> $TargetSlot" "White"
    Write-Status "Production URL would remain: $productionUrl" "White"
    exit 0
}

# Store current production state for rollback
Write-Status "💾 Storing current production state for rollback..." "Blue"
$rollbackInfo = @{
    Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    FunctionAppName = $FunctionAppName
    ResourceGroupName = $ResourceGroupName
    ProductionUrl = $productionUrl
}

# Perform the slot swap
Write-Status "🔄 Performing slot swap..." "Blue"
try {
    if ($SourceSlot -eq "production") {
        Write-Error "❌ Cannot swap production slot with itself"
        exit 1
    }
    
    Write-Status "Swapping $SourceSlot slot to production..." "Yellow"
    az functionapp deployment slot swap --name $FunctionAppName --resource-group $ResourceGroupName --slot $SourceSlot --target-slot $TargetSlot --output table
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Slot swap failed"
        exit 1
    }
    
    Write-Status "✅ Slot swap completed successfully" "Green"
} catch {
    Write-Error "❌ Slot swap failed: $($_.Exception.Message)"
    exit 1
}

# Post-deployment validation
Write-Status "🧪 Post-deployment validation..." "Blue"
Start-Sleep -Seconds 30  # Wait for swap to settle

$postDeploymentValid = $true
if (-not $SkipValidation) {
    $postDeploymentValid = Test-DeploymentValidation -SlotUrl $productionUrl -TimeoutSeconds $ValidationTimeoutSeconds
}

if (-not $postDeploymentValid) {
    Write-Status "❌ Post-deployment validation failed" "Red"
    
    if ($AutoRollback) {
        Write-Status "🔄 Initiating automatic rollback..." "Yellow"
        try {
            az functionapp deployment slot swap --name $FunctionAppName --resource-group $ResourceGroupName --slot $TargetSlot --target-slot $SourceSlot --output table
            
            if ($LASTEXITCODE -eq 0) {
                Write-Status "✅ Rollback completed successfully" "Green"
                Write-Status "Production has been restored to previous state" "White"
            } else {
                Write-Status "❌ Rollback failed - manual intervention required" "Red"
            }
        } catch {
            Write-Status "❌ Rollback failed: $($_.Exception.Message)" "Red"
            Write-Status "Manual rollback required" "Yellow"
        }
    } else {
        Write-Status "⚠️ Auto-rollback disabled - manual intervention may be required" "Yellow"
    }
    
    exit 1
}

# Deployment successful
Write-Status "🎉 Blue-Green deployment completed successfully!" "Green"

# Display deployment summary
Write-Status "`n📋 Deployment Summary:" "Cyan"
Write-Status "  Function App: $FunctionAppName" "White"
Write-Status "  Resource Group: $ResourceGroupName" "White"
Write-Status "  Deployment Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" "White"
Write-Status "  Source Slot: $SourceSlot" "White"
Write-Status "  Target Slot: $TargetSlot" "White"
Write-Status "  Production URL: $productionUrl" "White"
Write-Status "  Validation: $(if ($SkipValidation) { 'Skipped' } else { 'Passed' })" "White"

# Display useful commands
Write-Status "`n🔗 Useful Commands:" "Cyan"
Write-Status "  View logs: func azure functionapp logstream $FunctionAppName" "White"
Write-Status "  List slots: az functionapp deployment slot list --name $FunctionAppName --resource-group $ResourceGroupName" "White"
Write-Status "  Manual rollback: az functionapp deployment slot swap --name $FunctionAppName --resource-group $ResourceGroupName --slot $TargetSlot --target-slot $SourceSlot" "White"

Write-Status "`n✨ Deployment completed with zero downtime!" "Green"