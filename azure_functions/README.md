# Azure Functions - PEI Dashboard

## 📋 Quick Start

### Essential Files

1. **pei-dashboard.bacpac** - ⭐ Database schema (single source of truth)
2. **UNIFIED_MIGRATION.sql** - ⭐ Complete migration script (30 tables)
3. **verify_schema_alignment.py** - 🛠️ Schema verification tool

### Documentation

- **docs/database/** - Essential documentation
  - `RINGKASAN_FINAL.md` - Final summary (Bahasa Indonesia)
  - `FINAL_VERIFICATION_REPORT.md` - Complete verification report
  - `README_VERIFICATION.md` - Documentation index
  - `VERIFICATION_SUMMARY_ID.md` - Indonesian summary

- **docs/verification_archive_2026-02-16/** - Archived detailed docs

---

## 🚀 Database Migration

### Run Migration Script

```bash
# Option 1: Azure Portal
# 1. Open Azure Portal → SQL Database → Query editor
# 2. Copy-paste UNIFIED_MIGRATION.sql
# 3. Click Run

# Option 2: SSMS
# 1. Open SQL Server Management Studio
# 2. File → Open → UNIFIED_MIGRATION.sql
# 3. Press F5

# Option 3: Azure CLI
az sql db execute \
  --resource-group <resource-group> \
  --server <server-name> \
  --name <database-name> \
  --file UNIFIED_MIGRATION.sql
```

### Verify Migration

```sql
-- Check table count (should be 30)
SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_TYPE = 'BASE TABLE';

-- List all tables
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_TYPE = 'BASE TABLE' 
ORDER BY TABLE_NAME;
```

---

## 📊 Database Schema

### 30 Tables Total

#### News & Sentiment (6 tables)
- news_articles, news_sources, keywords
- article_keywords, sentiment_analyses, sentiment_analysis_articles

#### System (2 tables)
- configuration, execution_logs

#### Biofuel & Renewable (7 tables)
- data_biodiesel_hip, data_bioetanol_hip, data_cpo_prices
- data_saf_uco_prices, data_ebt_capacity, data_ebt_prices
- data_renewable_energy

#### Fossil Fuel & Oil (5 tables)
- data_fossil, data_fossil_prediction, data_oil_prices
- data_oil_crackspreads, data_petrochemical_prices

#### Nuclear & Power (3 tables)
- data_iaea_electrical, data_iaea_nuclear_capacity
- data_ruptl_projects

#### Market & Economic (4 tables)
- data_eia_market, data_market_indicators
- data_volatility_index, data_geopolitical_risk_index

#### Waste to Energy (3 tables)
- data_wte_komposisi, data_wte_sumber, data_wte_timbulan

---

## 🔍 Verification

### Run Schema Verification

```bash
python verify_schema_alignment.py
```

This will:
- Extract schema from pei-dashboard.bacpac
- Scan code for table references
- Compare and verify alignment
- Generate verification report

---

## 📚 Documentation

### Essential Docs
- **RINGKASAN_FINAL.md** - Quick summary
- **FINAL_VERIFICATION_REPORT.md** - Complete report
- **UNIFIED_MIGRATION.sql** - Migration script

### Archived Docs
- **docs/verification_archive_2026-02-16/** - Detailed documentation

---

## ✅ Verification Status

**Last Verified:** 16 Februari 2026  
**Status:** ✅ 100% Aligned with pei-dashboard.bacpac

| Component | Status |
|-----------|--------|
| Tables in bacpac | 30 ✅ |
| Scraper functions | 28/28 ✅ |
| Database handlers | 7/7 ✅ |
| Processing functions | 3/3 ✅ |
| Schema alignment | 100% ✅ |

---

## 🛠️ Development

### Project Structure

```
azure_functions/
├── scrapers/              # 28 scraper functions
├── processing/            # Data processing
├── shared/                # Shared utilities
├── scripts/               # Utility scripts
├── tests/                 # Test files
└── docs/                  # Documentation
```

### Key Components

- **Scrapers:** 28 functions for data collection
- **Processing:** News aggregation, deduplication, caching
- **Database:** Handlers, migration, optimization
- **Orchestration:** Schedulers and orchestrators

---

## 📞 Support

For questions or issues:
1. Review documentation in `docs/database/`
2. Check `UNIFIED_MIGRATION.sql` comments
3. Run `verify_schema_alignment.py`
4. Contact development team

---

## 🎯 Quick Links

- [Final Summary](docs/database/RINGKASAN_FINAL.md)
- [Verification Report](docs/database/FINAL_VERIFICATION_REPORT.md)
- [Documentation Index](docs/database/README_VERIFICATION.md)
- [Migration Script](UNIFIED_MIGRATION.sql)

---

**Status:** ✅ Production Ready  
**Last Updated:** 16 Februari 2026  
**Version:** 1.0
