# ✅ Checklist Migrasi ke Azure

## 📋 Quick Reference Checklist

Gunakan checklist ini untuk tracking progress migrasi. Centang setiap item setelah selesai.

---

## 📌 Resource Yang Sudah Ada

| Resource | Nama |
|----------|------|
| Resource Group | `PeiDashboard` |
| Key Vault | `PeiDashboard` |
| SQL Server | `pei-dashboard` |
| SQL Database | `pei-dashboard` |
| Function App | `pei-dashboard` |
| Function URL | `pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net` |
| Location | Canada Central |

---

## Phase 1: Persiapan (Estimasi: 2-3 jam)

### Tools & Software
- [ ] Azure CLI installed dan tested
- [ ] Azure Functions Core Tools installed
- [ ] Python 3.9+ installed
- [ ] Git installed
- [ ] Visual Studio Code installed (optional)
- [ ] Login ke Azure berhasil (`az login`)
- [ ] Subscription dipilih (`az account set`)

### Dokumentasi
- [ ] Baca `MIGRATION_GUIDE.md` lengkap
- [ ] Baca `IMPLEMENTATION_COMPLETE.md`
- [ ] Siapkan file `deployment-info.txt` untuk catat info penting

### Data Preparation
- [ ] Backup semua data Excel yang ada
- [ ] Verifikasi data Excel bisa dibuka
- [ ] Catat lokasi file Excel

---

## Phase 2: Setup Azure Resources (Estimasi: 3-4 jam)

### Resource Groups ✅
- [x] Resource Group: `PeiDashboard` (sudah ada)

### Azure SQL Database ✅
- [x] SQL Server: `pei-dashboard` (sudah ada)
- [x] SQL Database: `pei-dashboard` (sudah ada)
- [ ] Catat SQL admin username: `sqladmin`
- [ ] Catat SQL admin password: `___________` ⚠️ SIMPAN AMAN!
- [ ] Configure firewall untuk Azure services
- [ ] Configure firewall untuk IP lokal Anda
- [ ] Get connection string dan simpan
- [ ] Jalankan `database_schema.sql`
- [ ] Verifikasi tables sudah dibuat

### Azure Storage Account
- [ ] Buat Storage Account dengan nama unik
- [ ] Catat Storage Account name: `stpeidashboard___________`
- [ ] Buat container: `temp-files`
- [ ] Buat container: `processing`
- [ ] Buat container: `backups`
- [ ] Buat container: `archive`
- [ ] Get connection string dan simpan

### Azure Key Vault ✅
- [x] Key Vault: `PeiDashboard` (sudah ada)
- [ ] Simpan secret: `DatabaseConnectionString`
- [ ] Simpan secret: `StorageConnectionString`
- [ ] Simpan secret: `CopilotApiKey` (placeholder dulu)
- [ ] Simpan secret: `CopilotEndpoint` (placeholder dulu)

---

## Phase 3: Setup Copilot/OpenAI (Estimasi: 1-2 jam)

### Microsoft Copilot atau Azure OpenAI
- [ ] Pilih: [ ] Microsoft Copilot atau [ ] Azure OpenAI
- [ ] Buat resource (jika Azure OpenAI)
- [ ] Deploy model GPT-4 (jika Azure OpenAI)
- [ ] Get API key
- [ ] Get endpoint URL
- [ ] Update Key Vault dengan API key
- [ ] Update Key Vault dengan endpoint
- [ ] Test API connection (optional)

---

## Phase 4: Setup Azure Functions (Estimasi: 2-3 jam)

### Function App ✅
- [x] Function App: `pei-dashboard` (sudah ada)
- [x] URL: `pei-dashboard-f5eebmdhe2a9dfgs.canadacentral-01.azurewebsites.net`
- [x] Location: Canada Central
- [x] OS: Linux
- [ ] Enable Managed Identity
- [ ] Catat Principal ID: `___________`
- [ ] Grant Key Vault access ke Managed Identity
- [ ] Configure Application Settings (Key Vault references)
- [ ] Buat Application Insights
- [ ] Link Application Insights ke Function App
- [ ] Catat Instrumentation Key

