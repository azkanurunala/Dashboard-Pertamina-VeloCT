# Deployment Guide: Database Schema Audit Tool

Complete guide for deploying, configuring, and operating the Database Schema Audit Tool in production environments.

## Table of Contents

- [Overview](#overview)
- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Deployment Steps](#deployment-steps)
- [Configuration](#configuration)
- [Rollback Plan](#rollback-plan)
- [Monitoring and Alerting](#monitoring-and-alerting)
- [Operational Procedures](#operational-procedures)
- [Troubleshooting](#troubleshooting)

## Overview

### Deployment Strategy

The Database Schema Audit Tool follows a phased deployment approach:

1. **Phase 1: Audit Only** (Read-only operations)
2. **Phase 2: Dry-Run Fixes** (Preview changes)
3. **Phase 3: Automated Fixes** (Apply changes with monitoring)
4. **Phase 4: Full Production** (Regular operations)

### System Requirements

- **Python**: 3.9 or higher
- **Memory**: Minimum 512MB RAM, recommended 1GB+
- **Disk Space**: Minimum 100MB for tool + space for backups
- **OS**: Linux, macOS, or Windows with bash support
- **Permissions**: Read/write access to code directories

### Dependencies

```
sqlparse>=0.4.4
hypothesis>=6.92.0
pytest>=7.4.3
pytest-cov>=4.1.0
```

## Pre-Deployment Checklist

### Environment Preparation

- [ ] Python 3.9+ installed and verified
- [ ] pip package manager available
- [ ] Git installed (for version control)
- [ ] Sufficient disk space available
- [ ] Network access (if downloading dependencies)

### Code Preparation

- [ ] All code committed to version control
- [ ] Working branch created for deployment
- [ ] BACPAC file available and up-to-date
- [ ] Code directory structure verified
- [ ] Backup strategy defined

### Team Preparation

- [ ] Deployment plan reviewed with team
- [ ] Rollback procedures understood
- [ ] Monitoring plan in place
- [ ] Communication channels established
- [ ] Deployment window scheduled

### Documentation Review

- [ ] README.md reviewed
- [ ] USER_GUIDE.md reviewed
- [ ] DEVELOPER_GUIDE.md reviewed
- [ ] This deployment guide reviewed

## Deployment Steps

### Automated Deployment

The tool includes an automated deployment script for quick setup.

#### Step 1: Navigate to Tool Directory

```bash
cd azure_functions/tools/schema_audit
```

#### Step 2: Make Deployment Script Executable

```bash
chmod +x deploy.sh
```

#### Step 3: Run Deployment Script

```bash
./deploy.sh
```

The script will:
- Check Python version
- Install dependencies
- Verify installation
- Run tests
- Create required directories
- Generate deployment summary

#### Step 4: Review Deployment Log

```bash
cat deployment_*.log
```

Check for any warnings or errors.

### Manual Deployment

If automated deployment is not suitable, follow these manual steps.

#### Step 1: Verify Python Version

```bash
python3 --version
# Should be 3.9 or higher
```

#### Step 2: Install Dependencies

```bash
pip3 install -r requirements.txt
```

#### Step 3: Verify Installation

```bash
python3 cli.py --help
```

Should display help text without errors.

#### Step 4: Create Required Directories

```bash
mkdir -p output backups logs reports
```

#### Step 5: Run Test Suite (Optional)

```bash
pytest --tb=short -v
```

#### Step 6: Verify Documentation

```bash
ls -la *.md
# Should see README.md, USER_GUIDE.md, DEVELOPER_GUIDE.md, etc.
```

### Post-Deployment Verification

#### Verify CLI Commands

```bash
# Test audit command
python3 cli.py audit --help

# Test fix command
python3 cli.py fix --help

# Test validate command
python3 cli.py validate --help

# Test report command
python3 cli.py report --help
```

All commands should display help text without errors.

#### Run Smoke Test

```bash
# Create a test BACPAC path (adjust as needed)
BACPAC_PATH="../../../pei-dashboard.bacpac"

# Run audit in dry-run mode
python3 cli.py audit \
  --bacpac "$BACPAC_PATH" \
  --code ../../ \
  --output smoke_test_audit.md

# Check output
cat smoke_test_audit.md
```

#### Verify File Permissions

```bash
# Check tool files are readable
ls -la *.py

# Check directories are writable
touch output/test.txt && rm output/test.txt
touch backups/test.txt && rm backups/test.txt
touch logs/test.txt && rm logs/test.txt
```

## Configuration

### Environment Variables

Set these environment variables for customized behavior:

```bash
# Logging level (DEBUG, INFO, WARNING, ERROR)
export SCHEMA_AUDIT_LOG_LEVEL=INFO

# Default backup directory
export SCHEMA_AUDIT_BACKUP_DIR=/path/to/backups

# Default output directory
export SCHEMA_AUDIT_OUTPUT_DIR=/path/to/output
```

Add to your shell profile (`.bashrc`, `.zshrc`, etc.):

```bash
# Database Schema Audit Tool Configuration
export SCHEMA_AUDIT_LOG_LEVEL=INFO
export SCHEMA_AUDIT_BACKUP_DIR="$HOME/schema_audit_backups"
export SCHEMA_AUDIT_OUTPUT_DIR="$HOME/schema_audit_output"
```

### Configuration File (Optional)

Create a configuration file for repeated use:

```bash
# config.sh
BACPAC_PATH="/path/to/pei-dashboard.bacpac"
CODE_PATH="/path/to/azure_functions"
BACKUP_DIR="/path/to/backups"
OUTPUT_DIR="/path/to/output"
```

Use in scripts:

```bash
source config.sh
python3 cli.py audit --bacpac "$BACPAC_PATH" --code "$CODE_PATH"
```

### Logging Configuration

Logging is configured in `logging_config.py`. To customize:

1. Edit `logging_config.py`
2. Adjust log levels, formats, or handlers
3. Restart the tool

Default configuration:
- Console output: INFO level
- File output: DEBUG level (if enabled)
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

## Rollback Plan

### Rollback Scenarios

1. **Deployment Failure**: Installation or verification fails
2. **Test Failures**: Critical tests fail after deployment
3. **Runtime Errors**: Tool fails during operation
4. **Data Issues**: Fixes cause problems in code

### Rollback Procedures

#### Scenario 1: Deployment Failure

If deployment script fails:

```bash
# 1. Review deployment log
cat deployment_*.log

# 2. Identify the failure point
# 3. Fix the issue (e.g., install missing dependencies)
# 4. Re-run deployment
./deploy.sh
```

#### Scenario 2: Test Failures

If tests fail after deployment:

```bash
# 1. Review test output
pytest --tb=short -v

# 2. Determine if failures are critical
# 3. If critical, rollback to previous version
git checkout previous_version

# 4. Re-install dependencies
pip3 install -r requirements.txt
```

#### Scenario 3: Runtime Errors

If tool fails during operation:

```bash
# 1. Stop any running operations
# 2. Review error logs
cat logs/*.log

# 3. If fixes were applied, restore from backup
# See "Restoring from Backup" section below
```

#### Scenario 4: Data Issues

If applied fixes cause problems:

```bash
# 1. Identify the backup directory
ls -la backups/

# 2. Restore affected files
# See "Restoring from Backup" section below

# 3. Verify restoration
python3 cli.py validate --directory /path/to/restored/files
```

### Restoring from Backup

#### Automatic Backups

The tool creates automatic backups before applying fixes:

```bash
# Backups are stored in: backups/TIMESTAMP/
# Example: backups/20240216_143022/

# List available backups
ls -la backups/

# Restore entire backup
BACKUP_DIR="backups/20240216_143022"
cp -r "$BACKUP_DIR"/* /path/to/azure_functions/

# Restore specific file
cp "$BACKUP_DIR/path/to/file.py" /path/to/azure_functions/path/to/file.py
```

#### Manual Backups

If you created manual backups:

```bash
# Restore from manual backup
MANUAL_BACKUP="/path/to/manual_backup"
cp -r "$MANUAL_BACKUP"/* /path/to/azure_functions/
```

#### Verify Restoration

After restoring:

```bash
# 1. Verify file integrity
diff -r backups/TIMESTAMP/ /path/to/azure_functions/

# 2. Validate Python syntax
python3 cli.py validate --directory /path/to/azure_functions/

# 3. Run tests (if available)
pytest /path/to/azure_functions/tests/
```

### Version Control Rollback

If using Git:

```bash
# 1. Check current status
git status

# 2. Discard all changes
git reset --hard HEAD

# 3. Or revert to specific commit
git log --oneline
git reset --hard COMMIT_HASH

# 4. Verify restoration
git status
```

### Emergency Rollback Procedure

For critical production issues:

1. **Immediate Action**:
   ```bash
   # Stop any running operations
   # Restore from most recent backup
   cp -r backups/latest/* /path/to/azure_functions/
   ```

2. **Verification**:
   ```bash
   # Validate restored files
   python3 cli.py validate --directory /path/to/azure_functions/
   ```

3. **Communication**:
   - Notify team of rollback
   - Document the issue
   - Schedule post-mortem

4. **Investigation**:
   - Review logs
   - Identify root cause
   - Plan corrective action

## Monitoring and Alerting

### Monitoring Strategy

Monitor the following aspects of the tool:

1. **Execution Success Rate**: Track successful vs. failed runs
2. **Performance Metrics**: Execution time, memory usage
3. **Error Rates**: Frequency and types of errors
4. **Fix Success Rate**: Successful fixes vs. failures
5. **Backup Health**: Backup creation and storage

### Logging

#### Log Locations

```bash
# Deployment logs
deployment_*.log

# Operation logs (if configured)
logs/schema_audit_*.log

# CLI output
# Captured in terminal or redirected to file
```

#### Log Levels

- **DEBUG**: Detailed execution information
- **INFO**: General progress and results
- **WARNING**: Non-critical issues
- **ERROR**: Critical failures

#### Viewing Logs

```bash
# View recent logs
tail -f logs/schema_audit_*.log

# Search for errors
grep ERROR logs/*.log

# Search for warnings
grep WARNING logs/*.log

# View specific operation
grep "audit" logs/*.log
```

### Metrics to Track

#### Execution Metrics

```bash
# Track in a metrics file or monitoring system
{
  "timestamp": "2024-02-16T14:30:00Z",
  "operation": "audit",
  "duration_seconds": 15.3,
  "files_scanned": 145,
  "mismatches_found": 12,
  "status": "success"
}
```

#### Error Metrics

```bash
# Track error frequency
{
  "timestamp": "2024-02-16T14:30:00Z",
  "operation": "fix",
  "error_type": "SyntaxError",
  "error_count": 1,
  "affected_files": ["scraper.py"]
}
```

### Alerting Rules

Set up alerts for:

1. **Critical Errors**:
   - Alert when any operation fails with ERROR level
   - Immediate notification to team

2. **High Mismatch Count**:
   - Alert when critical mismatches exceed threshold (e.g., >10)
   - Daily summary notification

3. **Performance Degradation**:
   - Alert when execution time exceeds threshold (e.g., >60 seconds)
   - Weekly performance report

4. **Backup Failures**:
   - Alert when backup creation fails
   - Immediate notification

### Monitoring Script Example

```bash
#!/bin/bash
# monitor_schema_audit.sh

LOG_FILE="logs/schema_audit_$(date +%Y%m%d).log"
ALERT_EMAIL="team@example.com"

# Check for errors in last hour
ERROR_COUNT=$(grep -c ERROR "$LOG_FILE" 2>/dev/null || echo 0)

if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "Schema Audit Tool: $ERROR_COUNT errors detected" | \
        mail -s "Schema Audit Alert" "$ALERT_EMAIL"
fi

# Check execution time
# Parse log for duration and alert if > 60 seconds
```

### Health Check Script

```bash
#!/bin/bash
# health_check.sh

echo "=== Schema Audit Tool Health Check ==="

# Check Python
python3 --version || echo "ERROR: Python not found"

# Check dependencies
python3 -c "import sqlparse, hypothesis, pytest" || echo "ERROR: Dependencies missing"

# Check CLI
python3 cli.py --help > /dev/null || echo "ERROR: CLI not working"

# Check directories
for dir in output backups logs reports; do
    [ -d "$dir" ] || echo "WARNING: Directory $dir missing"
done

# Check disk space
DISK_USAGE=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "WARNING: Disk usage at ${DISK_USAGE}%"
fi

echo "=== Health Check Complete ==="
```

Run health check:

```bash
chmod +x health_check.sh
./health_check.sh
```

### Integration with Monitoring Systems

#### Prometheus Metrics (Example)

```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Counters
audit_runs_total = Counter('schema_audit_runs_total', 'Total audit runs')
fix_runs_total = Counter('schema_fix_runs_total', 'Total fix runs')
errors_total = Counter('schema_audit_errors_total', 'Total errors')

# Histograms
audit_duration = Histogram('schema_audit_duration_seconds', 'Audit duration')
fix_duration = Histogram('schema_fix_duration_seconds', 'Fix duration')

# Gauges
mismatches_found = Gauge('schema_mismatches_found', 'Current mismatches')
```

#### CloudWatch Logs (AWS)

```bash
# Send logs to CloudWatch
aws logs put-log-events \
  --log-group-name /schema-audit/operations \
  --log-stream-name $(date +%Y%m%d) \
  --log-events file://log_events.json
```

#### Azure Monitor

```bash
# Send metrics to Azure Monitor
az monitor metrics alert create \
  --name schema-audit-errors \
  --resource-group myResourceGroup \
  --condition "count > 0"
```

## Operational Procedures

### Daily Operations

#### Morning Check

```bash
# 1. Check for overnight errors
grep ERROR logs/schema_audit_$(date +%Y%m%d).log

# 2. Review backup status
ls -lh backups/ | tail -5

# 3. Check disk space
df -h .
```

#### Scheduled Audit

```bash
# Run daily audit
python3 cli.py audit \
  --bacpac /path/to/pei-dashboard.bacpac \
  --code /path/to/azure_functions/ \
  --output reports/daily_audit_$(date +%Y%m%d).md

# Email report to team
mail -s "Daily Schema Audit" team@example.com < reports/daily_audit_$(date +%Y%m%d).md
```

### Weekly Operations

#### Weekly Review

```bash
# 1. Review all audits from past week
ls -la reports/daily_audit_*.md | tail -7

# 2. Aggregate mismatch trends
# (Custom script to parse reports)

# 3. Clean old backups (keep last 30 days)
find backups/ -type d -mtime +30 -exec rm -rf {} \;

# 4. Clean old logs (keep last 90 days)
find logs/ -type f -mtime +90 -delete
```

#### Performance Review

```bash
# Analyze execution times
grep "duration" logs/*.log | awk '{print $NF}' | sort -n

# Check memory usage trends
# (Use system monitoring tools)
```

### Monthly Operations

#### Monthly Maintenance

```bash
# 1. Update dependencies
pip3 install --upgrade -r requirements.txt

# 2. Run full test suite
pytest --cov=. --cov-report=html

# 3. Review and update documentation
# (Manual review)

# 4. Archive old reports
tar -czf reports_archive_$(date +%Y%m).tar.gz reports/
mv reports_archive_*.tar.gz archives/
```

#### Monthly Report

Generate monthly summary:
- Total audits run
- Total fixes applied
- Error rate
- Performance metrics
- Recommendations

### Backup Management

#### Backup Retention Policy

- **Recent backups**: Keep all backups from last 7 days
- **Weekly backups**: Keep one backup per week for last 4 weeks
- **Monthly backups**: Keep one backup per month for last 12 months
- **Yearly backups**: Keep one backup per year indefinitely

#### Backup Cleanup Script

```bash
#!/bin/bash
# cleanup_backups.sh

BACKUP_DIR="backups"

# Keep all backups from last 7 days
find "$BACKUP_DIR" -type d -mtime -7

# For older backups, keep only weekly
# (Implementation depends on naming convention)

# Archive old backups
tar -czf backup_archive_$(date +%Y%m).tar.gz "$BACKUP_DIR"/*
```

## Troubleshooting

### Common Issues

#### Issue: Deployment Script Fails

**Symptoms**: `deploy.sh` exits with error

**Diagnosis**:
```bash
# Check deployment log
cat deployment_*.log | grep ERROR
```

**Solutions**:
- Verify Python version: `python3 --version`
- Check dependencies: `pip3 list`
- Verify permissions: `ls -la`
- Check disk space: `df -h`

#### Issue: High Memory Usage

**Symptoms**: Tool becomes slow or crashes

**Diagnosis**:
```bash
# Monitor memory during execution
top -p $(pgrep -f cli.py)
```

**Solutions**:
- Process smaller directories
- Increase available memory
- Close other applications
- Use batch processing

#### Issue: Slow Execution

**Symptoms**: Operations take longer than expected

**Diagnosis**:
```bash
# Profile execution
python3 -m cProfile cli.py audit --bacpac ... --code ...
```

**Solutions**:
- Check disk I/O: `iostat`
- Optimize file scanning patterns
- Use SSD for better performance
- Process in parallel (if supported)

### Getting Support

For issues not covered here:

1. **Check Documentation**:
   - README.md
   - USER_GUIDE.md
   - DEVELOPER_GUIDE.md

2. **Review Logs**:
   - Deployment logs
   - Operation logs
   - Error messages

3. **Contact Team**:
   - Email: team@example.com
   - Slack: #schema-audit
   - Issue tracker: [link]

4. **Provide Information**:
   - Error messages
   - Log files
   - Steps to reproduce
   - Environment details

## Appendix

### Deployment Checklist

Use this checklist for each deployment:

- [ ] Pre-deployment checklist completed
- [ ] Deployment script executed successfully
- [ ] Post-deployment verification passed
- [ ] Smoke test completed
- [ ] Documentation reviewed
- [ ] Team notified
- [ ] Monitoring configured
- [ ] Backup strategy verified
- [ ] Rollback plan understood
- [ ] Deployment summary created

### Quick Reference

```bash
# Deploy
./deploy.sh

# Run audit
python3 cli.py audit --bacpac BACPAC --code CODE

# Preview fixes
python3 cli.py fix --bacpac BACPAC --code CODE --dry-run

# Apply fixes
python3 cli.py fix --bacpac BACPAC --code CODE --severity CRITICAL

# Validate
python3 cli.py validate --directory CODE

# Restore backup
cp -r backups/TIMESTAMP/* CODE/

# Health check
./health_check.sh
```

### Contact Information

- **Development Team**: dev-team@example.com
- **Operations Team**: ops-team@example.com
- **Emergency Contact**: on-call@example.com

---

**Document Version**: 1.0.0  
**Last Updated**: 2024-02-16  
**Next Review**: 2024-03-16
