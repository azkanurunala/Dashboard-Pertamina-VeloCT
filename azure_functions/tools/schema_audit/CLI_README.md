# Database Schema Audit CLI

Command-line interface for the Database Schema Audit and Fix Tool.

## Installation

The CLI is part of the schema audit tool. No additional installation is required beyond the project dependencies.

## Usage

### Basic Syntax

```bash
python -m azure_functions.tools.schema_audit.cli [COMMAND] [OPTIONS]
```

### Global Options

- `--verbose, -v`: Enable verbose logging
- `--dry-run`: Simulate operations without making changes

## Commands

### 1. Audit Command

Run audit-only mode to detect schema mismatches.

```bash
python -m azure_functions.tools.schema_audit.cli audit \
  --bacpac pei-dashboard.bacpac \
  --code azure_functions/ \
  --output audit_report.md \
  --include-migrations
```

**Options:**
- `--bacpac BACPAC` (required): Path to BACPAC file containing reference schema
- `--code CODE` (required): Path to code directory to audit
- `--output OUTPUT`: Output file for audit report (default: audit_report.md)
- `--include-migrations`: Include migration scripts in audit

**Exit Codes:**
- `0`: Success, no critical mismatches
- `1`: Failure (error occurred)
- `2`: Success, but critical mismatches found

### 2. Fix Command

Apply fixes to detected schema mismatches.

```bash
# Dry-run first (recommended)
python -m azure_functions.tools.schema_audit.cli fix \
  --bacpac pei-dashboard.bacpac \
  --code azure_functions/ \
  --dry-run

# Apply fixes
python -m azure_functions.tools.schema_audit.cli fix \
  --bacpac pei-dashboard.bacpac \
  --code azure_functions/ \
  --output fix_report.md \
  --backup-dir backups \
  --severity CRITICAL
```

**Options:**
- `--bacpac BACPAC` (required): Path to BACPAC file containing reference schema
- `--code CODE` (required): Path to code directory to fix
- `--output OUTPUT`: Output file for fix report (default: fix_report.md)
- `--backup-dir BACKUP_DIR`: Directory for file backups (default: backups)
- `--severity {CRITICAL,WARNING,INFO}`: Minimum severity level to fix (default: CRITICAL)

**Exit Codes:**
- `0`: Success
- `1`: Failure (error occurred)

### 3. Validate Command

Validate Python files for syntax and import errors.

```bash
# Validate specific files
python -m azure_functions.tools.schema_audit.cli validate \
  --files azure_functions/**/*.py \
  --output validation_report.md

# Validate entire directory
python -m azure_functions.tools.schema_audit.cli validate \
  --directory azure_functions/ \
  --output validation_report.md
```

**Options:**
- `--files FILES [FILES ...]`: Python files to validate (supports glob patterns)
- `--directory DIRECTORY`: Directory to validate all Python files
- `--output OUTPUT`: Output file for validation report (default: validation_report.md)

**Exit Codes:**
- `0`: Success, all files valid
- `1`: Failure (error occurred)
- `2`: Success, but some files invalid

### 4. Report Command

Generate comprehensive reports.

```bash
python -m azure_functions.tools.schema_audit.cli report \
  --bacpac pei-dashboard.bacpac \
  --code azure_functions/ \
  --output reports/ \
  --types audit schema erd mapping
```

**Options:**
- `--bacpac BACPAC` (required): Path to BACPAC file containing reference schema
- `--code CODE`: Path to code directory (optional, for mapping reports)
- `--output OUTPUT`: Output directory for reports (default: reports)
- `--types {audit,schema,erd,mapping,all} [...]`: Types of reports to generate (default: all)

**Report Types:**
- `audit`: Schema mismatch audit report
- `schema`: Database schema documentation
- `erd`: Entity Relationship Diagram (Mermaid format)
- `mapping`: Scraper-to-table mapping
- `all`: Generate all report types

**Exit Codes:**
- `0`: Success
- `1`: Failure (error occurred)

## Examples

### Complete Workflow

```bash
# 1. Run audit to identify issues
python -m azure_functions.tools.schema_audit.cli audit \
  --bacpac pei-dashboard.bacpac \
  --code azure_functions/ \
  --verbose

# 2. Review audit_report.md

# 3. Test fixes in dry-run mode
python -m azure_functions.tools.schema_audit.cli fix \
  --bacpac pei-dashboard.bacpac \
  --code azure_functions/ \
  --dry-run \
  --verbose

# 4. Apply fixes
python -m azure_functions.tools.schema_audit.cli fix \
  --bacpac pei-dashboard.bacpac \
  --code azure_functions/ \
  --severity CRITICAL

# 5. Validate changes
python -m azure_functions.tools.schema_audit.cli validate \
  --directory azure_functions/

# 6. Generate comprehensive reports
python -m azure_functions.tools.schema_audit.cli report \
  --bacpac pei-dashboard.bacpac \
  --code azure_functions/ \
  --output reports/
```

