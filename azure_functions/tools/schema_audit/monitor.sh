#!/bin/bash
# Database Schema Audit Tool - Monitoring Script
# Version: 1.0.0
# Description: Monitoring and health check script

set -u  # Exit on undefined variable

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
TOOL_NAME="Database Schema Audit Tool - Monitor"
VERSION="1.0.0"
MONITOR_LOG="monitor_$(date +%Y%m%d_%H%M%S).log"
ALERT_THRESHOLD_ERRORS=5
ALERT_THRESHOLD_DISK=90
ALERT_THRESHOLD_MEMORY=80

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$MONITOR_LOG"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1" | tee -a "$MONITOR_LOG"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1" | tee -a "$MONITOR_LOG"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1" | tee -a "$MONITOR_LOG"
}

log_section() {
    echo -e "${CYAN}=== $1 ===${NC}" | tee -a "$MONITOR_LOG"
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Monitoring and health check script for Database Schema Audit Tool

OPTIONS:
    -c, --check TYPE         Run specific check (all|health|logs|metrics|backups)
    -a, --alert              Enable alerting (requires configuration)
    -v, --verbose            Verbose output
    -o, --output FILE        Output report to file
    -h, --help               Show this help message

EXAMPLES:
    # Run all checks
    $0 --check all

    # Run health check only
    $0 --check health

    # Run with alerting
    $0 --check all --alert

    # Generate report
    $0 --check all --output health_report.txt

EOF
}

check_python() {
    log_section "Python Environment"
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1)
        log_success "Python installed: $PYTHON_VERSION"
        
        # Check if version is sufficient
        PYTHON_VER=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        REQUIRED_VER="3.9"
        
        if [ "$(printf '%s\n' "$REQUIRED_VER" "$PYTHON_VER" | sort -V | head -n1)" = "$REQUIRED_VER" ]; then
            log_success "Python version is sufficient (>= 3.9)"
        else
            log_warning "Python version may be too old (< 3.9)"
        fi
    else
        log_error "Python 3 not found"
        return 1
    fi
    
    echo ""
    return 0
}

