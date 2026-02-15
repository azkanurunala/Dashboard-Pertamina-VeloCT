"""
Basic tests for MigrationAuditor to verify implementation.
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
    OperationType
)


def test_migration_auditor_initialization():
    """Test that MigrationAuditor can be initialized."""
    auditor = MigrationAuditor()
    assert auditor is not None
    assert auditor.reference_schema is None
    assert len(auditor.migration_scripts) == 0
    assert len(auditor.operations) == 0


def test_migration_auditor_with_reference_schema():
    """Test initialization with reference schema."""
    schema = DatabaseSchema()
    auditor = MigrationAuditor(reference_schema=schema)
    assert auditor.reference_schema is schema


def test_scan_migration_scripts_empty_directory():
    """Test scanning an empty directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        auditor = MigrationAuditor()
        scripts = auditor.scan_migration_scripts(tmpdir)
        assert scripts == []


def test_scan_migration_scripts_with_sql_file():
    """Test scanning directory with SQL migration file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a migration SQL file
        sql_file = Path(tmpdir) / "migrate_test.sql"
        sql_file.write_text("""
        CREATE TABLE test_table (
            id INT PRIMARY KEY,
            name VARCHAR(100)
        );
        """)
        
        auditor = MigrationAuditor()
        scripts = auditor.scan_migration_scripts(tmpdir)
        
        assert len(scripts) == 1
        assert str(sql_file) in scripts


def test_audit_sql_migration_create_table():
    """Test auditing SQL migration with CREATE TABLE."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a migration SQL file
        sql_file = Path(tmpdir) / "migrate_test.sql"
        sql_content = """
        CREATE TABLE data_test (
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(100) NOT NULL,
            value FLOAT
        );
        """
        sql_file.write_text(sql_content)
        
        auditor = MigrationAuditor()
        auditor.scan_migration_scripts(tmpdir)
        operations = auditor.audit_migration_operations()
        
        assert len(operations) > 0
        create_ops = [op for op in operations if op.operation_type == OperationType.CREATE]
        assert len(create_ops) == 1
        assert create_ops[0].table_name == "data_test"
        assert "id" in create_ops[0].columns
        assert "name" in create_ops[0].columns
        assert "value" in create_ops[0].columns



def test_audit_sql_migration_alter_table():
    """Test auditing SQL migration with ALTER TABLE."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sql_file = Path(tmpdir) / "migrate_alter.sql"
        sql_content = """
        ALTER TABLE data_test ADD new_column VARCHAR(50);
        """
        sql_file.write_text(sql_content)
        
        auditor = MigrationAuditor()
        auditor.scan_migration_scripts(tmpdir)
        operations = auditor.audit_migration_operations()
        
        assert len(operations) > 0
        alter_ops = [op for op in operations if op.operation_type == OperationType.ALTER]
        assert len(alter_ops) == 1
        assert alter_ops[0].table_name == "data_test"
        assert "new_column" in alter_ops[0].columns


def test_audit_python_migration():
    """Test auditing Python migration script."""
    with tempfile.TemporaryDirectory() as tmpdir:
        py_file = Path(tmpdir) / "migrate_test.py"
        py_content = '''
import asyncio

async def migrate():
    query = """
    CREATE TABLE data_python_test (
        id INT PRIMARY KEY,
        data VARCHAR(200)
    )
    """
    # Execute query
    pass

if __name__ == "__main__":
    asyncio.run(migrate())
'''
        py_file.write_text(py_content)
        
        auditor = MigrationAuditor()
        auditor.scan_migration_scripts(tmpdir)
        operations = auditor.audit_migration_operations()
        
        assert len(operations) > 0
        create_ops = [op for op in operations if op.operation_type == OperationType.CREATE]
        assert len(create_ops) == 1
        assert create_ops[0].table_name == "data_python_test"


def test_generate_sql_migration():
    """Test generating SQL migration script."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create table schema
        table_schema = TableSchema(
            name="test_generated",
            columns=[
                ColumnSchema(name="id", data_type="INT", nullable=False, is_identity=True),
                ColumnSchema(name="name", data_type="NVARCHAR", max_length=100, nullable=False),
                ColumnSchema(name="value", data_type="FLOAT", nullable=True)
            ],
            primary_key=["id"]
        )
        
        auditor = MigrationAuditor()
        output_path = os.path.join(tmpdir, "generated_migration.sql")
        result_path = auditor.generate_new_migration(table_schema, output_path, migration_type='create')
        
        assert os.path.exists(result_path)
        
        # Read and verify content
        with open(result_path, 'r') as f:
            content = f.read()
        
        assert "CREATE TABLE test_generated" in content
        assert "id INT" in content
        assert "name NVARCHAR(100)" in content
        assert "value FLOAT" in content


def test_check_migration_compatibility():
    """Test checking migration compatibility with reference schema."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create reference schema
        ref_schema = DatabaseSchema()
        ref_schema.tables["data_test"] = TableSchema(
            name="data_test",
            columns=[
                ColumnSchema(name="id", data_type="INT", nullable=False),
                ColumnSchema(name="name", data_type="NVARCHAR", max_length=100, nullable=False)
            ]
        )
        
        # Create migration that matches reference
        sql_file = Path(tmpdir) / "migrate_compatible.sql"
        sql_file.write_text("""
        CREATE TABLE data_test (
            id INT NOT NULL,
            name NVARCHAR(100) NOT NULL
        );
        """)
        
        auditor = MigrationAuditor(reference_schema=ref_schema)
        auditor.scan_migration_scripts(tmpdir)
        result = auditor.check_migration_compatibility()
        
        assert 'compatible' in result
        assert 'issues' in result
        assert 'warnings' in result
        assert 'summary' in result


def test_clear():
    """Test clearing auditor state."""
    auditor = MigrationAuditor()
    auditor.migration_scripts = ["test.sql"]
    auditor.operations = [None]
    auditor.mismatches = [None]
    
    auditor.clear()
    
    assert len(auditor.migration_scripts) == 0
    assert len(auditor.operations) == 0
    assert len(auditor.mismatches) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
