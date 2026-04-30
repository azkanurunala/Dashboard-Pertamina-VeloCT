# Connection string loaded from SQL_SERVER_CONNECTION_STRING env var (or local.settings.json Values).
$conn_str = $env:SQL_SERVER_CONNECTION_STRING
if (-not $conn_str) {
    $settingsPath = Join-Path $PSScriptRoot "local.settings.json"
    if (Test-Path $settingsPath) {
        $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
        $conn_str = $settings.Values.SQL_SERVER_CONNECTION_STRING
    }
}
if (-not $conn_str) {
    throw "SQL_SERVER_CONNECTION_STRING is not set (env var or local.settings.json Values.SQL_SERVER_CONNECTION_STRING)."
}

$conn = New-Object System.Data.SqlClient.SqlConnection($conn_str)
$conn.Open()
$cmd = $conn.CreateCommand()
$cmd.CommandText = "SELECT COUNT(*) FROM news_articles WHERE category = 'indeks kepercayaan knsmn'"
$count = $cmd.ExecuteScalar()

$cmd2 = $conn.CreateCommand()
$cmd2.CommandText = "SELECT category, COUNT(*) FROM news_articles WHERE LOWER(category) LIKE '%indeks%' OR LOWER(category) LIKE '%knsmn%' OR LOWER(category) LIKE '%konsumen%' OR LOWER(category) LIKE '%ikk%' GROUP BY category"
$reader = $cmd2.ExecuteReader()
$output = "Total articles with category 'indeks kepercayaan knsmn': $count`nSimilar categories found:`n"
while ($reader.Read()) {
    $cat = $reader.GetValue(0)
    $c = $reader.GetValue(1)
    $output += " - '$cat': $c articles`n"
}
$reader.Close()
$conn.Close()

Set-Content -Path (Join-Path $PSScriptRoot "category_output.txt") -Value $output