### Local Testing (Optional)
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Set local environment variables
- [ ] Test functions locally: `func start`
- [ ] Test dengan Postman/curl

---

## Phase 5: Data Migration (Estimasi: 2-4 jam)

### Excel to SQL Migration
- [ ] Review migration script: `shared/excel_migration.py`
- [ ] Set environment variables untuk connection
- [ ] Backup database sebelum migration
- [ ] Jalankan migration script
- [ ] Verifikasi jumlah records di database
- [ ] Check data integrity
- [ ] Verifikasi foreign keys
- [ ] Test query beberapa data

### Validation Queries
```sql
-- Jalankan queries ini untuk validasi
- [ ] SELECT COUNT(*) FROM news_articles
- [ ] SELECT COUNT(*) FROM news_sources
- [ ] SELECT COUNT(*) FROM sentiment_analyses
- [ ] SELECT TOP 10 * FROM news_articles ORDER BY scraped_date DESC
```

---

## Phase 6: Deployment (Estimasi: 1-2 jam)

### Deploy Functions
- [ ] Review semua code di `azure_functions/`
- [ ] Pastikan `requirements.txt` lengkap
- [ ] Deploy: `func azure functionapp publish func-pei-dashboard-[NAMA]`
- [ ] Tunggu deployment selesai (5-10 menit)
- [ ] Verifikasi semua functions ter-deploy
- [ ] List functions: `az functionapp function list`

### Verify Deployment
- [ ] Check function status di Azure Portal
- [ ] Verify environment variables loaded
- [ ] Check Application Insights connection
- [ ] Review deployment logs

---

## Phase 7: Testing (Estimasi: 3-4 jam)

### Individual Function Tests
- [ ] Test CNBC scraper
- [ ] Test CNN scraper
- [ ] Test Reuters scraper
- [ ] Test Kompas scraper
- [ ] Test Tempo scraper
- [ ] Test sentiment analysis function
- [ ] Test aggregator function
- [ ] Test deduplication function
- [ ] Test backup function

### Integration Tests
- [ ] Test full scraping workflow
- [ ] Test data processing pipeline
- [ ] Test sentiment analysis end-to-end
- [ ] Test scheduler triggers
- [ ] Test error handling
- [ ] Test retry mechanisms

### Database Tests
- [ ] Verify data insertion
- [ ] Check deduplication working
- [ ] Test database queries
- [ ] Verify indexes working
- [ ] Check foreign key constraints

### Unit Tests
- [ ] Run: `pytest tests/ -v`
- [ ] All tests passing: ___/14 tests

---

## Phase 8: Monitoring Setup (Estimasi: 1-2 jam)

### Application Insights
- [ ] Create custom dashboard
- [ ] Add function execution metrics
- [ ] Add success rate chart
- [ ] Add response time chart
- [ ] Add error rate chart
- [ ] Configure alerts untuk failures
- [ ] Configure alerts untuk high latency
- [ ] Test alerts dengan dummy error

### Log Analytics
- [ ] Enable diagnostic logs
- [ ] Configure log retention
- [ ] Create custom queries
- [ ] Setup log alerts

### Cost Monitoring
- [ ] Setup cost alerts
- [ ] Review pricing calculator
- [ ] Estimate monthly costs: $___________

---

## Phase 9: Security Review (Estimasi: 1 jam)

### Security Checklist
- [ ] Verify Managed Identity digunakan
- [ ] Check Key Vault access policies
- [ ] Review firewall rules
- [ ] Verify no hardcoded secrets
- [ ] Check HTTPS only
- [ ] Review CORS settings
- [ ] Verify authentication enabled
- [ ] Check authorization rules

---

## Phase 10: Documentation (Estimasi: 1 jam)

### Update Documentation
- [ ] Update `deployment-info.txt` dengan semua info
- [ ] Document connection strings (secure location)
- [ ] Document API endpoints
- [ ] Document monitoring dashboards
- [ ] Create runbook untuk common tasks
- [ ] Document troubleshooting steps
- [ ] Create team training materials

---

## Phase 11: Go Live Preparation (Estimasi: 2-3 jam)

### Pre-Launch
- [ ] Review semua checklist di atas
- [ ] Backup production database
- [ ] Notify stakeholders
- [ ] Schedule go-live time
- [ ] Prepare rollback plan
- [ ] Assign on-call person

