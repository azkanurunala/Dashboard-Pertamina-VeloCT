# Instruksi Cleanup File

## 🎯 Tujuan
Membersihkan file-file temporary dan obsolete setelah verifikasi selesai, hanya menyimpan file-file essential.

---

## ⚡ Quick Start (Otomatis)

### Cara Tercepat - Jalankan Script Otomatis

```bash
python cleanup_files.py
```

Script ini akan:
1. ✅ Membuat archive untuk dokumentasi detail
2. ✅ Menghapus file-file obsolete
3. ✅ Mengorganisir file-file penting
4. ✅ Membuat folder structure yang rapi

**Aman dijalankan** - Script akan membuat backup sebelum menghapus.

---

## 📋 Manual Cleanup (Jika Prefer Manual)

### Step 1: Archive Dokumentasi Detail (Opsional)

```bash
# Buat folder archive
mkdir -p docs/verification_archive_2026-02-16

# Pindahkan dokumentasi detail
move SCHEMA_VERIFICATION_REPORT.md docs/verification_archive_2026-02-16/
move VERIFICATION_CHECKLIST.md docs/verification_archive_2026-02-16/
move DATABASE_ARCHITECTURE.md docs/verification_archive_2026-02-16/
move TABLE_MAPPING.md docs/verification_archive_2026-02-16/
move QUICK_REFERENCE.md docs/verification_archive_2026-02-16/
move LAPORAN_UNTUK_CLIENT.md docs/verification_archive_2026-02-16/
move schema_verification_report.json docs/verification_archive_2026-02-16/
```

### Step 2: Hapus Old Migration Scripts

```bash
# Hapus migration scripts lama (sudah diganti UNIFIED_MIGRATION.sql)
del scripts\migrate_all_tables.sql
del scripts\migrate_bioetanol_table.py
del scripts\migrate_ebt_capacity_table.py
del scripts\migrate_eia_table.py
del scripts\migrate_fossil_table.py
del scripts\migrate_harga_ebt_table.py
del scripts\migrate_iaea_tables.py
del scripts\migrate_oil_prices_table.py
del scripts\migrate_ruptl_table.py
del scripts\migrate_wte_tables.py
del scripts\direct_migrate_test.py
```

### Step 3: Hapus Temporary Files

```bash
# Hapus extraction scripts temporary
del extract_bacpac_schema.py
del extract_full_schema.py
del extract_complete_schema.py
del analyze_bacpac.py
del fix_legacy_table_references.py

# Hapus data files temporary
del bacpac_schema.json
del bacpac_full_schema.json
del bacpac_complete_schema.json
del model_raw.xml
del origin.xml
del schema_output.txt
```

### Step 4: Organize Essential Files

```bash
# Buat folder docs/database
mkdir docs\database

# Pindahkan dokumentasi essential
move RINGKASAN_FINAL.md docs\database\
move FINAL_VERIFICATION_REPORT.md docs\database\
move README_VERIFICATION.md docs\database\
move VERIFICATION_SUMMARY_ID.md docs\database\
```

---

## ✅ File yang Akan Dipertahankan

### Root Folder
```
azure_functions/
├── pei-dashboard.bacpac           ⭐ Single source of truth
├── UNIFIED_MIGRATION.sql          ⭐ Main migration script
├── verify_schema_alignment.py     🛠️ Verification tool
└── CLEANUP_GUIDE.md               📚 Cleanup reference
```

### Shared Folder
```
shared/
├── database_schema.sql            📄 Reference schema
├── database_schema_with_go.sql    📄 Reference schema with GO
└── ... (other shared files)
```

### Docs Folder (Baru)
```
docs/
├── database/
│   ├── RINGKASAN_FINAL.md         📋 Final summary
│   ├── FINAL_VERIFICATION_REPORT.md 📋 Verification report
│   ├── README_VERIFICATION.md     📋 Documentation index
│   └── VERIFICATION_SUMMARY_ID.md 📋 Indonesian summary
│
└── verification_archive_2026-02-16/
    ├── SCHEMA_VERIFICATION_REPORT.md
    ├── VERIFICATION_CHECKLIST.md
    ├── DATABASE_ARCHITECTURE.md
    ├── TABLE_MAPPING.md
    ├── QUICK_REFERENCE.md
    ├── LAPORAN_UNTUK_CLIENT.md
    └── schema_verification_report.json
```

---

## 🗑️ File yang Akan Dihapus

### Old Migration Scripts (~10 files)
- ❌ scripts/migrate_all_tables.sql
- ❌ scripts/migrate_bioetanol_table.py
- ❌ scripts/migrate_ebt_capacity_table.py
- ❌ scripts/migrate_eia_table.py
- ❌ scripts/migrate_fossil_table.py
- ❌ scripts/migrate_harga_ebt_table.py
- ❌ scripts/migrate_iaea_tables.py
- ❌ scripts/migrate_oil_prices_table.py
- ❌ scripts/migrate_ruptl_table.py
- ❌ scripts/migrate_wte_tables.py
- ❌ scripts/direct_migrate_test.py

