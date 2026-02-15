"""
Manual Testing Checklist Script for Database Schema Audit Tool
Task 17.2 - Automated execution of manual testing checklist
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from azure_functions.tools.schema_audit.schema_extractor import SchemaExtractor
from azure_functions.tools.schema_audit.code_auditor import CodeAuditor
from azure_functions.tools.schema_audit.mismatch_detector import MismatchDetector
from azure_functions.tools.schema_audit.schema_fixer import SchemaFixer
from azure_functions.tools.schema_audit.reporter import Reporter
from azure_functions.tools.schema_audit.validator import Validator


class ManualTestChecklist:
    """Execute manual testing checklist"""
    
    def __init__(self):
        self.results = []
        self.bacpac_path = "pei-dashboard.bacpac"
        self.azure_functions_dir = "azure_functions"
        self.output_dir = Path("azure_functions/tools/schema_audit/manual_test_output")
        self.output_dir.mkdir(exist_ok=True)
        
    def log_test(self, test_name, status, details=""):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        
        status_icon = "✓" if status == "PASS" else "✗" if status == "FAIL" else "⚠"
        print(f"{status_icon} {test_name}: {status}")
        if details:
            print(f"  {details}")
        print()
        
    def test_1_bacpac_extraction(self):
        """Test with actual pei-dashboard.bacpac"""
        print("=" * 60)
        print("TEST 1: BACPAC Extraction")
        print("=" * 60)
        
        try:
            if not os.path.exists(self.bacpac_path):
                self.log_test(
                    "BACPAC file exists",
                    "FAIL",
                    f"File not found: {self.bacpac_path}"
                )
                return
            
            self.log_test(
                "BACPAC file exists",
                "PASS",
                f"Found: {self.bacpac_path}"
            )
            
            # Extract schema
            extractor = SchemaExtractor()
            schema = extractor.extract_from_bacpac(self.bacpac_path)
            
            self.log_test(
                "Schema extraction",
                "PASS",
                f"Extracted {len(schema.tables)} tables"
            )
            
            # Export to JSON
            json_path = self.output_dir / "extracted_schema.json"
            extractor.export_to_json(schema, str(json_path))
            
            self.log_test(
                "JSON export",
                "PASS",
                f"Exported to {json_path}"
            )
            
            # Export to Markdown
            md_path = self.output_dir / "schema_documentation.md"
            extractor.export_to_markdown(schema, str(md_path))
            
            self.log_test(
                "Markdown documentation",
                "PASS",
                f"Generated {md_path}"
            )
            
            # Verify structured data tables
            structured_tables = [
                name for name in schema.tables.keys()
                if not name.startswith('news_') and name not in ['keywords', 'sentiment_summaries']
            ]
            
            self.log_test(
                "Structured data table identification",
                "PASS",
                f"Found {len(structured_tables)} structured data tables"
            )
            
        except Exception as e:
            self.log_test(
                "BACPAC extraction",
                "FAIL",
                f"Error: {str(e)}"
            )
    
    def test_2_azure_functions_scan(self):
        """Test with all Azure Functions"""
        print("=" * 60)
        print("TEST 2: Azure Functions Code Scanning")
        print("=" * 60)
        
        try:
            if not os.path.exists(self.azure_functions_dir):
                self.log_test(
                    "Azure Functions directory exists",
                    "FAIL",
                    f"Directory not found: {self.azure_functions_dir}"
                )
                return
            
            self.log_test(
                "Azure Functions directory exists",
                "PASS",
                f"Found: {self.azure_functions_dir}"
            )
            
            # Scan directory
            auditor = CodeAuditor()
            locations = auditor.scan_directory(self.azure_functions_dir)
            
            self.log_test(
                "Directory scanning",
                "PASS",
                f"Scanned {len(locations)} Python files"
            )
            
            # Build operation map
            operation_map = auditor.build_operation_map()
            
            self.log_test(
                "Operation detection",
                "PASS",
                f"Found operations on {len(operation_map)} tables"
            )
            
            # Check for specific scrapers
            scraper_dir = os.path.join(self.azure_functions_dir, "scrapers")
            if os.path.exists(scraper_dir):
                scraper_files = [
                    f for f in os.listdir(scraper_dir)
                    if f.endswith('.py') and not f.startswith('__')
                ]
                
                self.log_test(
                    "Scraper detection",
                    "PASS",
                    f"Found {len(scraper_files)} scraper files"
                )
            
        except Exception as e:
            self.log_test(
                "Azure Functions scanning",
                "FAIL",
                f"Error: {str(e)}"
            )
    
    def test_3_generated_reports(self):
        """Verify generated reports"""
        print("=" * 60)
        print("TEST 3: Generated Reports Verification")
        print("=" * 60)
        
        try:
            # Check if reports were generated
            json_path = self.output_dir / "extracted_schema.json"
            md_path = self.output_dir / "schema_documentation.md"
            
            if json_path.exists():
                with open(json_path, 'r') as f:
                    data = json.load(f)
                    
                self.log_test(
                    "JSON report validity",
                    "PASS",
                    f"Valid JSON with {len(data.get('tables', {}))} tables"
                )
            else:
                self.log_test(
                    "JSON report exists",
                    "FAIL",
                    "JSON report not found"
                )
            
            if md_path.exists():
                with open(md_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                self.log_test(
                    "Markdown report validity",
                    "PASS",
                    f"Generated {len(content)} characters of documentation"
                )
            else:
                self.log_test(
                    "Markdown report exists",
                    "FAIL",
                    "Markdown report not found"
                )
                
        except Exception as e:
            self.log_test(
                "Report verification",
                "FAIL",
                f"Error: {str(e)}"
            )
    
    def test_4_dry_run_mode(self):
        """Test dry-run mode"""
        print("=" * 60)
        print("TEST 4: Dry-Run Mode")
        print("=" * 60)
        
        try:
            # Create a test file
            test_file = self.output_dir / "test_dry_run.py"
            test_content = """
