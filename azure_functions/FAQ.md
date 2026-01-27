# ❓ FAQ - Frequently Asked Questions

## Pertanyaan Umum Tentang Migrasi ke Azure

---

## 📋 General Questions

### Q: Berapa lama waktu yang dibutuhkan untuk migrasi lengkap?
**A:** Estimasi waktu:
- **Setup Azure Resources:** 1-2 hari (6-8 jam)
- **Data Migration:** 1 hari (4-6 jam)
- **Deployment & Testing:** 2-3 hari (8-12 jam)
- **Monitoring & Go Live:** 1 hari (4-6 jam)
- **Total:** 5-7 hari kerja (20-30 jam)

Dengan tim yang berpengalaman, bisa lebih cepat (3-4 hari).

### Q: Apakah sistem lama harus dimatikan selama migrasi?
**A:** Tidak! Sistem lama tetap berjalan. Kita akan:
1. Build sistem baru di Azure secara parallel
2. Migrasi data historis
3. Test sistem baru
4. Run parallel 1-2 minggu (optional)
5. Cutover ke sistem baru

### Q: Apakah data akan hilang?
**A:** Tidak. Kita akan:
- Backup semua data Excel sebelum migrasi
- Migrasi data ke SQL Server
- Validasi data setelah migrasi
- Keep backup Excel files
- Sistem lama tetap ada sebagai backup

### Q: Berapa biaya bulanan untuk Azure?
**A:** Estimasi biaya:
- Azure Functions: $8-10/bulan
- Azure SQL Database (S0): $15/bulan
- Azure Storage: $2-5/bulan
- Azure OpenAI: $50-200/bulan (tergantung usage)
- **Total: $75-230/bulan**

Bisa lebih murah dengan reserved instances atau optimization.

---

## 🔧 Technical Questions

### Q: Apakah perlu 3 Azure subscriptions terpisah?
**A:** Tidak wajib, tapi **sangat direkomendasikan** untuk security:
- Subscription 1: Azure Functions
- Subscription 2: Azure SQL Database
- Subscription 3: Microsoft Copilot/OpenAI

Jika budget terbatas, bisa gunakan 1 subscription dengan 3 resource groups terpisah.

### Q: Kenapa pakai Azure SQL Database, bukan Excel?
**A:** Keuntungan SQL Database:
- ✅ Scalable (bisa handle jutaan records)
- ✅ Concurrent access (multiple users)
- ✅ ACID transactions (data integrity)
- ✅ Automated backups
- ✅ Query performance (indexes)
- ✅ Security (encryption, access control)
- ✅ Integration dengan Azure services

Excel bagus untuk small data, tapi tidak scalable untuk production.

### Q: Apakah bisa pakai database lain (PostgreSQL, MySQL)?
**A:** Bisa! Code sudah dibuat modular. Tinggal:
1. Ganti connection string
2. Adjust SQL syntax (minor changes)
3. Update `database_handler.py`

Tapi Azure SQL Database paling terintegrasi dengan Azure ecosystem.

### Q: Kenapa pakai Microsoft Copilot, bukan Google Gemini?
**A:** Alasan:
- ✅ Better integration dengan Azure
- ✅ Enterprise-grade security
- ✅ Managed identity support
- ✅ Better for Indonesian language
- ✅ Compliance & data residency

Tapi code bisa di-adjust untuk Gemini jika diperlukan.

### Q: Apakah perlu Azure Functions Premium Plan?
**A:** Tidak untuk start. Consumption Plan sudah cukup:
- Pay per execution
- Auto-scaling
- Cost-effective

Upgrade ke Premium jika:
- Need VNet integration
- Need longer execution time (>10 min)
- Need always-on instances
- High traffic (>1M executions/month)

### Q: Bagaimana cara handle rate limiting dari news websites?
**A:** Sudah di-handle di code:
- Exponential backoff retry
- Configurable delays between requests
- User-agent rotation
- Respect robots.txt
- Circuit breaker pattern

Bisa adjust di `scrapers/base_scraper.py`.

---

## 🔒 Security Questions

### Q: Apakah data aman di Azure?
**A:** Ya, dengan implementasi:
- ✅ Encryption at rest (database & storage)
- ✅ Encryption in transit (HTTPS/TLS)
- ✅ Azure Key Vault untuk secrets
- ✅ Managed Identity (no hardcoded passwords)
- ✅ Network security groups
- ✅ Azure AD authentication
- ✅ RBAC (Role-Based Access Control)

### Q: Bagaimana cara manage passwords dan API keys?
**A:** Menggunakan Azure Key Vault:
- Semua secrets disimpan di Key Vault
- Functions access via Managed Identity
- No secrets in code atau config files
- Automatic rotation support
- Audit logs untuk access

### Q: Apakah perlu VPN untuk access database?
**A:** Tidak wajib untuk start. Bisa gunakan:
1. **Azure Firewall Rules** (allow specific IPs)
2. **Azure Private Link** (private connection)
3. **VPN Gateway** (site-to-site VPN)

