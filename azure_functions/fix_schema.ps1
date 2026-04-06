$conn_str = "Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;User ID=CloudSAa33fbc7c;Password=uRahcie3&105272;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"
$log_file = "C:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\schema_fix_log.txt"

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