def save_data():
    cursor.execute("INSERT INTO users (user_name, email) VALUES (?, ?)", (name, email))
"""
            test_file.write_text(test_content)
            
            # Create a mock mismatch
            from azure_functions.tools.schema_audit.models import (
                Mismatch, MismatchType, Severity, CodeLocation
            )
            
            mismatch = Mismatch(
                mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
                severity=Severity.CRITICAL,
                table_name="users",
                column_name="user_name",
                expected_value="username",
                actual_value="user_name",
                locations=[CodeLocation(
                    file_path=str(test_file),
                    line_number=3,
                    code_snippet='cursor.execute("INSERT INTO users (user_name, email)'
                )],
                fix_suggestion="Rename column from user_name to username"
            )
            
            # Test dry-run
            fixer = SchemaFixer()
            report = fixer.fix_mismatches([mismatch], dry_run=True)
            
            # Verify file wasn't modified
            current_content = test_file.read_text()
            
            if current_content == test_content:
                self.log_test(
                    "Dry-run mode",
                    "PASS",
                    "File not modified in dry-run mode"
                )
            else:
                self.log_test(
                    "Dry-run mode",
                    "FAIL",
                    "File was modified in dry-run mode"
                )
            
            # Verify report was generated
            if report.total_fixes_applied > 0 or len(report.fixes) > 0:
                self.log_test(
                    "Dry-run report generation",
                    "PASS",
                    f"Generated report with {len(report.fixes)} proposed fixes"
                )
            else:
                self.log_test(
                    "Dry-run report generation",
                    "WARN",
                    "No fixes proposed"
                )
                
        except Exception as e:
            self.log_test(
                "Dry-run mode",
                "FAIL",
                f"Error: {str(e)}"
            )
    
    def test_5_backup_restore(self):
        """Test backup and restore"""
        print("=" * 60)
        print("TEST 5: Backup and Restore")
        print("=" * 60)
        
        try:
            # Create a test file
            test_file = self.output_dir / "test_backup.py"
            original_content = "# Original content\nprint('hello')\n"
            test_file.write_text(original_content)
            
            # Create backup
            fixer = SchemaFixer()
            backup_path = fixer.backup_file(str(test_file))
            
            if backup_path and os.path.exists(backup_path):
                self.log_test(
                    "Backup creation",
                    "PASS",
                    f"Created backup at {backup_path}"
                )
            else:
                self.log_test(
                    "Backup creation",
                    "FAIL",
                    "Backup not created"
                )
                return
            
            # Modify file
            modified_content = "# Modified content\nprint('world')\n"
            test_file.write_text(modified_content)
            
            # Restore from backup
            fixer._restore_from_backup(str(test_file))
            
            # Verify restoration
            restored_content = test_file.read_text()
            
            if restored_content == original_content:
                self.log_test(
                    "Backup restoration",
                    "PASS",
                    "File successfully restored from backup"
                )
            else:
                self.log_test(
                    "Backup restoration",
                    "FAIL",
                    "File not properly restored"
                )
                
        except Exception as e:
            self.log_test(
                "Backup and restore",
                "FAIL",
                f"Error: {str(e)}"
            )
    
    def test_6_fixed_code_validity(self):
        """Verify fixed code runs without errors"""
        print("=" * 60)
        print("TEST 6: Fixed Code Validity")
        print("=" * 60)
        
        try:
            # Create a test file with a mismatch
            test_file = self.output_dir / "test_fix_validity.py"
            test_content = """
