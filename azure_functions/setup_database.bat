@echo off
echo ========================================
echo Azure SQL Database Schema Setup
echo ========================================
echo.

echo Executing database schema...
echo.

sqlcmd -S pei-dashboard.database.windows.net -d pei-dashboard -G -i shared\database_schema.sql

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Database schema setup completed!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo Database schema setup failed!
    echo Error code: %ERRORLEVEL%
    echo ========================================
)

pause
