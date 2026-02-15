# Deployment Checklist: Database Schema Audit Tool

Use this checklist to ensure a smooth deployment of the Database Schema Audit Tool.

## Pre-Deployment Phase

### Environment Verification

- [ ] **Python Version**
  ```bash
  python3 --version
  # Should be 3.9 or higher
  ```

- [ ] **Pip Available**
  ```bash
  pip3 --version
  ```

- [ ] **Git Installed**
  ```bash
  git --version
  ```

- [ ] **Disk Space**
  ```bash
  df -h .
  # Ensure at least 500MB available
  ```

- [ ] **Permissions**
  ```bash
  # Verify read/write access to code directories
  touch test.txt && rm test.txt
  ```

### Code Preparation

- [ ] **All Changes Committed**
  ```bash
  git status
  # Should show clean working directory
  ```

- [ ] **Create Deployment Branch**
  ```bash
  git checkout -b deployment/schema-audit-tool
  ```

- [ ] **BACPAC File Available**
  ```bash
  ls -la pei-dashboard.bacpac
  ```

- [ ] **Code Directory Verified**
  ```bash
  ls -la azure_functions/
  ```

### Backup Strategy

- [ ] **Manual Backup Created**
  ```bash
  cp -r azure_functions/ backups/manual_$(date +%Y%m%d_%H%M%S)/
  ```

- [ ] **Backup Location Documented**
  - Location: ___________________________
  - Date: ___________________________

### Team Coordination

- [ ] **Deployment Plan Reviewed**
  - Team members notified: ___________________________
  - Deployment window: ___________________________

- [ ] **Communication Channels Established**
  - Primary: ___________________________
  - Emergency: ___________________________

- [ ] **Rollback Procedures Understood**
  - Rollback owner: ___________________________
  - Rollback time estimate: ___________________________

## Deployment Phase

### Step 1: Navigate to Tool Directory

- [ ] **Change Directory**
  ```bash
  cd azure_functions/tools/schema_audit
  ```

- [ ] **Verify Location**
  ```bash
  pwd
  ls -la
  ```

### Step 2: Make Scripts Executable (Linux/macOS)

- [ ] **Set Execute Permissions**
  ```bash
  chmod +x deploy.sh rollback.sh monitor.sh
  ```

### Step 3: Run Deployment Script

- [ ] **Execute Deployment**
  ```bash
  ./deploy.sh
  ```
  
  **Windows Alternative:**
  ```bash
  bash deploy.sh
  ```

- [ ] **Monitor Output**
  - Watch for errors or warnings
  - Note any issues: ___________________________

- [ ] **Review Deployment Log**
  ```bash
  cat deployment_*.log
  ```

### Step 4: Verify Installation

- [ ] **Check CLI Help**
  ```bash
  python3 cli.py --help
  ```

- [ ] **Test Each Command**
  ```bash
  python3 cli.py audit --help
  python3 cli.py fix --help
  python3 cli.py validate --help
  python3 cli.py report --help
  ```

- [ ] **Verify Directories Created**
  ```bash
  ls -la output/ backups/ logs/ reports/
  ```

### Step 5: Run Smoke Tests

- [ ] **Test Audit Command**
  ```bash
  python3 cli.py audit \
    --bacpac ../../../pei-dashboard.bacpac \
    --code ../../ \
    --output smoke_test_audit.md
  ```

- [ ] **Review Smoke Test Output**
  ```bash
  cat smoke_test_audit.md
  ```

- [ ] **Test Dry-Run Fix**
  ```bash
  python3 cli.py fix \
    --bacpac ../../../pei-dashboard.bacpac \
    --code ../../ \
    --dry-run \
    --output smoke_test_fix.md
  ```

- [ ] **Test Validation**
  ```bash
  python3 cli.py validate \
    --directory ../../ \
    --output smoke_test_validate.md
  ```

### Step 6: Run Test Suite (Optional)

- [ ] **Execute Tests**
  ```bash
  pytest --tb=short -v
  ```

- [ ] **Review Test Results**
  - Tests passed: _____ / _____
  - Tests failed: _____ (acceptable if non-critical)

- [ ] **Check Code Coverage**
  ```bash
  pytest --cov=. --cov-report=html
  open htmlcov/index.html
  ```

## Post-Deployment Phase

### Verification

- [ ] **Verify All Components**
  ```bash
  python3 -c "
  from schema_extractor import SchemaExtractor
  from code_auditor import CodeAuditor
  from mismatch_detector import MismatchDetector
  from schema_fixer import SchemaFixer
  from validator import Validator
  from reporter import Reporter
  print('All components imported successfully')
  "
  ```

