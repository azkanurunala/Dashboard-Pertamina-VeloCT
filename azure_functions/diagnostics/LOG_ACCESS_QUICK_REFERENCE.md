# Azure Function Log Access - Quick Reference

## Three Ways to Access Logs

### 1. Azure Portal (Web UI) ⭐ Easiest for Beginners

**When to use**: Real-time monitoring, visual interface, quick health checks

**Access**:
1. Go to https://portal.azure.com
2. Search for "pei-dashboard"
3. Click **Monitoring** → **Log stream**

**Pros**:
- ✅ No setup required
- ✅ Color-coded log levels
- ✅ Real-time updates
- ✅ Visual and intuitive

**Cons**:
- ❌ No historical logs
- ❌ Manual copy-paste to save
- ❌ Limited filtering

**Full Guide**: [AZURE_PORTAL_LOG_ACCESS.md](AZURE_PORTAL_LOG_ACCESS.md)

---

### 2. Azure CLI (Command Line) ⭐ Best for Automation

**When to use**: Capturing logs to files, scripting, automation

**Setup**:
```bash
# Install Azure CLI (one-time)
winget install Microsoft.AzureCLI  # Windows
brew install azure-cli              # macOS

# Login (one-time)
az login
```

**Access**:
```bash
# Tail logs for 30 seconds
az functionapp log tail --name pei-dashboard --resource-group PeiDashboard --timeout 30

# Save to file
az functionapp log tail --name pei-dashboard --resource-group PeiDashboard --timeout 30 > logs/capture.txt
```

**Using Diagnostic Tool**:
```bash
# Check if CLI is set up
python diagnostic_tool.py check-access

# Tail logs
python diagnostic_tool.py tail-logs 30

# Get recent errors with classification
python diagnostic_tool.py get-errors 30 --classify
```

**Pros**:
- ✅ Easy to save to files
- ✅ Scriptable and automatable
- ✅ Real-time streaming
- ✅ Works in CI/CD pipelines

**Cons**:
- ❌ Requires CLI installation
- ❌ Command-line interface only
- ❌ No historical logs

**Full Guide**: [README.md](README.md) - AzureLogAccess section

---

### 3. Application Insights (Queries) ⭐ Best for Analysis

**When to use**: Historical analysis, advanced filtering, finding patterns

**Access via Azure CLI**:
```bash
# Get errors from last 30 minutes
az monitor app-insights query \
  --app pei-dashboard \
  --resource-group PeiDashboard \
  --analytics-query "traces | where timestamp > ago(30m) and severityLevel >= 3 | order by timestamp desc"
```

**Using Diagnostic Tool**:
```bash
# Get recent errors
python diagnostic_tool.py get-errors 30

# Analyze specific function
python diagnostic_tool.py analyze-function cnbc_scraper_function 60
```

**Common Queries**:

Get all errors:
```kusto
traces
| where timestamp > ago(30m)
| where severityLevel >= 3
| order by timestamp desc
```

Get failed requests:
```kusto
requests
| where timestamp > ago(30m)
| where success == false
| order by timestamp desc
```

Get exceptions:
```kusto
exceptions
| where timestamp > ago(30m)
| order by timestamp desc
```

**Pros**:
- ✅ Historical data (up to 90 days)
- ✅ Powerful query language (Kusto)
- ✅ Advanced filtering and aggregation
- ✅ Export to CSV/JSON

**Cons**:
- ❌ Slight delay (not real-time)
- ❌ Requires query knowledge
- ❌ More complex syntax

**Full Guide**: [appinsights_queries.md](appinsights_queries.md)

---

## Comparison Table

| Feature | Azure Portal | Azure CLI | Application Insights |
|---------|--------------|-----------|---------------------|
| **Real-time** | ✅ Yes | ✅ Yes | ❌ No (slight delay) |
| **Historical** | ❌ No | ❌ No | ✅ Yes (90 days) |
| **Setup Required** | ❌ No | ⚠️ CLI install | ❌ No |
| **Save to File** | ⚠️ Manual | ✅ Easy | ✅ Export |
| **Filtering** | ⚠️ Limited | ⚠️ Limited | ✅ Advanced |
| **Automation** | ❌ No | ✅ Yes | ✅ Yes |
| **Visual Interface** | ✅ Yes | ❌ No | ⚠️ Portal only |
| **Offline Access** | ❌ No | ❌ No | ✅ Yes (exports) |
| **Learning Curve** | ✅ Easy | ⚠️ Medium | ⚠️ Medium |

---

## Recommended Workflow

### For Quick Debugging (5 minutes)

