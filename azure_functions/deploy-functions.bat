@echo off
echo Deploying to Azure Functions...
powershell -ExecutionPolicy Bypass -File "scripts/deploy-functions.ps1" -FunctionAppName "pei-dashboard"
pause
