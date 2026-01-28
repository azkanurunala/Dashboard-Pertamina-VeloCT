# Azure Functions Diagnostic System

Comprehensive diagnostic and debugging tools for Azure Functions scraper errors.

## Overview

This diagnostic system provides:

- **Log Access**: Connect to Azure Portal log stream and Application Insights
- **Error Classification**: Automatically classify errors by type (import, dependency, config, network, database, runtime)
- **Log Parsing**: Parse logs from multiple sources with structured output
- **Diagnostic Sessions**: Track debugging workflows with error reports and test results
- **Suggested Fixes**: Get actionable recommendations for each error type

## Log Access Methods

The diagnostic system supports three methods for accessing Azure Function logs:

### 1. Azure Portal (Web UI)
- **Best for**: Real-time monitoring, visual interface, quick checks
- **Access**: https://portal.azure.com → pei-dashboard → Log stream
- **Pros**: No setup, color-coded, real-time
- **Cons**: Manual copy-paste, no historical logs
- **Guide**: See [AZURE_PORTAL_LOG_ACCESS.md](AZURE_PORTAL_LOG_ACCESS.md)

### 2. Azure CLI (Command Line)
- **Best for**: Automation, capturing logs to files, scripting
- **Access**: `az functionapp log tail --name pei-dashboard --resource-group PeiDashboard`
- **Pros**: Easy to save, scriptable, real-time
- **Cons**: Requires CLI installation and login
- **Guide**: See sections below and `diagnostic_tool.py`

### 3. Application Insights (Queries)
- **Best for**: Historical analysis, advanced filtering, trends
- **Access**: Kusto queries via Azure CLI or Portal
- **Pros**: Historical data, powerful queries, export
- **Cons**: Slight delay, requires query knowledge
- **Guide**: See [appinsights_queries.md](appinsights_queries.md)

## Components

### 1. AzureLogAccess

Access Azure Function logs through multiple methods:

```python
from diagnostics import AzureLogAccess

# Initialize
log_access = AzureLogAccess(
    function_app_name="pei-dashboard",
    resource_group="PeiDashboard"
)

# Tail logs in real-time
entries = log_access.tail_logs(timeout_seconds=30)

# Get recent errors
errors = log_access.get_recent_errors(minutes=30)

# Get logs for specific function
function_logs = log_access.get_function_logs("cnbc_scraper_function", minutes=30)

# Get failed requests
failed_requests = log_access.get_failed_requests(minutes=30)

# Get exceptions
exceptions = log_access.get_exceptions(minutes=30)
```

### 2. ErrorClassifier

Classify errors and get suggested fixes:

```python
from diagnostics import ErrorClassifier

classifier = ErrorClassifier()

# Classify an error
error_type = classifier.classify_error(error_message, stack_trace)

# Create error report
error_report = classifier.create_error_report(
    function_name="cnbc_scraper_function",
    error_message="ModuleNotFoundError: No module named 'requests'",
    stack_trace="...",
    http_status_code=500
)

# Get suggested fix
suggested_fix = classifier.get_suggested_fix(error_report)
print(suggested_fix)
# Output: "Add 'requests' to requirements.txt or fix import path"

# Extract specific information
missing_package = classifier.extract_missing_package(error_message, stack_trace)
missing_config = classifier.extract_missing_configuration(error_message, stack_trace)
http_status = classifier.extract_http_status_code(error_message, stack_trace)
is_connection_error = classifier.is_connection_error(error_message, stack_trace)
```

### 3. LogParser

Parse logs from various sources:

```python
from diagnostics import LogParser

parser = LogParser()

# Parse log stream
entries = parser.parse_log_stream(log_text)

# Parse Application Insights JSON
entries = parser.parse_application_insights_json(json_data)

# Filter logs
errors = parser.filter_errors(entries)
function_logs = parser.filter_by_function(entries, "cnbc_scraper")
time_range_logs = parser.filter_by_time_range(entries, start_time, end_time)

# Extract stack traces
stack_traces = parser.extract_stack_traces(entries)

# Get error summary
summary = parser.get_error_summary(entries)
print(f"Total errors: {summary['total_errors']}")
print(f"Error rate: {summary['error_rate']:.1%}")
```

### 4. DiagnosticSession

Track complete debugging sessions:

```python
from diagnostics import DiagnosticSession, TestResult
from datetime import datetime

# Create session
session = DiagnosticSession(
    session_id="debug-2024-01-28",
    start_time=datetime.utcnow()
)

# Add errors
session.add_error(error_report)

# Add fixes
session.add_fix("Updated requirements.txt with missing packages")
session.add_fix("Fixed import statements to use relative paths")

# Add test results
test_result = TestResult(
    source_name="CNBC",
    success=True,
    http_status_code=200,
    articles_found=15,
    articles_saved=15,
    execution_time_seconds=3.5
)
session.add_test_result(test_result)

# Add notes
session.add_note("Deployed fixes to Azure")

# Complete session
session.complete()

# Get summary
summary = session.get_summary()
print(f"Duration: {summary['duration_seconds']} seconds")
print(f"Tests passed: {summary['tests']['passed']}/{summary['tests']['total']}")

# Export reports
session.export_to_json("diagnostic_report.json")
session.export_to_markdown("diagnostic_report.md")
```