1. **Open Azure Portal log stream** (real-time monitoring)
2. **Trigger function** via HTTP request or test
3. **Watch logs** for errors
4. **Copy error messages** for analysis

### For Systematic Debugging (30 minutes)

1. **Check Azure CLI access**:
   ```bash
   python diagnostic_tool.py check-access
   ```

2. **Get recent errors with classification**:
   ```bash
   python diagnostic_tool.py get-errors 30 --classify
   ```

3. **Analyze specific function**:
   ```bash
   python diagnostic_tool.py analyze-function cnbc_scraper_function 60
   ```

4. **Review suggested fixes** and apply

5. **Verify fixes** by checking logs again

### For Deep Analysis (1+ hour)

1. **Start diagnostic session**:
   ```bash
   python diagnostic_tool.py start-session debug-2024-01-28
   ```

2. **Query Application Insights** for patterns:
   ```bash
   # Get error trends
   python diagnostic_tool.py get-errors 1440  # Last 24 hours
   ```

3. **Classify all errors** and document

4. **Apply fixes systematically**

5. **Test all functions** and verify

6. **Export diagnostic report**:
   ```python
   session.export_to_markdown("diagnostic_report.md")
   ```

---

## Common Tasks

### Task: "I want to see what's happening right now"

**Solution**: Azure Portal log stream
```
1. Go to portal.azure.com
2. Search "pei-dashboard"
3. Click Monitoring → Log stream
4. Trigger a function to see logs
```

### Task: "I want to capture errors for analysis"

**Solution**: Azure CLI with diagnostic tool
```bash
python diagnostic_tool.py get-errors 30 --classify > errors.txt
```

### Task: "I want to see what happened yesterday"

**Solution**: Application Insights query
```bash
az monitor app-insights query \
  --app pei-dashboard \
  --resource-group PeiDashboard \
  --analytics-query "traces | where timestamp > ago(24h) and severityLevel >= 3"
```

### Task: "I want to monitor during deployment"

**Solution**: Azure Portal log stream (keep open)
```
1. Open log stream in browser
2. Deploy changes in terminal
3. Watch logs for deployment messages
4. Test function and verify logs show new behavior
```

### Task: "I want to automate error checking"

**Solution**: Azure CLI in script
```bash
#!/bin/bash
# check_errors.sh

# Get errors and classify
python diagnostic_tool.py get-errors 30 --classify > daily_errors.txt

# Send notification if errors found
if grep -q "ERROR" daily_errors.txt; then
    echo "Errors found! Check daily_errors.txt"
fi
```

---

## Troubleshooting

### "No logs appearing in Portal"

1. **Trigger a function** - logs only appear during execution
2. **Refresh the page** - connection may have dropped
3. **Check Application Insights** - ensure it's enabled
4. **Try Azure CLI** - fallback method

### "Azure CLI not found"

```bash
# Install Azure CLI
winget install Microsoft.AzureCLI  # Windows
brew install azure-cli              # macOS

# Verify installation
az --version
```

### "Not logged in to Azure CLI"

```bash
# Login
az login

# Verify login
az account show
```

### "Permission denied"

1. Check your role in Azure Portal:
   - Go to Resource Group → Access control (IAM)
   - Verify you have Reader or Contributor role
2. Contact Azure admin to request access

### "Application Insights query failed"

1. Verify Application Insights is enabled:
   - Function App → Application Insights
2. Check query syntax:
   - See [appinsights_queries.md](appinsights_queries.md) for examples
3. Try simpler query first:
   ```kusto
   traces | take 10
   ```

---

## Next Steps

1. **Choose your method** based on your needs:
   - Quick check → Azure Portal
   - Capture logs → Azure CLI
   - Analysis → Application Insights

2. **Read the detailed guide** for your chosen method:
   - [AZURE_PORTAL_LOG_ACCESS.md](AZURE_PORTAL_LOG_ACCESS.md)
   - [README.md](README.md)
   - [appinsights_queries.md](appinsights_queries.md)

3. **Try the diagnostic tool**:
   ```bash
   python diagnostic_tool.py check-access
   python diagnostic_tool.py get-errors 30 --classify
   ```

4. **Start debugging** your functions!

---

## Summary

**Three methods, one goal**: Access Azure Function logs to debug scraper errors.

- **Azure Portal**: Visual, real-time, no setup
- **Azure CLI**: Scriptable, save to files, automation
- **Application Insights**: Historical, powerful queries, analysis

**Recommendation**: Start with Azure Portal for quick checks, use Azure CLI for systematic debugging, and Application Insights for deep analysis.

**All methods are documented** and integrated with the diagnostic system for comprehensive debugging support.
