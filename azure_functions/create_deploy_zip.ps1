$sourceDir = "c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions"
$destinationZip = "c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\manual_deploy.zip"

# Exclusions
$exclude = @(
    "deploy.zip",
    "manual_deploy.zip",
    ".venv",
    ".python_packages",
    "__pycache__",
    ".git",
    ".vscode",
    "bin",
    "obj",
    "tests",
    "local.settings.json"
)

# Get all items to zip
$items = Get-ChildItem -Path $sourceDir -Exclude $exclude

# Create zip
Compress-Archive -Path $items.FullName -DestinationPath $destinationZip -Force

Write-Host "Zip created at $destinationZip"
Get-Item $destinationZip | Select-Object Name, @{Name="Size(MB)";Expression={$_.Length / 1MB}}