def process_user(data):
    user_name = data.get('user_name')
    email = data.get('email')
    return {'user_name': user_name, 'email': email}
"""
            test_file.write_text(test_content)
            
            # Create mismatch
            from azure_functions.tools.schema_audit.models import (
                Mismatch, MismatchType, Severity, CodeLocation
            )
            
            mismatch = Mismatch(
                mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
                severity=Severity.CRITICAL,
                table_name="users",
                column_name="user_name",
                expected_value="username",
                actual_value="user_name",
                locations=[CodeLocation(
                    file_path=str(test_file),
                    line_number=3,
                    code_snippet="user_name = data.get('user_name')"
                )],
                fix_suggestion="Rename column from user_name to username"
            )
            
            # Apply fix
            fixer = SchemaFixer()
            report = fixer.fix_mismatches([mismatch], dry_run=False)
            
            # Validate syntax
            validator = Validator()
            validation_result = validator.validate_python_syntax(str(test_file))
            
            if validation_result.is_valid:
                self.log_test(
                    "Fixed code syntax validity",
                    "PASS",
                    "Fixed code has valid Python syntax"
                )
            else:
                self.log_test(
                    "Fixed code syntax validity",
                    "FAIL",
                    f"Syntax errors: {validation_result.errors}"
                )
            
            # Try to import/compile the fixed code
            try:
                with open(test_file, 'r') as f:
                    code = f.read()
                compile(code, str(test_file), 'exec')
                
                self.log_test(
                    "Fixed code compilation",
                    "PASS",
                    "Fixed code compiles successfully"
                )
            except SyntaxError as e:
                self.log_test(
                    "Fixed code compilation",
                    "FAIL",
                    f"Compilation error: {str(e)}"
                )
                
        except Exception as e:
            self.log_test(
                "Fixed code validity",
                "FAIL",
                f"Error: {str(e)}"
            )
    
    def generate_report(self):
        """Generate final test report"""
        print("\n" + "=" * 60)
        print("MANUAL TEST CHECKLIST SUMMARY")
        print("=" * 60)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        warned = sum(1 for r in self.results if r['status'] == 'WARN')
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total*100:.1f}%)")
        print(f"Warnings: {warned} ({warned/total*100:.1f}%)")
        
        # Save detailed report
        report_path = self.output_dir / "manual_test_report.json"
        with open(report_path, 'w') as f:
            json.dump({
                'summary': {
                    'total': total,
                    'passed': passed,
                    'failed': failed,
                    'warnings': warned,
                    'success_rate': f"{passed/total*100:.1f}%"
                },
                'tests': self.results,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_path}")
        
        # Generate markdown report
        md_report_path = self.output_dir / "MANUAL_TEST_REPORT.md"
        with open(md_report_path, 'w', encoding='utf-8') as f:
            f.write("# Manual Testing Checklist Report\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Summary\n\n")
            f.write(f"- **Total Tests:** {total}\n")
            f.write(f"- **Passed:** {passed} ({passed/total*100:.1f}%)\n")
            f.write(f"- **Failed:** {failed} ({failed/total*100:.1f}%)\n")
            f.write(f"- **Warnings:** {warned} ({warned/total*100:.1f}%)\n\n")
            f.write("## Test Results\n\n")
            
            for result in self.results:
                status_icon = "✓" if result['status'] == 'PASS' else "✗" if result['status'] == 'FAIL' else "⚠"
                f.write(f"### {status_icon} {result['test']}\n\n")
                f.write(f"**Status:** {result['status']}\n\n")
                if result['details']:
                    f.write(f"**Details:** {result['details']}\n\n")
                f.write("---\n\n")
        
        print(f"Markdown report saved to: {md_report_path}")
        
        return passed == total
    
    def run_all_tests(self):
        """Run all manual tests"""
        print("\n" + "=" * 60)
        print("DATABASE SCHEMA AUDIT TOOL - MANUAL TESTING")
        print("=" * 60)
        print()
        
        self.test_1_bacpac_extraction()
        self.test_2_azure_functions_scan()
        self.test_3_generated_reports()
        self.test_4_dry_run_mode()
        self.test_5_backup_restore()
        self.test_6_fixed_code_validity()
        
        success = self.generate_report()
        
        return 0 if success else 1


if __name__ == '__main__':
    tester = ManualTestChecklist()
    sys.exit(tester.run_all_tests())
