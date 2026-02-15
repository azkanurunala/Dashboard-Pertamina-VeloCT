# Quick Deployment Guide

Fast-track deployment guide for the Database Schema Audit Tool.

## Prerequisites (5 minutes)

```bash
# 1. Verify Python 3.9+
python3 --version

# 2. Navigate to tool directory
cd azure_functions/tools/schema_audit

# 3. Verify BACPAC file exists
ls -la ../../../pei-dashboard.bacpac
```

## Automated Deployment (2 minutes)

### Linux/macOS

```bash
# Make script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

### Windows

```bash
# Run with bash
bash deploy.sh
```

## Manual Deployment (5 minutes)

```bash
# 1. Install dependencies
pip3 install -r requirements.txt

# 2. Create directories
mkdir -p output backups logs reports

# 3. Verify installation
python3 cli.py --help

# 4. Run smoke test
python3 cli.py audit \
  --bacpac ../../../pei-dashboard.bacpac \
  --code ../../ \
  --output smoke_test.md
```

## Quick Start (3 minutes)

### Phase 1: Audit Only

```bash
# Run audit to identify issues
python3 cli.py audit \
  --bacpac ../../../pei-dashboard.bacpac \
  --code ../../ \
  --output audit_report.md

# Review results
cat audit_report.md
```

### Phase 2: Preview Fixes

```bash
# Dry-run to preview changes
python3 cli.py fix \
  --bacpac ../../../pei-dashboard.bacpac \
  --code ../../ \
  --dry-run \
  --output fix_preview.md

# Review preview
cat fix_preview.md
```

### Phase 3: Apply Fixes

```bash
# Create backup first
cp -r ../../ backups/manual_$(date +%Y%m%d_%H%M%S)/

# Apply critical fixes only
python3 cli.py fix \
  --bacpac ../../../pei-dashboard.bacpac \
  --code ../../ \
  --severity CRITICAL \
  --backup-dir backups/auto_$(date +%Y%m%d_%H%M%S) \
  --output fix_report.md

# Validate changes
python3 cli.py validate \
  --directory ../../ \
  --output validation_report.md
```

## Monitoring (1 minute)

```bash
# Make monitor script executable (Linux/macOS)
chmod +x monitor.sh

# Run health check
./monitor.sh --check all

# Or on Windows
bash monitor.sh --check all
```

## Rollback (2 minutes)

```bash
# Make rollback script executable (Linux/macOS)
chmod +x rollback.sh

# List available backups
ls -la backups/

# Rollback to specific backup
./rollback.sh \
  --backup-dir backups/TIMESTAMP \
  --target-dir ../../ \
  --verify

# Or on Windows
bash rollback.sh \
  --backup-dir backups/TIMESTAMP \
  --target-dir ../../ \
  --verify
```

## Common Commands

### Audit

```bash
# Basic audit
python3 cli.py audit --bacpac BACPAC --code CODE

# Audit with migrations
python3 cli.py audit --bacpac BACPAC --code CODE --include-migrations

# Verbose audit
python3 cli.py audit --bacpac BACPAC --code CODE --verbose
```

### Fix

```bash
# Dry-run (preview only)
python3 cli.py fix --bacpac BACPAC --code CODE --dry-run

# Fix critical only
python3 cli.py fix --bacpac BACPAC --code CODE --severity CRITICAL

# Fix all
python3 cli.py fix --bacpac BACPAC --code CODE --severity INFO
```

### Validate

```bash
# Validate directory
python3 cli.py validate --directory CODE

# Validate specific files
python3 cli.py validate --files "CODE/**/*.py"
```

### Report

```bash
# Generate all reports
python3 cli.py report --bacpac BACPAC --code CODE --types all

# Generate specific reports
python3 cli.py report --bacpac BACPAC --types schema erd
```

## Troubleshooting

### Issue: "BACPAC file not found"

```bash
# Check file exists
ls -la ../../../pei-dashboard.bacpac

# Use absolute path
python3 cli.py audit --bacpac /full/path/to/pei-dashboard.bacpac --code ../../
```

### Issue: "Dependencies not installed"

```bash
# Reinstall dependencies
pip3 install -r requirements.txt

# Verify installation
python3 -c "import sqlparse, hypothesis, pytest; print('OK')"
```

### Issue: "Permission denied"

```bash
# Check permissions
ls -la

# Fix permissions (Linux/macOS)
chmod +x *.sh

# Or run with bash
bash deploy.sh
```

### Issue: "Syntax errors after fixing"

```bash
# Restore from backup
cp -r backups/TIMESTAMP/* ../../

# Verify restoration
python3 cli.py validate --directory ../../
```

## File Locations

```
azure_functions/tools/schema_audit/
├── deploy.sh              # Deployment script
├── rollback.sh            # Rollback script
├── monitor.sh             # Monitoring script
├── cli.py                 # Main CLI interface
├── requirements.txt       # Dependencies
├── README.md              # Full documentation
├── USER_GUIDE.md          # User guide
├── DEVELOPER_GUIDE.md     # Developer guide
├── DEPLOYMENT_GUIDE.md    # Detailed deployment guide
├── DEPLOYMENT_CHECKLIST.md # Deployment checklist
└── QUICK_DEPLOYMENT_GUIDE.md # This file
```

## Support

- **Full Documentation**: See README.md
- **User Guide**: See USER_GUIDE.md
- **Deployment Details**: See DEPLOYMENT_GUIDE.md
- **Deployment Checklist**: See DEPLOYMENT_CHECKLIST.md

## Next Steps

1. ✅ Complete deployment
2. 📖 Read USER_GUIDE.md for detailed workflows
3. 🔍 Run initial audit
4. 🛠️ Apply fixes as needed
5. 📊 Set up monitoring
6. 👥 Train team members

---

**Total Time**: ~15-20 minutes for complete deployment

**Status Check**: Run `./monitor.sh --check all` to verify deployment health
