# Deployment Validation Script
# Comprehensive validation for Azure Functions deployment

param(
    [Parameter(Mandatory=$true)]
    [string]$FunctionAppName,
    
    [Parameter(Mandatory=$false)]
    [string]$SlotName = "production",
    
    [Parameter(Mandatory=$false)]
    [int]$TimeoutSeconds = 300,
    
    [Parameter(Mandatory=$false)]
    [switch]$Detailed = $false,
    
    [Parameter(Mandatory=$false)]
    [string]$ConfigFile = ""
)

$ErrorActionPreference = "Stop"

Write-Host "🧪 Starting Deployment Validation..." -ForegroundColor Green
Write-Host "Function App: $FunctionAppName" -ForegroundColor Yellow
Write-Host "Slot: $SlotName" -ForegroundColor Yellow

# Function to write colored output
function Write-Status {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

# Function to test HTTP endpoint
function Test-HttpEndpoint {
    param(
        [string]$Url,
        [string]$Method = "GET",
        [hashtable]$Headers = @{},
        [string]$Body = "",
        [int]$TimeoutSeconds = 30,
        [int]$MaxRetries = 3
    )
    
    $retryCount = 0
    while ($retryCount -lt $MaxRetries) {
        try {
            $params = @{
                Uri = $Url
                Method = $Method
                TimeoutSec = $TimeoutSeconds
            }
            
            if ($Headers.Count -gt 0) {
                $params.Headers = $Headers
            }
            
            if ($Body -ne "") {
                $params.Body = $Body
                $params.ContentType = "application/json"
            }
            
            $response = Invoke-RestMethod @params
            return @{
                Success = $true
                Response = $response
                StatusCode = 200
                Error = $null
            }
        } catch {
            $statusCode = if ($_.Exception.Response) { $_.Exception.Response.StatusCode } else { "Unknown" }
            $error = $_.Exception.Message
            
            if ($retryCount -eq $MaxRetries - 1) {
                return @{
                    Success = $false
                    Response = $null
                    StatusCode = $statusCode
                    Error = $error
                }
            }
        }
        
        $retryCount++
        Start-Sleep -Seconds 5
    }
}

# Function to validate database connectivity
function Test-DatabaseConnectivity {
    param([string]$BaseUrl)
    
    Write-Status "Testing database connectivity..." "Blue"
    
    $result = Test-HttpEndpoint -Url "$BaseUrl/api/test_function" -TimeoutSeconds 30
    
    if ($result.Success) {
        if ($result.Response.database_status -and $result.Response.database_status -ne "Database configuration not found") {
            Write-Status "✅ Database connectivity test passed" "Green"
            return $true
        } else {
            Write-Status "⚠️ Database configuration issue detected" "Yellow"
            Write-Status "Status: $($result.Response.database_status)" "White"
            return $false
        }
    } else {
        Write-Status "❌ Database connectivity test failed" "Red"
        Write-Status "Error: $($result.Error)" "White"
        return $false
    }
}

# Function to validate function app configuration
function Test-FunctionAppConfiguration {
    param([string]$FunctionAppName, [string]$SlotName, [string]$ResourceGroupName)
    
    Write-Status "Validating Function App configuration..." "Blue"
    
    try {
        # Get app settings
        $slotParam = if ($SlotName -ne "production") { "--slot $SlotName" } else { "" }
        $settingsJson = if ($slotParam) {
            az functionapp config appsettings list --name $FunctionAppName --resource-group $ResourceGroupName --slot $SlotName --output json
        } else {
            az functionapp config appsettings list --name $FunctionAppName --resource-group $ResourceGroupName --output json
        }
        
        $settings = $settingsJson | ConvertFrom-Json
        
        # Required settings
        $requiredSettings = @(
            "AzureWebJobsStorage",
            "FUNCTIONS_EXTENSION_VERSION",
            "FUNCTIONS_WORKER_RUNTIME",
            "SQL_SERVER_CONNECTION_STRING",
            "AZURE_KEY_VAULT_URL",
            "APPLICATIONINSIGHTS_CONNECTION_STRING"
        )
        
        $missingSettings = @()
        foreach ($setting in $requiredSettings) {
            $found = $settings | Where-Object { $_.name -eq $setting }
            if (-not $found) {
                $missingSettings += $setting
            }
        }
        
        if ($missingSettings.Count -eq 0) {
            Write-Status "✅ All required configuration settings present" "Green"
            return $true
        } else {
            Write-Status "❌ Missing required configuration settings:" "Red"
            foreach ($missing in $missingSettings) {
                Write-Status "  - $missing" "White"
            }
            return $false
        }
    } catch {
        Write-Status "❌ Failed to validate configuration: $($_.Exception.Message)" "Red"
        return $false
    }
}

# Function to test function endpoints
function Test-FunctionEndpoints {
    param([string]$BaseUrl)
    
    Write-Status "Testing function endpoints..." "Blue"
    
    # Get function list
    try {
        $functionsResult = Test-HttpEndpoint -Url "$BaseUrl/admin/functions" -TimeoutSeconds 30
        
        if (-not $functionsResult.Success) {
            Write-Status "⚠️ Could not retrieve function list (this may be normal)" "Yellow"
            # Test known endpoints instead
            $testEndpoints = @("/api/test_function")
        } else {
            $functions = $functionsResult.Response
            $testEndpoints = $functions | ForEach-Object { "/api/$($_.name)" }
        }
        
        $passedTests = 0
        $totalTests = $testEndpoints.Count
        
        foreach ($endpoint in $testEndpoints) {
            $result = Test-HttpEndpoint -Url "$BaseUrl$endpoint" -TimeoutSeconds 30
            
            if ($result.Success) {
                Write-Status "✅ $endpoint - OK" "Green"
                $passedTests++
            } else {
                Write-Status "❌ $endpoint - Failed ($($result.StatusCode))" "Red"
                if ($Detailed) {
                    Write-Status "  Error: $($result.Error)" "White"
                }
            }
        }
        
        $successRate = if ($totalTests -gt 0) { ($passedTests / $totalTests) * 100 } else { 0 }
        Write-Status "Endpoint test results: $passedTests/$totalTests passed ($([math]::Round($successRate, 1))%)" "White"
        
        return $successRate -ge 80  # 80% success rate threshold
    } catch {
        Write-Status "❌ Failed to test function endpoints: $($_.Exception.Message)" "Red"
        return $false
    }
}

# Function to test performance
function Test-Performance {
    param([string]$BaseUrl)
    
    Write-Status "Testing performance..." "Blue"
    
    $testUrl = "$BaseUrl/api/test_function"
    $responseTimes = @()
    $testCount = 5
    
    for ($i = 1; $i -le $testCount; $i++) {
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        $result = Test-HttpEndpoint -Url $testUrl -TimeoutSeconds 30
        $stopwatch.Stop()
        
        if ($result.Success) {
            $responseTimes += $stopwatch.ElapsedMilliseconds
            Write-Status "Test $i/$testCount - $($stopwatch.ElapsedMilliseconds)ms" "White"
        } else {
            Write-Status "Test $i/$testCount - Failed" "Red"
        }
    }
    
    if ($responseTimes.Count -gt 0) {
        $avgResponseTime = ($responseTimes | Measure-Object -Average).Average
        $maxResponseTime = ($responseTimes | Measure-Object -Maximum).Maximum
        
        Write-Status "Average response time: $([math]::Round($avgResponseTime, 0))ms" "White"
        Write-Status "Maximum response time: $maxResponseTime ms" "White"
        
        # Performance thresholds
        $performanceGood = $avgResponseTime -lt 2000 -and $maxResponseTime -lt 5000
        
        if ($performanceGood) {
            Write-Status "✅ Performance test passed" "Green"
        } else {
            Write-Status "⚠️ Performance test warning - response times may be high" "Yellow"
        }
        
        return $performanceGood
    } else {
        Write-Status "❌ Performance test failed - no successful requests" "Red"
        return $false
    }
}

# Main validation logic
Write-Status "🔍 Getting Function App information..." "Blue"

try {
    $appInfo = az functionapp show --name $FunctionAppName --output json | ConvertFrom-Json
    if (-not $appInfo) {
        Write-Error "❌ Function App '$FunctionAppName' not found."
        exit 1
    }
    
    $resourceGroupName = $appInfo.resourceGroup
    Write-Status "✅ Function App found in resource group: $resourceGroupName" "Green"
} catch {
    Write-Error "❌ Failed to retrieve Function App information: $($_.Exception.Message)"
    exit 1
}

# Determine base URL
$baseUrl = if ($SlotName -eq "production") {
    "https://$($appInfo.defaultHostName)"
} else {
    "https://$FunctionAppName-$SlotName.azurewebsites.net"
}

Write-Status "Testing URL: $baseUrl" "White"

# Run validation tests
$validationResults = @{}

Write-Status "`n🧪 Running validation tests..." "Cyan"

# Test 1: Basic connectivity
Write-Status "`n1. Basic Connectivity Test" "Cyan"
$connectivityResult = Test-HttpEndpoint -Url "$baseUrl/api/test_function" -TimeoutSeconds 30
$validationResults["Connectivity"] = $connectivityResult.Success

if ($connectivityResult.Success) {
    Write-Status "✅ Basic connectivity test passed" "Green"
} else {
    Write-Status "❌ Basic connectivity test failed" "Red"
    Write-Status "Error: $($connectivityResult.Error)" "White"
}

# Test 2: Configuration validation
Write-Status "`n2. Configuration Validation" "Cyan"
$configResult = Test-FunctionAppConfiguration -FunctionAppName $FunctionAppName -SlotName $SlotName -ResourceGroupName $resourceGroupName
$validationResults["Configuration"] = $configResult

# Test 3: Database connectivity
Write-Status "`n3. Database Connectivity Test" "Cyan"
$dbResult = Test-DatabaseConnectivity -BaseUrl $baseUrl
$validationResults["Database"] = $dbResult

# Test 4: Function endpoints
Write-Status "`n4. Function Endpoints Test" "Cyan"
$endpointsResult = Test-FunctionEndpoints -BaseUrl $baseUrl
$validationResults["Endpoints"] = $endpointsResult

# Test 5: Performance test (if detailed)
if ($Detailed) {
    Write-Status "`n5. Performance Test" "Cyan"
    $performanceResult = Test-Performance -BaseUrl $baseUrl
    $validationResults["Performance"] = $performanceResult
}

# Summary
Write-Status "`n📊 Validation Summary:" "Cyan"
$passedTests = 0
$totalTests = $validationResults.Count

foreach ($test in $validationResults.GetEnumerator()) {
    $status = if ($test.Value) { "✅ PASSED" } else { "❌ FAILED" }
    $color = if ($test.Value) { "Green" } else { "Red" }
    Write-Status "  $($test.Key): $status" $color
    
    if ($test.Value) {
        $passedTests++
    }
}

$successRate = ($passedTests / $totalTests) * 100
Write-Status "`nOverall Result: $passedTests/$totalTests tests passed ($([math]::Round($successRate, 1))%)" "White"

if ($successRate -ge 80) {
    Write-Status "🎉 Deployment validation PASSED" "Green"
    exit 0
} else {
    Write-Status "❌ Deployment validation FAILED" "Red"
    Write-Status "Please review the failed tests and fix issues before proceeding" "Yellow"
    exit 1
}