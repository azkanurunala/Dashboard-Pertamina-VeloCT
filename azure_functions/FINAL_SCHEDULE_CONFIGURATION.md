# ✅ Final Schedule Configuration - PEI Dashboard

**Tanggal Update**: 16 Februari 2026  
**Status**: ✅ CONFIGURED & ACTIVE  
**Timezone**: WIB (UTC+7)

---

## 📅 Production Schedules (WIB)

### Timer Functions Schedule

| Timer | WIB Time | UTC Time | Cron Expression | Frequency |
|-------|----------|----------|-----------------|-----------|
| **Morning** | 05:00 WIB | 22:00 UTC | `0 0 22 * * *` | Daily |
| **Afternoon** | 05:10 WIB | 22:10 UTC | `0 10 22 * * *` | Daily |
| **Weekly** | 05:20 WIB | 22:20 UTC | `0 20 22 * * *` | Daily |
| **Monthly** | 05:30 WIB | 22:30 UTC | `0 30 22 * * *` | Daily |

---

## 🔧 Configuration Details

### Environment Variables Set in Azure

```bash
MORNING_TIMER_SCHEDULE="0 0 22 * * *"
AFTERNOON_TIMER_SCHEDULE="0 10 22 * * *"
WEEKLY_TIMER_SCHEDULE="0 20 22 * * *"
MONTHLY_TIMER_SCHEDULE="0 30 22 * * *"
```

### What Each Timer Does

#### 1. Morning Timer (05:00 WIB / 22:00 UTC)
**File**: `daily_morning_timer/function.json`  
**Logic**: `../src/scheduling/scheduling_day_morning.py`

**Tasks**:
- News Scraping (Local Indonesian sources)
- CPO Price Scraping
- News Sentiment Summarization (Daily)

**Sources**:
- Kompas, Tempo, Kontan, Bisnis Indonesia, CNBC Indonesia, etc.
- CPO price data
- Sentiment analysis for local news

#### 2. Afternoon Timer (05:10 WIB / 22:10 UTC)
**File**: `daily_afternoon_timer/function.json`  
**Logic**: `../src/scheduling/scheduling_day_afternoon.py`

**Tasks**:
- International News Scraping
- International News Sentiment Summarization
- SAF & Crackspeed Data Scraping

**Sources**:
- CNN, Reuters, The Guardian, SCMP, etc.
- S&P Global data (SAF, Crackspeed BBM, Crackspread Non-BBM)

#### 3. Weekly Timer (05:20 WIB / 22:20 UTC)
**File**: `weekly_summary_timer/function.json`  
**Logic**: `../src/scheduling/scheduling_week.py`

**Tasks**:
- Weekly News Sentiment Summarization
- S&P Weekly Data Scraping

**Note**: Currently runs daily for testing. For production, change to:
- `0 20 22 * * 1` (Monday only)

#### 4. Monthly Timer (05:30 WIB / 22:30 UTC)
**File**: `monthly_aggregation_timer/function.json`  
**Logic**: `../src/scheduling/scheduling_month.py`

**Tasks**:
- EIA Data Scraping
- ESDM Price Data Scraping
- Biodiesel ESDM Data Scraping
- Bioetanol ESDM Data Scraping
- Petrochemical & Price Forecast (on 12th of month)
- SIPSN & IAEA Data Scraping (on 15th of month)

**Note**: Currently runs daily for testing. For production, change to:
- `0 30 22 1 * *` (1st of month only)

---

## 🕐 Timezone Conversion Reference

### WIB to UTC Conversion
**WIB = UTC + 7 hours**  
**UTC = WIB - 7 hours**

| WIB Time | UTC Time (Previous Day) |
|----------|-------------------------|
| 00:00 WIB | 17:00 UTC |
| 01:00 WIB | 18:00 UTC |
| 02:00 WIB | 19:00 UTC |
| 03:00 WIB | 20:00 UTC |
| 04:00 WIB | 21:00 UTC |
| **05:00 WIB** | **22:00 UTC** ⭐ |
| 06:00 WIB | 23:00 UTC |
| 07:00 WIB | 00:00 UTC (same day) |
| 12:00 WIB | 05:00 UTC |
| 18:00 WIB | 11:00 UTC |

---

## 📝 Cron Expression Format

```
┌───────────── second (0-59)
│ ┌───────────── minute (0-59)
│ │ ┌───────────── hour (0-23)
│ │ │ ┌───────────── day of month (1-31)
│ │ │ │ ┌───────────── month (1-12)
│ │ │ │ │ ┌───────────── day of week (0-6) (Sunday=0)
│ │ │ │ │ │
* * * * * *
```

### Examples
```
0 0 22 * * *     = 22:00 UTC every day (05:00 WIB)
0 10 22 * * *    = 22:10 UTC every day (05:10 WIB)
0 20 22 * * 1    = 22:20 UTC every Monday (05:20 WIB Monday)
0 30 22 1 * *    = 22:30 UTC on 1st of month (05:30 WIB on 1st)
```

---

## 🔄 Future Production Schedules

### Recommended Changes for Production

When ready for production, update to proper weekly/monthly schedules:

