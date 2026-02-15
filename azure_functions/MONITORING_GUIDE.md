# 📊 Monitoring Guide - Azure Functions (Tanpa Log Stream)

**Tanggal**: 16 Februari 2026  
**Function App**: pei-dashboard

---

## 🎯 Cara Monitor Azure Functions

### 1. Azure Portal - Monitor Tab (Recommended)

**Langkah**:
1. Buka [Azure Portal](https://portal.azure.com)
2. Search "pei-dashboard" → klik Function App
3. Klik **Functions** di sidebar kiri
4. Pilih function yang ingin dimonitor (contoh: `daily_morning_timer`)
5. Klik **Monitor** tab

**Yang Bisa Dilihat**:
- ✅ Invocation history (kapan function dijalankan)
- ✅ Success/Failure status
- ✅ Execution duration
- ✅ Error messages (jika ada)
- ✅ Grafik execution over time

**Keuntungan**:
- Visual dan mudah dibaca
- Tidak perlu command line
- Bisa filter by date/time
- Bisa lihat detail error

---

### 2. Application Insights (Powerful Analytics)

**Langkah**:
1. Azure Portal → Search "Application Insights"
2. Pilih Application Insights untuk pei-dashboard
3. Klik **Logs** di sidebar kiri
4. Gunakan Kusto queries

**Query Contoh**:

#### Cek Timer Function Executions (24 jam terakhir)
```kusto
requests
| where timestamp > ago(24h)
| where name contains "timer"
| project timestamp, name, success, duration, resultCode
| order by timestamp desc
```

#### Cek Errors
```kusto
exceptions
| where timestamp > ago(24h)
| project timestamp, operation_Name, type, outerMessage
| order by timestamp desc
```

#### Cek Function Performance
```kusto
requests
| where timestamp > ago(1h)
| summarize 
    Count = count(),
    AvgDuration = avg(duration),
    MaxDuration = max(duration),
    SuccessRate = countif(success == true) * 100.0 / count()
    by name
| order by Count desc
```

#### Cek Timer Trigger Specific
```kusto
traces
| where timestamp > ago(24h)
| where message contains "Timer schedule"
| project timestamp, message, severityLevel
| order by timestamp desc
```

**Keuntungan**:
- Query powerful untuk analisis mendalam
- Bisa export data
- Bisa create custom dashboards
- Real-time monitoring

---

### 3. Azure CLI - Query Logs

**Cek Recent Invocations**:
```bash
az monitor app-insights query \
  --app 9db8826b-a342-44c5-973d-a045bac44ee2 \
  --analytics-query "requests | where timestamp > ago(1h) | project timestamp, name, success, duration | order by timestamp desc" \
  --output table
```

**Cek Errors**:
```bash
az monitor app-insights query \
  --app 9db8826b-a342-44c5-973d-a045bac44ee2 \
  --analytics-query "exceptions | where timestamp > ago(24h) | project timestamp, operation_Name, outerMessage" \
  --output table
```

---

### 4. Azure Portal - Metrics (Real-time Graphs)

**Langkah**:
1. Azure Portal → pei-dashboard Function App
2. Klik **Metrics** di sidebar kiri
3. Pilih metric yang ingin dilihat

**Metrics Penting**:
- **Function Execution Count** - Berapa kali function dijalankan
- **Function Execution Units** - Resource usage
- **Http Server Errors** - Error 5xx
- **Response Time** - Latency
- **Requests** - Total requests

**Keuntungan**:
- Real-time graphs
- Bisa set time range (1h, 24h, 7d, 30d)
- Bisa compare multiple metrics
- Visual dan mudah dipahami

---

### 5. Azure Portal - Alerts (Notifikasi Otomatis)

**Setup Alert untuk Timer Failures**:

1. Azure Portal → pei-dashboard
2. Klik **Alerts** di sidebar kiri
3. Klik **+ Create** → **Alert rule**
4. Configure:
   - **Scope**: pei-dashboard
   - **Condition**: 
     - Signal: "Failed requests"
     - Threshold: Greater than 0
     - Evaluation frequency: 5 minutes
   - **Actions**: 
     - Email notification
     - SMS (optional)
     - Webhook (optional)
5. Klik **Create alert rule**

**Alert Examples**:
- Timer function failed
- Function execution time > 5 minutes
- Error rate > 10%
- No executions in last hour (for scheduled functions)

---

### 6. PowerShell Script - Quick Check

Saya buatkan script untuk cek status tanpa log stream:

```powershell
# check_function_status.ps1
$appId = "9db8826b-a342-44c5-973d-a045bac44ee2"

Write-Host "🔍 Checking Function Status..." -ForegroundColor Cyan
Write-Host ""

# Check recent executions
Write-Host "Recent Executions (Last 1 hour):" -ForegroundColor Yellow
$query = "requests | where timestamp > ago(1h) | where name contains 'timer' | project timestamp, name, success, duration | order by timestamp desc | take 10"

az monitor app-insights query --app $appId --analytics-query $query --output table

Write-Host ""
Write-Host "Recent Errors:" -ForegroundColor Yellow
$errorQuery = "exceptions | where timestamp > ago(1h) | project timestamp, operation_Name, outerMessage | order by timestamp desc | take 5"

az monitor app-insights query --app $appId --analytics-query $errorQuery --output table
```

---

### 7. Database Check (Indirect Monitoring)

Karena functions Anda scraping dan menyimpan ke database, Anda bisa cek apakah data baru masuk:

```sql
-- Cek data terbaru di news_articles
SELECT TOP 10 
    title, 
    published_date, 
    created_at 
FROM news_articles 
ORDER BY created_at DESC;

-- Cek berapa artikel hari ini
SELECT 
    CAST(created_at AS DATE) as date,
    COUNT(*) as article_count
FROM news_articles
WHERE created_at >= DATEADD(day, -7, GETDATE())
GROUP BY CAST(created_at AS DATE)
ORDER BY date DESC;

-- Cek execution logs
SELECT TOP 20 
    function_name,
    execution_time,
    status,
    error_message
FROM execution_logs
ORDER BY execution_time DESC;
```

---

## 📱 Monitoring Dashboard Setup

### Option 1: Azure Dashboard

1. Azure Portal → **Dashboard**
2. Klik **+ New dashboard**
3. Add tiles:
   - Function execution count (last 24h)
   - Error rate
   - Response time
   - Recent failures
4. Save dashboard

### Option 2: Power BI (Advanced)

1. Connect Power BI to Application Insights
2. Create custom reports
3. Schedule automatic refresh
4. Share with team

---

## 🔔 Notification Setup

### Email Notifications

**Setup di Azure Portal**:
1. Function App → Alerts → Create alert rule
2. Add action group
3. Add email addresses
4. Test notification

### Teams/Slack Webhook

```bash
# Example: Send notification to Teams
curl -H "Content-Type: application/json" \
  -d '{"text": "Timer function failed at 05:00 WIB"}' \
  https://your-teams-webhook-url
```

---

## 📊 Recommended Monitoring Strategy

### Daily Monitoring (5 menit)
1. Buka Azure Portal → pei-dashboard → Overview
2. Cek "Function Execution Count" graph
3. Lihat ada error atau tidak

### Weekly Review (15 menit)
1. Application Insights → Logs
2. Run performance query
3. Check error trends
4. Review slow functions

### Monthly Analysis (30 menit)
1. Export metrics to Excel/CSV
2. Analyze trends
3. Optimize slow functions
4. Review costs

---

## 🎯 Quick Status Check Commands

### Check if schedules are set
```bash
az functionapp config appsettings list \
  --name pei-dashboard \
  --resource-group PeiDashboard \
  --query "[?contains(name, 'TIMER_SCHEDULE')].{Name:name, Value:value}" \
  --output table
```

### Check function app status
```bash
az functionapp show \
  --name pei-dashboard \
  --resource-group PeiDashboard \
  --query "{Name:name, State:state, Location:location}" \
  --output table
```

### List all functions
```bash
az functionapp function list \
  --name pei-dashboard \
  --resource-group PeiDashboard \
  --output table
```

---

## 📈 Monitoring Checklist

### Setelah Deploy
- [ ] Verify schedules are set correctly
- [ ] Check first timer execution
- [ ] Verify data masuk ke database
- [ ] Setup email alerts
- [ ] Bookmark Azure Portal dashboard

### Daily
- [ ] Check execution count (should match schedule)
- [ ] Check for errors in last 24h
- [ ] Verify data freshness in database

### Weekly
- [ ] Review performance metrics
- [ ] Check error trends
- [ ] Optimize slow functions if needed

### Monthly
- [ ] Full performance review
- [ ] Cost analysis
- [ ] Update documentation if needed

---

## 🔗 Quick Links

### Azure Portal
- **Function App**: [Open](https://portal.azure.com/#@/resource/subscriptions/5e4ecee4-ce42-47f4-b953-7f29ad625c53/resourceGroups/PeiDashboard/providers/Microsoft.Web/sites/pei-dashboard)
- **Application Insights**: Search "pei-dashboard" in Azure Portal
- **Metrics**: Function App → Monitoring → Metrics
- **Alerts**: Function App → Monitoring → Alerts

### Monitoring URLs
- **Overview Dashboard**: Portal → pei-dashboard → Overview
- **Function Monitor**: Portal → pei-dashboard → Functions → [function name] → Monitor
- **Application Insights Logs**: Portal → Application Insights → Logs

---

## 💡 Pro Tips

1. **Bookmark Azure Portal pages** untuk akses cepat
2. **Setup email alerts** untuk critical failures
3. **Check database** sebagai indirect monitoring
4. **Use Application Insights** untuk analisis mendalam
5. **Create custom dashboard** untuk monitoring harian
6. **Export metrics** untuk reporting bulanan

---

**Kesimpulan**: Anda tidak perlu log stream untuk monitoring! Azure Portal dan Application Insights sudah sangat powerful untuk monitoring visual dan analytics.

**Recommended**: Gunakan Azure Portal → Functions → Monitor untuk daily monitoring yang mudah dan visual.
