# ⚠️ Scheduler Configuration Issue - URGENT

**Tanggal**: 16 Februari 2026  
**Status**: 🔴 CRITICAL - Timer schedules tidak dikonfigurasi di Azure  
**Impact**: Timer functions tidak akan berjalan otomatis

---

## 🔍 Masalah yang Ditemukan

### 1. Timer Schedules TIDAK ADA di Azure
Setelah deployment, ditemukan bahwa **environment variables untuk timer schedules tidak ada di Azure configuration**.

**Yang Hilang**:
- `MORNING_TIMER_SCHEDULE`
- `AFTERNOON_TIMER_SCHEDULE`
- `WEEKLY_TIMER_SCHEDULE`
- `MONTHLY_TIMER_SCHEDULE`

### 2. Local Settings Menggunakan Testing Schedule
File `local.settings.json` masih menggunakan **testing schedules**:

```json
{
  "MORNING_TIMER_SCHEDULE": "0 10 6 * * *",      // 6:10 AM daily (TESTING)
  "AFTERNOON_TIMER_SCHEDULE": "0 15 6 * * *",    // 6:15 AM daily (TESTING)
  "WEEKLY_TIMER_SCHEDULE": "0 20 6 * * *",       // 6:20 AM daily (TESTING)
  "MONTHLY_TIMER_SCHEDULE": "0 25 6 * * *"       // 6:25 AM daily (TESTING)
}
```

**Masalah**:
- Semua schedule berjalan di jam 6 pagi (tidak realistis untuk production)
- Weekly dan Monthly berjalan SETIAP HARI (seharusnya weekly/monthly)
- Interval hanya 5 menit antar timer (untuk testing saja)

---

## 🎯 Solusi

### Opsi 1: Gunakan Script Otomatis (Recommended)

Jalankan script yang sudah disiapkan:

```powershell
powershell -ExecutionPolicy Bypass -File update_production_schedules.ps1
```

Script ini akan:
1. Menampilkan schedule testing vs production
2. Meminta konfirmasi
3. Update semua schedules di Azure
4. Verifikasi hasil update

### Opsi 2: Manual Update via Azure CLI

```bash
# Morning Timer - 6:00 AM daily
az functionapp config appsettings set \
  --name pei-dashboard \
  --resource-group PeiDashboard \
  --settings "MORNING_TIMER_SCHEDULE=0 0 6 * * *"

# Afternoon Timer - 2:00 PM daily
az functionapp config appsettings set \
  --name pei-dashboard \
  --resource-group PeiDashboard \
  --settings "AFTERNOON_TIMER_SCHEDULE=0 0 14 * * *"

# Weekly Timer - 8:00 AM every Monday
az functionapp config appsettings set \
  --name pei-dashboard \
  --resource-group PeiDashboard \
  --settings "WEEKLY_TIMER_SCHEDULE=0 0 8 * * 1"

# Monthly Timer - 9:00 AM on 1st of month
az functionapp config appsettings set \
  --name pei-dashboard \
  --resource-group PeiDashboard \
  --settings "MONTHLY_TIMER_SCHEDULE=0 0 9 1 * *"
```

### Opsi 3: Manual Update via Azure Portal

1. Buka Azure Portal
2. Navigate ke Function App: `pei-dashboard`
3. Settings → Configuration → Application settings
4. Klik "+ New application setting"
5. Tambahkan setiap schedule:
   - Name: `MORNING_TIMER_SCHEDULE`, Value: `0 0 6 * * *`
   - Name: `AFTERNOON_TIMER_SCHEDULE`, Value: `0 0 14 * * *`
   - Name: `WEEKLY_TIMER_SCHEDULE`, Value: `0 0 8 * * 1`
   - Name: `MONTHLY_TIMER_SCHEDULE`, Value: `0 0 9 1 * *`
6. Klik "Save"
7. Restart Function App

---

## 📅 Proposed Production Schedules

### Recommended Schedules

| Timer | Schedule | Description | Cron Expression |
|-------|----------|-------------|-----------------|
| **Morning** | 6:00 AM daily | Morning scraping run | `0 0 6 * * *` |
| **Afternoon** | 2:00 PM daily | Afternoon scraping run | `0 0 14 * * *` |
| **Weekly** | 8:00 AM Monday | Weekly summary | `0 0 8 * * 1` |
| **Monthly** | 9:00 AM 1st | Monthly aggregation | `0 0 9 1 * *` |