```bash
# Keep daily schedules
MORNING_TIMER_SCHEDULE="0 0 22 * * *"      # 05:00 WIB daily
AFTERNOON_TIMER_SCHEDULE="0 10 22 * * *"   # 05:10 WIB daily

# Change to actual weekly (Monday only)
WEEKLY_TIMER_SCHEDULE="0 20 22 * * 1"      # 05:20 WIB every Monday

# Change to actual monthly (1st of month only)
MONTHLY_TIMER_SCHEDULE="0 30 22 1 * *"     # 05:30 WIB on 1st of month
```

### Update Command
```bash
az functionapp config appsettings set \
  --name pei-dashboard \
  --resource-group PeiDashboard \
  --settings \
    "WEEKLY_TIMER_SCHEDULE=0 20 22 * * 1" \
    "MONTHLY_TIMER_SCHEDULE=0 30 22 1 * *"
```

---

## 🧪 Testing & Monitoring

### Verify Schedules
```bash
# Check current schedules
az functionapp config appsettings list \
  --name pei-dashboard \
  --resource-group PeiDashboard \
  --query "[?contains(name, 'TIMER_SCHEDULE')].{Name:name, Value:value}" \
  --output table
```

### Monitor Timer Executions
```bash
# Stream logs
func azure functionapp logstream pei-dashboard

# Or in Azure Portal
# Portal → Function App → Functions → [timer function] → Monitor
```

### Check Next Run Time
1. Azure Portal → Function App → Functions
2. Click on timer function (e.g., `daily_morning_timer`)
3. Go to "Monitor" tab
4. Check "Invocations" for execution history
5. Next run time shown in function overview

---

## ⚠️ Important Notes

### 1. Current Configuration (Testing)
- All timers run **DAILY** for testing purposes
- 10-minute intervals between timers
- Runs at night UTC (morning WIB)

### 2. Timezone Awareness
- Azure Functions uses **UTC** by default
- All cron expressions are in **UTC**
- Schedule shows as previous day in UTC (e.g., 05:00 WIB = 22:00 UTC previous day)

### 3. Restart Required
- Function App was restarted after schedule update
- Changes take effect immediately after restart
- Monitor first execution to confirm timing

### 4. Execution Order
```
22:00 UTC (05:00 WIB) → Morning Timer
  ↓ 10 minutes
22:10 UTC (05:10 WIB) → Afternoon Timer
  ↓ 10 minutes
22:20 UTC (05:20 WIB) → Weekly Timer
  ↓ 10 minutes
22:30 UTC (05:30 WIB) → Monthly Timer
```

---

## 📊 Execution Timeline (WIB)

### Daily Execution Flow

```
05:00 WIB - Morning Timer Starts
├─ News Scraping (Local)
├─ Wait 60 seconds
├─ CPO Price Scraping
├─ Wait 60 seconds
└─ Sentiment Analysis (Local)

05:10 WIB - Afternoon Timer Starts
├─ News Scraping (International)
├─ Wait 60 seconds
├─ Sentiment Analysis (International)
├─ Wait 60 seconds
└─ SAF & Crackspeed Scraping

05:20 WIB - Weekly Timer Starts
├─ Weekly Sentiment Summarization
└─ S&P Weekly Data

05:30 WIB - Monthly Timer Starts
├─ EIA Data
├─ ESDM Price Data
├─ Biodiesel ESDM
├─ Bioetanol ESDM
├─ [12th] Petrochemical & Price Forecast
└─ [15th] SIPSN & IAEA Data
```

---

## 🔗 Related Files

### Timer Function Configurations
- `daily_morning_timer/function.json`
- `daily_afternoon_timer/function.json`
- `weekly_summary_timer/function.json`
- `monthly_aggregation_timer/function.json`

### Scheduler Logic
- `orchestration/scheduler_function.py`

### Scheduling Scripts (Reference)
- `../src/scheduling/scheduling_day_morning.py`
- `../src/scheduling/scheduling_day_afternoon.py`
- `../src/scheduling/scheduling_week.py`
- `../src/scheduling/scheduling_month.py`

---

## ✅ Verification Checklist

- [x] Schedules configured in Azure
- [x] Timezone conversion verified (WIB → UTC)
- [x] Function App restarted
- [ ] Monitor first execution at 05:00 WIB
- [ ] Verify all 4 timers execute successfully
- [ ] Check logs for any errors
- [ ] Confirm data is being scraped correctly

---

## 📞 Quick Commands

### View Current Schedules
```bash
az functionapp config appsettings list --name pei-dashboard --resource-group PeiDashboard --query "[?contains(name, 'TIMER_SCHEDULE')]" --output table
```

### Restart Function App
```bash
az functionapp restart --name pei-dashboard --resource-group PeiDashboard
```

### Stream Logs
```bash
func azure functionapp logstream pei-dashboard
```

### Test Timer Manually
```bash
# Get function key
az functionapp keys list --name pei-dashboard --resource-group PeiDashboard

# Trigger manually (if HTTP trigger is enabled)
curl "https://pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net/api/daily_morning_timer?code=YOUR_KEY"
```

---

**Status**: ✅ ACTIVE  
**Next Execution**: 05:00 WIB (22:00 UTC) Daily  
**Last Updated**: 16 Februari 2026  

**Catatan**: Schedule saat ini untuk testing (semua berjalan daily). Untuk production, ubah Weekly ke Monday only dan Monthly ke 1st of month only.
