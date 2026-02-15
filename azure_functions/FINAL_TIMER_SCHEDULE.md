# ⏰ Final Timer Schedule Configuration

**Tanggal**: 16 Februari 2026  
**Status**: ✅ Configured  
**Timezone**: WIB (UTC+7)

---

## 📅 Production Schedule (WIB)

| Timer | WIB Time | UTC Time | Cron Expression | Purpose |
|-------|----------|----------|-----------------|---------|
| **Morning** | 05:20 WIB | 22:20 UTC | `0 20 22 * * *` | International news scraping |
| **Afternoon** | 05:30 WIB | 22:30 UTC | `0 30 22 * * *` | Indonesian news scraping |
| **Weekly** | 05:40 WIB | 22:40 UTC | `0 40 22 * * *` | Weekly summary & analysis |
| **Monthly** | 05:50 WIB | 22:50 UTC | `0 50 22 * * *` | Monthly aggregation |

---

## 🔧 Azure Configuration

### Environment Variables Set
```bash
MORNING_TIMER_SCHEDULE   = "0 20 22 * * *"  # 05:20 WIB
AFTERNOON_TIMER_SCHEDULE = "0 30 22 * * *"  # 05:30 WIB
WEEKLY_TIMER_SCHEDULE    = "0 40 22 * * *"  # 05:40 WIB
MONTHLY_TIMER_SCHEDULE   = "0 50 22 * * *"  # 05:50 WIB
```

### Applied Command
```bash
az functionapp config appsettings set \
  --name pei-dashboard \
  --resource-group PeiDashboard \
  --settings \
    "MORNING_TIMER_SCHEDULE=0 20 22 * * *" \
    "AFTERNOON_TIMER_SCHEDULE=0 30 22 * * *" \
    "WEEKLY_TIMER_SCHEDULE=0 40 22 * * *" \
    "MONTHLY_TIMER_SCHEDULE=0 50 22 * * *"
```

---

## 📊 Execution Timeline (WIB)

```
05:20 WIB → Morning Timer
    ↓ (10 minutes later)
05:30 WIB → Afternoon Timer
    ↓ (10 minutes later)
05:40 WIB → Weekly Timer
    ↓ (10 minutes later)
05:50 WIB → Monthly Timer
```

**Total Duration**: 30 minutes (05:20 - 05:50 WIB)

---

## 🌍 Timezone Conversion Reference

### WIB to UTC Conversion
- **Formula**: UTC = WIB - 7 hours
- **Example**: 05:20 WIB = 22:20 UTC (previous day)

### Quick Reference Table
| WIB | UTC (Previous Day) |
|-----|-------------------|
| 05:00 | 22:00 |
| 05:10 | 22:10 |
| 05:20 | 22:20 ✅ |
| 05:30 | 22:30 ✅ |
| 05:40 | 22:40 ✅ |
| 05:50 | 22:50 ✅ |
| 06:00 | 23:00 |

---

## 🔍 Verification Commands

### Check Schedules in Azure
```bash
az functionapp config appsettings list \
  --name pei-dashboard \
  --resource-group PeiDashboard \
  --query "[?contains(name, 'TIMER_SCHEDULE')].{Name:name, Value:value}" \
  --output table
```

**Expected Output**:
```
Name                        Value
--------------------------  ---------------
MORNING_TIMER_SCHEDULE      0 20 22 * * *
AFTERNOON_TIMER_SCHEDULE    0 30 22 * * *
WEEKLY_TIMER_SCHEDULE       0 40 22 * * *
MONTHLY_TIMER_SCHEDULE      0 50 22 * * *
```

### Check Timer Functions Deployed
```bash
az functionapp function list \
  --name pei-dashboard \
  --resource-group PeiDashboard \
  --query "[?contains(name, 'timer')].name" \
  --output table
```

**Expected Output**:
```
Result
--------------------------
daily_morning_timer
daily_afternoon_timer
weekly_summary_timer
monthly_aggregation_timer
```

---

## 📝 Timer Function Details

### 1. Morning Timer (05:20 WIB)
**Purpose**: International news scraping  
**Sources**: 
- SCMP, Bioenergy Times, Energies Media
- Migas EIA, S&P News, S&P Data
- Google News, IAEA PRIS

**Keywords**: oil, energy, petroleum, gas, renewable, biodiesel, bioethanol, crude oil, energy market, fuel prices

**Expected Duration**: ~5-10 minutes

---

