$conn_str = "Server=tcp:pei-dashboard.database.windows.net,1433;Database=pei-dashboard;User ID=CloudSAa33fbc7c;Password=uRahcie3&105272;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"

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

Set-Content -Path "C:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\category_output.txt" -Value $output
