# Manual Testing Checklist Report

**Date:** 2026-02-16 03:28:16

## Summary

- **Total Tests:** 17
- **Passed:** 17 (100.0%)
- **Failed:** 0 (0.0%)
- **Warnings:** 0 (0.0%)

## Test Results

### ✓ BACPAC file exists

**Status:** PASS

**Details:** Found: pei-dashboard.bacpac

---

### ✓ Schema extraction

**Status:** PASS

**Details:** Extracted 30 tables

---

### ✓ JSON export

**Status:** PASS

**Details:** Exported to azure_functions\tools\schema_audit\manual_test_output\extracted_schema.json

---

### ✓ Markdown documentation

**Status:** PASS

**Details:** Generated azure_functions\tools\schema_audit\manual_test_output\schema_documentation.md

---

### ✓ Structured data table identification

**Status:** PASS

**Details:** Found 27 structured data tables

---

### ✓ Azure Functions directory exists

**Status:** PASS

**Details:** Found: azure_functions

---

### ✓ Directory scanning

**Status:** PASS

**Details:** Scanned 262 Python files

---

### ✓ Operation detection

**Status:** PASS

**Details:** Found operations on 44 tables

---

### ✓ Scraper detection

**Status:** PASS

**Details:** Found 30 scraper files

---

### ✓ JSON report validity

**Status:** PASS

**Details:** Valid JSON with 30 tables

---

### ✓ Markdown report validity

**Status:** PASS

**Details:** Generated 14549 characters of documentation

---

### ✓ Dry-run mode

**Status:** PASS

**Details:** File not modified in dry-run mode

---

### ✓ Dry-run report generation

**Status:** PASS

**Details:** Generated report with 1 proposed fixes

---

### ✓ Backup creation

**Status:** PASS

**Details:** Created backup at backups\backup_20260216_032816\79f5c535\test_backup.py

---

### ✓ Backup restoration

**Status:** PASS

**Details:** File successfully restored from backup

---

### ✓ Fixed code syntax validity

**Status:** PASS

**Details:** Fixed code has valid Python syntax

---

### ✓ Fixed code compilation

**Status:** PASS

**Details:** Fixed code compiles successfully

---

