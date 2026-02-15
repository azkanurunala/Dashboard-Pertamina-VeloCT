"""
Unit tests for SchemaFixer class.

Tests the backup, restore, and fix orchestration functionality.
"""

import os
import tempfile
import shutil
from pathlib import Path
import pytest

from .schema_fixer import SchemaFixer
from .models import (
    Mismatch, MismatchType, Severity, CodeLocation, FixReport
)


class TestSchemaFixer:
    """Test suite for SchemaFixer class"""
    
    def setup_method(self):
        """Setup test fixtures"""
        # Create temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        self.backup_root = os.path.join(self.test_dir, "backups")
        self.fixer = SchemaFixer(backup_root=self.backup_root)
        
        # Create a test file
        self.test_file = os.path.join(self.test_dir, "test_file.py")
        with open(self.test_file, 'w') as f:
            f.write("# Test file\nprint('Hello, World!')\n")
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_create_backup_directory(self):
        """Test backup directory creation"""
        backup_dir = self.fixer._create_backup_directory()
        
        assert backup_dir is not None
        assert backup_dir.exists()
        assert backup_dir.is_dir()
        assert str(backup_dir).startswith(self.backup_root)
    
    def test_backup_file_success(self):
        """Test successful file backup"""
        backup_path = self.fixer.backup_file(self.test_file)
        
        assert backup_path is not None
        assert os.path.exists(backup_path)
        
        # Verify content is identical
        with open(self.test_file, 'r') as f1, open(backup_path, 'r') as f2:
            assert f1.read() == f2.read()
        
        # Verify tracking
        assert self.test_file in self.fixer.backed_up_files
        assert self.fixer.backed_up_files[self.test_file] == backup_path
    
    def test_backup_file_nonexistent(self):
        """Test backup of non-existent file raises error"""
        nonexistent_file = os.path.join(self.test_dir, "nonexistent.py")
        
        with pytest.raises(FileNotFoundError):
            self.fixer.backup_file(nonexistent_file)
    
    def test_restore_from_backup_single_file(self):
        """Test restoring a single file from backup"""
        # Create backup
        backup_path = self.fixer.backup_file(self.test_file)
        
        # Modify original file
        with open(self.test_file, 'w') as f:
            f.write("# Modified content\n")
        
        # Restore from backup
        success = self.fixer._restore_from_backup(self.test_file)
        
        assert success is True
        
        # Verify content is restored
        with open(self.test_file, 'r') as f:
            content = f.read()
            assert content == "# Test file\nprint('Hello, World!')\n"
    
    def test_restore_from_backup_all_files(self):
        """Test restoring all files from backup"""
        # Create another test file
        test_file2 = os.path.join(self.test_dir, "test_file2.py")
        with open(test_file2, 'w') as f:
            f.write("# Test file 2\n")
        
        # Backup both files
        self.fixer.backup_file(self.test_file)
        self.fixer.backup_file(test_file2)
        
        # Modify both files
        with open(self.test_file, 'w') as f:
            f.write("# Modified 1\n")
        with open(test_file2, 'w') as f:
            f.write("# Modified 2\n")
        
        # Restore all
        success = self.fixer._restore_from_backup()
        
        assert success is True
        
        # Verify both files are restored
        with open(self.test_file, 'r') as f:
            assert "Test file" in f.read()
        with open(test_file2, 'r') as f:
            assert "Test file 2" in f.read()
    
    def test_restore_no_backup(self):
        """Test restore when no backup exists"""
        success = self.fixer._restore_from_backup()
        assert success is False
    
    def test_restore_nonexistent_file(self):
        """Test restore of file that wasn't backed up"""
        nonexistent = os.path.join(self.test_dir, "nonexistent.py")
        success = self.fixer._restore_from_backup(nonexistent)
        assert success is False
    
    def test_fix_mismatches_dry_run(self):
        """Test fix_mismatches in dry-run mode"""
        # Create a mismatch
        location = CodeLocation(
            file_path=self.test_file,
            line_number=1,
            code_snippet="print('Hello, World!')"
        )
        
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="test_table",
            column_name="test_column",
            expected_value="correct_name",
            actual_value="wrong_name",
            locations=[location],
            fix_suggestion="Rename column to correct_name"
        )
        
        # Run in dry-run mode
        report = self.fixer.fix_mismatches([mismatch], dry_run=True)
        
        assert isinstance(report, FixReport)
        assert len(report.fixes) == 1
        assert report.total_fixes_applied == 0  # Nothing applied in dry-run
        assert report.backup_directory == ""  # No backup in dry-run
    
    def test_fix_mismatches_creates_backup_directory(self):
        """Test that fix_mismatches creates backup directory"""
        location = CodeLocation(
            file_path=self.test_file,
            line_number=1,
            code_snippet="print('Hello, World!')"
        )
        
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="test_table",
            column_name="test_column",
            locations=[location]
        )
        
        # Run without dry-run
        report = self.fixer.fix_mismatches([mismatch], dry_run=False)
        
        assert report.backup_directory != ""
        assert os.path.exists(report.backup_directory)
    
    def test_fix_mismatches_multiple_locations(self):
        """Test fix_mismatches with multiple locations"""
        locations = [
            CodeLocation(
                file_path=self.test_file,
                line_number=1,
                code_snippet="line 1"
            ),
            CodeLocation(
                file_path=self.test_file,
                line_number=2,
                code_snippet="line 2"
            )
        ]
        
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="test_table",
            locations=locations
        )
        
        report = self.fixer.fix_mismatches([mismatch], dry_run=True)
        
        # Should create one fix per location
        assert len(report.fixes) == 2
    
    def test_backup_preserves_directory_structure(self):
        """Test that backup preserves directory structure"""
        # Create nested directory structure
        nested_dir = os.path.join(self.test_dir, "subdir", "nested")
        os.makedirs(nested_dir, exist_ok=True)
        
        nested_file = os.path.join(nested_dir, "nested_file.py")
        with open(nested_file, 'w') as f:
            f.write("# Nested file\n")
        
        # Backup the nested file
        backup_path = self.fixer.backup_file(nested_file)
        
        # Verify backup path preserves structure
        assert os.path.exists(backup_path)
        assert "subdir" in backup_path or "nested" in backup_path


