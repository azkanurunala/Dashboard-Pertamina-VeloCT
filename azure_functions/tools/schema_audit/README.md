# Database Schema Audit Tool

Alat komprehensif untuk mengaudit dan memperbaiki ketidaksesuaian schema database antara file BACPAC referensi dengan implementasi di Azure Functions. Tool ini memastikan konsistensi schema di seluruh sistem dengan melakukan audit menyeluruh dan perbaikan otomatis.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Command-Line Usage](#command-line-usage)
- [Configuration](#configuration)
- [Examples](#examples)
- [Project Structure](#project-structure)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Documentation](#documentation)

## Features

- **Schema Extraction**: Ekstraksi schema lengkap dari file BACPAC
- **Code Auditing**: Pemindaian otomatis operasi database di kode Python
- **Mismatch Detection**: Identifikasi ketidaksesuaian schema dengan kategorisasi severity
- **Automatic Fixing**: Perbaikan otomatis dengan backup dan rollback
- **Validation**: Validasi sintaks Python dan konsistensi schema
- **Comprehensive Reporting**: Laporan audit, fix, dan dokumentasi schema
- **Migration Support**: Audit dan perbaikan migration scripts
- **Dry-Run Mode**: Preview perubahan tanpa menerapkannya

## Installation

### Prerequisites

- Python 3.9 or higher
- pip package manager

### Install Dependencies

```bash
cd azure_functions/tools/schema_audit
pip install -r requirements.txt
```

### Verify Installation

```bash
python -m azure_functions.tools.schema_audit.cli --help
```

Or if you're in the schema_audit directory:

```bash
python cli.py --help
```

## Quick Start

### 1. Run Audit (Read-Only)

Audit your codebase to detect schema mismatches:

```bash
python cli.py audit \
  --bacpac ../../../pei-dashboard.bacpac \
  --code ../../ \
  --output audit_report.md
```

### 2. Preview Fixes (Dry-Run)

See what changes would be made without applying them:

```bash
python cli.py fix \
  --bacpac ../../../pei-dashboard.bacpac \
  --code ../../ \
  --dry-run \
  --output fix_preview.md
```

### 3. Apply Fixes

Apply fixes to critical mismatches:

```bash
python cli.py fix \
  --bacpac ../../../pei-dashboard.bacpac \
  --code ../../ \
  --severity CRITICAL \
  --backup-dir backups \
  --output fix_report.md
```

### 4. Validate Changes

Validate Python files after fixes:

```bash
python cli.py validate \
  --directory ../../ \
  --output validation_report.md
```

## Command-Line Usage

### Global Flags

- `--verbose, -v`: Enable verbose logging
- `--dry-run`: Simulate operations without making changes

### Commands

#### `audit` - Run Audit

Detect schema mismatches between BACPAC and code.

```bash
python cli.py audit [OPTIONS]
```

**Options:**
- `--bacpac PATH` (required): Path to BACPAC file
- `--code PATH` (required): Path to code directory
- `--output PATH`: Output file for report (default: audit_report.md)
- `--include-migrations`: Include migration scripts in audit

**Exit Codes:**
- `0`: Success, no critical mismatches
- `1`: Error occurred
- `2`: Success, but critical mismatches found

**Example:**
```bash
python cli.py audit \
  --bacpac pei-dashboard.bacpac \
  --code azure_functions/ \
  --include-migrations \
  --verbose
```

#### `fix` - Apply Fixes

Fix detected schema mismatches.

```bash
python cli.py fix [OPTIONS]
```

**Options:**
- `--bacpac PATH` (required): Path to BACPAC file
- `--code PATH` (required): Path to code directory
- `--output PATH`: Output file for report (default: fix_report.md)
- `--backup-dir PATH`: Directory for backups (default: backups)
- `--severity LEVEL`: Minimum severity to fix (CRITICAL|WARNING|INFO, default: CRITICAL)

**Exit Codes:**
- `0`: Success
- `1`: Error occurred

**Example:**
```bash
python cli.py fix \
  --bacpac pei-dashboard.bacpac \
  --code azure_functions/ \
  --severity WARNING \
  --backup-dir backups/$(date +%Y%m%d_%H%M%S)
```

#### `validate` - Validate Files

Validate Python files for syntax and import errors.

```bash
python cli.py validate [OPTIONS]
```

**Options:**
- `--files PATTERN [PATTERN ...]`: File patterns to validate (supports glob)
- `--directory PATH`: Directory to validate all Python files
- `--output PATH`: Output file for report (default: validation_report.md)

**Exit Codes:**
- `0`: Success, all files valid
- `1`: Error occurred
- `2`: Success, but some files invalid

**Example:**
```bash
python cli.py validate \
  --directory azure_functions/scrapers/ \
  --output validation_report.md
```

#### `report` - Generate Reports

Generate comprehensive documentation and reports.

```bash
python cli.py report [OPTIONS]
```

**Options:**
- `--bacpac PATH` (required): Path to BACPAC file
- `--code PATH`: Path to code directory (optional)
- `--output PATH`: Output directory (default: reports)
- `--types TYPE [TYPE ...]`: Report types (audit|schema|erd|mapping|all, default: all)

**Exit Codes:**
- `0`: Success
- `1`: Error occurred

**Example:**
```bash
python cli.py report \
  --bacpac pei-dashboard.bacpac \
  --code azure_functions/ \
  --output reports/ \
  --types schema erd mapping
```

## Configuration

### Environment Variables

The tool respects the following environment variables:

- `SCHEMA_AUDIT_LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)
- `SCHEMA_AUDIT_BACKUP_DIR`: Default backup directory

### Logging

Logging is configured automatically based on the `--verbose` flag:

- **Normal mode**: INFO level, shows progress and results
- **Verbose mode**: DEBUG level, shows detailed execution information

Logs are written to:
- Console (stdout/stderr)
- Log files in `logs/` directory (if configured)

## Examples

### Example 1: Full Audit and Fix Workflow

```bash
# Step 1: Run audit to identify issues
python cli.py audit \
  --bacpac pei-dashboard.bacpac \
  --code azure_functions/ \
  --output reports/audit_$(date +%Y%m%d).md \
  --verbose

# Step 2: Preview fixes (dry-run)
python cli.py fix \
  --bacpac pei-dashboard.bacpac \
  --code azure_functions/ \
  --dry-run \
  --output reports/fix_preview.md

# Step 3: Apply critical fixes
python cli.py fix \
  --bacpac pei-dashboard.bacpac \
  --code azure_functions/ \
  --severity CRITICAL \
  --backup-dir backups/$(date +%Y%m%d_%H%M%S)

# Step 4: Validate changes
python cli.py validate \
  --directory azure_functions/ \
  --output reports/validation.md
```

### Example 2: Generate Documentation

```bash
# Generate all reports
python cli.py report \
  --bacpac pei-dashboard.bacpac \
  --code azure_functions/ \
  --output documentation/ \
  --types all

# Generate only schema documentation
python cli.py report \
  --bacpac pei-dashboard.bacpac \
  --output documentation/ \
  --types schema erd
```

### Example 3: Validate Specific Files

```bash
# Validate specific scraper files
python cli.py validate \
  --files azure_functions/scrapers/*_scraper.py \
  --output validation_scrapers.md

# Validate all Python files in a directory
python cli.py validate \
  --directory azure_functions/shared/ \
  --output validation_shared.md
```

## Project Structure

```
azure_functions/tools/schema_audit/
├── __init__.py                    # Package initialization
├── cli.py                         # Command-line interface
├── models.py                      # Data models
├── schema_extractor.py            # BACPAC schema extraction
├── code_auditor.py                # Code scanning and analysis
├── mismatch_detector.py           # Schema comparison
├── schema_fixer.py                # Automatic fixing
├── validator.py                   # Validation logic
├── reporter.py                    # Report generation
├── model_updater.py               # Model and handler updates
├── migration_auditor.py           # Migration script auditing
├── logging_config.py              # Logging configuration
├── requirements.txt               # Dependencies
├── README.md                      # This file
├── DEVELOPER_GUIDE.md             # Developer documentation
├── USER_GUIDE.md                  # User guide
├── tests/                         # Test files
│   ├── test_*.py                  # Unit tests
│   └── test_*_integration.py      # Integration tests
├── output/                        # Generated reports
└── backups/                       # File backups
```

## Development

### Running Tests

Run all tests:
```bash
pytest
```

Run specific test file:
```bash
pytest test_schema_extractor.py
```

Run with coverage:
```bash
pytest --cov=. --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html  # macOS
start htmlcov/index.html # Windows
```

### Type Checking

Run type checking with mypy:
```bash
mypy . --ignore-missing-imports
```

### Code Quality

Run linting:
```bash
pylint *.py
```

Format code:
```bash
black *.py
```

### Running Property-Based Tests

Property-based tests use Hypothesis:
```bash
pytest -k "property" --hypothesis-show-statistics
```

## Troubleshooting

### Common Issues

#### Issue: "BACPAC file not found"

**Solution:** Ensure the path to the BACPAC file is correct and the file exists.

```bash
# Check if file exists
ls -la pei-dashboard.bacpac

# Use absolute path
python cli.py audit --bacpac /full/path/to/pei-dashboard.bacpac --code azure_functions/
```

#### Issue: "No Python files found"

**Solution:** Verify the code directory path and ensure it contains Python files.

```bash
# Check directory contents
ls -la azure_functions/

# Use correct relative path
python cli.py audit --bacpac pei-dashboard.bacpac --code ../../azure_functions/
```

#### Issue: "Syntax errors after fixing"

**Solution:** Use dry-run mode first, then review changes before applying.

```bash
# Always dry-run first
python cli.py fix --bacpac pei-dashboard.bacpac --code azure_functions/ --dry-run

# Check validation report
python cli.py validate --directory azure_functions/ --output validation.md
```

#### Issue: "Import errors after fixing"

**Solution:** Restore from backup and review the fix strategy.

```bash
# Backups are in the backup directory
ls -la backups/

# Manually restore if needed
cp backups/TIMESTAMP/path/to/file.py azure_functions/path/to/file.py
```

#### Issue: "Out of memory"

**Solution:** Process files in smaller batches or increase available memory.

```bash
# Process specific directories
python cli.py audit --bacpac pei-dashboard.bacpac --code azure_functions/scrapers/

# Then process other directories
python cli.py audit --bacpac pei-dashboard.bacpac --code azure_functions/shared/
```

### Getting Help

For more help:

1. Check the [User Guide](USER_GUIDE.md) for detailed workflows
2. Check the [Developer Guide](DEVELOPER_GUIDE.md) for architecture details
3. Run with `--verbose` flag for detailed logging
4. Check log files in `logs/` directory
5. Review generated reports for specific error messages

## Documentation

- **[User Guide](USER_GUIDE.md)**: Detailed workflows and usage scenarios
- **[Developer Guide](DEVELOPER_GUIDE.md)**: Architecture and extension points
- **[API Documentation](docs/api/)**: Module and class documentation

## License

This tool is part of the PEI Dashboard Azure Functions project.

## Support

For issues or questions, please contact the development team or create an issue in the project repository.
