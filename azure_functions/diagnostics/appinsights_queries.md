# Application Insights Query Templates

Kusto Query Language (KQL) templates for debugging Azure Functions.

## Quick Reference

### Get Recent Errors (Last 30 Minutes)

```kusto
traces
| where timestamp > ago(30m)
| where severityLevel >= 3
| order by timestamp desc
| project timestamp, message, severityLevel, operation_Name, operation_Id
```

### Get Failed Requests

```kusto
requests
| where timestamp > ago(30m)
| where success == false
| order by timestamp desc
| project timestamp, name, resultCode, duration, operation_Id
```

### Get Exceptions

```kusto
exceptions
| where timestamp > ago(30m)
| order by timestamp desc
| project timestamp, type, outerMessage, innermostMessage, operation_Name, operation_Id
```

## Detailed Queries

### 1. Function Execution Timeline

```kusto
traces
| where timestamp > ago(1h)
| where operation_Name contains "scraper"
| order by timestamp asc
| project timestamp, operation_Name, message, severityLevel
```

### 2. Error Rate by Function

```kusto
traces
| where timestamp > ago(24h)
| summarize 
    TotalLogs = count(),
    ErrorCount = countif(severityLevel >= 3)
    by operation_Name
| extend ErrorRate = ErrorCount * 100.0 / TotalLogs
| order by ErrorRate desc
```

### 3. Import Errors

```kusto
traces
| where timestamp > ago(1h)
| where message contains "ModuleNotFoundError" or message contains "ImportError"
| project timestamp, operation_Name, message
| order by timestamp desc
```

### 4. Configuration Errors

```kusto
traces
| where timestamp > ago(1h)
| where message contains "ConfigurationError" 
    or message contains "environment variable"
    or message contains "KeyVault"
    or message contains "connection string"
| project timestamp, operation_Name, message
| order by timestamp desc
```

### 5. Network Errors

```kusto
traces
| where timestamp > ago(1h)
| where message contains "NetworkError"
    or message contains "TimeoutError"
    or message contains "ConnectionError"
    or message contains "HTTP"
| project timestamp, operation_Name, message
| order by timestamp desc
```

### 6. Database Errors

```kusto
traces
| where timestamp > ago(1h)
| where message contains "database"
    or message contains "sql"
    or message contains "pyodbc"
    or message contains "connection failed"
| project timestamp, operation_Name, message
| order by timestamp desc
```

### 7. Function Performance

```kusto
requests
| where timestamp > ago(24h)
| where name contains "scraper"
| summarize 
    Count = count(),
    AvgDuration = avg(duration),
    P50Duration = percentile(duration, 50),
    P95Duration = percentile(duration, 95),
    P99Duration = percentile(duration, 99)
    by name
| order by AvgDuration desc
```

### 8. Slowest Function Executions

```kusto
requests
| where timestamp > ago(24h)
| where name contains "scraper"
| order by duration desc
| take 20
| project timestamp, name, duration, resultCode, operation_Id
```

### 9. Function Invocation Count

```kusto
requests
| where timestamp > ago(24h)
| summarize Count = count() by name
| order by Count desc
```

### 10. Error Messages with Stack Traces

```kusto
exceptions
| where timestamp > ago(1h)
| project 
    timestamp,
    operation_Name,
    type,
    outerMessage,
    innermostMessage,
    details
| order by timestamp desc
```

### 11. Dependency Failures

```kusto
dependencies
| where timestamp > ago(1h)
| where success == false
| project timestamp, name, type, target, resultCode, duration
| order by timestamp desc
```

### 12. Custom Events

```kusto
customEvents
| where timestamp > ago(1h)
| project timestamp, name, customDimensions
| order by timestamp desc
```

### 13. Correlation Analysis

```kusto
let operationId = "your-operation-id-here";
union traces, requests, exceptions, dependencies
| where operation_Id == operationId
| order by timestamp asc
| project timestamp, itemType, message, name, resultCode
```

### 14. Error Frequency Over Time

```kusto
traces
| where timestamp > ago(24h)
| where severityLevel >= 3
| summarize ErrorCount = count() by bin(timestamp, 1h), operation_Name
| render timechart
```

### 15. HTTP Status Code Distribution

```kusto
requests
| where timestamp > ago(24h)
| summarize Count = count() by resultCode
| order by Count desc
```

## Advanced Queries

### Find Functions with Highest Error Rate

```kusto
let timeRange = 24h;
traces
| where timestamp > ago(timeRange)
| summarize 
    TotalLogs = count(),
    ErrorLogs = countif(severityLevel >= 3),
    WarningLogs = countif(severityLevel == 2)
    by operation_Name
| extend 
    ErrorRate = ErrorLogs * 100.0 / TotalLogs,
    WarningRate = WarningLogs * 100.0 / TotalLogs
| where TotalLogs > 10  // Filter out functions with too few logs
| order by ErrorRate desc
| project 
    Function = operation_Name,
    TotalLogs,
    ErrorLogs,
    ErrorRate = round(ErrorRate, 2),
    WarningLogs,
    WarningRate = round(WarningRate, 2)
```