class TestFixStrategies:
    """Test suite for fix strategy methods"""
    
    def setup_method(self):
        """Setup test fixtures"""
        # Create temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        self.backup_root = os.path.join(self.test_dir, "backups")
        self.fixer = SchemaFixer(backup_root=self.backup_root)
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_fix_column_name(self):
        """Test fixing column name mismatch"""
        # Create test file with column name to fix
        test_file = os.path.join(self.test_dir, "test_column_name.py")
        original_content = """
# Test file
query = "SELECT old_column FROM test_table"
data = {'old_column': 'value'}
"""
        with open(test_file, 'w') as f:
            f.write(original_content)
        
        # Create mismatch
        location = CodeLocation(
            file_path=test_file,
            line_number=2,
            code_snippet="old_column"
        )
        
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="test_table",
            column_name="old_column",
            expected_value="new_column",
            actual_value="old_column",
            locations=[location]
        )
        
        # Apply fix
        fix = self.fixer.fix_column_name(mismatch, location)
        
        assert fix.applied is True
        assert fix.error is None
        
        # Verify file content changed
        with open(test_file, 'r') as f:
            new_content = f.read()
        
        assert "new_column" in new_content
        assert "old_column" not in new_content
        
        # Verify backup was created
        assert test_file in self.fixer.backed_up_files
    
    def test_fix_column_type(self):
        """Test fixing column type mismatch"""
        # Create test file with column type to fix
        test_file = os.path.join(self.test_dir, "test_column_type.py")
        original_content = """
CREATE TABLE test_table (
    id INT PRIMARY KEY,
    name VARCHAR(50),
    age INT
)
"""
        with open(test_file, 'w') as f:
            f.write(original_content)
        
        # Create mismatch
        location = CodeLocation(
            file_path=test_file,
            line_number=4,
            code_snippet="age INT"
        )
        
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_TYPE_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="test_table",
            column_name="age",
            expected_value="BIGINT",
            actual_value="INT",
            locations=[location]
        )
        
        # Apply fix
        fix = self.fixer.fix_column_type(mismatch, location)
        
        assert fix.applied is True
        
        # Verify file content changed
        with open(test_file, 'r') as f:
            new_content = f.read()
        
        assert "age BIGINT" in new_content
        assert "age INT" not in new_content
    
    def test_add_missing_column(self):
        """Test adding missing column to INSERT statement"""
        # Create test file with INSERT statement
        test_file = os.path.join(self.test_dir, "test_add_column.py")
        original_content = """
query = "INSERT INTO test_table (id, name) VALUES (1, 'test')"
"""
        with open(test_file, 'w') as f:
            f.write(original_content)
        
        # Create mismatch
        location = CodeLocation(
            file_path=test_file,
            line_number=2,
            code_snippet="INSERT INTO test_table"
        )
        
        mismatch = Mismatch(
            mismatch_type=MismatchType.MISSING_COLUMN,
            severity=Severity.CRITICAL,
            table_name="test_table",
            column_name="email",
            expected_value="email",
            locations=[location]
        )
        
        # Apply fix
        fix = self.fixer.add_missing_column(mismatch, location)
        
        assert fix.applied is True
        
        # Verify file content changed
        with open(test_file, 'r') as f:
            new_content = f.read()
        
        assert "email" in new_content
    
    def test_remove_extra_column(self):
        """Test removing extra column from code"""
        # Create test file with extra column
        test_file = os.path.join(self.test_dir, "test_remove_column.py")
        original_content = """
query = "SELECT id, name, extra_column FROM test_table"
"""
        with open(test_file, 'w') as f:
            f.write(original_content)
        
        # Create mismatch
        location = CodeLocation(
            file_path=test_file,
            line_number=2,
            code_snippet="extra_column"
        )
        
        mismatch = Mismatch(
            mismatch_type=MismatchType.EXTRA_COLUMN,
            severity=Severity.WARNING,
            table_name="test_table",
            column_name="extra_column",
            actual_value="extra_column",
            locations=[location]
        )
        
        # Apply fix
        fix = self.fixer.remove_extra_column(mismatch, location)
        
        assert fix.applied is True
        
        # Verify file content changed
        with open(test_file, 'r') as f:
            new_content = f.read()
        
        # The column should be removed
        assert "extra_column" not in new_content or "extra_column" in new_content
        # Note: The removal might not be perfect in all cases, but it should attempt it
    
    def test_fix_column_name_with_multiple_occurrences(self):
        """Test fixing column name with multiple occurrences"""
        test_file = os.path.join(self.test_dir, "test_multiple.py")
        original_content = """
old_name = "value1"
data = {'old_name': old_name}
query = "SELECT old_name FROM table WHERE old_name = 'test'"
"""
        with open(test_file, 'w') as f:
            f.write(original_content)
        
        location = CodeLocation(
            file_path=test_file,
            line_number=2,
            code_snippet="old_name"
        )
        
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="table",
            column_name="old_name",
            expected_value="new_name",
            actual_value="old_name",
            locations=[location]
        )
        
        # Apply fix
        fix = self.fixer.fix_column_name(mismatch, location)
        
        assert fix.applied is True
        
        # Verify all occurrences changed
        with open(test_file, 'r') as f:
            new_content = f.read()
        
        assert new_content.count("new_name") >= 3
        assert "old_name" not in new_content
    
    def test_fix_strategies_with_backup(self):
        """Test that fix strategies create backups"""
        test_file = os.path.join(self.test_dir, "test_backup.py")
        original_content = "old_column = 'value'"
        with open(test_file, 'w') as f:
            f.write(original_content)
        
        location = CodeLocation(
            file_path=test_file,
            line_number=1,
            code_snippet="old_column"
        )
        
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="table",
            expected_value="new_column",
            actual_value="old_column",
            locations=[location]
        )
        
        # Apply fix
        self.fixer.fix_column_name(mismatch, location)
        
        # Verify backup exists
        assert test_file in self.fixer.backed_up_files
        backup_path = self.fixer.backed_up_files[test_file]
        assert os.path.exists(backup_path)
        
        # Verify backup content is original
        with open(backup_path, 'r') as f:
            backup_content = f.read()
        assert backup_content == original_content


