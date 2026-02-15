"""
Unit tests for the Validator class.

Tests cover:
- Python syntax validation
- Import validation
- Schema consistency checking
- Dry-run mode
"""

import pytest
import tempfile
import os
from pathlib import Path

from .validator import Validator
from .models import ValidationResult


class TestValidator:
    """Test suite for Validator class"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.validator = Validator()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        # Clean up temp directory
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_temp_file(self, filename: str, content: str) -> str:
        """Helper to create a temporary Python file"""
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path
    
    # ===== Syntax Validation Tests =====
    
    def test_validate_python_syntax_valid_file(self):
        """Test syntax validation with valid Python code"""
        content = """
def hello():
    print("Hello, World!")
    return True
"""
        file_path = self.create_temp_file("valid.py", content)
        
        result = self.validator.validate_python_syntax(file_path)
        
        assert result.is_valid
        assert len(result.errors) == 0
        assert file_path in self.validator.validated_files
    
    def test_validate_python_syntax_invalid_file(self):
        """Test syntax validation with invalid Python code"""
        content = """
def hello()
    print("Missing colon")
    return True
"""
        file_path = self.create_temp_file("invalid.py", content)
        
        result = self.validator.validate_python_syntax(file_path)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert "Syntax error" in result.errors[0]
    
    def test_validate_python_syntax_nonexistent_file(self):
        """Test syntax validation with non-existent file"""
        result = self.validator.validate_python_syntax("nonexistent.py")
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()
    
    def test_validate_python_syntax_non_python_file(self):
        """Test syntax validation with non-Python file"""
        file_path = self.create_temp_file("test.txt", "Not Python code")
        
        result = self.validator.validate_python_syntax(file_path)
        
        assert result.is_valid  # Should pass but with warning
        assert len(result.warnings) > 0
        assert "Not a Python file" in result.warnings[0]
    
    # ===== Import Validation Tests =====
    
    def test_validate_imports_valid_imports(self):
        """Test import validation with valid imports"""
        content = """
import os
import sys
from pathlib import Path
"""
        file_path = self.create_temp_file("valid_imports.py", content)
        
        result = self.validator.validate_imports(file_path)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_imports_invalid_import(self):
        """Test import validation with invalid import"""
        content = """
import os
import nonexistent_module_xyz
from pathlib import Path
"""
        file_path = self.create_temp_file("invalid_imports.py", content)
        
        result = self.validator.validate_imports(file_path)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert "nonexistent_module_xyz" in result.errors[0]
    
    def test_validate_imports_no_imports(self):
        """Test import validation with no imports"""
        content = """
def hello():
    return "No imports here"
"""
        file_path = self.create_temp_file("no_imports.py", content)
        
        result = self.validator.validate_imports(file_path)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_imports_relative_imports(self):
        """Test import validation with relative imports (should skip)"""
        content = """
from . import models
from ..utils import helper
"""
        file_path = self.create_temp_file("relative_imports.py", content)
        
        result = self.validator.validate_imports(file_path)
        
        # Relative imports should be skipped, so validation should pass
        assert result.is_valid
    
    # ===== Schema Consistency Tests =====
    
    def test_validate_schema_consistency_single_file(self):
        """Test schema consistency with single file"""
        content = """
query = '''
CREATE TABLE users (
    id INT PRIMARY KEY,
    name VARCHAR(100)
)
'''
"""
        file_path = self.create_temp_file("schema1.py", content)
        
        result = self.validator.validate_schema_consistency([file_path])
        
        assert result.is_valid
    
    def test_validate_schema_consistency_multiple_files(self):
        """Test schema consistency across multiple files"""
        content1 = """
query1 = 'CREATE TABLE users (id INT, name VARCHAR(100))'
"""
        content2 = """
