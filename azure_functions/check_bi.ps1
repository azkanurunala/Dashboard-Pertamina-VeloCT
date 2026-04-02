$url = "https://www.bi.go.id/id/publikasi/ruang-media/news-release/Default.aspx"
$userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
Write-Host "Testing connectivity to $url"
try {
    $resp = Invoke-WebRequest -Uri $url -Method Get -UserAgent $userAgent -TimeoutSec 15
    Write-Host "Status: $($resp.StatusCode)"
    Write-Host "Content Length: $($resp.Content.Length)"
} catch {
    Write-Host "Failed: $($_.Exception.Message)"
    if ($_.Exception.InnerException) {
        Write-Host "Inner: $($_.Exception.InnerException.Message)"
    }
}
