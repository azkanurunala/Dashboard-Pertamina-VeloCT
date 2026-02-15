"""
Integration tests for fix strategies with fix_mismatches orchestration.

Tests the end-to-end workflow of detecting and fixing mismatches.
"""

import os
import tempfile
import shutil
import pytest

from .schema_fixer import SchemaFixer
from .models import (
    Mismatch, MismatchType, Severity, CodeLocation
)


class TestFixIntegration:
    """Integration tests for fix orchestration"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.backup_root = os.path.join(self.test_dir, "backups")
        self.fixer = SchemaFixer(backup_root=self.backup_root)
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_fix_multiple_mismatches(self):
        """Test fixing multiple different types of mismatches"""
        # Create test files
        file1 = os.path.join(self.test_dir, "file1.py")
        with open(file1, 'w') as f:
            f.write("old_column = 'value'\n")
        
        file2 = os.path.join(self.test_dir, "file2.py")
        with open(file2, 'w') as f:
            f.write("CREATE TABLE test (id INT, name VARCHAR(50))\n")
        
        # Create mismatches
        mismatch1 = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="table1",
            column_name="old_column",
            expected_value="new_column",
            actual_value="old_column",
            locations=[CodeLocation(file1, 1, code_snippet="old_column")]
        )
        
        mismatch2 = Mismatch(
            mismatch_type=MismatchType.COLUMN_TYPE_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="test",
            column_name="id",
            expected_value="BIGINT",
            actual_value="INT",
            locations=[CodeLocation(file2, 1, code_snippet="id INT")]
        )
        
        # Apply fixes
        report = self.fixer.fix_mismatches([mismatch1, mismatch2], dry_run=False)
        
        # Verify report
        assert report.total_fixes_applied == 2
        assert report.total_fixes_failed == 0
        assert report.total_files_modified == 2
        assert report.backup_directory != ""
        
        # Verify file1 changed
        with open(file1, 'r') as f:
            content1 = f.read()
        assert "new_column" in content1
        assert "old_column" not in content1
        
        # Verify file2 changed
        with open(file2, 'r') as f:
            content2 = f.read()
        assert "BIGINT" in content2
    
    def test_fix_with_dry_run(self):
        """Test that dry-run doesn't modify files"""
        test_file = os.path.join(self.test_dir, "test.py")
        original_content = "old_name = 'value'"
        with open(test_file, 'w') as f:
            f.write(original_content)
        
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="table",
            expected_value="new_name",
            actual_value="old_name",
            locations=[CodeLocation(test_file, 1, code_snippet="old_name")]
        )
        
        # Run in dry-run mode
        report = self.fixer.fix_mismatches([mismatch], dry_run=True)
        
        # Verify no changes applied
        assert report.total_fixes_applied == 0
        assert report.backup_directory == ""
        
        # Verify file unchanged
        with open(test_file, 'r') as f:
            content = f.read()
        assert content == original_content
    
    def test_fix_with_error_handling(self):
        """Test error handling when fix fails"""
        # Create mismatch with non-existent file
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="table",
            expected_value="new_name",
            actual_value="old_name",
            locations=[CodeLocation("/nonexistent/file.py", 1, code_snippet="old_name")]
        )
        
        # Apply fixes - should handle error gracefully
        report = self.fixer.fix_mismatches([mismatch], dry_run=False)
        
        # Verify error was recorded
        assert report.total_fixes_failed == 1
        assert report.total_fixes_applied == 0
        assert len(report.fixes) == 1
        assert report.fixes[0].error is not None
    
    def test_fix_same_file_multiple_times(self):
        """Test fixing multiple mismatches in the same file"""
        test_file = os.path.join(self.test_dir, "test.py")
        with open(test_file, 'w') as f:
            f.write("old1 = 'value1'\nold2 = 'value2'\n")
        
        mismatch1 = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="table",
            expected_value="new1",
            actual_value="old1",
            locations=[CodeLocation(test_file, 1, code_snippet="old1")]
        )
        
        mismatch2 = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="table",
            expected_value="new2",
            actual_value="old2",
            locations=[CodeLocation(test_file, 2, code_snippet="old2")]
        )
        
        # Apply fixes
        report = self.fixer.fix_mismatches([mismatch1, mismatch2], dry_run=False)
        
        # Verify both fixes applied
        assert report.total_fixes_applied == 2
        assert report.total_files_modified == 1  # Same file
        
        # Verify file has both changes
        with open(test_file, 'r') as f:
            content = f.read()
        assert "new1" in content
        assert "new2" in content
        assert "old1" not in content
        assert "old2" not in content
        
        # Verify only one backup created
        assert len(self.fixer.backed_up_files) == 1
    
    def test_fix_report_statistics(self):
        """Test that fix report calculates statistics correctly"""
        test_file = os.path.join(self.test_dir, "test.py")
        with open(test_file, 'w') as f:
            f.write("old_name = 'value'")
        
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="table",
            expected_value="new_name",
            actual_value="old_name",
            locations=[CodeLocation(test_file, 1, code_snippet="old_name")]
        )
        
        report = self.fixer.fix_mismatches([mismatch], dry_run=False)
        
        # Verify statistics
        assert report.get_success_rate() == 100.0
        assert len(report.get_modified_files()) == 1
        assert test_file in report.get_modified_files()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