## Command-Line Tool

The `diagnostic_tool.py` provides a CLI interface:

### Check Azure Access

```bash
python diagnostic_tool.py check-access
```

Checks if Azure CLI is installed and you're logged in. Provides setup instructions.

### Tail Logs

```bash
# Tail logs for 30 seconds (default)
python diagnostic_tool.py tail-logs

# Tail logs for 60 seconds
python diagnostic_tool.py tail-logs 60
```

Captures real-time logs from the function app.

### Get Recent Errors

```bash
# Get errors from last 30 minutes
python diagnostic_tool.py get-errors

# Get errors from last 60 minutes with classification
python diagnostic_tool.py get-errors 60 --classify
```

Retrieves and optionally classifies recent errors from Application Insights.

### Analyze Function

```bash
# Analyze CNBC scraper logs
python diagnostic_tool.py analyze-function cnbc_scraper_function

# Analyze with custom time range
python diagnostic_tool.py analyze-function cnbc_scraper_function 60
```

Provides detailed analysis of a specific function's logs including:
- Error summary
- Error classification
- Suggested fixes

### Classify Errors from File

```bash
python diagnostic_tool.py classify-error logs/error_log.txt
```

Classifies errors from a saved log file.

### Start Diagnostic Session

```bash
python diagnostic_tool.py start-session debug-2024-01-28
```

Creates a new diagnostic session for tracking debugging workflow.

## Error Types

The system classifies errors into these categories:

### 1. Import Errors
- **Symptoms**: `ModuleNotFoundError`, `ImportError`, `cannot import name`
- **Common Causes**: Missing dependencies, incorrect import paths
- **Suggested Fix**: Check import statements, verify relative paths (`from ..shared` not `from shared`)

### 2. Dependency Errors
- **Symptoms**: Package not found during runtime
- **Common Causes**: `requirements.txt` not deployed, version conflicts
- **Suggested Fix**: Ensure `requirements.txt` is in root, redeploy with `--build remote`

### 3. Configuration Errors
- **Symptoms**: `ConfigurationError`, missing environment variables, Key Vault issues
- **Common Causes**: Key Vault references not resolved, missing app settings
- **Suggested Fix**: Add direct environment variables, verify Key Vault access

### 4. Network Errors
- **Symptoms**: `NetworkError`, `TimeoutError`, HTTP status codes
- **Common Causes**: Target website blocking requests, slow responses
- **Suggested Fix**: Adjust timeouts, add retry logic, update user agents

### 5. Database Errors
- **Symptoms**: Connection failures, SQL exceptions
- **Common Causes**: Invalid connection string, firewall rules, authentication
- **Suggested Fix**: Verify connection string, check firewall, test authentication
- **Sub-classification**: Connection errors vs query errors

### 6. Runtime Errors
- **Symptoms**: General exceptions not matching other categories
- **Common Causes**: Code logic errors, unexpected data
- **Suggested Fix**: Review stack trace for specific error details

## Prerequisites

### Azure Portal Access

For web-based log streaming:
- Azure account with access to PeiDashboard resource group
- Web browser (Chrome, Edge, Firefox, or Safari)
- Reader or Contributor role on the Function App

**See**: [AZURE_PORTAL_LOG_ACCESS.md](AZURE_PORTAL_LOG_ACCESS.md) for detailed Azure Portal log stream instructions.

### Azure CLI

Install Azure CLI:
```bash
# Windows
winget install Microsoft.AzureCLI

# macOS
brew install azure-cli

# Linux
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

Login to Azure:
```bash
az login
```

### Python Dependencies

The diagnostic system requires:
```
azure-cli
```

All other dependencies are part of the standard library.

## Usage Examples

### Example 1: Quick Error Check

```bash
# Check if you can access logs
python diagnostic_tool.py check-access

# Get recent errors with classification
python diagnostic_tool.py get-errors 30 --classify
```

### Example 2: Analyze Specific Function

```bash
# Analyze CNBC scraper
python diagnostic_tool.py analyze-function cnbc_scraper_function 60
```

Output:
```
Analyzing cnbc_scraper_function logs from last 60 minutes...
============================================================

Found 45 log entries

Summary:
  Total entries: 45
  Total errors: 3
  Error rate: 6.7%

Errors by level:
  ERROR: 3

Classifying 3 errors...

Errors by type:
  import_error: 2
  configuration_error: 1

Recent errors (showing first 3):

1. [IMPORT_ERROR]
   Time: 2024-01-28 10:30:15
   Message: ModuleNotFoundError: No module named 'requests'...
   💡 Suggested fix: Add 'requests' to requirements.txt or fix import path

2. [IMPORT_ERROR]
   Time: 2024-01-28 10:31:22
   Message: cannot import name 'CNBCNewsScraper' from 'scrapers.cnbc_scraper'...
   💡 Suggested fix: Check import statements and verify relative paths (use ..shared not shared)

