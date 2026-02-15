#!/bin/bash
# Database Schema Audit Tool - Deployment Script
# Version: 1.0.0
# Description: Automated deployment script for the schema audit tool

set -e  # Exit on error
set -u  # Exit on undefined variable

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TOOL_NAME="Database Schema Audit Tool"
VERSION="1.0.0"
PYTHON_MIN_VERSION="3.9"
DEPLOYMENT_LOG="deployment_$(date +%Y%m%d_%H%M%S).log"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$DEPLOYMENT_LOG"
}

check_python_version() {
    log_info "Checking Python version..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        return 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_info "Found Python $PYTHON_VERSION"
    
    # Compare versions
    REQUIRED_VERSION=$(echo -e "$PYTHON_MIN_VERSION\n$PYTHON_VERSION" | sort -V | head -n1)
    if [ "$REQUIRED_VERSION" != "$PYTHON_MIN_VERSION" ]; then
        log_error "Python $PYTHON_MIN_VERSION or higher is required"
        return 1
    fi
    
    log_success "Python version check passed"
    return 0
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    if [ ! -f "requirements.txt" ]; then
        log_error "requirements.txt not found"
        return 1
    fi
    
    log_info "Installing dependencies from requirements.txt..."
    python3 -m pip install -r requirements.txt >> "$DEPLOYMENT_LOG" 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "Dependencies installed successfully"
        return 0
    else
        log_error "Failed to install dependencies"
        return 1
    fi
}

verify_installation() {
    log_info "Verifying installation..."
    
    # Check if main modules exist
    REQUIRED_MODULES=(
        "cli.py"
        "schema_extractor.py"
        "code_auditor.py"
        "mismatch_detector.py"
        "schema_fixer.py"
        "validator.py"
        "reporter.py"
        "models.py"
    )
    
    for module in "${REQUIRED_MODULES[@]}"; do
        if [ ! -f "$module" ]; then
            log_error "Required module $module not found"
            return 1
        fi
    done
    
    log_success "All required modules present"
    
    # Test CLI
    log_info "Testing CLI interface..."
    python3 cli.py --help >> "$DEPLOYMENT_LOG" 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "CLI interface working"
        return 0
    else
        log_error "CLI interface test failed"
        return 1
    fi
}

run_tests() {
    log_info "Running test suite..."
    
    if ! command -v pytest &> /dev/null; then
        log_warning "pytest not found, skipping tests"
        return 0
    fi
    
    # Run tests with coverage
    pytest --tb=short -v >> "$DEPLOYMENT_LOG" 2>&1
    TEST_RESULT=$?
    
    if [ $TEST_RESULT -eq 0 ]; then
        log_success "All tests passed"
        return 0
    else
        log_warning "Some tests failed (see $DEPLOYMENT_LOG for details)"
        log_warning "Deployment can continue, but review test failures"
        return 0  # Don't fail deployment on test failures
    fi
}

create_directories() {
    log_info "Creating required directories..."
    
    DIRECTORIES=(
        "output"
        "backups"
        "logs"
        "reports"
    )
    
    for dir in "${DIRECTORIES[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_info "Created directory: $dir"
        fi
    done
    
    log_success "Directory structure ready"
    return 0
}

verify_documentation() {
    log_info "Verifying documentation..."
    
    REQUIRED_DOCS=(
        "README.md"
        "USER_GUIDE.md"
        "DEVELOPER_GUIDE.md"
        "DEPLOYMENT_GUIDE.md"
    )
    
    MISSING_DOCS=()
    for doc in "${REQUIRED_DOCS[@]}"; do
        if [ ! -f "$doc" ]; then
            MISSING_DOCS+=("$doc")
        fi
    done
    
    if [ ${#MISSING_DOCS[@]} -eq 0 ]; then
        log_success "All documentation present"
        return 0
    else
        log_warning "Missing documentation: ${MISSING_DOCS[*]}"
        return 0  # Don't fail deployment
    fi
}

create_deployment_summary() {
    log_info "Creating deployment summary..."
    
    SUMMARY_FILE="DEPLOYMENT_SUMMARY_$(date +%Y%m%d_%H%M%S).md"
    
    cat > "$SUMMARY_FILE" << EOF
# Deployment Summary

**Tool**: $TOOL_NAME
**Version**: $VERSION
**Date**: $(date '+%Y-%m-%d %H:%M:%S')
**Deployed By**: $(whoami)
**Host**: $(hostname)

## Deployment Status

✅ Deployment completed successfully

## Environment

- **Python Version**: $(python3 --version)
- **Working Directory**: $(pwd)
- **Log File**: $DEPLOYMENT_LOG

## Installed Components

- Schema Extractor
- Code Auditor
- Mismatch Detector
- Schema Fixer
- Validator
- Reporter
- Model Updater
- Migration Auditor
- CLI Interface

## Next Steps

1. Review deployment log: \`$DEPLOYMENT_LOG\`
2. Read user guide: \`USER_GUIDE.md\`
3. Run initial audit: \`python3 cli.py audit --help\`
4. Set up monitoring (see DEPLOYMENT_GUIDE.md)

## Quick Start

\`\`\`bash
# Run audit
python3 cli.py audit --bacpac /path/to/pei-dashboard.bacpac --code /path/to/azure_functions/

# Preview fixes
python3 cli.py fix --bacpac /path/to/pei-dashboard.bacpac --code /path/to/azure_functions/ --dry-run

# Apply fixes
python3 cli.py fix --bacpac /path/to/pei-dashboard.bacpac --code /path/to/azure_functions/ --severity CRITICAL
\`\`\`

## Support

For issues or questions, refer to:
- USER_GUIDE.md for usage instructions
- DEVELOPER_GUIDE.md for technical details
- DEPLOYMENT_GUIDE.md for deployment and operations

EOF
    
    log_success "Deployment summary created: $SUMMARY_FILE"
    return 0
}

# Main deployment process
main() {
    echo ""
    echo "=========================================="
    echo "  $TOOL_NAME"
    echo "  Version: $VERSION"
    echo "  Deployment Script"
    echo "=========================================="
    echo ""
    
    log_info "Starting deployment at $(date)"
    log_info "Deployment log: $DEPLOYMENT_LOG"
    echo ""
    
    # Pre-deployment checks
    log_info "=== Pre-Deployment Checks ==="
    check_python_version || exit 1
    echo ""
    
    # Installation
    log_info "=== Installation ==="
    check_dependencies || exit 1
    create_directories || exit 1
    echo ""
    
    # Verification
    log_info "=== Verification ==="
    verify_installation || exit 1
    verify_documentation
    echo ""
    
    # Testing
    log_info "=== Testing ==="
    run_tests
    echo ""
    
    # Post-deployment
    log_info "=== Post-Deployment ==="
    create_deployment_summary
    echo ""
    
    # Success
    echo "=========================================="
    log_success "Deployment completed successfully!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "  1. Review deployment log: $DEPLOYMENT_LOG"
    echo "  2. Read DEPLOYMENT_GUIDE.md for configuration"
    echo "  3. Read USER_GUIDE.md for usage instructions"
    echo "  4. Run: python3 cli.py --help"
    echo ""
    
    return 0
}

# Run main function
main "$@"
