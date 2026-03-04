#!/bin/bash
# Azure Functions Startup Script
# Installs ODBC Driver 17 for SQL Server on the Azure Linux runtime

echo "Starting custom startup script..."

# Check if ODBC Driver 17 is already installed
if ! odbcinst -q -d -n "ODBC Driver 17 for SQL Server" 2>/dev/null; then
    echo "Installing ODBC Driver 17 for SQL Server..."
    
    # Install prerequisites
    apt-get update
    ACCEPT_EULA=Y apt-get install -y msodbcsql17 unixodbc-dev
    
    echo "ODBC Driver 17 installed successfully"
else
    echo "ODBC Driver 17 already installed"
fi

echo "Startup script completed"
