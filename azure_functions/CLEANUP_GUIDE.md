# Cleanup Guide - File Management

## 📋 File Classification

### ✅ KEEP - Files to Retain (Essential)

#### Production Files
1. **pei-dashboard.bacpac** - ⭐ Single source of truth
2. **UNIFIED_MIGRATION.sql** - ⭐ Main migration script
3. **shared/database_schema.sql** - Reference schema
4. **shared/database_schema_with_go.sql** - Reference schema with GO

#### Documentation (Keep for Reference)
5. **RINGKASAN_FINAL.md** - Final summary
6. **FINAL_VERIFICATION_REPORT.md** - Verification report
7. **README_VERIFICATION.md** - Documentation index
8. **VERIFICATION_SUMMARY_ID.md** - Indonesian summary

#### Tools (Keep for Future Verification)
9. **verify_schema_alignment.py** - Verification tool (reusable)

---

### 🗑️ DELETE - Files to Remove (Temporary/Obsolete)

#### Old Migration Scripts (Replaced by UNIFIED_MIGRATION.sql)
- [ ] scripts/migrate_all_tables.sql
- [ ] scripts/migrate_bioetanol_table.py
- [ ] scripts/migrate_ebt_capacity_table.py
- [ ] scripts/migrate_eia_table.py
- [ ] scripts/migrate_fossil_table.py
- [ ] scripts/migrate_harga_ebt_table.py
- [ ] scripts/migrate_iaea_tables.py
- [ ] scripts/migrate_oil_prices_table.py
- [ ] scripts/migrate_ruptl_table.py
- [ ] scripts/migrate_wte_tables.py
- [ ] scripts/direct_migrate_test.py

#### Temporary Extraction Scripts
- [ ] extract_bacpac_schema.py
- [ ] extract_full_schema.py
- [ ] extract_complete_schema.py
- [ ] analyze_bacpac.py
- [ ] generate_functions.py (if exists)

#### Temporary Data Files
- [ ] bacpac_schema.json
- [ ] bacpac_full_schema.json
- [ ] bacpac_complete_schema.json
- [ ] model_raw.xml
- [ ] origin.xml
- [ ] schema_output.txt
- [ ] temp_extract/ (folder if exists)

#### Backup Files (if created)
- [ ] *.backup files

#### Legacy Fix Scripts (No longer needed)
- [ ] fix_legacy_table_references.py
- [ ] fix_procedure.py (if exists)

---

### ⚠️ OPTIONAL - Keep or Delete Based on Preference

#### Detailed Documentation (Can archive)
- [ ] SCHEMA_VERIFICATION_REPORT.md
- [ ] VERIFICATION_CHECKLIST.md
- [ ] DATABASE_ARCHITECTURE.md
- [ ] TABLE_MAPPING.md
- [ ] QUICK_REFERENCE.md
- [ ] LAPORAN_UNTUK_CLIENT.md

**Recommendation:** Keep in a `docs/verification/` folder or archive as ZIP

#### Verification Report Data
- [ ] schema_verification_report.json

**Recommendation:** Keep for audit trail

---

## 🚀 Recommended Cleanup Actions

### Step 1: Create Archive (Optional)
```bash
# Create archive of verification docs
mkdir -p docs/verification_archive_2026-02-16
mv SCHEMA_VERIFICATION_REPORT.md docs/verification_archive_2026-02-16/
mv VERIFICATION_CHECKLIST.md docs/verification_archive_2026-02-16/
mv DATABASE_ARCHITECTURE.md docs/verification_archive_2026-02-16/
mv TABLE_MAPPING.md docs/verification_archive_2026-02-16/
mv QUICK_REFERENCE.md docs/verification_archive_2026-02-16/
mv LAPORAN_UNTUK_CLIENT.md docs/verification_archive_2026-02-16/
mv schema_verification_report.json docs/verification_archive_2026-02-16/
```

### Step 2: Delete Old Migration Scripts
```bash
# Delete old migration scripts (replaced by UNIFIED_MIGRATION.sql)
rm scripts/migrate_all_tables.sql
rm scripts/migrate_bioetanol_table.py
rm scripts/migrate_ebt_capacity_table.py
rm scripts/migrate_eia_table.py
rm scripts/migrate_fossil_table.py
rm scripts/migrate_harga_ebt_table.py
rm scripts/migrate_iaea_tables.py
rm scripts/migrate_oil_prices_table.py
rm scripts/migrate_ruptl_table.py
rm scripts/migrate_wte_tables.py
rm scripts/direct_migrate_test.py
```