Untuk production, rekomendasikan Private Link atau VPN.

### Q: Bagaimana cara backup dan recovery?
**A:** Automated backup system:
- Daily full backups
- Hourly differential backups
- 30-day retention policy
- Point-in-time recovery
- Backup validation
- Documented recovery procedures

Lihat: `backup/database_backup.py` dan `backup/database_recovery.py`

---

## 📊 Data & Migration Questions

### Q: Berapa banyak data yang bisa di-handle?
**A:** Sangat scalable:
- **Current:** Ratusan ribu articles
- **Capacity:** Jutaan articles
- **Limit:** Tergantung database tier

Azure SQL Database bisa scale up/down sesuai kebutuhan.

### Q: Bagaimana cara migrasi data Excel yang besar?
**A:** Migration script sudah handle:
- Batch processing (1000 records per batch)
- Progress tracking
- Error handling
- Data validation
- Rollback capability

Untuk data sangat besar (>1GB), bisa gunakan Azure Data Factory.

### Q: Apakah format data berubah setelah migrasi?
**A:** Tidak. Data mapping:
- Excel columns → SQL columns
- Same data types
- Same relationships
- Additional metadata (timestamps, IDs)

### Q: Bagaimana cara handle duplicate data?
**A:** Deduplication service:
- URL-based deduplication
- Automatic detection
- Keep earliest scraped article
- Configurable rules
- Manual review option

Lihat: `processing/deduplication_service.py`

---

## 🚀 Deployment Questions

### Q: Apakah bisa deploy dari local machine?
**A:** Ya! Menggunakan:
```powershell
func azure functionapp publish func-newscraper-[NAMA]
```

Atau setup CI/CD dengan:
- Azure DevOps Pipelines
- GitHub Actions
- GitLab CI/CD

### Q: Bagaimana cara rollback jika deployment gagal?
**A:** Azure Functions support:
- Deployment slots (blue-green deployment)
- Version history
- Quick rollback via Portal
- Automated rollback on failure

### Q: Apakah perlu downtime saat deployment?
**A:** Tidak! Zero-downtime deployment:
- Deploy ke staging slot
- Test di staging
- Swap staging ↔ production
- Instant rollback jika ada issue

### Q: Bagaimana cara update code setelah live?
**A:** Process:
1. Update code di local
2. Test locally
3. Deploy ke staging slot
4. Test di staging
5. Swap to production
6. Monitor

---

## 📈 Performance Questions

### Q: Berapa lama waktu execution per scraper?
**A:** Tergantung website:
- Fast sites: 10-30 detik
- Slow sites: 1-3 menit
- With rate limiting: 2-5 menit

Azure Functions timeout: 10 menit (Consumption Plan)

### Q: Berapa banyak scrapers bisa run parallel?
**A:** Azure Functions auto-scale:
- Default: 200 concurrent instances
- Bisa increase limit via support ticket
- Parallel execution di code level

### Q: Bagaimana cara optimize performance?
**A:** Optimization strategies:
- ✅ Caching (implemented)
- ✅ Database indexes (implemented)
- ✅ Connection pooling (implemented)
- ✅ Parallel execution (implemented)
- ✅ Batch processing (implemented)

Lihat: `processing/data_cache.py`

### Q: Apakah bisa handle high traffic?
**A:** Ya! Azure Functions:
- Auto-scaling
- Load balancing
- Global distribution
- CDN integration

---

## 💰 Cost Questions

### Q: Bagaimana cara monitor costs?
**A:** Azure Cost Management:
- Daily cost tracking
- Budget alerts
- Cost analysis
- Recommendations
- Export to Excel

Setup di Azure Portal > Cost Management.

### Q: Bagaimana cara reduce costs?
**A:** Cost optimization:
1. **Right-size database** (start with S0, adjust)
2. **Use reserved instances** (1-3 year commitment)
3. **Optimize function execution** (reduce duration)
4. **Use caching** (reduce database queries)
5. **Archive old data** (cheaper storage tier)
6. **Monitor unused resources**

### Q: Apakah ada free tier?
**A:** Partial:
- Azure Functions: 1M executions/month free
- Azure SQL: No free tier (minimum $5/month)
- Azure Storage: First 5GB free
- Azure OpenAI: No free tier

Total minimum: ~$20-30/month

### Q: Berapa cost untuk testing/development?
**A:** Bisa lebih murah:
- Use smaller database tier (Basic)
- Use dev/test pricing
- Delete resources saat tidak digunakan
- Use Azure Dev/Test subscription

Estimasi: $10-20/month untuk dev/test.

---

## 🔄 Operations Questions

### Q: Bagaimana cara monitoring system?
**A:** Monitoring tools:
- Application Insights (metrics, logs, traces)
- Azure Monitor (alerts, dashboards)
- Log Analytics (query logs)
- Azure Portal (visual monitoring)

