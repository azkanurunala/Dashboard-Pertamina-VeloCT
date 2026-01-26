# Comprehensive Deployment Script with Blue-Green Strategy
# Orchestrates the complete deployment process with validation and rollback

param(
    [Parameter(Mandatory=$true)]
    [string]$FunctionAppName,
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroupName = "",
    
    [Parameter(Mandatory=$false)]
    [string]$DeploymentSlot = "staging",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipBuild = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipValidation = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$AutoPromote = $false,
    
    [Parameter(Mandatory=$false)]
    [int]$ValidationTimeoutSeconds = 300,
    
    [Parameter(Mandatory=$false)]
    [switch]$WhatIf = $false
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting Comprehensive Deployment with Blue-Green Strategy..." -ForegroundColor Green
Write-Host "Function App: $FunctionAppName" -ForegroundColor Yellow
Write-Host "Deployment Slot: $DeploymentSlot" -ForegroundColor Yellow

# Function to write colored output
function Write-Status {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

# Function to execute script and handle errors
function Invoke-DeploymentScript {
    param(
        [string]$ScriptPath,
        [string]$Arguments,
        [string]$Description
    )
    
    Write-Status "🔧 $Description..." "Blue"
    
    try {
        $command = "& '$ScriptPath' $Arguments"
        Write-Status "Executing: $command" "Gray"
        
        Invoke-Expression $command
        
        if ($LASTEXITCODE -eq 0) {
            Write-Status "✅ $Description completed successfully" "Green"
            return $true
        } else {
            Write-Status "❌ $Description failed with exit code: $LASTEXITCODE" "Red"
            return $false
        }
    } catch {
        Write-Status "❌ $Description failed with exception: $($_.Exception.Message)" "Red"
        return $false
    }
}

# Function to confirm action
function Confirm-Action {
    param([string]$Message)
    
    if ($AutoPromote) {
        Write-Status "$Message (Auto-promote enabled)" "Yellow"
        return $true
    }
    
    Write-Host $Message -ForegroundColor Yellow
    $response = Read-Host "Continue? (y/N)"
    return $response -eq "y" -or $response -eq "Y"
}

# Validate prerequisites
Write-Status "🔍 Validating prerequisites..." "Blue"

# Check if we're in the right directory
if (-not (Test-Path "host.json")) {
    Write-Error "❌ host.json not found. Please run this script from the azure_functions directory."
    exit 1
}

# Check if Azure Functions Core Tools is installed
try {
    $funcVersion = func --version
    Write-Status "✅ Azure Functions Core Tools version: $funcVersion" "Green"
} catch {
    Write-Error "❌ Azure Functions Core Tools is not installed. Please install it first."
    exit 1
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

# What-if mode
if ($WhatIf) {
    Write-Status "🔍 What-If Mode - No actual deployment will occur" "Cyan"
    Write-Status "Would deploy to slot: $DeploymentSlot" "White"
    Write-Status "Would validate deployment in slot" "White"
    Write-Status "Would prompt for promotion to production (unless -AutoPromote)" "White"
    exit 0
}

# Step 1: Deploy to staging slot
Write-Status "`n📦 Step 1: Deploying to $DeploymentSlot slot..." "Cyan"

$deployArgs = "-FunctionAppName '$FunctionAppName'"
if ($ResourceGroupName) {
    $deployArgs += " -ResourceGroupName '$ResourceGroupName'"
}
if ($SkipBuild) {
    $deployArgs += " -BuildLocally"
}

# Deploy to specific slot
try {
    Write-Status "Deploying to $DeploymentSlot slot..." "Blue"
    
    if ($SkipBuild) {
        func azure functionapp publish $FunctionAppName --slot $DeploymentSlot --no-build
    } else {
        func azure functionapp publish $FunctionAppName --slot $DeploymentSlot --build remote
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Status "✅ Deployment to $DeploymentSlot slot successful" "Green"
    } else {
        Write-Error "❌ Deployment to $DeploymentSlot slot failed"
        exit 1
    }
} catch {
    Write-Error "❌ Deployment failed: $($_.Exception.Message)"
    exit 1
}

# Step 2: Validate deployment in slot
Write-Status "`n🧪 Step 2: Validating deployment in $DeploymentSlot slot..." "Cyan"

if (-not $SkipValidation) {
    $validationArgs = "-FunctionAppName '$FunctionAppName' -SlotName '$DeploymentSlot' -TimeoutSeconds $ValidationTimeoutSeconds -Detailed"
    
    $validationSuccess = Invoke-DeploymentScript -ScriptPath "scripts/deployment-validation.ps1" -Arguments $validationArgs -Description "Deployment validation"
    
    if (-not $validationSuccess) {
        Write-Status "❌ Deployment validation failed" "Red"
        Write-Status "Deployment remains in $DeploymentSlot slot and was not promoted to production" "Yellow"
        
        if (Confirm-Action "Would you like to view the deployment logs?") {
            Write-Status "Opening function logs..." "Blue"
            func azure functionapp logstream $FunctionAppName --slot $DeploymentSlot
        }
        
        exit 1
    }
} else {
    Write-Status "⚠️ Validation skipped as requested" "Yellow"
}

# Step 3: Promote to production (Blue-Green swap)
Write-Status "`n🔄 Step 3: Promoting to production..." "Cyan"

$slotUrl = "https://$FunctionAppName-$DeploymentSlot.azurewebsites.net"
$productionUrl = "https://$($appInfo.defaultHostName)"

Write-Status "Staging URL: $slotUrl" "White"
Write-Status "Production URL: $productionUrl" "White"

if (Confirm-Action "Deploy validation passed. Promote $DeploymentSlot to production?") {
    
    # Perform blue-green deployment
    $blueGreenArgs = "-FunctionAppName '$FunctionAppName' -ResourceGroupName '$ResourceGroupName' -SourceSlot '$DeploymentSlot' -TargetSlot 'production'"
    if ($SkipValidation) {
        $blueGreenArgs += " -SkipValidation"
    }
    $blueGreenArgs += " -ValidationTimeoutSeconds $ValidationTimeoutSeconds -AutoRollback"
    
    $promotionSuccess = Invoke-DeploymentScript -ScriptPath "scripts/blue-green-deploy.ps1" -Arguments $blueGreenArgs -Description "Blue-green deployment"
    
    if ($promotionSuccess) {
        Write-Status "🎉 Deployment completed successfully!" "Green"
        
        # Display final summary
        Write-Status "`n📋 Deployment Summary:" "Cyan"
        Write-Status "  Function App: $FunctionAppName" "White"
        Write-Status "  Resource Group: $ResourceGroupName" "White"
        Write-Status "  Deployment Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" "White"
        Write-Status "  Deployed via: $DeploymentSlot slot" "White"
        Write-Status "  Production URL: $productionUrl" "White"
        Write-Status "  Validation: $(if ($SkipValidation) { 'Skipped' } else { 'Passed' })" "White"
        
        # Test production endpoint
        Write-Status "`n🧪 Final production test..." "Blue"
        Start-Sleep -Seconds 10
        
        try {
            $response = Invoke-RestMethod -Uri "$productionUrl/api/test_function" -Method GET -TimeoutSec 30
            if ($response -and $response.status -eq "success") {
                Write-Status "✅ Production endpoint responding correctly" "Green"
                Write-Status "Response: $($response.message)" "White"
            } else {
                Write-Status "⚠️ Production endpoint responded but with unexpected content" "Yellow"
            }
        } catch {
            Write-Status "⚠️ Could not test production endpoint: $($_.Exception.Message)" "Yellow"
            Write-Status "Please test manually at: $productionUrl/api/test_function" "White"
        }
        
    } else {
        Write-Status "❌ Promotion to production failed" "Red"
        Write-Status "Code remains in $DeploymentSlot slot" "Yellow"
        exit 1
    }
    
} else {
    Write-Status "Promotion cancelled by user" "Yellow"
    Write-Status "Deployment remains in $DeploymentSlot slot" "White"
    Write-Status "You can promote later using: .\scripts\blue-green-deploy.ps1 -FunctionAppName '$FunctionAppName' -SourceSlot '$DeploymentSlot'" "White"
}

# Display useful next steps
Write-Status "`n📝 Next Steps:" "Cyan"
Write-Status "1. Monitor production at: $productionUrl" "White"
Write-Status "2. Check Application Insights for metrics and logs" "White"
Write-Status "3. Test all function endpoints thoroughly" "White"
Write-Status "4. Monitor for any issues in the first few hours" "White"

Write-Status "`n🔗 Useful Commands:" "Cyan"
Write-Status "  View logs: func azure functionapp logstream $FunctionAppName" "White"
Write-Status "  List slots: az functionapp deployment slot list --name $FunctionAppName --resource-group $ResourceGroupName" "White"
Write-Status "  Rollback if needed: .\scripts\rollback-deployment.ps1 -FunctionAppName '$FunctionAppName' -TargetSlot '$DeploymentSlot'" "White"
Write-Status "  Validate deployment: .\scripts\deployment-validation.ps1 -FunctionAppName '$FunctionAppName'" "White"

Write-Status "`n✨ Deployment process completed!" "Green"