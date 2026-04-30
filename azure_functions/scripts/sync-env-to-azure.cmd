@echo off
REM Wrapper that calls the PowerShell sync script from cmd.
REM Usage: scripts\sync-env-to-azure.cmd [-FunctionAppName name] [-DryRun]
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sync-env-to-azure.ps1" %*