query2 = "INSERT INTO users (id, name) VALUES (1, 'John')"
"""
        file1 = self.create_temp_file("schema1.py", content1)
        file2 = self.create_temp_file("schema2.py", content2)
        
        result = self.validator.validate_schema_consistency([file1, file2])
        
        assert result.is_valid
    
    def test_validate_schema_consistency_empty_list(self):
        """Test schema consistency with empty file list"""
        result = self.validator.validate_schema_consistency([])
        
        assert result.is_valid
        assert len(result.warnings) > 0
    
    # ===== Dry-Run Mode Tests =====
    
    def test_dry_run_mode_enabled(self):
        """Test that dry-run mode is properly set"""
        validator = Validator(dry_run=True)
        
        assert validator._check_dry_run_mode()
        assert validator.dry_run
    
    def test_dry_run_mode_disabled(self):
        """Test that dry-run mode can be disabled"""
        validator = Validator(dry_run=False)
        
        assert not validator._check_dry_run_mode()
        assert not validator.dry_run
    
    # ===== Batch Validation Tests =====
    
    def test_validate_files_multiple(self):
        """Test validating multiple files at once"""
        content1 = "def func1(): pass"
        content2 = "def func2(): pass"
        content3 = "def func3( pass"  # Invalid syntax
        
        file1 = self.create_temp_file("file1.py", content1)
        file2 = self.create_temp_file("file2.py", content2)
        file3 = self.create_temp_file("file3.py", content3)
        
        results = self.validator.validate_files([file1, file2, file3])
        
        assert len(results) == 3
        assert results[file1].is_valid
        assert results[file2].is_valid
        assert not results[file3].is_valid
    
    def test_validate_files_with_imports(self):
        """Test validating files with imports"""
        content = """
import os
import sys

def get_path():
    return os.path.join('a', 'b')