Setup di Phase 8 migration guide.

### Q: Bagaimana cara troubleshooting errors?
**A:** Troubleshooting steps:
1. Check Application Insights logs
2. Check Function App logs
3. Check database connection
4. Check Key Vault access
5. Review error messages
6. Check firewall rules

Lihat: `MIGRATION_GUIDE.md` section Troubleshooting

### Q: Apakah perlu on-call person?
**A:** Recommended untuk production:
- First week: 24/7 monitoring
- After stable: Business hours support
- Setup alerts untuk critical issues
- Document runbooks

### Q: Bagaimana cara handle scheduled maintenance?
**A:** Azure handles:
- Automatic OS updates
- Security patches
- Infrastructure maintenance
- Minimal downtime (usually <1 min)

You handle:
- Application updates
- Database maintenance
- Backup verification

---

## 🎓 Training Questions

### Q: Apakah team perlu training Azure?
**A:** Recommended:
- **Azure Fundamentals** (AZ-900) - 1 day
- **Azure Functions** - 2-3 days
- **Azure SQL Database** - 1-2 days
- **Monitoring & Operations** - 1 day

Total: 1 week training

### Q: Apakah ada documentation untuk team?
**A:** Yes! Complete documentation:
- `MIGRATION_GUIDE.md` - Step-by-step guide
- `MIGRATION_CHECKLIST.md` - Tracking checklist
- `QUICK_START.md` - Quick start guide
- `FAQ.md` - This file
- `IMPLEMENTATION_COMPLETE.md` - Technical docs
- Code comments - Inline documentation

### Q: Bagaimana cara onboard new team members?
**A:** Onboarding process:
1. Read all documentation
2. Setup local development environment
3. Access Azure Portal (with limited permissions)
4. Shadow experienced team member
5. Complete small tasks
6. Gradually increase responsibilities

---

## 🌐 Integration Questions

### Q: Apakah bisa integrate dengan sistem lain?
**A:** Ya! Integration options:
- REST API (HTTP triggers)
- Azure Service Bus
- Azure Event Grid
- Azure Logic Apps
- Power Automate
- Custom webhooks

### Q: Apakah bisa export data ke Excel?
**A:** Ya! Options:
1. Query database → Export to Excel
2. Azure Data Factory → Scheduled exports
3. Power BI → Live connection
4. Custom export function

### Q: Apakah bisa integrate dengan Power BI?
**A:** Ya! Power BI bisa:
- Connect langsung ke Azure SQL
- Real-time dashboards
- Scheduled refresh
- Custom visualizations

---

## 🆘 Support Questions

### Q: Bagaimana cara get support dari Microsoft?
**A:** Support options:
1. **Azure Portal** - Submit support ticket
2. **Azure Documentation** - docs.microsoft.com
3. **Microsoft Q&A** - Community support
4. **Stack Overflow** - Tag: azure-functions
5. **GitHub Issues** - For open source components

### Q: Apakah ada SLA untuk Azure services?
**A:** Ya! SLA guarantees:
- Azure Functions: 99.95% uptime
- Azure SQL Database: 99.99% uptime
- Azure Storage: 99.9% uptime
- Azure Key Vault: 99.9% uptime

### Q: Bagaimana cara report issues?
**A:** Issue reporting:
1. Check logs di Application Insights
2. Document error messages
3. Note time of occurrence
4. Submit ticket via Azure Portal
5. Include diagnostic information

---

## 📱 Contact & Resources

### Documentation
- Migration Guide: `MIGRATION_GUIDE.md`
- Quick Start: `QUICK_START.md`
- Checklist: `MIGRATION_CHECKLIST.md`

### Azure Resources
- Azure Portal: https://portal.azure.com
- Azure Documentation: https://docs.microsoft.com/azure/
- Azure Status: https://status.azure.com/

### Support
- Azure Support: https://azure.microsoft.com/support/
- Community: https://techcommunity.microsoft.com/

---

## 💡 Tips & Best Practices

### Do's ✅
- ✅ Backup everything before migration
- ✅ Test incrementally
- ✅ Document all changes
- ✅ Monitor costs from day 1
- ✅ Setup alerts early
- ✅ Use Managed Identity
- ✅ Follow security best practices
- ✅ Keep secrets in Key Vault
- ✅ Use version control (Git)
- ✅ Automate deployments

### Don'ts ❌
- ❌ Hardcode passwords in code
- ❌ Skip testing
- ❌ Ignore security warnings
- ❌ Deploy directly to production
- ❌ Forget to backup
- ❌ Ignore cost alerts
- ❌ Skip documentation
- ❌ Use admin accounts for everything
- ❌ Expose secrets in logs
- ❌ Ignore monitoring

---

**Masih ada pertanyaan? Silakan update FAQ ini atau contact team lead!**

*FAQ ini dibuat: 27 Januari 2026*
*Versi: 1.0*