- [ ] **Check Documentation**
  ```bash
  ls -la *.md
  # Verify README.md, USER_GUIDE.md, DEVELOPER_GUIDE.md, DEPLOYMENT_GUIDE.md exist
  ```

- [ ] **Verify Deployment Summary**
  ```bash
  cat DEPLOYMENT_SUMMARY_*.md
  ```

### Configuration

- [ ] **Set Environment Variables (Optional)**
  ```bash
  export SCHEMA_AUDIT_LOG_LEVEL=INFO
  export SCHEMA_AUDIT_BACKUP_DIR=/path/to/backups
  ```

- [ ] **Add to Shell Profile (Optional)**
  ```bash
  echo 'export SCHEMA_AUDIT_LOG_LEVEL=INFO' >> ~/.bashrc
  source ~/.bashrc
  ```

### Monitoring Setup

- [ ] **Test Monitoring Script**
  ```bash
  ./monitor.sh --check all
  ```

- [ ] **Review Health Report**
  ```bash
  ./monitor.sh --check all --output health_report.txt
  cat health_report.txt
  ```

- [ ] **Configure Alerting (Optional)**
  - Edit monitor.sh to add email/Slack integration
  - Test alert delivery

- [ ] **Schedule Regular Health Checks (Optional)**
  ```bash
  # Add to crontab for daily checks
  crontab -e
  # Add: 0 9 * * * /path/to/schema_audit/monitor.sh --check all --alert
  ```

### Documentation Review

- [ ] **README.md Reviewed**
  - Installation instructions clear
  - Examples work as documented

- [ ] **USER_GUIDE.md Reviewed**
  - Workflows documented
  - Troubleshooting section complete

- [ ] **DEVELOPER_GUIDE.md Reviewed**
  - Architecture documented
  - Extension points clear

- [ ] **DEPLOYMENT_GUIDE.md Reviewed**
  - Deployment steps accurate
  - Rollback procedures clear
  - Monitoring setup documented

## Phase 1: Audit Only (Read-Only Operations)

### Objective
Run audits without making any changes to verify tool functionality.

- [ ] **Run Initial Audit**
  ```bash
  python3 cli.py audit \
    --bacpac ../../../pei-dashboard.bacpac \
    --code ../../ \
    --output reports/phase1_audit_$(date +%Y%m%d).md \
    --verbose
  ```

- [ ] **Review Audit Results**
  - Total mismatches found: _____
  - Critical mismatches: _____
  - Warning mismatches: _____
  - Info mismatches: _____

- [ ] **Share Results with Team**
  - Report distributed: [ ] Yes [ ] No
  - Team feedback received: [ ] Yes [ ] No

- [ ] **Identify High-Priority Issues**
  - List critical issues: ___________________________
  - Prioritization complete: [ ] Yes [ ] No

- [ ] **Phase 1 Sign-Off**
  - Approved by: ___________________________
  - Date: ___________________________

## Phase 2: Dry-Run Fixes (Preview Changes)

### Objective
Preview fixes without applying them to verify fix strategies.

- [ ] **Run Dry-Run Fix**
  ```bash
  python3 cli.py fix \
    --bacpac ../../../pei-dashboard.bacpac \
    --code ../../ \
    --dry-run \
    --severity CRITICAL \
    --output reports/phase2_fix_preview_$(date +%Y%m%d).md
  ```

- [ ] **Review Fix Preview**
  - Files to be modified: _____
  - Changes look correct: [ ] Yes [ ] No
  - Concerns identified: ___________________________

- [ ] **Test with Different Severity Levels**
  ```bash
  # Test WARNING level
  python3 cli.py fix --bacpac ... --code ... --dry-run --severity WARNING
  
  # Test INFO level
  python3 cli.py fix --bacpac ... --code ... --dry-run --severity INFO
  ```

- [ ] **Validate Fix Strategies**
  - Column name fixes: [ ] Correct [ ] Needs adjustment
  - Type fixes: [ ] Correct [ ] Needs adjustment
  - Missing column fixes: [ ] Correct [ ] Needs adjustment

- [ ] **Phase 2 Sign-Off**
  - Approved by: ___________________________
  - Date: ___________________________

## Phase 3: Automated Fixes (Apply Changes)

### Objective
Apply fixes to critical issues with monitoring.

### Pre-Fix Checklist