### Cron Expression Format

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
0 0 6 * * *     = 6:00 AM every day
0 0 14 * * *    = 2:00 PM every day
0 0 8 * * 1     = 8:00 AM every Monday
0 0 9 1 * *     = 9:00 AM on 1st of every month
0 30 12 * * *   = 12:30 PM every day
0 0 0 * * 0     = Midnight every Sunday
```

---

## 🔧 Customization Guide

Jika Anda ingin schedule yang berbeda, edit nilai di script atau gunakan custom cron:

### Common Patterns

**Hourly**:
```
0 0 * * * *     = Every hour at minute 0
0 30 * * * *    = Every hour at minute 30
```

**Multiple times per day**:
```
0 0 6,12,18 * * *   = 6 AM, 12 PM, 6 PM daily
0 0 */4 * * *       = Every 4 hours
```

**Specific days**:
```
0 0 9 * * 1-5   = 9 AM Monday to Friday
0 0 10 * * 6,0  = 10 AM Saturday and Sunday
```

**Specific dates**:
```
0 0 9 1,15 * *  = 9 AM on 1st and 15th of month
0 0 8 * 1,7 *   = 8 AM every day in Jan and July
```

---

## ⚠️ Important Notes

### 1. Timezone
Azure Functions menggunakan **UTC timezone** by default. Pastikan schedule sudah disesuaikan dengan timezone yang diinginkan.

**Contoh**: Jika ingin 6 AM WIB (UTC+7):
- 6 AM WIB = 11 PM UTC (previous day)
- Cron: `0 0 23 * * *`

### 2. Restart Required
Setelah update schedules, **restart Function App**:
```bash
az functionapp restart --name pei-dashboard --resource-group PeiDashboard
```

### 3. Monitor First Run
Setelah restart, monitor logs untuk memastikan timer trigger dengan benar:
```bash
func azure functionapp logstream pei-dashboard
```

---

## 🧪 Testing Schedules

### Test dengan Schedule Dekat
Untuk testing, gunakan schedule yang akan trigger dalam beberapa menit:

```bash
# Get current UTC time
date -u

# Set timer to trigger in 5 minutes
# If current time is 14:30 UTC, set to 14:35
az functionapp config appsettings set \
  --name pei-dashboard \
  --resource-group PeiDashboard \
  --settings "MORNING_TIMER_SCHEDULE=0 35 14 * * *"
```

### Verify Timer Execution
1. Azure Portal → Function App → Functions → `daily_morning_timer`
2. Click "Monitor"
3. Check "Invocations" tab for execution history

---

## 📊 Current Status

### Azure Configuration (Before Fix)
```json
{
  "MORNING_TIMER_SCHEDULE": "NOT SET ❌",
  "AFTERNOON_TIMER_SCHEDULE": "NOT SET ❌",
  "WEEKLY_TIMER_SCHEDULE": "NOT SET ❌",
  "MONTHLY_TIMER_SCHEDULE": "NOT SET ❌"
}
```

### Expected After Fix
```json
{
  "MORNING_TIMER_SCHEDULE": "0 0 6 * * * ✅",
  "AFTERNOON_TIMER_SCHEDULE": "0 0 14 * * * ✅",
  "WEEKLY_TIMER_SCHEDULE": "0 0 8 * * 1 ✅",
  "MONTHLY_TIMER_SCHEDULE": "0 0 9 1 * * ✅"
}
```

---

## 🔗 Related Files

- **Timer Functions**:
  - `daily_morning_timer/function.json`
  - `daily_afternoon_timer/function.json`
  - `weekly_summary_timer/function.json`
  - `monthly_aggregation_timer/function.json`

- **Scheduler Logic**:
  - `orchestration/scheduler_function.py`

- **Configuration**:
  - `local.settings.json` (local only, not deployed)

---

## 📝 Action Items

### Immediate (URGENT)
- [ ] Tentukan production schedules yang benar
- [ ] Jalankan `update_production_schedules.ps1` atau update manual
- [ ] Restart Function App
- [ ] Verify schedules di Azure Portal

### Short-term
- [ ] Monitor first timer execution
- [ ] Update `local.settings.json` dengan production schedules
- [ ] Document final schedules in README
- [ ] Setup alerts for timer failures

### Long-term
- [ ] Review and optimize timer schedules based on usage
- [ ] Consider timezone adjustments if needed
- [ ] Implement monitoring dashboard for timer executions

---

## 🆘 Troubleshooting

### Timer Not Triggering
1. Check schedule is set in Azure: `az functionapp config appsettings list`
2. Verify cron expression is valid
3. Check Function App is running: `az functionapp show`
4. Review logs: `func azure functionapp logstream pei-dashboard`

### Wrong Execution Time
1. Verify timezone (Azure uses UTC)
2. Check cron expression
3. Restart Function App after changes

### Timer Triggering Too Often
1. Check for duplicate schedules
2. Verify cron expression (especially day of week/month)
3. Review execution history in Azure Portal

---

**Priority**: 🔴 CRITICAL  
**Action Required**: YES - Configure schedules immediately  
**Estimated Time**: 5-10 minutes  
**Risk if Not Fixed**: Timer functions will never run automatically

---

**Next Step**: Run `update_production_schedules.ps1` or manually configure schedules in Azure Portal.
