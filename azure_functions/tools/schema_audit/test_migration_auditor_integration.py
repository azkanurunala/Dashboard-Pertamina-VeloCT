"""
Integration tests for MigrationAuditor to verify end-to-end workflows.
"""

import pytest
import tempfile
import os
from pathlib import Path

from azure_functions.tools.schema_audit.migration_auditor import MigrationAuditor
from azure_functions.tools.schema_audit.models import (
    DatabaseSchema,
    TableSchema,
    ColumnSchema,
    OperationType,
    MismatchType
)


class TestMigrationAuditorIntegration:
    """Integration tests for MigrationAuditor."""
    
    def test_full_audit_workflow_sql(self):
        """Test complete audit workflow with SQL migration scripts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create reference schema
            ref_schema = DatabaseSchema()
            ref_schema.tables["data_biodiesel_hip"] = TableSchema(
                name="data_biodiesel_hip",
                columns=[
                    ColumnSchema(name="id", data_type="INT", nullable=False, is_identity=True),
                    ColumnSchema(name="published_date", data_type="DATE", nullable=True),
                    ColumnSchema(name="hip_month", data_type="NVARCHAR", max_length=50, nullable=True),
                    ColumnSchema(name="price_idr_liter", data_type="FLOAT", nullable=True),
                    ColumnSchema(name="scraped_at", data_type="DATETIME2", nullable=True)
                ],
                primary_key=["id"]
            )
            
            # Create migration script (simpler version without IF statements)
            sql_file = Path(tmpdir) / "migrate_biodiesel.sql"
            sql_file.write_text("""
            CREATE TABLE data_biodiesel_hip (
                id INT IDENTITY(1,1) PRIMARY KEY,
                published_date DATE,
                hip_month NVARCHAR(50),
                price_idr_liter FLOAT,
                scraped_at DATETIME2 DEFAULT GETUTCDATE()
            );
            """)
            
            # Initialize auditor
            auditor = MigrationAuditor(reference_schema=ref_schema)
            
            # Scan for scripts
            scripts = auditor.scan_migration_scripts(tmpdir)
            assert len(scripts) == 1
            
            # Audit operations
            operations = auditor.audit_migration_operations()
            assert len(operations) > 0
            
            # Check compatibility
            compat_result = auditor.check_migration_compatibility()
            # The migration should be mostly compatible
            # Check that we got a result with expected structure
            assert 'compatible' in compat_result
            assert 'issues' in compat_result
            assert 'warnings' in compat_result
            assert 'summary' in compat_result
            # Verify summary has expected keys
            assert 'total_scripts' in compat_result['summary']
            assert 'total_operations' in compat_result['summary']
            assert compat_result['summary']['total_scripts'] == 1
            assert compat_result['summary']['total_operations'] > 0
    
    def test_detect_schema_mismatch(self):
        """Test detection of schema mismatches in migrations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create reference schema with correct columns
            ref_schema = DatabaseSchema()
            ref_schema.tables["data_test"] = TableSchema(
                name="data_test",
                columns=[
                    ColumnSchema(name="id", data_type="INT", nullable=False),
                    ColumnSchema(name="correct_name", data_type="VARCHAR", max_length=100, nullable=False)
                ]
            )
            
            # Create migration with wrong column name
            sql_file = Path(tmpdir) / "migrate_wrong.sql"
            sql_file.write_text("""
            CREATE TABLE data_test (
                id INT NOT NULL,
                wrong_name VARCHAR(100) NOT NULL
            );
            """)
            
            auditor = MigrationAuditor(reference_schema=ref_schema)
            auditor.scan_migration_scripts(tmpdir)
            
            # Check compatibility - should find mismatch
            compat_result = auditor.check_migration_compatibility()
            
            # Should have issues due to wrong column name
            assert len(compat_result['issues']) > 0 or len(compat_result['warnings']) > 0
    
    def test_fix_migration_workflow(self):
        """Test fixing migration scripts with schema mismatches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create reference schema
            ref_schema = DatabaseSchema()
            ref_schema.tables["data_test"] = TableSchema(
                name="data_test",
                columns=[
                    ColumnSchema(name="id", data_type="INT", nullable=False),
                    ColumnSchema(name="correct_column", data_type="VARCHAR", max_length=100, nullable=False)
                ]
            )
            
            # Create migration with mismatch
            sql_file = Path(tmpdir) / "migrate_fix_test.sql"
            original_content = """
            CREATE TABLE data_test (
                id INT NOT NULL,
                wrong_column VARCHAR(100) NOT NULL
            );
            """
            sql_file.write_text(original_content)
            
            auditor = MigrationAuditor(reference_schema=ref_schema)
            auditor.scan_migration_scripts(tmpdir)
            
            # Try to fix (dry run first)
            fix_result = auditor.fix_migration_schema(str(sql_file), dry_run=True)
            
            assert 'fixed' in fix_result
            assert 'changes' in fix_result
            assert 'errors' in fix_result
            
            # Verify original file unchanged in dry run
            with open(sql_file, 'r') as f:
                content_after_dry_run = f.read()
            assert content_after_dry_run == original_content
    
    def test_generate_migration_for_new_table(self):
        """Test generating migration script for a new table."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create table schema
            table_schema = TableSchema(
                name="data_new_table",
                columns=[
                    ColumnSchema(name="id", data_type="INT", nullable=False, is_identity=True),
                    ColumnSchema(name="name", data_type="NVARCHAR", max_length=200, nullable=False),
                    ColumnSchema(name="value", data_type="FLOAT", nullable=True),
                    ColumnSchema(name="created_at", data_type="DATETIME2", nullable=True, default_value="GETUTCDATE()")
                ],
                primary_key=["id"]
            )
            
            auditor = MigrationAuditor()
            
            # Generate SQL migration
            sql_path = os.path.join(tmpdir, "migrate_new_table.sql")
            result_path = auditor.generate_new_migration(table_schema, sql_path, migration_type='create')
            
            assert os.path.exists(result_path)
            
            # Verify generated content
            with open(result_path, 'r') as f:
                content = f.read()
            
            assert "CREATE TABLE data_new_table" in content
            assert "id INT" in content
            assert "IDENTITY(1,1)" in content
            assert "name NVARCHAR(200)" in content
            assert "value FLOAT" in content
            assert "PRIMARY KEY" in content
            
            # Generate Python migration
            py_path = os.path.join(tmpdir, "migrate_new_table.py")
            result_path = auditor.generate_new_migration(table_schema, py_path, migration_type='create')
            
            assert os.path.exists(result_path)
            
            with open(result_path, 'r') as f:
                content = f.read()
            
            assert "import asyncio" in content
            assert "CREATE TABLE data_new_table" in content
            assert "async def migrate" in content
    
    def test_migration_simulation_detects_conflicts(self):
        """Test that migration simulation detects conflicting operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create migration with duplicate CREATE TABLE
            sql_file = Path(tmpdir) / "migrate_conflict.sql"
            sql_file.write_text("""
            CREATE TABLE data_test (id INT);
            CREATE TABLE data_test (id INT, name VARCHAR(100));
            """)
            
            auditor = MigrationAuditor()
            auditor.scan_migration_scripts(tmpdir)
            operations = auditor.audit_migration_operations()
            
            # Simulate migration
            sim_result = auditor._simulate_migration(operations)
            
            # Should detect duplicate CREATE
            assert sim_result['success'] is False
            assert len(sim_result['errors']) > 0
            assert any('duplicate' in str(err).lower() for err in sim_result['errors'])
    
    def test_compatibility_report_generation(self):
        """Test generating compatibility report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ref_schema = DatabaseSchema()
            ref_schema.tables["data_test"] = TableSchema(
                name="data_test",
                columns=[
                    ColumnSchema(name="id", data_type="INT", nullable=False)
                ]
            )
            
            sql_file = Path(tmpdir) / "migrate_test.sql"
            sql_file.write_text("CREATE TABLE data_test (id INT NOT NULL);")
            
            auditor = MigrationAuditor(reference_schema=ref_schema)
            auditor.scan_migration_scripts(tmpdir)
            compat_result = auditor.check_migration_compatibility()
            
            # Generate report
            report = auditor.get_compatibility_report(compat_result)
            
            assert "Migration Compatibility Report" in report
            assert "Summary" in report
            assert "Compatible" in report
    
    def test_multiple_migration_scripts(self):
        """Test auditing multiple migration scripts in order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple migration scripts with proper naming
            sql_file1 = Path(tmpdir) / "migrate_001_create.sql"
            sql_file1.write_text("CREATE TABLE data_table1 (id INT);")
            
            sql_file2 = Path(tmpdir) / "migrate_002_alter.sql"
            sql_file2.write_text("ALTER TABLE data_table1 ADD name VARCHAR(100);")
            
            sql_file3 = Path(tmpdir) / "migrate_003_create2.sql"
            sql_file3.write_text("CREATE TABLE data_table2 (id INT);")
            
            auditor = MigrationAuditor()
            scripts = auditor.scan_migration_scripts(tmpdir)
            
            # Should find all 3 scripts
            assert len(scripts) == 3
            
            # Audit all operations
            operations = auditor.audit_migration_operations()
            
            # Should have 3 operations (2 CREATE, 1 ALTER)
            assert len(operations) == 3
            
            create_ops = [op for op in operations if op.operation_type == OperationType.CREATE]
            alter_ops = [op for op in operations if op.operation_type == OperationType.ALTER]
            
            assert len(create_ops) == 2
            assert len(alter_ops) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