### Temporary Scripts (~5 files)
- ❌ extract_bacpac_schema.py
- ❌ extract_full_schema.py
- ❌ extract_complete_schema.py
- ❌ analyze_bacpac.py
- ❌ fix_legacy_table_references.py

### Temporary Data Files (~6 files)
- ❌ bacpac_schema.json
- ❌ bacpac_full_schema.json
- ❌ bacpac_complete_schema.json
- ❌ model_raw.xml
- ❌ origin.xml
- ❌ schema_output.txt

**Total: ~21 files akan dihapus**

---

## 📦 File yang Akan Di-Archive

### Detailed Documentation (~7 files)
- 📦 SCHEMA_VERIFICATION_REPORT.md
- 📦 VERIFICATION_CHECKLIST.md
- 📦 DATABASE_ARCHITECTURE.md
- 📦 TABLE_MAPPING.md
- 📦 QUICK_REFERENCE.md
- 📦 LAPORAN_UNTUK_CLIENT.md
- 📦 schema_verification_report.json

**Lokasi archive:** `docs/verification_archive_2026-02-16/`

---

## ✅ Verifikasi Setelah Cleanup

### Check 1: File Essential Ada
```bash
# Check file penting masih ada
dir pei-dashboard.bacpac
dir UNIFIED_MIGRATION.sql
dir verify_schema_alignment.py
dir docs\database\RINGKASAN_FINAL.md
```

### Check 2: Old Migration Scripts Terhapus
```bash
# Check migration scripts lama sudah terhapus
dir scripts\migrate_*.py
dir scripts\migrate_*.sql
# Seharusnya tidak ada atau minimal
```

### Check 3: Temporary Files Terhapus
```bash
# Check temporary files sudah terhapus
dir extract_*.py
dir *.json
# Seharusnya tidak ada atau minimal
```

### Check 4: Archive Folder Ada
```bash
# Check archive folder dibuat
dir docs\verification_archive_2026-02-16
# Seharusnya ada 7 files
```

---

## 🎯 Hasil Akhir

### Before Cleanup
```
📁 Root: ~40+ files (messy)
📁 scripts/: ~30+ files (many obsolete)
```

### After Cleanup
```
📁 Root: ~5 essential files (clean)
📁 docs/database/: 4 documentation files
📁 docs/verification_archive/: 7 archived files
📁 scripts/: Only active scripts
```

**Space saved:** ~20-30 files removed from root  
**Organization:** Much cleaner and easier to navigate

---

## 🚀 Recommended Action

### Option 1: Automatic (Recommended)
```bash
python cleanup_files.py
```
✅ Fast, safe, automatic

### Option 2: Manual
Follow steps in "Manual Cleanup" section above  
✅ More control, step by step

### Option 3: Review First
1. Read CLEANUP_GUIDE.md
2. Review what will be deleted
3. Then run cleanup_files.py

---

## ⚠️ Important Notes

1. **Backup First** (Optional but recommended)
   ```bash
   # Create full backup before cleanup
   mkdir backup_full
   xcopy /E /I . backup_full
   ```

2. **Can't Undo**
   - Deleted files cannot be recovered easily
   - Archive folder keeps detailed docs
   - Essential files are never touched

3. **Safe to Run**
   - Script only deletes temporary/obsolete files
   - Never touches production code
   - Never touches pei-dashboard.bacpac
   - Never touches UNIFIED_MIGRATION.sql

---

## 📞 After Cleanup

### What to Do Next

1. ✅ Verify UNIFIED_MIGRATION.sql is in root
2. ✅ Test verification tool still works:
   ```bash
   python verify_schema_alignment.py
   ```
3. ✅ Review docs/database/ folder
4. ✅ Archive or delete verification_archive folder (optional)
5. ✅ Delete cleanup scripts if satisfied:
   ```bash
   del cleanup_files.py
   del CLEANUP_GUIDE.md
   del INSTRUKSI_CLEANUP.md
   ```

---

## ✅ Summary

**Cleanup akan:**
- ✅ Menghapus 21+ file obsolete
- ✅ Mengarsip 7 file dokumentasi detail
- ✅ Mengorganisir 4 file dokumentasi essential
- ✅ Menjaga 5 file essential di root
- ✅ Membuat struktur folder yang rapi

**Hasil:**
- ✅ Root folder lebih bersih
- ✅ Hanya file penting yang tersisa
- ✅ Dokumentasi terorganisir dengan baik
- ✅ Siap untuk production

---

**Ready to cleanup?** Run: `python cleanup_files.py` 🚀