check_dependencies() {
    log_section "Dependencies"
    
    REQUIRED_PACKAGES=("sqlparse" "hypothesis" "pytest")
    MISSING_PACKAGES=()
    
    for package in "${REQUIRED_PACKAGES[@]}"; do
        if python3 -c "import $package" 2>/dev/null; then
            VERSION=$(python3 -c "import $package; print(getattr($package, '__version__', 'unknown'))" 2>/dev/null)
            log_success "$package installed (version: $VERSION)"
        else
            log_error "$package not installed"
            MISSING_PACKAGES+=("$package")
        fi
    done
    
    if [ ${#MISSING_PACKAGES[@]} -eq 0 ]; then
        log_success "All dependencies installed"
        echo ""
        return 0
    else
        log_warning "Missing packages: ${MISSING_PACKAGES[*]}"
        echo ""
        return 1
    fi
}

check_cli() {
    log_section "CLI Interface"
    
    if [ ! -f "cli.py" ]; then
        log_error "cli.py not found"
        echo ""
        return 1
    fi
    
    # Test CLI help
    if python3 cli.py --help > /dev/null 2>&1; then
        log_success "CLI interface working"
    else
        log_error "CLI interface not working"
        echo ""
        return 1
    fi
    
    # Check CLI commands
    COMMANDS=("audit" "fix" "validate" "report")
    for cmd in "${COMMANDS[@]}"; do
        if python3 cli.py "$cmd" --help > /dev/null 2>&1; then
            log_success "Command '$cmd' available"
        else
            log_warning "Command '$cmd' not available"
        fi
    done
    
    echo ""
    return 0
}

check_directories() {
    log_section "Directory Structure"
    
    REQUIRED_DIRS=("output" "backups" "logs" "reports")
    MISSING_DIRS=()
    
    for dir in "${REQUIRED_DIRS[@]}"; do
        if [ -d "$dir" ]; then
            SIZE=$(du -sh "$dir" 2>/dev/null | cut -f1)
            FILES=$(find "$dir" -type f 2>/dev/null | wc -l)
            log_success "$dir/ exists (size: $SIZE, files: $FILES)"
        else
            log_warning "$dir/ not found"
            MISSING_DIRS+=("$dir")
        fi
    done
    
    if [ ${#MISSING_DIRS[@]} -gt 0 ]; then
        log_info "Missing directories can be created with: mkdir -p ${MISSING_DIRS[*]}"
    fi
    
    echo ""
    return 0
}

check_disk_space() {
    log_section "Disk Space"
    
    DISK_USAGE=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//')
    DISK_AVAIL=$(df -h . | tail -1 | awk '{print $4}')
    
    if [ "$DISK_USAGE" -lt "$ALERT_THRESHOLD_DISK" ]; then
        log_success "Disk usage: ${DISK_USAGE}% (available: $DISK_AVAIL)"
    else
        log_warning "Disk usage: ${DISK_USAGE}% (available: $DISK_AVAIL) - HIGH!"
    fi
    
    echo ""
    return 0
}

check_memory() {
    log_section "Memory Usage"
    
    if command -v free &> /dev/null; then
        MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
        MEMORY_AVAIL=$(free -h | grep Mem | awk '{print $7}')
        
        if [ "$MEMORY_USAGE" -lt "$ALERT_THRESHOLD_MEMORY" ]; then
            log_success "Memory usage: ${MEMORY_USAGE}% (available: $MEMORY_AVAIL)"
        else
            log_warning "Memory usage: ${MEMORY_USAGE}% (available: $MEMORY_AVAIL) - HIGH!"
        fi
    else
        log_info "Memory check not available on this system"
    fi
    
    echo ""
    return 0
}

check_logs() {
    log_section "Log Analysis"
    
    if [ ! -d "logs" ]; then
        log_info "No logs directory found"
        echo ""
        return 0
    fi
    
    # Find recent log files
    RECENT_LOGS=$(find logs/ -name "*.log" -mtime -7 2>/dev/null)
    
    if [ -z "$RECENT_LOGS" ]; then
        log_info "No recent log files found (last 7 days)"
        echo ""
        return 0
    fi
    
    # Count errors and warnings
    ERROR_COUNT=0
    WARNING_COUNT=0
    
    while IFS= read -r logfile; do
        if [ -f "$logfile" ]; then
            ERRORS=$(grep -c "ERROR" "$logfile" 2>/dev/null || echo 0)
            WARNINGS=$(grep -c "WARNING" "$logfile" 2>/dev/null || echo 0)
            ERROR_COUNT=$((ERROR_COUNT + ERRORS))
            WARNING_COUNT=$((WARNING_COUNT + WARNINGS))
        fi
    done <<< "$RECENT_LOGS"
    
    log_info "Recent logs (last 7 days):"
    log_info "  Errors: $ERROR_COUNT"
    log_info "  Warnings: $WARNING_COUNT"
    
    if [ "$ERROR_COUNT" -gt "$ALERT_THRESHOLD_ERRORS" ]; then
        log_warning "High error count detected!"
    elif [ "$ERROR_COUNT" -eq 0 ]; then
        log_success "No errors in recent logs"
    fi
    
    # Show recent errors
    if [ "$ERROR_COUNT" -gt 0 ] && [ "$ERROR_COUNT" -le 10 ]; then
        log_info "Recent errors:"
        grep "ERROR" logs/*.log 2>/dev/null | tail -5 | while read -r line; do
            echo "    $line"
        done
    fi
    
    echo ""
    return 0
}

check_backups() {
    log_section "Backup Status"
    
    if [ ! -d "backups" ]; then
        log_warning "No backups directory found"
        echo ""
        return 1
    fi
    
    # Count backups
    BACKUP_COUNT=$(find backups/ -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
    
    if [ "$BACKUP_COUNT" -eq 0 ]; then
        log_info "No backups found"
        echo ""
        return 0
    fi
    
    log_info "Total backups: $BACKUP_COUNT"
    
    # Find most recent backup
    LATEST_BACKUP=$(find backups/ -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort -r | head -1)
    
    if [ -n "$LATEST_BACKUP" ]; then
        BACKUP_NAME=$(basename "$LATEST_BACKUP")
        BACKUP_SIZE=$(du -sh "$LATEST_BACKUP" 2>/dev/null | cut -f1)
        BACKUP_FILES=$(find "$LATEST_BACKUP" -type f 2>/dev/null | wc -l)
        BACKUP_AGE=$(find "$LATEST_BACKUP" -maxdepth 0 -mtime +7 2>/dev/null)
        
        log_info "Latest backup: $BACKUP_NAME"
        log_info "  Size: $BACKUP_SIZE"
        log_info "  Files: $BACKUP_FILES"
        
        if [ -z "$BACKUP_AGE" ]; then
            log_success "Latest backup is recent (< 7 days old)"
        else
            log_warning "Latest backup is old (> 7 days old)"
        fi
    fi
    
    # Check backup disk usage
    BACKUP_TOTAL_SIZE=$(du -sh backups/ 2>/dev/null | cut -f1)
    log_info "Total backup size: $BACKUP_TOTAL_SIZE"
    
    echo ""
    return 0
}

check_metrics() {
    log_section "Performance Metrics"
    
    # Check if there are any operation logs to analyze
    if [ ! -d "logs" ]; then
        log_info "No logs available for metrics"
        echo ""
        return 0
    fi
    
    # Try to extract execution times from logs
    RECENT_LOGS=$(find logs/ -name "*.log" -mtime -7 2>/dev/null)
    
    if [ -z "$RECENT_LOGS" ]; then
        log_info "No recent operations to analyze"
        echo ""
        return 0
    fi
    
    # Count operations
    AUDIT_COUNT=$(grep -h "audit" logs/*.log 2>/dev/null | wc -l)
    FIX_COUNT=$(grep -h "fix" logs/*.log 2>/dev/null | wc -l)
    
    log_info "Recent operations (last 7 days):"
    log_info "  Audits: $AUDIT_COUNT"
    log_info "  Fixes: $FIX_COUNT"
    
    echo ""
    return 0
}

generate_health_report() {
    REPORT_FILE="${1:-health_report_$(date +%Y%m%d_%H%M%S).txt}"
    
    log_section "Generating Health Report"
    
    {
        echo "=========================================="
        echo "  Database Schema Audit Tool"
        echo "  Health Report"
        echo "=========================================="
        echo ""
        echo "Generated: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Host: $(hostname)"
        echo "User: $(whoami)"
        echo ""
        
        # Run all checks and capture output
        check_python
        check_dependencies
        check_cli
        check_directories
        check_disk_space
        check_memory
        check_logs
        check_backups
        check_metrics
        
        echo "=========================================="
        echo "  Health Check Complete"
        echo "=========================================="
        
    } > "$REPORT_FILE"
    
    log_success "Health report saved to: $REPORT_FILE"
    echo ""
}

send_alert() {
    local message="$1"
    local severity="${2:-INFO}"
    
    # This is a placeholder for alerting integration
    # Implement based on your alerting system (email, Slack, PagerDuty, etc.)
    
    log_info "ALERT [$severity]: $message"
    
    # Example: Send email (requires mail command)
    # echo "$message" | mail -s "Schema Audit Alert: $severity" admin@example.com
    
    # Example: Send to Slack (requires curl and webhook URL)
    # curl -X POST -H 'Content-type: application/json' \
    #   --data "{\"text\":\"$message\"}" \
    #   https://hooks.slack.com/services/YOUR/WEBHOOK/URL
    
    # Example: Write to alert log
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$severity] $message" >> alerts.log
}

check_and_alert() {
    local check_type="$1"
    local enable_alert="${2:-false}"
    
    case $check_type in
        health)
            check_python
            check_dependencies
            check_cli
            ;;
        logs)
            check_logs
            ;;
        metrics)
            check_metrics
            ;;
        backups)
            check_backups
            ;;
        all)
            check_python
            check_dependencies
            check_cli
            check_directories
            check_disk_space
            check_memory
            check_logs
            check_backups
            check_metrics
            ;;
        *)
            log_error "Unknown check type: $check_type"
            return 1
            ;;
    esac
    
    # Check for alert conditions
    if [ "$enable_alert" = true ]; then
        # Check disk space
        DISK_USAGE=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//')
        if [ "$DISK_USAGE" -gt "$ALERT_THRESHOLD_DISK" ]; then
            send_alert "High disk usage: ${DISK_USAGE}%" "WARNING"
        fi
        
        # Check error count
        if [ -d "logs" ]; then
            ERROR_COUNT=$(grep -r "ERROR" logs/*.log 2>/dev/null | wc -l)
            if [ "$ERROR_COUNT" -gt "$ALERT_THRESHOLD_ERRORS" ]; then
                send_alert "High error count: $ERROR_COUNT errors" "WARNING"
            fi
        fi
    fi
}

# Main monitoring process
main() {
    CHECK_TYPE="all"
    ENABLE_ALERT=false
    VERBOSE=false
    OUTPUT_FILE=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--check)
                CHECK_TYPE="$2"
                shift 2
                ;;
            -a|--alert)
                ENABLE_ALERT=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -o|--output)
                OUTPUT_FILE="$2"
                shift 2
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
    
    log_info "Starting health check at $(date)"
    echo ""
    
    if [ -n "$OUTPUT_FILE" ]; then
        generate_health_report "$OUTPUT_FILE"
    else
        check_and_alert "$CHECK_TYPE" "$ENABLE_ALERT"
    fi
    
    echo ""
    echo "=========================================="
    log_success "Health check complete"
    echo "=========================================="
    echo ""
    
    return 0
}

# Run main function
main "$@"
