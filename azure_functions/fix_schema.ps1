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
$log_file = Join-Path $PSScriptRoot "schema_fix_log.txt"

"Starting execution..." | Out-File -FilePath $log_file

try {
    $conn = New-Object System.Data.SqlClient.SqlConnection($conn_str)
    $conn.Open()

    "Connected to database. Checking if column exists..." | Out-File -FilePath $log_file -Append

    # Check if articles_scraped column exists
    $cmdCheck = $conn.CreateCommand()
    $cmdCheck.CommandText = "SELECT COL_LENGTH('dbo.execution_logs', 'articles_scraped')"
    $colLength = $cmdCheck.ExecuteScalar()

    if ([string]::IsNullOrEmpty($colLength)) {
        "Column 'articles_scraped' does not exist. Adding column..." | Out-File -FilePath $log_file -Append
        $cmdAlter = $conn.CreateCommand()
        $cmdAlter.CommandText = "ALTER TABLE execution_logs ADD articles_scraped INT NULL DEFAULT 0;"
        $null = $cmdAlter.ExecuteNonQuery()
        "Column 'articles_scraped' added successfully." | Out-File -FilePath $log_file -Append
    } else {
        "Column 'articles_scraped' already exists." | Out-File -FilePath $log_file -Append
    }

    $conn.Close()
} catch {
    "Error: $_" | Out-File -FilePath $log_file -Append
}