- [ ] **Create Pre-Fix Backup**
  ```bash
  cp -r azure_functions/ backups/pre_fix_$(date +%Y%m%d_%H%M%S)/
  ```

- [ ] **Commit Current State**
  ```bash
  git add -A
  git commit -m "Pre-fix checkpoint: Schema audit tool deployment"
  ```

- [ ] **Notify Team**
  - Team notified of fix operation: [ ] Yes [ ] No

### Apply Fixes

- [ ] **Apply Critical Fixes**
  ```bash
  python3 cli.py fix \
    --bacpac ../../../pei-dashboard.bacpac \
    --code ../../ \
    --severity CRITICAL \
    --backup-dir backups/fix_$(date +%Y%m%d_%H%M%S) \
    --output reports/phase3_fix_report_$(date +%Y%m%d).md
  ```

- [ ] **Monitor Fix Progress**
  - Watch for errors in real-time
  - Note any failures: ___________________________

- [ ] **Review Fix Report**
  ```bash
  cat reports/phase3_fix_report_*.md
  ```
  - Fixes applied: _____ / _____
  - Fixes failed: _____

### Post-Fix Validation

- [ ] **Validate Modified Files**
  ```bash
  python3 cli.py validate \
    --directory ../../ \
    --output reports/phase3_validation_$(date +%Y%m%d).md
  ```

- [ ] **Review Validation Results**
  - All files valid: [ ] Yes [ ] No
  - Syntax errors: _____
  - Import errors: _____

- [ ] **Run Application Tests (if available)**
  ```bash
  # Run your application's test suite
  pytest azure_functions/tests/
  ```

- [ ] **Manual Verification**
  - Spot-check modified files
  - Verify changes are correct
  - Test affected functionality

### Rollback Test

- [ ] **Test Rollback Procedure**
  ```bash
  # Test on a copy, not production
  ./rollback.sh --backup-dir backups/fix_TIMESTAMP --target-dir test_restore/ --force
  ```

- [ ] **Verify Rollback Works**
  - Files restored correctly: [ ] Yes [ ] No

- [ ] **Phase 3 Sign-Off**
  - Approved by: ___________________________
  - Date: ___________________________

## Phase 4: Full Production (Regular Operations)

### Objective
Establish regular operational procedures.

- [ ] **Schedule Regular Audits**
  - Frequency: ___________________________
  - Responsible person: ___________________________

- [ ] **Configure Monitoring**
  - Health checks scheduled: [ ] Yes [ ] No
  - Alerting configured: [ ] Yes [ ] No

- [ ] **Document Operational Procedures**
  - Daily operations documented: [ ] Yes [ ] No
  - Weekly operations documented: [ ] Yes [ ] No
  - Monthly operations documented: [ ] Yes [ ] No

- [ ] **Train Team Members**
  - Training sessions conducted: [ ] Yes [ ] No
  - Documentation distributed: [ ] Yes [ ] No

- [ ] **Establish Support Process**
  - Support contact: ___________________________
  - Escalation path: ___________________________

- [ ] **Phase 4 Sign-Off**
  - Approved by: ___________________________
  - Date: ___________________________

## Final Sign-Off

### Deployment Complete

- [ ] **All Phases Completed**
  - Phase 1: Audit Only [ ] Complete
  - Phase 2: Dry-Run Fixes [ ] Complete
  - Phase 3: Automated Fixes [ ] Complete
  - Phase 4: Full Production [ ] Complete

- [ ] **Documentation Complete**
  - All documentation reviewed and approved
  - Team trained on tool usage

- [ ] **Monitoring Active**
  - Health checks running
  - Alerts configured

- [ ] **Backup Strategy Verified**
  - Backups being created
  - Retention policy in place

- [ ] **Rollback Plan Tested**
  - Rollback procedure verified
  - Team understands rollback process

### Final Approval

**Deployment Approved By:**

- Technical Lead: ___________________________ Date: ___________
- Operations Lead: ___________________________ Date: ___________
- Project Manager: ___________________________ Date: ___________

### Post-Deployment Notes

**Issues Encountered:**
___________________________________________________________________
___________________________________________________________________
___________________________________________________________________

**Lessons Learned:**
___________________________________________________________________
___________________________________________________________________
___________________________________________________________________

**Recommendations for Future Deployments:**
___________________________________________________________________
___________________________________________________________________
___________________________________________________________________

---

**Deployment Completed:** ___________________________  
**Deployment Duration:** ___________________________  
**Overall Status:** [ ] Success [ ] Success with issues [ ] Failed