### Quick Audit

```bash
python -m azure_functions.tools.schema_audit.cli audit \
  --bacpac pei-dashboard.bacpac \
  --code azure_functions/
```

### Fix Only Critical Issues

```bash
python -m azure_functions.tools.schema_audit.cli fix \
  --bacpac pei-dashboard.bacpac \
  --code azure_functions/ \
  --severity CRITICAL
```

### Generate Schema Documentation

```bash
python -m azure_functions.tools.schema_audit.cli report \
  --bacpac pei-dashboard.bacpac \
  --types schema erd
```

## Output Files

### Audit Report (`audit_report.md`)
- Summary of all schema mismatches
- Categorized by severity (Critical, Warning, Info)
- Grouped by table
- Includes fix suggestions

### Fix Report (`fix_report.md`)
- Details of all fixes applied
- Before/after code snippets
- Success/failure status
- Backup directory location

### Validation Report (`validation_report.md`)
- List of validated files
- Syntax and import errors
- Summary statistics

### Schema Documentation
- Complete database schema documentation
- Table definitions with columns, types, constraints
- Foreign key relationships
- Indexes and constraints

### ERD Diagram
- Mermaid format Entity Relationship Diagram
- Visual representation of database schema
- Can be rendered in Markdown viewers

### Mapping Report
- Scraper-to-table mapping
- Shows which scrapers write to which tables
- Operation counts and details

## Error Handling

The CLI provides comprehensive error handling:

- **File not found**: Clear error message with file path
- **Invalid BACPAC**: Validation error with details
- **Syntax errors**: Detailed error location and message
- **Permission errors**: Clear indication of access issues

All errors are logged with appropriate severity levels.

## Logging

### Normal Mode
Shows progress and summary information:
```
INFO - Starting audit workflow...
INFO - Step 1/4: Extracting schema from BACPAC
INFO - ✓ Extracted 25 tables
```

### Verbose Mode (`--verbose`)
Shows detailed debug information:
```
DEBUG - Parsing table: data_biodiesel_hip
DEBUG - Found 12 columns in table
DEBUG - Detected mismatch: column name difference
```

## Dry-Run Mode

Use `--dry-run` to simulate operations without making changes:

```bash
python -m azure_functions.tools.schema_audit.cli fix \
  --bacpac pei-dashboard.bacpac \
  --code azure_functions/ \
  --dry-run
```

In dry-run mode:
- No files are modified
- No backups are created
- All changes are reported as "would be applied"
- Useful for testing before actual execution

## Backup and Rollback

When fixes are applied:
1. Backups are automatically created before any modifications
2. Backups are stored in timestamped directories (e.g., `backups/backup_20260216_143022/`)
3. Original file structure is preserved in backups
4. Backups can be manually restored if needed

To restore from backup:
```bash
# Backups are in: backups/backup_YYYYMMDD_HHMMSS/
# Manually copy files back to original locations
```

## Troubleshooting

### "BACPAC file not found"
- Verify the path to the BACPAC file
- Use absolute path if relative path doesn't work

### "No Python files found"
- Check the directory path
- Verify glob patterns are correct
- Use `--verbose` to see which files are being scanned

### "Syntax error after fix"
- Check the fix report for details
- Restore from backup if needed
- Report the issue with the specific file and error

### "Import validation failed"
- Some imports may not be resolvable in the current environment
- This is informational and may not indicate a real problem
- Review the validation report for details

## Integration with CI/CD

The CLI can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Audit Database Schema
  run: |
    python -m azure_functions.tools.schema_audit.cli audit \
      --bacpac pei-dashboard.bacpac \
      --code azure_functions/ \
      --output audit_report.md
  
- name: Upload Audit Report
  uses: actions/upload-artifact@v2
  with:
    name: audit-report
    path: audit_report.md
```

Exit codes can be used to fail builds when critical issues are found.

## Support

For issues or questions:
1. Check the main README.md
2. Review the design document in `.kiro/specs/database-schema-audit/design.md`
3. Enable `--verbose` mode for detailed logging
4. Check generated reports for specific error details