3. [CONFIGURATION_ERROR]
   Time: 2024-01-28 10:32:45
   Message: Database connection string not found...
   💡 Suggested fix: Add 'DatabaseConnectionString' to application settings or environment variables
```

### Example 3: Complete Diagnostic Workflow

```python
from diagnostics import (
    AzureLogAccess,
    ErrorClassifier,
    DiagnosticSession,
    TestResult
)
from datetime import datetime

# 1. Start diagnostic session
session = DiagnosticSession(
    session_id="debug-scrapers-2024-01-28",
    start_time=datetime.utcnow()
)

# 2. Access logs
log_access = AzureLogAccess()
errors = log_access.get_recent_errors(minutes=30)

# 3. Classify errors
classifier = ErrorClassifier()
for entry in errors:
    error_report = classifier.create_error_report(
        function_name=entry.function_name or "unknown",
        error_message=entry.message,
        stack_trace=entry.exception or "",
        timestamp=entry.timestamp
    )
    session.add_error(error_report)
    
    # Get suggested fix
    fix = classifier.get_suggested_fix(error_report)
    print(f"Error: {error_report.error_type.value}")
    print(f"Fix: {fix}\n")

# 4. Apply fixes (manual step)
session.add_fix("Updated requirements.txt with missing packages")
session.add_fix("Fixed import statements in all scraper functions")
session.add_note("Deployed fixes using: func azure functionapp publish pei-dashboard --python --build remote")

# 5. Test functions
test_result = TestResult(
    source_name="CNBC",
    success=True,
    http_status_code=200,
    articles_found=15,
    articles_saved=15,
    execution_time_seconds=3.5
)
session.add_test_result(test_result)

# 6. Complete session
session.complete()

# 7. Generate reports
session.export_to_json("diagnostic_sessions/debug-scrapers-2024-01-28.json")
session.export_to_markdown("diagnostic_sessions/debug-scrapers-2024-01-28.md")

print(f"Session completed in {session.get_duration_seconds():.2f} seconds")
print(f"Tests passed: {session.get_summary()['tests']['passed']}/{session.get_summary()['tests']['total']}")
```

## Integration with Existing Scripts

The diagnostic system integrates with existing PowerShell scripts:

### check_function_logs.ps1
```powershell
# Existing script for quick log access
az functionapp log tail --name pei-dashboard --resource-group PeiDashboard --timeout 5
```

### get_logs.ps1
```powershell
# Existing script for Application Insights queries
az monitor app-insights query `
    --app pei-dashboard `
    --resource-group PeiDashboard `
    --analytics-query "traces | where timestamp > ago(30m) | order by timestamp desc | take 50"
```

You can now enhance these with the diagnostic tool:
```bash
# Capture logs to file
az functionapp log tail --name pei-dashboard --resource-group PeiDashboard --timeout 30 > logs/capture.txt

# Classify errors from captured logs
python diagnostic_tool.py classify-error logs/capture.txt
```

## Troubleshooting

### Azure CLI Not Found
```
Error: Azure CLI not found. Please install Azure CLI.
```
**Solution**: Install Azure CLI from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

### Not Logged In
```
Error: Not logged in to Azure CLI
```
**Solution**: Run `az login` and follow the authentication prompts

### No Logs Captured
```
No log entries captured.
```
**Solutions**:
1. Verify function app name and resource group are correct
2. Check if functions are being invoked (no invocations = no logs)
3. Try accessing logs via Azure Portal as fallback
4. Ensure Application Insights is enabled for the function app

### Permission Denied
```
Error: You do not have permission to access this resource
```
**Solution**: Ensure your Azure account has appropriate permissions (Reader or Contributor role on the resource group)

## Best Practices

1. **Start with check-access**: Always verify Azure CLI access before running other commands
2. **Use classification**: Always use `--classify` flag when getting errors for actionable insights
3. **Track sessions**: Use diagnostic sessions to document your debugging workflow
4. **Save logs**: Capture logs to files for offline analysis and historical reference
5. **Analyze before fixing**: Understand all errors before applying fixes to avoid partial solutions
6. **Test after fixes**: Always verify fixes with test invocations before marking issues resolved

## Requirements Validation

This diagnostic system validates the following requirements:

- **Requirement 1.1**: Real-time log stream access via Azure Portal and CLI
- **Requirement 1.2**: Capture error messages and stack traces
- **Requirement 1.3**: Application Insights telemetry queries
- **Requirement 1.4**: Import errors, dependency issues, and runtime exceptions
- **Requirement 2.1**: Error classification by type
- **Requirement 2.2**: Missing package identification
- **Requirement 2.3**: Configuration error reporting
- **Requirement 2.4**: Network error details (HTTP status, timeout)
- **Requirement 2.5**: Database error classification (connection vs query)

## Next Steps

After setting up diagnostic access:

1. **Run initial diagnostics**: `python diagnostic_tool.py get-errors --classify`
2. **Identify error patterns**: Look for common error types across functions
3. **Apply targeted fixes**: Use suggested fixes for each error type
4. **Deploy fixes**: Redeploy functions with corrections
5. **Verify fixes**: Test functions and confirm errors are resolved
6. **Document session**: Export diagnostic session report for reference