### 2. Afternoon Timer (05:30 WIB)
**Purpose**: Indonesian news scraping  
**Sources**:
- Bank Indonesia, BPS
- Kontan BBM, Kontan Biodiesel
- Bloomberg Technoz, Migas ESDM
- Biodiesel ESDM, Bioetanol ESDM
- CPO, SIPSN

**Keywords**: minyak, energi, BBM, biodiesel, bioetanol, pertamina, harga minyak, pasar energi, bahan bakar, energi terbarukan

**Expected Duration**: ~5-10 minutes

---

### 3. Weekly Timer (05:40 WIB)
**Purpose**: Weekly summary & analysis  
**Process**:
- Aggregate news from past 7 days
- Generate comprehensive weekly analysis
- Create trend reports and insights
- Policy analyst perspective

**Expected Duration**: ~3-5 minutes

---

### 4. Monthly Timer (05:50 WIB)
**Purpose**: Monthly aggregation  
**Process**:
- Aggregate news from past 30 days
- Generate monthly trend reports
- Create comprehensive market insights
- Risk analyst perspective
- Calculate monthly trends

**Expected Duration**: ~5-8 minutes

---

## 🧪 Testing Schedule

### First Execution Expected
- **Date**: 16 Februari 2026
- **Time**: 05:20 WIB (22:20 UTC)
- **Function**: daily_morning_timer

### Monitoring Checklist
- [ ] 05:20 WIB - Morning timer triggers
- [ ] 05:30 WIB - Afternoon timer triggers
- [ ] 05:40 WIB - Weekly timer triggers
- [ ] 05:50 WIB - Monthly timer triggers
- [ ] Check logs for successful execution
- [ ] Verify data in database
- [ ] Check for any errors

---

## 📊 Monitoring Commands

### Real-time Log Monitoring
```bash
# Stream logs (will show timer triggers)
func azure functionapp logstream pei-dashboard
```

### Check Recent Executions (Application Insights)
```bash
az monitor app-insights query \
  --app 9db8826b-a342-44c5-973d-a045bac44ee2 \
  --analytics-query "requests | where timestamp > ago(1h) | where name contains 'timer' | project timestamp, name, success, duration | order by timestamp desc" \
  --output table
```

### Quick Status Check
```powershell
powershell -ExecutionPolicy Bypass -File check_function_status.ps1
```

---

## 🚨 Troubleshooting

### Timer Not Triggering at Expected Time

**Check 1**: Verify schedules are set
```bash
az functionapp config appsettings list --name pei-dashboard --resource-group PeiDashboard
```

**Check 2**: Restart Function App
```bash
az functionapp restart --name pei-dashboard --resource-group PeiDashboard
```

**Check 3**: Verify timer functions deployed
```bash
az functionapp function list --name pei-dashboard --resource-group PeiDashboard
```

**Check 4**: Check Application Insights for errors
- Azure Portal → Application Insights → Logs
- Query: `exceptions | where timestamp > ago(1h)`

---

## 📈 Success Metrics

### Deployment Success
- ✅ 4 timer functions deployed
- ✅ All schedules configured
- ✅ Function App restarted

### Runtime Success (Per Timer)
- ✅ Timer triggers at scheduled time
- ✅ Logs show execution started
- ✅ Scraping/analysis completes
- ✅ Data saved to database
- ✅ No errors in logs

---

## 🔗 Related Files

- **Timer Fix Documentation**: `TIMER_FIX_DEPLOYMENT.md`
- **Monitoring Guide**: `MONITORING_GUIDE.md`
- **Status Check Script**: `check_function_status.ps1`
- **Deployment Summary**: `DEPLOYMENT_FINAL_SUMMARY.md`

---

## 📞 Quick Reference

### Important Times (WIB)
```
05:20 → Morning scraping starts
05:30 → Afternoon scraping starts
05:40 → Weekly summary starts
05:50 → Monthly aggregation starts
06:00 → All timers should be complete
```

### Important URLs
- **Azure Portal**: https://portal.azure.com
- **Function App**: https://portal.azure.com/#@/resource/.../pei-dashboard
- **Application Insights**: Search "pei-dashboard" in portal

### Important Commands
```bash
# Check status
az functionapp show --name pei-dashboard --resource-group PeiDashboard

# Restart
az functionapp restart --name pei-dashboard --resource-group PeiDashboard

# View logs
func azure functionapp logstream pei-dashboard
```

---

**Status**: ✅ Schedules Configured  
**Next Execution**: 05:20 WIB (22:20 UTC)  
**Monitoring**: Azure Portal + Application Insights

**Ready for production! 🚀**