### Identify Recurring Errors

```kusto
traces
| where timestamp > ago(24h)
| where severityLevel >= 3
| extend ErrorSignature = substring(message, 0, 100)  // First 100 chars as signature
| summarize 
    Occurrences = count(),
    FirstSeen = min(timestamp),
    LastSeen = max(timestamp),
    AffectedFunctions = dcount(operation_Name)
    by ErrorSignature
| where Occurrences > 5  // Only show errors that occurred more than 5 times
| order by Occurrences desc
```

### Function Health Dashboard

```kusto
let timeRange = 24h;
requests
| where timestamp > ago(timeRange)
| summarize 
    TotalRequests = count(),
    SuccessfulRequests = countif(success == true),
    FailedRequests = countif(success == false),
    AvgDuration = avg(duration),
    P95Duration = percentile(duration, 95)
    by name
| extend 
    SuccessRate = SuccessfulRequests * 100.0 / TotalRequests,
    FailureRate = FailedRequests * 100.0 / TotalRequests
| order by FailureRate desc
| project 
    Function = name,
    TotalRequests,
    SuccessRate = round(SuccessRate, 2),
    FailureRate = round(FailureRate, 2),
    AvgDuration = round(AvgDuration, 2),
    P95Duration = round(P95Duration, 2)
```

### Trace Complete Function Execution

```kusto
let functionName = "cnbc_scraper_function";
let timeRange = 1h;
union traces, requests, exceptions
| where timestamp > ago(timeRange)
| where operation_Name contains functionName
| order by timestamp asc
| project 
    timestamp,
    Type = itemType,
    Level = severityLevel,
    Message = coalesce(message, name, type),
    Duration = duration,
    Success = success
```

## Usage with Azure CLI

### Execute Query via CLI

```bash
az monitor app-insights query \
    --app pei-dashboard \
    --resource-group PeiDashboard \
    --analytics-query "traces | where timestamp > ago(30m) | where severityLevel >= 3 | order by timestamp desc" \
    --output table
```

### Save Query Results to File

```bash
az monitor app-insights query \
    --app pei-dashboard \
    --resource-group PeiDashboard \
    --analytics-query "traces | where timestamp > ago(30m) | where severityLevel >= 3" \
    --output json > errors.json
```

### Query with Time Range

```bash
az monitor app-insights query \
    --app pei-dashboard \
    --resource-group PeiDashboard \
    --analytics-query "traces | order by timestamp desc" \
    --timespan PT30M \
    --output table
```

## Query Best Practices

1. **Use time filters**: Always include `where timestamp > ago(Xh)` to limit data scanned
2. **Project only needed columns**: Use `project` to select only required fields
3. **Limit results**: Use `take` or `top` to limit result set size
4. **Use summarize for aggregations**: More efficient than client-side processing
5. **Filter early**: Apply filters before joins or aggregations
6. **Use let statements**: Define variables for reusable values
7. **Test incrementally**: Start with simple queries and add complexity

## Common Time Ranges

- Last 5 minutes: `ago(5m)`
- Last 30 minutes: `ago(30m)`
- Last hour: `ago(1h)`
- Last 24 hours: `ago(24h)`
- Last 7 days: `ago(7d)`
- Specific time range: `between(datetime(2024-01-28 00:00:00) .. datetime(2024-01-28 23:59:59))`

## Severity Levels

- 0: Verbose
- 1: Information
- 2: Warning
- 3: Error
- 4: Critical

Filter for errors and above: `where severityLevel >= 3`

## Useful Functions

- `ago(timespan)`: Time relative to now
- `bin(timestamp, interval)`: Group by time interval
- `count()`: Count rows
- `countif(condition)`: Count rows matching condition
- `avg(column)`: Average value
- `sum(column)`: Sum values
- `min(column)`: Minimum value
- `max(column)`: Maximum value
- `percentile(column, percentile)`: Percentile value
- `dcount(column)`: Distinct count
- `contains`: Case-insensitive substring match
- `startswith`: String starts with
- `endswith`: String ends with
- `matches regex`: Regular expression match

## Integration with Diagnostic Tool

Use these queries with the diagnostic tool:

```python
from diagnostics import AzureLogAccess

log_access = AzureLogAccess()

# Custom query
query = """
traces
| where timestamp > ago(30m)
| where severityLevel >= 3
| order by timestamp desc
"""

entries = log_access.query_application_insights(query, "PT30M")
```

## Troubleshooting Queries

### No Results Returned

1. Check time range is appropriate
2. Verify function app name in query
3. Ensure Application Insights is receiving data
4. Check if functions have been invoked recently

### Query Timeout

1. Reduce time range
2. Add more specific filters
3. Use `take` to limit results
4. Avoid expensive operations like joins on large datasets

### Permission Errors

1. Verify you have Reader access to Application Insights
2. Check resource group permissions
3. Ensure Application Insights resource exists
