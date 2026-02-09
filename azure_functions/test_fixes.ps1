$functions = @("bps_scraper_function", "bioetanol_esdm_scraper_function", "bisnis_indonesia_scraper_function")
$results = @{}

foreach ($func in $functions) {
    Write-Host "Testing $func..."
    $url = "http://localhost:7071/api/$func"
    try {
        $response = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 45
        $results[$func] = @{
            status = "SUCCESS"
            content = $response
        }
    } catch {
        $results[$func] = @{
            status = "ERROR"
            message = $_.Exception.Message
        }
    }
}

$results | ConvertTo-Json -Depth 5 | Out-File "test_fixes_result.json"