### Launch Day
- [ ] Enable schedulers
- [ ] Monitor first executions
- [ ] Check logs setiap 30 menit
- [ ] Verify data collection
- [ ] Monitor costs
- [ ] Document any issues

### Post-Launch (First 24 Hours)
- [ ] Hour 1: Check all functions running
- [ ] Hour 2: Verify data in database
- [ ] Hour 4: Review error logs
- [ ] Hour 8: Check performance metrics
- [ ] Hour 12: Verify backups running
- [ ] Hour 24: Full system review

---

## Phase 12: Parallel Running (Optional, 1-2 minggu)

### Week 1
- [ ] Run old and new system parallel
- [ ] Compare results daily
- [ ] Document differences
- [ ] Fix any issues
- [ ] Monitor performance

### Week 2
- [ ] Continue monitoring
- [ ] Validate data accuracy
- [ ] Get user feedback
- [ ] Make final adjustments
- [ ] Prepare for cutover

---

## Phase 13: Cutover & Decommission (Estimasi: 1 hari)

### Cutover
- [ ] Final backup of old system
- [ ] Stop old system
- [ ] Verify new system handling all load
- [ ] Update all documentation
- [ ] Notify all stakeholders
- [ ] Update DNS/endpoints if needed

### Decommission Old System
- [ ] Archive old code
- [ ] Archive old data
- [ ] Document lessons learned
- [ ] Celebrate success! 🎉

---

## 📊 Progress Tracking

### Overall Progress
- Phase 1: Persiapan [ ] 0% [ ] 50% [ ] 100%
- Phase 2: Azure Resources [ ] 0% [ ] 50% [ ] 100%
- Phase 3: Copilot Setup [ ] 0% [ ] 50% [ ] 100%
- Phase 4: Functions Setup [ ] 0% [ ] 50% [ ] 100%
- Phase 5: Data Migration [ ] 0% [ ] 50% [ ] 100%
- Phase 6: Deployment [ ] 0% [ ] 50% [ ] 100%
- Phase 7: Testing [ ] 0% [ ] 50% [ ] 100%
- Phase 8: Monitoring [ ] 0% [ ] 50% [ ] 100%
- Phase 9: Security [ ] 0% [ ] 50% [ ] 100%
- Phase 10: Documentation [ ] 0% [ ] 50% [ ] 100%
- Phase 11: Go Live [ ] 0% [ ] 50% [ ] 100%
- Phase 12: Parallel Run [ ] 0% [ ] 50% [ ] 100%
- Phase 13: Cutover [ ] 0% [ ] 50% [ ] 100%

### Timeline
- Start Date: ___/___/______
- Target Go-Live: ___/___/______
- Actual Go-Live: ___/___/______

### Team
- Project Lead: ___________
- Azure Admin: ___________
- Developer: ___________
- Tester: ___________
- On-Call: ___________

---

## 🆘 Emergency Contacts

### Azure Support
- Support Portal: https://portal.azure.com/#blade/Microsoft_Azure_Support/HelpAndSupportBlade
- Phone: ___________

### Team Contacts
- Lead: ___________ (Phone: ___________)
- Backup: ___________ (Phone: ___________)

---

## 📝 Notes & Issues

### Issues Encountered
```
Date: ___/___/______
Issue: 
Solution:

Date: ___/___/______
Issue:
Solution:
```

### Lessons Learned
```
1. 
2.
3.
```

---

## ✅ Sign-Off

### Phase Approvals
- [ ] Phase 1-5 Approved by: ___________ Date: ___/___/______
- [ ] Phase 6-10 Approved by: ___________ Date: ___/___/______
- [ ] Phase 11-13 Approved by: ___________ Date: ___/___/______

### Final Sign-Off
- [ ] System Live and Stable
- [ ] All Tests Passing
- [ ] Monitoring Active
- [ ] Documentation Complete
- [ ] Team Trained

**Signed:** ___________ **Date:** ___/___/______

---

**🎉 Congratulations! Migration Complete!**

*Checklist ini dibuat: 27 Januari 2026*
*Versi: 1.0*