"""
        file_path = self.create_temp_file("with_imports.py", content)
        
        results = self.validator.validate_files([file_path])
        
        assert len(results) == 1
        assert results[file_path].is_valid
    
    # ===== Summary Tests =====
    
    def test_get_validation_summary(self):
        """Test getting validation summary"""
        content1 = "def func1(): pass"
        content2 = "def func2( pass"  # Invalid
        
        file1 = self.create_temp_file("file1.py", content1)
        file2 = self.create_temp_file("file2.py", content2)
        
        self.validator.validate_python_syntax(file1)
        self.validator.validate_python_syntax(file2)
        
        summary = self.validator.get_validation_summary()
        
        assert summary['total_files_validated'] == 1  # Only valid file
        assert summary['total_cached_results'] == 2
        assert summary['valid_files'] == 1
        assert summary['invalid_files'] == 1
        assert summary['dry_run_mode'] == False
    
    def test_validation_caching(self):
        """Test that validation results are cached"""
        content = "def func(): pass"
        file_path = self.create_temp_file("cached.py", content)
        
        # First validation
        result1 = self.validator.validate_python_syntax(file_path)
        
        # Check cache
        assert file_path in self.validator.validation_cache
        assert self.validator.validation_cache[file_path].is_valid
        
        # Second validation should use cache
        result2 = self.validator.validate_python_syntax(file_path)
        
        assert result1.is_valid == result2.is_valid


    # ===== Test Case Generation Tests =====
    
    def test_generate_test_cases_single_table(self):
        """Test generating test cases for a single table"""
        tables = ['users']
        
        test_cases = self.validator.generate_test_cases(tables)
        
        # Should generate 3 test cases per table (INSERT, SELECT, UPDATE)
        assert len(test_cases) == 3
        
        # Check INSERT test
        insert_test = next(tc for tc in test_cases if tc['operation'] == 'INSERT')
        assert insert_test['table'] == 'users'
        assert insert_test['test_name'] == 'test_users_insert'
        assert 'def test_users_insert' in insert_test['test_code']
        
        # Check SELECT test
        select_test = next(tc for tc in test_cases if tc['operation'] == 'SELECT')
        assert select_test['table'] == 'users'
        assert select_test['test_name'] == 'test_users_select'
        
        # Check UPDATE test
        update_test = next(tc for tc in test_cases if tc['operation'] == 'UPDATE')
        assert update_test['table'] == 'users'
        assert update_test['test_name'] == 'test_users_update'
    
    def test_generate_test_cases_multiple_tables(self):
        """Test generating test cases for multiple tables"""
        tables = ['users', 'products', 'orders']
        
        test_cases = self.validator.generate_test_cases(tables)
        
        # Should generate 3 test cases per table
        assert len(test_cases) == 9
        
        # Check that all tables are covered
        tables_in_tests = set(tc['table'] for tc in test_cases)
        assert tables_in_tests == {'users', 'products', 'orders'}
        
        # Check that all operations are covered for each table
        for table in tables:
            table_tests = [tc for tc in test_cases if tc['table'] == table]
            operations = set(tc['operation'] for tc in table_tests)
            assert operations == {'INSERT', 'SELECT', 'UPDATE'}
    
    def test_generate_test_cases_empty_list(self):
        """Test generating test cases with empty table list"""
        test_cases = self.validator.generate_test_cases([])
        
        assert len(test_cases) == 0
    
    def test_generate_test_cases_code_validity(self):
        """Test that generated test code is valid Python"""
        tables = ['test_table']
        
        test_cases = self.validator.generate_test_cases(tables)
        
        # Each test case should have valid Python code
        for test_case in test_cases:
            code = test_case['test_code']
            # Should be parseable as Python
            import ast
            try:
                ast.parse(code)
            except SyntaxError:
                pytest.fail(f"Generated test code has syntax error: {code}")
    
    # ===== Comparison Script Generation Tests =====
    
    def test_generate_comparison_script_creates_file(self):
        """Test that comparison script is created"""
        reference_path = "schema.json"
        output_path = os.path.join(self.temp_dir, "compare.py")
        
        result_path = self.validator.generate_comparison_script(
            reference_path,
            output_path
        )
        
        assert result_path == output_path
        assert os.path.exists(output_path)
    
    def test_generate_comparison_script_content(self):
        """Test that comparison script has correct content"""
        reference_path = "reference_schema.json"
        output_path = os.path.join(self.temp_dir, "compare.py")
        
        self.validator.generate_comparison_script(reference_path, output_path)
        
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for key components
        assert '#!/usr/bin/env python3' in content
        assert 'def load_reference_schema' in content
        assert 'def get_database_schema' in content
        assert 'def compare_schemas' in content
        assert 'def main' in content
        assert reference_path in content
    
    def test_generate_comparison_script_is_valid_python(self):
        """Test that generated comparison script is valid Python"""
        reference_path = "schema.json"
        output_path = os.path.join(self.temp_dir, "compare.py")
        
        self.validator.generate_comparison_script(reference_path, output_path)
        
        # Validate syntax
        result = self.validator.validate_python_syntax(output_path)
        assert result.is_valid
    
    def test_generate_comparison_script_invalid_path(self):
        """Test comparison script generation with invalid output path"""
        reference_path = "schema.json"
        output_path = "/invalid/path/that/does/not/exist/compare.py"
        
        with pytest.raises(RuntimeError):
            self.validator.generate_comparison_script(reference_path, output_path)
    
    # ===== Deployment Report Generation Tests =====
    
    def test_generate_deployment_report_ready(self):
        """Test deployment report when system is ready"""
        # Create validation results with all valid files
        validation_results = {
            'file1.py': ValidationResult(is_valid=True),
            'file2.py': ValidationResult(is_valid=True)
        }
        
        report = self.validator.generate_deployment_report(
            validation_results,
            mismatches=[],
            fixes_applied=[]
        )
        
        assert report['status'] == 'READY'
        assert report['ready_for_deployment'] == True
        assert report['validation']['total_files'] == 2
        assert report['validation']['valid_files'] == 2
        assert report['validation']['invalid_files'] == 0
        assert report['mismatches']['critical'] == 0
    
    def test_generate_deployment_report_not_ready_critical_mismatches(self):
        """Test deployment report with critical mismatches"""
        from .models import Mismatch, MismatchType, Severity
        
        validation_results = {
            'file1.py': ValidationResult(is_valid=True)
        }
        
        mismatches = [
            Mismatch(
                mismatch_type=MismatchType.MISSING_COLUMN,
                severity=Severity.CRITICAL,
                table_name='users'
            )
        ]
        
        report = self.validator.generate_deployment_report(
            validation_results,
            mismatches=mismatches
        )
        
        assert report['status'] == 'NOT READY'
        assert report['ready_for_deployment'] == False
        assert report['mismatches']['critical'] == 1
        assert 'critical mismatches' in report['status_message'].lower()
    
    def test_generate_deployment_report_not_ready_invalid_files(self):
        """Test deployment report with invalid files"""
        validation_results = {
            'file1.py': ValidationResult(is_valid=True),
            'file2.py': ValidationResult(is_valid=False)
        }
        validation_results['file2.py'].add_error("Syntax error")
        
        report = self.validator.generate_deployment_report(
            validation_results,
            mismatches=[]
        )
        
        assert report['status'] == 'NOT READY'
        assert report['ready_for_deployment'] == False
        assert report['validation']['invalid_files'] == 1
        assert report['validation']['total_errors'] == 1
    
    def test_generate_deployment_report_with_warnings(self):
        """Test deployment report with warnings only"""
        from .models import Mismatch, MismatchType, Severity
        
        validation_results = {
            'file1.py': ValidationResult(is_valid=True)
        }
        
        mismatches = [
            Mismatch(
                mismatch_type=MismatchType.EXTRA_COLUMN,
                severity=Severity.WARNING,
                table_name='users'
            )
        ]
        
        report = self.validator.generate_deployment_report(
            validation_results,
            mismatches=mismatches
        )
        
        assert report['status'] == 'READY WITH WARNINGS'
        assert report['ready_for_deployment'] == True
        assert report['mismatches']['warning'] == 1
    
    def test_generate_deployment_report_with_fixes(self):
        """Test deployment report with applied fixes"""
        from .models import Fix, Mismatch, MismatchType, Severity
        
        validation_results = {
            'file1.py': ValidationResult(is_valid=True)
        }
        
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name='users'
        )
        
        fixes = [
            Fix(
                mismatch=mismatch,
                file_path='file1.py',
                line_number=10,
                old_code='old',
                new_code='new',
                applied=True
            ),
            Fix(
                mismatch=mismatch,
                file_path='file2.py',
                line_number=20,
                old_code='old',
                new_code='new',
                applied=False,
                error='Failed to apply'
            )
        ]
        
        report = self.validator.generate_deployment_report(
            validation_results,
            mismatches=[],
            fixes_applied=fixes
        )
        
        assert report['fixes']['successful'] == 1
        assert report['fixes']['failed'] == 1
        assert report['fixes']['total'] == 2
    
    def test_generate_deployment_report_recommendations(self):
        """Test that deployment report includes recommendations"""
        validation_results = {
            'file1.py': ValidationResult(is_valid=True)
        }
        
        report = self.validator.generate_deployment_report(
            validation_results,
            mismatches=[]
        )
        
        assert 'recommendations' in report
        assert len(report['recommendations']) > 0
        assert isinstance(report['recommendations'], list)
    
    def test_generate_deployment_report_timestamp(self):
        """Test that deployment report includes timestamp"""
        validation_results = {
            'file1.py': ValidationResult(is_valid=True)
        }
        
        report = self.validator.generate_deployment_report(
            validation_results,
            mismatches=[]
        )
        
        assert 'timestamp' in report
        assert report['timestamp'] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