### Step 3: Delete Temporary Files
```bash
# Delete temporary extraction scripts
rm extract_bacpac_schema.py
rm extract_full_schema.py
rm extract_complete_schema.py
rm analyze_bacpac.py
rm fix_legacy_table_references.py

# Delete temporary data files
rm bacpac_schema.json
rm bacpac_full_schema.json
rm bacpac_complete_schema.json
rm model_raw.xml
rm origin.xml
rm schema_output.txt

# Delete backup files if any
rm *.backup
```

### Step 4: Organize Remaining Files
```bash
# Create docs folder structure
mkdir -p docs/database
mkdir -p docs/verification

# Move essential docs
mv RINGKASAN_FINAL.md docs/database/
mv FINAL_VERIFICATION_REPORT.md docs/database/
mv README_VERIFICATION.md docs/database/
mv VERIFICATION_SUMMARY_ID.md docs/database/

# Move migration script to scripts folder (if not already there)
# UNIFIED_MIGRATION.sql stays in root or move to scripts/
```

---

## 📁 Final Folder Structure

```
azure_functions/
├── pei-dashboard.bacpac                    ⭐ Keep
├── UNIFIED_MIGRATION.sql                   ⭐ Keep
├── verify_schema_alignment.py              ⭐ Keep (tool)
│
├── shared/
│   ├── database_schema.sql                 ⭐ Keep
│   ├── database_schema_with_go.sql         ⭐ Keep
│   └── ... (other shared files)
│
├── docs/
│   ├── database/
│   │   ├── RINGKASAN_FINAL.md             ⭐ Keep
│   │   ├── FINAL_VERIFICATION_REPORT.md   ⭐ Keep
│   │   ├── README_VERIFICATION.md         ⭐ Keep
│   │   └── VERIFICATION_SUMMARY_ID.md     ⭐ Keep
│   │
│   └── verification_archive_2026-02-16/   📦 Archive
│       ├── SCHEMA_VERIFICATION_REPORT.md
│       ├── VERIFICATION_CHECKLIST.md
│       ├── DATABASE_ARCHITECTURE.md
│       ├── TABLE_MAPPING.md
│       ├── QUICK_REFERENCE.md
│       ├── LAPORAN_UNTUK_CLIENT.md
│       └── schema_verification_report.json
│
└── scripts/
    └── ... (keep other scripts, remove old migration scripts)
```

---

## ✅ Summary

### Files to Keep (11 files)
1. pei-dashboard.bacpac
2. UNIFIED_MIGRATION.sql
3. verify_schema_alignment.py
4. shared/database_schema.sql
5. shared/database_schema_with_go.sql
6. RINGKASAN_FINAL.md
7. FINAL_VERIFICATION_REPORT.md
8. README_VERIFICATION.md
9. VERIFICATION_SUMMARY_ID.md

### Files to Delete (~20+ files)
- Old migration scripts (10 files)
- Temporary extraction scripts (5 files)
- Temporary data files (5+ files)
- Legacy fix scripts (2 files)

### Files to Archive (7 files)
- Detailed documentation (6 files)
- Verification data (1 file)

---

## 🎯 Quick Cleanup Command

Want to clean up quickly? Run this:

```bash
# WARNING: Review before running!
# This will delete files permanently

# Delete old migration scripts
rm scripts/migrate_*.py scripts/migrate_*.sql scripts/direct_migrate_test.py 2>/dev/null

# Delete temporary files
rm extract_*.py analyze_bacpac.py fix_legacy_table_references.py 2>/dev/null
rm *.json model_raw.xml origin.xml schema_output.txt *.backup 2>/dev/null

# Archive detailed docs (optional)
mkdir -p docs/verification_archive_2026-02-16
mv SCHEMA_VERIFICATION_REPORT.md VERIFICATION_CHECKLIST.md DATABASE_ARCHITECTURE.md TABLE_MAPPING.md QUICK_REFERENCE.md LAPORAN_UNTUK_CLIENT.md schema_verification_report.json docs/verification_archive_2026-02-16/ 2>/dev/null

echo "✅ Cleanup complete!"
```

---

**Note:** Always backup before deleting! You can create a ZIP archive of all verification files before cleanup.
