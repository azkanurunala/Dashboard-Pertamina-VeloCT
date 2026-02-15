"""
Unit tests for Reporter module.

Tests the Reporter class functionality including:
- Audit report generation
- Fix report generation
- Schema documentation generation
- Markdown formatting

Requirements: 7.1, 7.2
"""

import pytest
from datetime import datetime
from azure_functions.tools.schema_audit.reporter import Reporter
from azure_functions.tools.schema_audit.models import (
    Mismatch, Fix, FixReport, DatabaseSchema, TableSchema, ColumnSchema,
    MismatchType, Severity, CodeLocation
)


class TestReporter:
    """Test suite for Reporter class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.reporter = Reporter()
    
    def test_generate_audit_report_empty(self):
        """Test audit report generation with no mismatches."""
        report = self.reporter.generate_audit_report([])
        
        assert "Schema Audit Report" in report
        assert "No schema mismatches found" in report
        assert "Generated:" in report
    
    def test_generate_audit_report_with_mismatches(self):
        """Test audit report generation with mismatches."""
        # Create test mismatches
        location = CodeLocation(
            file_path="test.py",
            line_number=10,
            code_snippet="test code"
        )
        
        mismatch1 = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="test_table",
            column_name="test_col",
            expected_value="correct_name",
            actual_value="wrong_name",
            locations=[location],
            fix_suggestion="Rename column to correct_name"
        )
        
        mismatch2 = Mismatch(
            mismatch_type=MismatchType.MISSING_COLUMN,
            severity=Severity.WARNING,
            table_name="test_table",
            column_name="missing_col",
            expected_value="VARCHAR(50)",
            locations=[location]
        )
        
        report = self.reporter.generate_audit_report([mismatch1, mismatch2])
        
        # Verify report structure
        assert "Schema Audit Report" in report
        assert "2" in report  # Total mismatches count
        assert "Critical" in report and "1" in report
        assert "Warning" in report and "1" in report
        assert "test_table" in report
        assert "test_col" in report
        assert "missing_col" in report
        assert "correct_name" in report
        assert "wrong_name" in report
    
    def test_generate_audit_report_severity_categorization(self):
        """Test that mismatches are correctly categorized by severity."""
        location = CodeLocation(
            file_path="test.py",
            line_number=10,
            code_snippet="test"
        )
        
        critical = Mismatch(
            mismatch_type=MismatchType.COLUMN_TYPE_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="table1",
            column_name="col1",
            expected_value="INT",
            actual_value="VARCHAR"
        )
        
        warning = Mismatch(
            mismatch_type=MismatchType.EXTRA_COLUMN,
            severity=Severity.WARNING,
            table_name="table2",
            column_name="col2"
        )
        
        info = Mismatch(
            mismatch_type=MismatchType.EXTRA_TABLE,
            severity=Severity.INFO,
            table_name="table3"
        )
        
        report = self.reporter.generate_audit_report([critical, warning, info])
        
        assert "Critical" in report and "1" in report
        assert "Warning" in report and "1" in report
        assert "Info" in report and "1" in report
        assert "🔴" in report  # Critical icon
        assert "🟡" in report  # Warning icon
        assert "🔵" in report  # Info icon
    
    def test_generate_fix_report_empty(self):
        """Test fix report generation with no fixes."""
        fix_report = FixReport()
        report = self.reporter.generate_fix_report(fix_report)
        
        assert "Fix Report" in report
        assert "No fixes were applied" in report
    
    def test_generate_fix_report_with_fixes(self):
        """Test fix report generation with fixes."""
        location = CodeLocation(
            file_path="test.py",
            line_number=10,
            code_snippet="old code"
        )
        
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="test_table",
            column_name="test_col",
            expected_value="new_name",
            actual_value="old_name"
        )
        
        fix1 = Fix(
            mismatch=mismatch,
            file_path="test.py",
            line_number=10,
            old_code="old_name = value",
            new_code="new_name = value",
            applied=True
        )
        
        fix2 = Fix(
            mismatch=mismatch,
            file_path="test2.py",
            line_number=20,
            old_code="old_name",
            new_code="new_name",
            applied=False,
            error="Syntax error"
        )
        
        fix_report = FixReport(
            fixes=[fix1, fix2],
            total_files_modified=2,
            total_fixes_applied=1,
            total_fixes_failed=1,
            timestamp=datetime.now()
        )
        
        report = self.reporter.generate_fix_report(fix_report)
        
        # Verify report structure
        assert "Fix Report" in report
        assert "2" in report  # Total fixes count
        assert "Successful" in report and "1" in report
        assert "Failed" in report and "1" in report
        assert "test.py" in report
        assert "test2.py" in report
        assert "old_name" in report
        assert "new_name" in report
        assert "Syntax error" in report
        assert "✓" in report  # Success marker
        assert "✗" in report  # Failure marker
    
    def test_generate_fix_report_success_rate(self):
        """Test that fix report calculates success rate correctly."""
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="test_table"
        )
        
        fixes = [
            Fix(mismatch=mismatch, file_path="f1.py", line_number=1,
                old_code="old", new_code="new", applied=True),
            Fix(mismatch=mismatch, file_path="f2.py", line_number=2,
                old_code="old", new_code="new", applied=True),
            Fix(mismatch=mismatch, file_path="f3.py", line_number=3,
                old_code="old", new_code="new", applied=False)
        ]
        
        fix_report = FixReport(fixes=fixes)
        fix_report.total_fixes_applied = 2
        fix_report.total_fixes_failed = 1
        
        report = self.reporter.generate_fix_report(fix_report)
        
        # Success rate should be 66.7% (2 out of 3)
        assert "66.7%" in report or "67%" in report
    
    def test_generate_schema_documentation_empty(self):
        """Test schema documentation with empty schema."""
        schema = DatabaseSchema()
        report = self.reporter.generate_schema_documentation(schema)
        
        assert "Database Schema Documentation" in report
        assert "0 tables" in report or "contains **0** tables" in report
    
    def test_generate_schema_documentation_with_tables(self):
        """Test schema documentation with tables."""
        # Create test schema
        column1 = ColumnSchema(
            name="id",
            data_type="INT",
            nullable=False,
            is_identity=True
        )
        
        column2 = ColumnSchema(
            name="name",
            data_type="VARCHAR",
            nullable=True,
            max_length=100
        )
        
        table = TableSchema(
            name="test_table",
            columns=[column1, column2],
            primary_key=["id"]
        )
        
        schema = DatabaseSchema(
            tables={"test_table": table},
            version="1.0",
            source_file="test.bacpac",
            extracted_at=datetime.now()
        )
        
        report = self.reporter.generate_schema_documentation(schema)
        
        # Verify documentation structure
        assert "Database Schema Documentation" in report
        assert "test_table" in report
        assert "Columns" in report and "2" in report
        assert "Primary Key" in report
        assert "id" in report
        assert "name" in report
        assert "INT" in report
        assert "VARCHAR(100)" in report
        assert "Identity" in report
    
    def test_generate_schema_documentation_with_foreign_keys(self):
        """Test schema documentation includes foreign keys."""
        from azure_functions.tools.schema_audit.models import ForeignKeySchema
        
        column = ColumnSchema(name="user_id", data_type="INT", nullable=False)
        
        fk = ForeignKeySchema(
            name="fk_user",
            column="user_id",
            referenced_table="users",
            referenced_column="id",
            on_delete="CASCADE",
            on_update="NO ACTION"
        )
        
        table = TableSchema(
            name="orders",
            columns=[column],
            foreign_keys=[fk]
        )
        
        schema = DatabaseSchema(tables={"orders": table})
        report = self.reporter.generate_schema_documentation(schema)
        
        assert "Foreign Keys" in report
        assert "fk_user" in report
        assert "users.id" in report
        assert "CASCADE" in report
    
    def test_generate_schema_documentation_with_indexes(self):
        """Test schema documentation includes indexes."""
        from azure_functions.tools.schema_audit.models import IndexSchema
        
        column = ColumnSchema(name="email", data_type="VARCHAR", max_length=255)
        
        index = IndexSchema(
            name="idx_email",
            columns=["email"],
            is_unique=True,
            is_clustered=False
        )
        
        table = TableSchema(
            name="users",
            columns=[column],
            indexes=[index]
        )
        
        schema = DatabaseSchema(tables={"users": table})
        report = self.reporter.generate_schema_documentation(schema)
        
        assert "Indexes" in report
        assert "idx_email" in report
        assert "email" in report
        assert "Yes" in report  # Unique
    
    def test_format_markdown_basic(self):
        """Test basic markdown formatting."""
        result = self.reporter._format_markdown(
            "# Title",
            "",
            "Content line 1",
            "Content line 2"
        )
        
        assert result == "# Title\n\nContent line 1\nContent line 2"
    
    def test_format_markdown_empty(self):
        """Test markdown formatting with no lines."""
        result = self.reporter._format_markdown()
        assert result == ""
    
    def test_format_markdown_single_line(self):
        """Test markdown formatting with single line."""
        result = self.reporter._format_markdown("Single line")
        assert result == "Single line"
    
    def test_generated_reports_tracking(self):
        """Test that generated reports are tracked."""
        assert len(self.reporter.generated_reports) == 0
        
        # Generate reports
        self.reporter.generate_audit_report([])
        assert len(self.reporter.generated_reports) == 1
        
        schema = DatabaseSchema()
        self.reporter.generate_schema_documentation(schema)
        assert len(self.reporter.generated_reports) == 2
        
        fix_report = FixReport()
        self.reporter.generate_fix_report(fix_report)
        assert len(self.reporter.generated_reports) == 3
    
    def test_audit_report_multiple_locations(self):
        """Test audit report with mismatch in multiple locations."""
        locations = [
            CodeLocation(file_path=f"file{i}.py", line_number=i*10, code_snippet="code")
            for i in range(5)
        ]
        
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="test_table",
            column_name="test_col",
            locations=locations
        )
        
        report = self.reporter.generate_audit_report([mismatch])
        
        # Should show first 3 locations and indicate more
        assert "file0.py" in report
        assert "file1.py" in report
        assert "file2.py" in report
        assert "and 2 more" in report or "... and 2 more" in report
    
    def test_fix_report_groups_by_file(self):
        """Test that fix report groups fixes by file."""
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="test_table"
        )
        
        fixes = [
            Fix(mismatch=mismatch, file_path="file1.py", line_number=1,
                old_code="old", new_code="new", applied=True),
            Fix(mismatch=mismatch, file_path="file1.py", line_number=2,
                old_code="old", new_code="new", applied=True),
            Fix(mismatch=mismatch, file_path="file2.py", line_number=1,
                old_code="old", new_code="new", applied=True)
        ]
        
        fix_report = FixReport(fixes=fixes)
        report = self.reporter.generate_fix_report(fix_report)
        
        # Both files should be in report
        assert "file1.py" in report
        assert "file2.py" in report
        # file1.py should show 2 changes
        assert "Total Changes" in report and "2" in report
    
    def test_schema_documentation_table_of_contents(self):
        """Test that schema documentation includes table of contents."""
        table1 = TableSchema(
            name="users",
            columns=[ColumnSchema(name="id", data_type="INT")]
        )
        table2 = TableSchema(
            name="orders",
            columns=[ColumnSchema(name="id", data_type="INT")]
        )
        
        schema = DatabaseSchema(tables={"users": table1, "orders": table2})
        report = self.reporter.generate_schema_documentation(schema)
        
        assert "Table of Contents" in report
        assert "[users]" in report or "users" in report
        assert "[orders]" in report or "orders" in report
    
    def test_generate_erd_diagram_empty(self):
        """Test ERD diagram generation with empty schema."""
        schema = DatabaseSchema()
        diagram = self.reporter.generate_erd_diagram(schema)
        
        assert "```mermaid" in diagram
        assert "erDiagram" in diagram
        assert "```" in diagram
    
    def test_generate_erd_diagram_with_tables(self):
        """Test ERD diagram generation with tables."""
        column1 = ColumnSchema(
            name="id",
            data_type="INT",
            nullable=False,
            is_identity=True
        )
        column2 = ColumnSchema(
            name="name",
            data_type="VARCHAR",
            nullable=True,
            max_length=100
        )
        
        table = TableSchema(
            name="users",
            columns=[column1, column2]
        )
        
        schema = DatabaseSchema(tables={"users": table})
        diagram = self.reporter.generate_erd_diagram(schema)
        
        assert "```mermaid" in diagram
        assert "erDiagram" in diagram
        assert "users {" in diagram
        assert "INT id" in diagram
        assert "VARCHAR(100) name" in diagram
        assert "PK" in diagram  # Primary key marker
    
    def test_generate_erd_diagram_with_relationships(self):
        """Test ERD diagram includes foreign key relationships."""
        from azure_functions.tools.schema_audit.models import ForeignKeySchema
        
        user_col = ColumnSchema(name="id", data_type="INT", is_identity=True)
        order_col = ColumnSchema(name="user_id", data_type="INT")
        
        fk = ForeignKeySchema(
            name="fk_user",
            column="user_id",
            referenced_table="users",
            referenced_column="id"
        )
        
        users_table = TableSchema(name="users", columns=[user_col])
        orders_table = TableSchema(
            name="orders",
            columns=[order_col],
            foreign_keys=[fk]
        )
        
        schema = DatabaseSchema(tables={"users": users_table, "orders": orders_table})
        diagram = self.reporter.generate_erd_diagram(schema)
        
        assert "users ||--o{ orders" in diagram
        assert "fk_user" in diagram
    
    def test_generate_mapping_table_empty(self):
        """Test mapping table generation with no operations."""
        mapping = self.reporter.generate_mapping_table({})
        
        assert "Scraper-Table Mapping" in mapping
        assert "**Total Tables:** 0" in mapping
        assert "**Total Scrapers:** 0" in mapping
    
    def test_generate_mapping_table_with_operations(self):
        """Test mapping table generation with operations."""
        from azure_functions.tools.schema_audit.models import TableOperation
        
        op1 = TableOperation(
            operation_type="INSERT",
            table_name="users",
            columns=["id", "name"],
            file_path="scrapers/user_scraper.py",
            line_number=10,
            code_snippet="INSERT INTO users"
        )
        
        op2 = TableOperation(
            operation_type="INSERT",
            table_name="orders",
            columns=["id", "user_id"],
            file_path="scrapers/order_scraper.py",
            line_number=20,
            code_snippet="INSERT INTO orders"
        )
        
        operations_map = {
            "users": [op1],
            "orders": [op2]
        }
        
        mapping = self.reporter.generate_mapping_table(operations_map)
        
        assert "Scraper-Table Mapping" in mapping
        assert "users" in mapping
        assert "orders" in mapping
        assert "user_scraper" in mapping
        assert "order_scraper" in mapping
        assert "Scrapers by Table" in mapping
        assert "Tables by Scraper" in mapping
    
    def test_generate_mapping_table_multiple_operations_per_table(self):
        """Test mapping table with multiple operations per table."""
        from azure_functions.tools.schema_audit.models import TableOperation
        
        ops = [
            TableOperation(
                operation_type="INSERT",
                table_name="users",
                columns=["id"],
                file_path="scraper1.py",
                line_number=i,
                code_snippet="code"
            )
            for i in range(5)
        ]
        
        mapping = self.reporter.generate_mapping_table({"users": ops})
        
        assert "5" in mapping  # Should show 5 operations
        assert "users" in mapping
    
    def test_generate_changelog_empty(self):
        """Test changelog generation with no fixes."""
        changelog = self.reporter.generate_changelog([])
        
        assert "Changelog" in changelog
        assert "No changes were made" in changelog
    
    def test_generate_changelog_with_fixes(self):
        """Test changelog generation with fixes."""
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="users",
            column_name="user_name",
            expected_value="username",
            actual_value="user_name"
        )
        
        fix1 = Fix(
            mismatch=mismatch,
            file_path="file1.py",
            line_number=10,
            old_code="user_name = data['user_name']",
            new_code="username = data['username']",
            applied=True
        )
        
        fix2 = Fix(
            mismatch=mismatch,
            file_path="file2.py",
            line_number=20,
            old_code="print(user_name)",
            new_code="print(username)",
            applied=True
        )
        
        changelog = self.reporter.generate_changelog([fix1, fix2])
        
        assert "Changelog" in changelog
        assert "**Total Changes:** 2" in changelog
        assert "**Files Modified:** 2" in changelog
        assert "file1.py" in changelog
        assert "file2.py" in changelog
        assert "user_name" in changelog
        assert "username" in changelog
        assert "Before:" in changelog
        assert "After:" in changelog
    
    def test_generate_changelog_groups_by_file(self):
        """Test that changelog groups changes by file."""
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="users"
        )
        
        fixes = [
            Fix(mismatch=mismatch, file_path="file1.py", line_number=i,
                old_code="old", new_code="new", applied=True)
            for i in range(3)
        ]
        
        changelog = self.reporter.generate_changelog(fixes)
        
        assert "file1.py" in changelog
        assert "**Changes:** 3" in changelog
    
    def test_generate_statistics_empty(self):
        """Test statistics generation with no data."""
        stats = self.reporter.generate_statistics()
        
        assert "Summary Statistics" in stats
        assert "Generated:" in stats
    
    def test_generate_statistics_with_schema(self):
        """Test statistics generation with schema data."""
        column = ColumnSchema(name="id", data_type="INT")
        table = TableSchema(name="users", columns=[column])
        schema = DatabaseSchema(
            tables={"users": table},
            version="1.0"
        )
        
        stats = self.reporter.generate_statistics(schema=schema)
        
        assert "Schema Statistics" in stats
        assert "**Total Tables:** 1" in stats
        assert "**Total Columns:** 1" in stats
        assert "**Schema Version:** 1.0" in stats
    
    def test_generate_statistics_with_mismatches(self):
        """Test statistics generation with mismatch data."""
        mismatches = [
            Mismatch(
                mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
                severity=Severity.CRITICAL,
                table_name="users"
            ),
            Mismatch(
                mismatch_type=MismatchType.MISSING_COLUMN,
                severity=Severity.WARNING,
                table_name="orders"
            )
        ]
        
        stats = self.reporter.generate_statistics(mismatches=mismatches)
        
        assert "Mismatch Statistics" in stats
        assert "**Total Mismatches:** 2" in stats
        assert "**Critical:** 1" in stats
        assert "**Warnings:** 1" in stats
        assert "**Tables Affected:** 2" in stats
    
    def test_generate_statistics_with_fixes(self):
        """Test statistics generation with fix data."""
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="users"
        )
        
        fixes = [
            Fix(mismatch=mismatch, file_path="f1.py", line_number=1,
                old_code="old", new_code="new", applied=True),
            Fix(mismatch=mismatch, file_path="f2.py", line_number=2,
                old_code="old", new_code="new", applied=False)
        ]
        
        stats = self.reporter.generate_statistics(fixes=fixes)
        
        assert "Fix Statistics" in stats
        assert "**Total Fixes:** 2" in stats
        assert "**Successfully Applied:** 1" in stats
        assert "**Failed:** 1" in stats
        assert "**Success Rate:** 50.0%" in stats
    
    def test_generate_statistics_with_operations(self):
        """Test statistics generation with operations data."""
        from azure_functions.tools.schema_audit.models import TableOperation
        
        ops = [
            TableOperation(
                operation_type="INSERT",
                table_name="users",
                columns=["id"],
                file_path="scraper.py",
                line_number=i,
                code_snippet="code"
            )
            for i in range(3)
        ]
        
        operations_map = {"users": ops}
        stats = self.reporter.generate_statistics(operations_map=operations_map)
        
        assert "Operations Statistics" in stats
        assert "**Total Operations:** 3" in stats
        assert "**Tables with Operations:** 1" in stats
        assert "INSERT: 3" in stats
    
    def test_generate_statistics_comprehensive(self):
        """Test statistics generation with all data types."""
        # Schema
        column = ColumnSchema(name="id", data_type="INT")
        table = TableSchema(name="users", columns=[column])
        schema = DatabaseSchema(tables={"users": table})
        
        # Mismatches
        mismatch = Mismatch(
            mismatch_type=MismatchType.COLUMN_NAME_MISMATCH,
            severity=Severity.CRITICAL,
            table_name="users"
        )
        
        # Fixes
        fix = Fix(
            mismatch=mismatch,
            file_path="file.py",
            line_number=1,
            old_code="old",
            new_code="new",
            applied=True
        )
        
        # Operations
        from azure_functions.tools.schema_audit.models import TableOperation
        op = TableOperation(
            operation_type="INSERT",
            table_name="users",
            columns=["id"],
            file_path="scraper.py",
            line_number=1,
            code_snippet="code"
        )
        
        stats = self.reporter.generate_statistics(
            schema=schema,
            mismatches=[mismatch],
            fixes=[fix],
            operations_map={"users": [op]}
        )
        
        assert "Schema Statistics" in stats
        assert "Mismatch Statistics" in stats
        assert "Fix Statistics" in stats
        assert "Operations Statistics" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
