# User Guide: Database Schema Audit Tool

Panduan lengkap untuk menggunakan Database Schema Audit Tool untuk mengaudit dan memperbaiki ketidaksesuaian schema database.

## Table of Contents

- [Introduction](#introduction)
- [Getting Started](#getting-started)
- [Audit Workflow](#audit-workflow)
- [Fix Workflow](#fix-workflow)
- [Validation Workflow](#validation-workflow)
- [Report Generation](#report-generation)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

## Introduction

### What is the Schema Audit Tool?

Database Schema Audit Tool adalah alat yang dirancang untuk memastikan konsistensi schema database di seluruh sistem Azure Functions. Tool ini:

- Mengekstrak schema referensi dari file BACPAC
- Memindai kode Python untuk operasi database
- Mengidentifikasi ketidaksesuaian schema
- Memperbaiki ketidaksesuaian secara otomatis
- Menghasilkan laporan dan dokumentasi

### When to Use This Tool

Gunakan tool ini ketika:

- Anda perlu memverifikasi konsistensi schema database
- Anda ingin mengidentifikasi potensi masalah sebelum deployment
- Anda perlu memperbaiki ketidaksesuaian schema secara batch
- Anda ingin mendokumentasikan struktur database
- Anda perlu mengaudit migration scripts

### Prerequisites

Sebelum menggunakan tool ini, pastikan:

- Python 3.9 atau lebih tinggi terinstal
- File BACPAC referensi tersedia
- Akses ke kode Azure Functions
- Dependencies terinstal (`pip install -r requirements.txt`)

## Getting Started

### Installation

1. Navigate ke direktori tool:

```bash
cd azure_functions/tools/schema_audit
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Verify installation:

```bash
python cli.py --help
```

### Basic Concepts

#### BACPAC File

BACPAC adalah file arsip yang berisi schema dan data database SQL Server. File ini digunakan sebagai referensi "ground truth" untuk schema yang benar.

#### Schema Mismatch

Ketidaksesuaian antara schema yang didefinisikan dalam BACPAC dengan schema yang digunakan dalam kode. Misalnya:

- Nama kolom berbeda
- Tipe data berbeda
- Kolom hilang atau tambahan

#### Severity Levels

- **CRITICAL**: Akan menyebabkan error runtime (harus diperbaiki)
- **WARNING**: Potensi masalah (sebaiknya diperbaiki)
- **INFO**: Informasi saja (opsional untuk diperbaiki)

#### Dry-Run Mode

Mode simulasi yang menampilkan perubahan tanpa menerapkannya. Selalu gunakan dry-run sebelum menerapkan perubahan.

## Audit Workflow

### Step 1: Run Initial Audit

Jalankan audit untuk mengidentifikasi semua ketidaksesuaian:

```bash
python cli.py audit \
  --bacpac ../../../pei-dashboard.bacpac \
  --code ../../ \
  --output audit_report.md \
  --verbose
```

**Output**: File `audit_report.md` berisi daftar semua ketidaksesuaian.

### Step 2: Review Audit Report

Buka `audit_report.md` dan review:

1. **Summary Section**: Total mismatches dan breakdown by severity
2. **Critical Mismatches**: Masalah yang harus diperbaiki
3. **Warning Mismatches**: Masalah yang sebaiknya diperbaiki
4. **Info Mismatches**: Informasi tambahan

Contoh audit report:

```markdown
# Schema Audit Report

## Summary

- **Total Mismatches**: 15
- **Critical**: 5
- **Warning**: 7
- **Info**: 3

## Critical Mismatches

### Table: data_biodiesel_hip

#### Column Name Mismatch: `tanggal` vs `date`

**Severity**: CRITICAL
**Expected**: `tanggal`
**Actual**: `date`
**Locations**:
- `azure_functions/scrapers/biodiesel_scraper.py:45`
- `azure_functions/scrapers/biodiesel_scraper.py:67`

**Fix Suggestion**: Rename column `date` to `tanggal` in all locations.
```

### Step 3: Prioritize Fixes

Prioritaskan perbaikan berdasarkan:

1. **Severity**: Critical > Warning > Info
2. **Impact**: Berapa banyak file yang terpengaruh
3. **Risk**: Seberapa kompleks perbaikannya

### Step 4: Include Migration Scripts (Optional)

Jika Anda ingin mengaudit migration scripts juga:

```bash
python cli.py audit \
  --bacpac ../../../pei-dashboard.bacpac \
  --code ../../ \
  --include-migrations \
  --output audit_with_migrations.md
```

### Understanding Audit Results

#### Exit Codes

- `0`: Success, no critical mismatches
- `1`: Error occurred during audit
- `2`: Success, but critical mismatches found

#### Mismatch Types

1. **MISSING_TABLE**: Tabel digunakan di kode tapi tidak ada di BACPAC
   - **Action**: Verifikasi apakah tabel memang diperlukan

2. **EXTRA_TABLE**: Tabel ada di BACPAC tapi tidak digunakan di kode
   - **Action**: Pertimbangkan untuk menggunakan tabel atau hapus dari schema

3. **COLUMN_NAME_MISMATCH**: Nama kolom berbeda
   - **Action**: Rename kolom di kode untuk match BACPAC

4. **COLUMN_TYPE_MISMATCH**: Tipe data kolom berbeda
   - **Action**: Update tipe data di CREATE TABLE statements

5. **MISSING_COLUMN**: Kolom ada di BACPAC tapi tidak digunakan di kode
   - **Action**: Tambahkan kolom ke INSERT/UPDATE operations

6. **EXTRA_COLUMN**: Kolom digunakan di kode tapi tidak ada di BACPAC
   - **Action**: Hapus kolom dari operations atau tambahkan ke BACPAC

## Fix Workflow

### Step 1: Preview Fixes (Dry-Run)

**PENTING**: Selalu jalankan dry-run terlebih dahulu!

```bash
python cli.py fix \
  --bacpac ../../../pei-dashboard.bacpac \
  --code ../../ \
  --dry-run \
  --output fix_preview.md \
  --verbose
```

**Output**: File `fix_preview.md` menampilkan semua perubahan yang akan dilakukan.

### Step 2: Review Fix Preview

Buka `fix_preview.md` dan review:

1. **Files to be Modified**: Daftar file yang akan diubah
2. **Changes**: Detail perubahan untuk setiap file
3. **Backup Plan**: Lokasi backup files

Contoh fix preview:

```markdown
# Fix Report (DRY-RUN)

## Summary

- **Total Fixes**: 5
- **Files Modified**: 3
- **Backup Directory**: backups/20240216_143022

## Changes

### File: azure_functions/scrapers/biodiesel_scraper.py

#### Line 45: Column Name Fix

**Before**:
```python
'date': data['date'],
```

**After**:
```python
'tanggal': data['date'],
```

#### Line 67: Column Name Fix

**Before**:
```python
INSERT INTO data_biodiesel_hip (date, value) VALUES (?, ?)
```

**After**:
```python
INSERT INTO data_biodiesel_hip (tanggal, value) VALUES (?, ?)
```
```

### Step 3: Create Backup (Manual - Optional)

Meskipun tool membuat backup otomatis, Anda bisa membuat backup manual:

```bash
# Create timestamped backup
cp -r azure_functions/ backups/manual_$(date +%Y%m%d_%H%M%S)/
```

### Step 4: Apply Fixes

Setelah review dry-run, apply fixes:

```bash
python cli.py fix \
  --bacpac ../../../pei-dashboard.bacpac \
  --code ../../ \
  --severity CRITICAL \
  --backup-dir backups/$(date +%Y%m%d_%H%M%S) \
  --output fix_report.md
```

**Options**:
- `--severity CRITICAL`: Hanya fix critical mismatches
- `--severity WARNING`: Fix critical dan warning mismatches
- `--severity INFO`: Fix semua mismatches

### Step 5: Review Fix Results

Buka `fix_report.md` untuk melihat hasil:

```markdown
# Fix Report

## Summary

- **Fixes Applied**: 5
- **Fixes Failed**: 0
- **Files Modified**: 3
- **Backup Directory**: backups/20240216_143022

## Status

✓ All fixes applied successfully!

## Modified Files

1. azure_functions/scrapers/biodiesel_scraper.py (2 changes)
2. azure_functions/scrapers/bioetanol_scraper.py (2 changes)
3. azure_functions/shared/database_handler.py (1 change)

## Backup Information

All modified files have been backed up to:
`backups/20240216_143022/`

To restore from backup:
```bash
cp -r backups/20240216_143022/* azure_functions/
```
```

### Step 6: Validate Changes

Setelah apply fixes, validate perubahan:

```bash
python cli.py validate \
  --directory ../../ \
  --output validation_report.md
```

### Handling Fix Failures

Jika ada fixes yang gagal:

1. **Review Error Messages**: Check fix_report.md untuk detail error
2. **Check Syntax**: Pastikan file masih valid Python
3. **Restore from Backup**: Jika perlu, restore file yang bermasalah
4. **Manual Fix**: Fix secara manual jika automatic fix gagal
5. **Report Issue**: Jika bug di tool, report ke development team

### Rollback Changes

Jika perlu rollback semua perubahan:

```bash
# Restore from backup
cp -r backups/20240216_143022/* azure_functions/

# Verify restoration
python cli.py validate --directory azure_functions/
```

## Validation Workflow

### Validate All Files

Validate semua Python files di direktori:

```bash
python cli.py validate \
  --directory ../../ \
  --output validation_report.md
```

### Validate Specific Files

Validate file-file tertentu:

```bash
python cli.py validate \
  --files ../../scrapers/*_scraper.py \
  --output validation_scrapers.md
```

### Validate with Glob Patterns

Gunakan glob patterns untuk filter files:

```bash
# Validate all scrapers
python cli.py validate --files "../../scrapers/*.py"

# Validate specific modules
python cli.py validate --files "../../shared/*.py" "../../processing/*.py"
```

### Understanding Validation Results

Validation report menampilkan:

1. **Syntax Errors**: Python syntax yang tidak valid
2. **Import Errors**: Import yang tidak bisa di-resolve
3. **Type Errors**: Type annotation issues (jika mypy enabled)

Contoh validation report:

```markdown
# Validation Report

**Generated**: 2024-02-16 14:30:22
**Total Files**: 45
**Valid Files**: 43
**Invalid Files**: 2

---

## Invalid Files

### `azure_functions/scrapers/test_scraper.py`

**Errors**:
- Line 23: SyntaxError: invalid syntax
- Line 45: NameError: name 'undefined_var' is not defined

**Warnings**:
- Line 10: Unused import 'datetime'
```

### Fixing Validation Errors

1. **Syntax Errors**: Fix Python syntax
2. **Import Errors**: Add missing imports atau fix import paths
3. **Type Errors**: Fix type annotations

## Report Generation

### Generate All Reports

Generate semua jenis reports:

```bash
python cli.py report \
  --bacpac ../../../pei-dashboard.bacpac \
  --code ../../ \
  --output reports/ \
  --types all
```

**Output**: Direktori `reports/` berisi:
- `audit_report.md`: Audit results
- `schema_report.md`: Schema documentation
- `erd_report.md`: Entity Relationship Diagram
- `mapping_report.md`: Scraper-table mapping

### Generate Specific Reports

Generate hanya report tertentu:

```bash
# Schema documentation only
python cli.py report \
  --bacpac ../../../pei-dashboard.bacpac \
  --output reports/ \
  --types schema

# ERD diagram only
python cli.py report \
  --bacpac ../../../pei-dashboard.bacpac \
  --output reports/ \
  --types erd

# Multiple specific reports
python cli.py report \
  --bacpac ../../../pei-dashboard.bacpac \
  --code ../../ \
  --output reports/ \
  --types schema erd mapping
```

### Report Types

#### 1. Audit Report

Daftar semua ketidaksesuaian schema dengan detail lokasi dan fix suggestions.

**Use Case**: Identify issues sebelum fixing

#### 2. Schema Documentation

Dokumentasi lengkap struktur database dengan semua tabel, kolom, dan constraints.

**Use Case**: Reference documentation untuk developers

#### 3. ERD Diagram

Entity Relationship Diagram dalam format Mermaid yang menampilkan relationships antar tabel.

**Use Case**: Visual understanding of database structure

#### 4. Scraper-Table Mapping

Mapping antara scraper functions dan tabel database yang mereka gunakan.

**Use Case**: Understand which scrapers write to which tables

### Viewing Reports

#### Markdown Reports

Buka dengan text editor atau Markdown viewer:

```bash
# macOS
open reports/schema_report.md

# Windows
start reports/schema_report.md

# Linux
xdg-open reports/schema_report.md
```

#### ERD Diagrams

ERD diagrams menggunakan Mermaid syntax. View dengan:

1. **GitHub**: Upload ke GitHub, akan auto-render
2. **VS Code**: Install Mermaid extension
3. **Online**: Copy-paste ke https://mermaid.live/

## Best Practices

### Before Running Fixes

1. **Always Run Audit First**: Understand what needs to be fixed
2. **Always Use Dry-Run**: Preview changes before applying
3. **Create Manual Backup**: Extra safety measure
4. **Review Changes Carefully**: Check dry-run output thoroughly
5. **Start with Critical Only**: Fix critical issues first

### During Fixes

1. **Fix in Batches**: Don't fix everything at once
2. **Test After Each Batch**: Validate changes incrementally
3. **Monitor Progress**: Watch for errors or warnings
4. **Keep Backups**: Don't delete backup directories
5. **Document Changes**: Note what was fixed and why

### After Fixes

1. **Validate Immediately**: Run validation workflow
2. **Test Functionality**: Run actual tests if available
3. **Review Logs**: Check for any warnings
4. **Update Documentation**: Document changes made
5. **Commit Changes**: Commit to version control with clear message

### General Best Practices

1. **Use Version Control**: Always commit before running fixes
2. **Test in Development First**: Don't run on production code directly
3. **Keep BACPAC Updated**: Ensure BACPAC reflects current schema
4. **Regular Audits**: Run audits regularly to catch issues early
5. **Document Exceptions**: If manual fixes needed, document why

### Safety Checklist

Before running fixes, verify:

- [ ] BACPAC file is correct and up-to-date
- [ ] Code is committed to version control
- [ ] Manual backup created (optional but recommended)
- [ ] Dry-run completed and reviewed
- [ ] Team notified of planned changes
- [ ] Test environment available for validation

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: "BACPAC file not found"

**Symptoms**: Error message about missing BACPAC file

**Solutions**:
```bash
# Check if file exists
ls -la ../../../pei-dashboard.bacpac

# Use absolute path
python cli.py audit --bacpac /full/path/to/pei-dashboard.bacpac --code ../../

# Check current directory
pwd
```

#### Issue 2: "No Python files found"

**Symptoms**: Audit completes but finds no operations

**Solutions**:
```bash
# Verify directory structure
ls -la ../../

# Check if Python files exist
find ../../ -name "*.py" | head -10

# Use correct relative path
python cli.py audit --bacpac ../../../pei-dashboard.bacpac --code ../../azure_functions/
```

#### Issue 3: "Syntax errors after fixing"

**Symptoms**: Validation fails after applying fixes

**Solutions**:
1. Check validation report for specific errors
2. Review fix_report.md for what was changed
3. Restore from backup:
   ```bash
   cp -r backups/TIMESTAMP/* azure_functions/
   ```
4. Try fixing manually or report issue

#### Issue 4: "Import errors after fixing"

**Symptoms**: Files can't import required modules

**Solutions**:
1. Check if imports were accidentally modified
2. Verify import paths are correct
3. Restore from backup if needed
4. Fix imports manually

#### Issue 5: "Permission denied"

**Symptoms**: Can't write to files or create backups

**Solutions**:
```bash
# Check file permissions
ls -la azure_functions/

# Fix permissions
chmod -R u+w azure_functions/

# Check backup directory permissions
mkdir -p backups && chmod u+w backups/
```

#### Issue 6: "Out of memory"

**Symptoms**: Process crashes or becomes very slow

**Solutions**:
1. Process smaller directories at a time
2. Close other applications
3. Increase available memory
4. Process in batches:
   ```bash
   # Process scrapers only
   python cli.py audit --bacpac pei-dashboard.bacpac --code azure_functions/scrapers/
   
   # Then process shared
   python cli.py audit --bacpac pei-dashboard.bacpac --code azure_functions/shared/
   ```

#### Issue 7: "Fixes not applied"

**Symptoms**: Dry-run shows changes but actual run doesn't apply them

**Solutions**:
1. Remove `--dry-run` flag
2. Check file permissions
3. Verify no other process is locking files
4. Check disk space:
   ```bash
   df -h
   ```

### Getting More Help

If issues persist:

1. **Enable Verbose Logging**:
   ```bash
   python cli.py audit --bacpac pei-dashboard.bacpac --code ../../ --verbose
   ```

2. **Check Log Files**: Look in `logs/` directory for detailed logs

3. **Review Documentation**: Check README.md and DEVELOPER_GUIDE.md

4. **Contact Support**: Reach out to development team with:
   - Command you ran
   - Error message
   - Relevant log files
   - Environment information (OS, Python version)

## FAQ

### General Questions

**Q: How long does an audit take?**

A: Typically 10-30 seconds for a medium-sized codebase (100-200 files). Larger codebases may take longer.

**Q: Is it safe to run on production code?**

A: The audit command is read-only and safe. The fix command modifies files, so always use dry-run first and test in development.

**Q: Can I undo changes?**

A: Yes, all modified files are backed up automatically. You can restore from the backup directory.

**Q: What if the tool makes a mistake?**

A: Restore from backup and report the issue. The tool includes extensive validation to prevent errors.

### Technical Questions

**Q: What Python version is required?**

A: Python 3.9 or higher.

**Q: Can I use this with other databases?**

A: Currently supports SQL Server BACPAC files only. Other formats may be added in the future.

**Q: Does it support other languages besides Python?**

A: Currently Python only. Support for other languages may be added.

**Q: Can I customize the fix strategies?**

A: Yes, see DEVELOPER_GUIDE.md for extension points.

### Workflow Questions

**Q: Should I fix all mismatches at once?**

A: No, start with critical mismatches only, then proceed to warnings if needed.

**Q: How often should I run audits?**

A: Run audits:
- Before major deployments
- After schema changes
- Regularly (e.g., weekly) as part of CI/CD

**Q: What if I disagree with a fix suggestion?**

A: You can:
- Skip that specific fix (fix only certain severity levels)
- Fix manually
- Update the BACPAC if the code is correct

**Q: Can I run this in CI/CD?**

A: Yes, the tool returns appropriate exit codes for CI/CD integration:
- 0: Success
- 1: Error
- 2: Success but issues found

Example CI/CD usage:
```bash
# Fail build if critical mismatches found
python cli.py audit --bacpac pei-dashboard.bacpac --code azure_functions/
if [ $? -eq 2 ]; then
  echo "Critical schema mismatches found!"
  exit 1
fi
```

## Next Steps

After completing this guide:

1. **Practice**: Run through the workflows on a test codebase
2. **Explore**: Try different commands and options
3. **Integrate**: Add to your development workflow
4. **Customize**: Extend the tool for your specific needs (see DEVELOPER_GUIDE.md)
5. **Share**: Help team members learn to use the tool

## Additional Resources

- **README.md**: Quick start and command reference
- **DEVELOPER_GUIDE.md**: Architecture and extension guide
- **Design Document**: `.kiro/specs/database-schema-audit/design.md`
- **Requirements**: `.kiro/specs/database-schema-audit/requirements.md`

## Feedback

Your feedback helps improve this tool. Please share:

- Issues encountered
- Feature requests
- Documentation improvements
- Success stories

Contact the development team or create an issue in the project repository.