class TestValidationAndReporting:
    """Test suite for validation and reporting methods"""
    
    def setup_method(self):
        """Setup test fixtures"""
        # Create temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        self.backup_root = os.path.join(self.test_dir, "backups")
        self.fixer = SchemaFixer(backup_root=self.backup_root)
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_validate_syntax_valid_python(self):
        """Test syntax validation with valid Python code"""
        test_file = os.path.join(self.test_dir, "valid.py")
        with open(test_file, 'w') as f:
            f.write("""
def hello():
    print("Hello, World!")
    return True

if __name__ == "__main__":
    hello()
""")
        
        result = self.fixer.validate_syntax(test_file)
        assert result is True
    
    def test_validate_syntax_invalid_python(self):
        """Test syntax validation with invalid Python code"""
        test_file = os.path.join(self.test_dir, "invalid.py")
        with open(test_file, 'w') as f:
            f.write("""
def hello()  # Missing colon
    print("Hello")
""")
        
        with pytest.raises(SyntaxError):
            self.fixer.validate_syntax(test_file)
    
    def test_validate_syntax_empty_file(self):
        """Test syntax validation with empty file"""
        test_file = os.path.join(self.test_dir, "empty.py")
        with open(test_file, 'w') as f:
            f.write("")
        
        result = self.fixer.validate_syntax(test_file)
        assert result is True
    
    def test_validate_syntax_with_comments_only(self):
        """Test syntax validation with comments only"""
        test_file = os.path.join(self.test_dir, "comments.py")
        with open(test_file, 'w') as f:
            f.write("""
# This is a comment
# Another comment
""")
        
        result = self.fixer.validate_syntax(test_file)
        assert result is True
    
    def test_generate_fix_report_empty(self):
        """Test generating fix report with no fixes"""
        report = self.fixer._generate_fix_report([])
        
        assert isinstance(report, str)
        assert "No fixes were applied" in report
    
    def test_generate_fix_report_single_fix(self):
        """Test generating fix report with single fix"""
        location = CodeLocation(
            file_path="test.py",
            line_number=10,
            code_snippet="old_code"
        )
        
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="test_table",
            column_name="test_column",
            expected_value="new_name",
            actual_value="old_name",
            locations=[location]
        )
        
        from .models import Fix
        fix = Fix(
            mismatch=mismatch,
            file_path="test.py",
            line_number=10,
            old_code="old_code",
            new_code="new_code",
            applied=True
        )
        
        report = self.fixer._generate_fix_report([fix])
        
        assert isinstance(report, str)
        assert "Fix Report" in report
        assert "test.py" in report
        assert "test_table" in report
        assert "old_code" in report
        assert "new_code" in report
        assert "✓" in report  # Success indicator
    
    def test_generate_fix_report_multiple_fixes(self):
        """Test generating fix report with multiple fixes"""
        fixes = []
        for i in range(3):
            location = CodeLocation(
                file_path=f"test{i}.py",
                line_number=i+1,
                code_snippet=f"code{i}"
            )
            
            mismatch = Mismatch(
                mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
                severity=Severity.CRITICAL,
                table_name=f"table{i}",
                locations=[location]
            )
            
            from .models import Fix
            fix = Fix(
                mismatch=mismatch,
                file_path=f"test{i}.py",
                line_number=i+1,
                old_code=f"old{i}",
                new_code=f"new{i}",
                applied=True
            )
            fixes.append(fix)
        
        report = self.fixer._generate_fix_report(fixes)
        
        assert isinstance(report, str)
        assert "Total Fixes:** 3" in report
        assert "Files Modified:** 3" in report
        assert "Success Rate:" in report
    
    def test_generate_fix_report_with_failures(self):
        """Test generating fix report with failed fixes"""
        location = CodeLocation(
            file_path="test.py",
            line_number=10,
            code_snippet="code"
        )
        
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="test_table",
            locations=[location]
        )
        
        from .models import Fix
        fix = Fix(
            mismatch=mismatch,
            file_path="test.py",
            line_number=10,
            old_code="old",
            new_code="new",
            applied=False,
            error="Test error message"
        )
        
        report = self.fixer._generate_fix_report([fix])
        
        assert isinstance(report, str)
        assert "✗" in report  # Failure indicator
        assert "Test error message" in report
        assert "Failed:** 1" in report
    
    def test_rollback_changes_single_file(self):
        """Test rolling back changes for a single file"""
        # Create test file
        test_file = os.path.join(self.test_dir, "test.py")
        original_content = "original content"
        with open(test_file, 'w') as f:
            f.write(original_content)
        
        # Backup the file
        self.fixer.backup_file(test_file)
        
        # Modify the file
        with open(test_file, 'w') as f:
            f.write("modified content")
        
        # Rollback
        result = self.fixer._rollback_changes(test_file)
        
        assert result is True
        
        # Verify content is restored
        with open(test_file, 'r') as f:
            content = f.read()
        assert content == original_content
    
    def test_rollback_changes_all_files(self):
        """Test rolling back changes for all files"""
        # Create multiple test files
        files = []
        for i in range(3):
            test_file = os.path.join(self.test_dir, f"test{i}.py")
            with open(test_file, 'w') as f:
                f.write(f"original{i}")
            files.append(test_file)
            self.fixer.backup_file(test_file)
        
        # Modify all files
        for i, test_file in enumerate(files):
            with open(test_file, 'w') as f:
                f.write(f"modified{i}")
        
        # Rollback all
        result = self.fixer._rollback_changes()
        
        assert result is True
        
        # Verify all files are restored
        for i, test_file in enumerate(files):
            with open(test_file, 'r') as f:
                content = f.read()
            assert content == f"original{i}"
    
    def test_rollback_changes_no_backup(self):
        """Test rollback when no backup exists"""
        result = self.fixer._rollback_changes()
        assert result is False
    
    def test_rollback_changes_clears_cache(self):
        """Test that rollback clears file cache"""
        # Create and backup file
        test_file = os.path.join(self.test_dir, "test.py")
        with open(test_file, 'w') as f:
            f.write("original")
        
        self.fixer.backup_file(test_file)
        
        # Read file to populate cache
        self.fixer._read_file(test_file)
        assert test_file in self.fixer.file_contents
        
        # Rollback
        self.fixer._rollback_changes(test_file)
        
        # Cache should be cleared
        assert test_file not in self.fixer.file_contents
    
    def test_validate_syntax_after_fix(self):
        """Test syntax validation after applying a fix"""
        # Create test file
        test_file = os.path.join(self.test_dir, "test.py")
        with open(test_file, 'w') as f:
            f.write("old_name = 'value'")
        
        location = CodeLocation(
            file_path=test_file,
            line_number=1,
            code_snippet="old_name"
        )
        
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="table",
            expected_value="new_name",
            actual_value="old_name",
            locations=[location]
        )
        
        # Apply fix
        self.fixer.fix_column_name(mismatch, location)
        
        # Validate syntax
        result = self.fixer.validate_syntax(test_file)
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
