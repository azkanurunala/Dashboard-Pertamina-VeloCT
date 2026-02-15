#!/bin/bash
# Database Schema Audit Tool - Rollback Script
# Version: 1.0.0
# Description: Automated rollback script for restoring from backups

set -e  # Exit on error
set -u  # Exit on undefined variable

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TOOL_NAME="Database Schema Audit Tool - Rollback"
VERSION="1.0.0"
ROLLBACK_LOG="rollback_$(date +%Y%m%d_%H%M%S).log"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$ROLLBACK_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$ROLLBACK_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$ROLLBACK_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$ROLLBACK_LOG"
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Rollback script for Database Schema Audit Tool

OPTIONS:
    -b, --backup-dir DIR     Backup directory to restore from (required)
    -t, --target-dir DIR     Target directory to restore to (required)
    -f, --force              Force rollback without confirmation
    -v, --verify             Verify restoration after rollback
    -h, --help               Show this help message

EXAMPLES:
    # Interactive rollback
    $0 --backup-dir backups/20240216_143022 --target-dir ../../

    # Force rollback without confirmation
    $0 -b backups/20240216_143022 -t ../../ --force

    # Rollback with verification
    $0 -b backups/20240216_143022 -t ../../ --verify

EOF
}

list_available_backups() {
    log_info "Available backups:"
    echo ""
    
    if [ ! -d "backups" ]; then
        log_warning "No backups directory found"
        return 1
    fi
    
    BACKUP_COUNT=0
    for backup in backups/*/; do
        if [ -d "$backup" ]; then
            BACKUP_COUNT=$((BACKUP_COUNT + 1))
            BACKUP_NAME=$(basename "$backup")
            BACKUP_SIZE=$(du -sh "$backup" | cut -f1)
            BACKUP_DATE=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$backup" 2>/dev/null || stat -c "%y" "$backup" 2>/dev/null | cut -d'.' -f1)
            FILE_COUNT=$(find "$backup" -type f | wc -l)
            
            echo "  [$BACKUP_COUNT] $BACKUP_NAME"
            echo "      Date: $BACKUP_DATE"
            echo "      Size: $BACKUP_SIZE"
            echo "      Files: $FILE_COUNT"
            echo ""
        fi
    done
    
    if [ $BACKUP_COUNT -eq 0 ]; then
        log_warning "No backups found"
        return 1
    fi
    
    return 0
}

verify_backup_dir() {
    local backup_dir="$1"
    
    if [ ! -d "$backup_dir" ]; then
        log_error "Backup directory not found: $backup_dir"
        return 1
    fi
    
    # Check if backup contains files
    FILE_COUNT=$(find "$backup_dir" -type f | wc -l)
    if [ $FILE_COUNT -eq 0 ]; then
        log_error "Backup directory is empty: $backup_dir"
        return 1
    fi
    
    log_info "Backup directory verified: $backup_dir"
    log_info "Files in backup: $FILE_COUNT"
    return 0
}

verify_target_dir() {
    local target_dir="$1"
    
    if [ ! -d "$target_dir" ]; then
        log_error "Target directory not found: $target_dir"
        return 1
    fi
    
    if [ ! -w "$target_dir" ]; then
        log_error "Target directory is not writable: $target_dir"
        return 1
    fi
    
    log_info "Target directory verified: $target_dir"
    return 0
}

confirm_rollback() {
    local backup_dir="$1"
    local target_dir="$2"
    
    echo ""
    echo "=========================================="
    echo "  ROLLBACK CONFIRMATION"
    echo "=========================================="
    echo ""
    echo "This will restore files from:"
    echo "  Source: $backup_dir"
    echo "  Target: $target_dir"
    echo ""
    log_warning "This operation will OVERWRITE existing files!"
    echo ""
    read -p "Are you sure you want to proceed? (yes/no): " confirmation
    
    if [ "$confirmation" != "yes" ]; then
        log_info "Rollback cancelled by user"
        return 1
    fi
    
    return 0
}

create_pre_rollback_backup() {
    local target_dir="$1"
    local pre_backup_dir="backups/pre_rollback_$(date +%Y%m%d_%H%M%S)"
    
    log_info "Creating pre-rollback backup..."
    
    mkdir -p "$pre_backup_dir"
    
    # Copy current state before rollback
    cp -r "$target_dir"/* "$pre_backup_dir/" 2>/dev/null || true
    
    if [ $? -eq 0 ]; then
        log_success "Pre-rollback backup created: $pre_backup_dir"
        echo "$pre_backup_dir"
        return 0
    else
        log_warning "Failed to create pre-rollback backup"
        return 1
    fi
}

perform_rollback() {
    local backup_dir="$1"
    local target_dir="$2"
    
    log_info "Starting rollback operation..."
    
    # Get list of files to restore
    FILES_TO_RESTORE=$(find "$backup_dir" -type f)
    TOTAL_FILES=$(echo "$FILES_TO_RESTORE" | wc -l)
    
    log_info "Restoring $TOTAL_FILES files..."
    
    RESTORED_COUNT=0
    FAILED_COUNT=0
    
    # Restore files
    while IFS= read -r file; do
        # Get relative path
        REL_PATH="${file#$backup_dir/}"
        TARGET_FILE="$target_dir/$REL_PATH"
        
        # Create target directory if needed
        TARGET_DIR=$(dirname "$TARGET_FILE")
        mkdir -p "$TARGET_DIR"
        
        # Copy file
        if cp "$file" "$TARGET_FILE" 2>/dev/null; then
            RESTORED_COUNT=$((RESTORED_COUNT + 1))
        else
            FAILED_COUNT=$((FAILED_COUNT + 1))
            log_warning "Failed to restore: $REL_PATH"
        fi
        
        # Progress indicator
        if [ $((RESTORED_COUNT % 10)) -eq 0 ]; then
            echo -ne "\rProgress: $RESTORED_COUNT/$TOTAL_FILES files restored..."
        fi
    done <<< "$FILES_TO_RESTORE"
    
    echo ""  # New line after progress
    
    log_info "Rollback complete"
    log_info "Files restored: $RESTORED_COUNT"
    
    if [ $FAILED_COUNT -gt 0 ]; then
        log_warning "Files failed: $FAILED_COUNT"
        return 1
    fi
    
    return 0
}

verify_restoration() {
    local target_dir="$1"
    
    log_info "Verifying restoration..."
    
    # Check if Python files are valid
    PYTHON_FILES=$(find "$target_dir" -name "*.py" -type f)
    INVALID_COUNT=0
    
    while IFS= read -r pyfile; do
        if [ -f "$pyfile" ]; then
            python3 -m py_compile "$pyfile" 2>/dev/null
            if [ $? -ne 0 ]; then
                INVALID_COUNT=$((INVALID_COUNT + 1))
                log_warning "Invalid Python file: $pyfile"
            fi
        fi
    done <<< "$PYTHON_FILES"
    
    if [ $INVALID_COUNT -eq 0 ]; then
        log_success "All Python files are valid"
        return 0
    else
        log_warning "$INVALID_COUNT Python files have syntax errors"
        return 1
    fi
}

generate_rollback_report() {
    local backup_dir="$1"
    local target_dir="$2"
    local pre_backup_dir="$3"
    
    REPORT_FILE="ROLLBACK_REPORT_$(date +%Y%m%d_%H%M%S).md"
    
    cat > "$REPORT_FILE" << EOF
# Rollback Report

**Date**: $(date '+%Y-%m-%d %H:%M:%S')
**Performed By**: $(whoami)
**Host**: $(hostname)

## Rollback Details

- **Source Backup**: $backup_dir
- **Target Directory**: $target_dir
- **Pre-Rollback Backup**: $pre_backup_dir

## Summary

- **Status**: ✅ Rollback completed successfully
- **Files Restored**: $(find "$backup_dir" -type f | wc -l)
- **Log File**: $ROLLBACK_LOG

## Verification

$(if verify_restoration "$target_dir" > /dev/null 2>&1; then
    echo "✅ All Python files are syntactically valid"
else
    echo "⚠️ Some Python files have syntax errors (see log for details)"
fi)

## Next Steps

1. Review rollback log: \`$ROLLBACK_LOG\`
2. Verify application functionality
3. Run tests if available
4. Monitor for issues

## Rollback of Rollback

If you need to undo this rollback:

\`\`\`bash
./rollback.sh --backup-dir $pre_backup_dir --target-dir $target_dir --force
\`\`\`

## Support

For issues, refer to DEPLOYMENT_GUIDE.md or contact the development team.

EOF
    
    log_success "Rollback report created: $REPORT_FILE"
}

# Main rollback process
main() {
    BACKUP_DIR=""
    TARGET_DIR=""
    FORCE=false
    VERIFY=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -b|--backup-dir)
                BACKUP_DIR="$2"
                shift 2
                ;;
            -t|--target-dir)
                TARGET_DIR="$2"
                shift 2
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -v|--verify)
                VERIFY=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    echo ""
    echo "=========================================="
    echo "  $TOOL_NAME"
    echo "  Version: $VERSION"
    echo "=========================================="
    echo ""
    
    log_info "Starting rollback at $(date)"
    log_info "Rollback log: $ROLLBACK_LOG"
    echo ""
    
    # Show available backups if no backup specified
    if [ -z "$BACKUP_DIR" ]; then
        list_available_backups
        echo ""
        read -p "Enter backup directory path: " BACKUP_DIR
    fi
    
    # Get target directory if not specified
    if [ -z "$TARGET_DIR" ]; then
        read -p "Enter target directory path: " TARGET_DIR
    fi
    
    # Verify directories
    log_info "=== Verification ==="
    verify_backup_dir "$BACKUP_DIR" || exit 1
    verify_target_dir "$TARGET_DIR" || exit 1
    echo ""
    
    # Confirm rollback
    if [ "$FORCE" = false ]; then
        confirm_rollback "$BACKUP_DIR" "$TARGET_DIR" || exit 0
    fi
    echo ""
    
    # Create pre-rollback backup
    log_info "=== Pre-Rollback Backup ==="
    PRE_BACKUP_DIR=$(create_pre_rollback_backup "$TARGET_DIR")
    echo ""
    
    # Perform rollback
    log_info "=== Rollback Operation ==="
    perform_rollback "$BACKUP_DIR" "$TARGET_DIR" || {
        log_error "Rollback failed"
        exit 1
    }
    echo ""
    
    # Verify restoration
    if [ "$VERIFY" = true ]; then
        log_info "=== Verification ==="
        verify_restoration "$TARGET_DIR"
        echo ""
    fi
    
    # Generate report
    log_info "=== Report Generation ==="
    generate_rollback_report "$BACKUP_DIR" "$TARGET_DIR" "$PRE_BACKUP_DIR"
    echo ""
    
    # Success
    echo "=========================================="
    log_success "Rollback completed successfully!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "  1. Review rollback log: $ROLLBACK_LOG"
    echo "  2. Verify application functionality"
    echo "  3. Run tests if available"
    echo ""
    echo "Pre-rollback backup saved to: $PRE_BACKUP_DIR"
    echo ""
    
    return 0
}

# Run main function
main "$@"
