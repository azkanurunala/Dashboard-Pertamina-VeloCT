$url = "http://localhost:7071/api/health_check_function"
try {
    $response = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 5
    $response | ConvertTo-Json | Out-File "test_ps_result.json"
} catch {
    $err = @{
        status = "ERROR"
        message = $_.Exception.Message
    }
    $err | ConvertTo-Json | Out-File "test_ps_result.json"
}
