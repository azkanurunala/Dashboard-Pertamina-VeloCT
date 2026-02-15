"""
Unit tests for ModelUpdater class.
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import os

from .models import (
    DatabaseSchema,
    TableSchema,
    ColumnSchema,
    ForeignKeySchema,
    IndexSchema
)
from .model_updater import ModelUpdater


class TestModelUpdater:
    """Test suite for ModelUpdater class."""
    
    def test_table_name_to_class_name(self):
        """Test conversion of table names to class names."""
        updater = ModelUpdater()
        
        assert updater._table_name_to_class_name('data_biodiesel_hip') == 'DataBiodieselHip'
        assert updater._table_name_to_class_name('data_harga_ebt') == 'DataHargaEbt'
        assert updater._table_name_to_class_name('simple_table') == 'SimpleTable'
        assert updater._table_name_to_class_name('my_test_table_name') == 'MyTestTableName'
    
    def test_sql_type_to_python_type(self):
        """Test SQL to Python type conversion."""
        updater = ModelUpdater()
        
        assert updater._sql_type_to_python_type('int') == 'int'
        assert updater._sql_type_to_python_type('bigint') == 'int'
        assert updater._sql_type_to_python_type('nvarchar') == 'str'
        assert updater._sql_type_to_python_type('nvarchar(100)') == 'str'
        assert updater._sql_type_to_python_type('datetime2') == 'datetime'
        assert updater._sql_type_to_python_type('bit') == 'bool'
        assert updater._sql_type_to_python_type('float') == 'float'
        assert updater._sql_type_to_python_type('decimal(18,2)') == 'float'
    
    def test_generate_field_definition(self):
        """Test generation of Python field definitions."""
        updater = ModelUpdater()
        
        # Non-nullable int field
        col1 = ColumnSchema(name='id', data_type='int', nullable=False, is_identity=True)
        field1 = updater._generate_field_definition(col1)
        assert 'id: Optional[int]' in field1
        assert '= None' in field1
        
        # Nullable string field
        col2 = ColumnSchema(name='name', data_type='nvarchar', nullable=True, max_length=100)
        field2 = updater._generate_field_definition(col2)
        assert 'name: Optional[str]' in field2
        assert '= None' in field2
        
        # Non-nullable datetime field
        col3 = ColumnSchema(name='created_at', data_type='datetime2', nullable=False)
        field3 = updater._generate_field_definition(col3)
        assert 'created_at: datetime' in field3
    
    def test_generate_dataclass(self):
        """Test generation of complete dataclass."""
        updater = ModelUpdater()
        
        # Create a simple table schema
        table_schema = TableSchema(
            name='data_test_table',
            columns=[
                ColumnSchema(name='id', data_type='int', nullable=False, is_identity=True),
                ColumnSchema(name='name', data_type='nvarchar', nullable=False, max_length=100),
                ColumnSchema(name='value', data_type='float', nullable=True),
                ColumnSchema(name='created_at', data_type='datetime2', nullable=False)
            ]
        )
        
        dataclass_code = updater._generate_dataclass('data_test_table', table_schema)
        
        # Verify dataclass structure
        assert '@dataclass' in dataclass_code
        assert 'class DataTestTable:' in dataclass_code
        assert 'id: Optional[int]' in dataclass_code
        assert 'name: str' in dataclass_code
        assert 'value: Optional[float]' in dataclass_code
        assert 'created_at: datetime' in dataclass_code
    
    def test_get_structured_data_tables(self):
        """Test filtering of structured data tables."""
        updater = ModelUpdater()
        
        # Create schema with mixed tables
        schema = DatabaseSchema(
            tables={
                'news_articles': TableSchema(name='news_articles', columns=[]),
                'data_biodiesel_hip': TableSchema(name='data_biodiesel_hip', columns=[]),
                'keywords': TableSchema(name='keywords', columns=[]),
                'data_harga_ebt': TableSchema(name='data_harga_ebt', columns=[])
            }
        )
        
        structured_tables = updater._get_structured_data_tables(schema)
        
        # Should only include data_* tables
        assert len(structured_tables) == 2
        assert 'data_biodiesel_hip' in structured_tables
        assert 'data_harga_ebt' in structured_tables
        assert 'news_articles' not in structured_tables
        assert 'keywords' not in structured_tables
    
    def test_generate_column_sql(self):
        """Test generation of SQL column definitions."""
        updater = ModelUpdater()
        
        # Identity column
        col1 = ColumnSchema(name='id', data_type='int', nullable=False, is_identity=True)
        sql1 = updater._generate_column_sql(col1)
        assert 'id INT IDENTITY(1,1) NOT NULL' == sql1
        
        # Varchar column with length
        col2 = ColumnSchema(name='name', data_type='nvarchar', nullable=False, max_length=100)
        sql2 = updater._generate_column_sql(col2)
        assert 'name NVARCHAR(100) NOT NULL' == sql2
        
        # Nullable datetime column
        col3 = ColumnSchema(name='created_at', data_type='datetime2', nullable=True)
        sql3 = updater._generate_column_sql(col3)
        assert 'created_at DATETIME2 NULL' == sql3
    
    def test_generate_create_table_sql(self):
        """Test generation of CREATE TABLE statements."""
        updater = ModelUpdater()
        
        # Create a table schema
        table_schema = TableSchema(
            name='data_test_table',
            columns=[
                ColumnSchema(name='id', data_type='int', nullable=False, is_identity=True),
                ColumnSchema(name='name', data_type='nvarchar', nullable=False, max_length=100),
                ColumnSchema(name='value', data_type='float', nullable=True)
            ],
            primary_key=['id']
        )
        
        create_sql = updater._generate_create_table_sql('data_test_table', table_schema)
        
        # Verify SQL structure
        assert 'CREATE TABLE data_test_table' in create_sql
        assert 'id INT IDENTITY(1,1) NOT NULL' in create_sql
        assert 'name NVARCHAR(100) NOT NULL' in create_sql
        assert 'value FLOAT NULL' in create_sql
        assert 'CONSTRAINT PK_data_test_table PRIMARY KEY (id)' in create_sql
    
    def test_update_models_file_dry_run(self):
        """Test updating models file in dry-run mode."""
        updater = ModelUpdater()
        
        # Create a temporary models file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write('"""Test models file."""\n')
            f.write('from dataclasses import dataclass\n')
            f.write('from datetime import datetime\n\n')
            temp_file = f.name
        
        try:
            # Create a simple schema
            schema = DatabaseSchema(
                tables={
                    'data_test_table': TableSchema(
                        name='data_test_table',
                        columns=[
                            ColumnSchema(name='id', data_type='int', nullable=False, is_identity=True),
                            ColumnSchema(name='name', data_type='nvarchar', nullable=False, max_length=100)
                        ]
                    )
                }
            )
            
            # Update in dry-run mode
            result = updater.update_models_file(schema, temp_file, dry_run=True)
            
            assert result is True
            
            # Verify file wasn't modified
            with open(temp_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert 'DataTestTable' not in content
        
        finally:
            # Clean up
            os.unlink(temp_file)
    
    def test_update_models_file_actual(self):
        """Test actually updating models file."""
        updater = ModelUpdater()
        
        # Create a temporary models file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write('"""Test models file."""\n')
            f.write('from dataclasses import dataclass\n')
            f.write('from datetime import datetime\n')
            f.write('from typing import Optional\n\n')
            temp_file = f.name
        
        try:
            # Create a simple schema
            schema = DatabaseSchema(
                tables={
                    'data_test_table': TableSchema(
                        name='data_test_table',
                        columns=[
                            ColumnSchema(name='id', data_type='int', nullable=False, is_identity=True),
                            ColumnSchema(name='name', data_type='nvarchar', nullable=False, max_length=100)
                        ]
                    )
                }
            )
            
            # Update file
            result = updater.update_models_file(schema, temp_file, dry_run=False)
            
            assert result is True
            
            # Verify file was modified
            with open(temp_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert 'class DataTestTable:' in content
            assert '@dataclass' in content
            assert 'id: Optional[int]' in content
            assert 'name: str' in content
        
        finally:
            # Clean up
            os.unlink(temp_file)
    
    def test_update_database_schema_sql_dry_run(self):
        """Test updating SQL schema file in dry-run mode."""
        updater = ModelUpdater()
        
        # Create a temporary SQL file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False, encoding='utf-8') as f:
            f.write('-- Test SQL schema file\n')
            temp_file = f.name
        
        try:
            # Create a simple schema
            schema = DatabaseSchema(
                tables={
                    'data_test_table': TableSchema(
                        name='data_test_table',
                        columns=[
                            ColumnSchema(name='id', data_type='int', nullable=False, is_identity=True),
                            ColumnSchema(name='name', data_type='nvarchar', nullable=False, max_length=100)
                        ],
                        primary_key=['id']
                    )
                }
            )
            
            # Update in dry-run mode
            result = updater.update_database_schema_sql(schema, temp_file, dry_run=True)
            
            assert result is True
            
            # Verify file wasn't modified
            with open(temp_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert 'CREATE TABLE data_test_table' not in content
        
        finally:
            # Clean up
            os.unlink(temp_file)
    
    def test_update_database_schema_sql_actual(self):
        """Test actually updating SQL schema file."""
        updater = ModelUpdater()
        
        # Create a temporary SQL file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False, encoding='utf-8') as f:
            f.write('-- Test SQL schema file\n')
            temp_file = f.name
        
        try:
            # Create a simple schema
            schema = DatabaseSchema(
                tables={
                    'data_test_table': TableSchema(
                        name='data_test_table',
                        columns=[
                            ColumnSchema(name='id', data_type='int', nullable=False, is_identity=True),
                            ColumnSchema(name='name', data_type='nvarchar', nullable=False, max_length=100)
                        ],
                        primary_key=['id']
                    )
                }
            )
            
            # Update file
            result = updater.update_database_schema_sql(schema, temp_file, dry_run=False)
            
            assert result is True
            
            # Verify file was modified
            with open(temp_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert 'CREATE TABLE data_test_table' in content
            assert 'id INT IDENTITY(1,1) NOT NULL' in content
            assert 'name NVARCHAR(100) NOT NULL' in content
            assert 'CONSTRAINT PK_data_test_table PRIMARY KEY (id)' in content
        
        finally:
            # Clean up
            os.unlink(temp_file)
    
    def test_table_name_to_method_name(self):
        """Test conversion of table names to method names."""
        updater = ModelUpdater()
        
        assert updater._table_name_to_method_name('data_biodiesel_hip') == 'save_biodiesel_hip_data'
        assert updater._table_name_to_method_name('data_harga_ebt') == 'save_harga_ebt_data'
        assert updater._table_name_to_method_name('simple_table') == 'save_simple_table_data'
    
    def test_check_completeness(self):
        """Test checking for missing save methods."""
        updater = ModelUpdater()
        
        # Create handler content with some existing methods
        handler_content = """
        class DatabaseHandler:
            async def save_biodiesel_hip_data(self, data):
                pass
        """
        
        # Create structured tables
        structured_tables = {
            'data_biodiesel_hip': TableSchema(name='data_biodiesel_hip', columns=[]),
            'data_harga_ebt': TableSchema(name='data_harga_ebt', columns=[]),
            'data_bioetanol_hip': TableSchema(name='data_bioetanol_hip', columns=[])
        }
        
        # Check completeness
        missing = updater._check_completeness(handler_content, structured_tables)
        
        # Should find 2 missing methods
        assert len(missing) == 2
        assert 'data_harga_ebt' in missing
        assert 'data_bioetanol_hip' in missing
        assert 'data_biodiesel_hip' not in missing
    
    def test_generate_save_method(self):
        """Test generation of save method for a table."""
        updater = ModelUpdater()
        
        # Create a table schema
        table_schema = TableSchema(
            name='data_test_table',
            columns=[
                ColumnSchema(name='id', data_type='int', nullable=False, is_identity=True),
                ColumnSchema(name='name', data_type='nvarchar', nullable=False, max_length=100),
                ColumnSchema(name='value', data_type='float', nullable=True),
                ColumnSchema(name='created_at', data_type='datetime2', nullable=False)
            ]
        )
        
        method_code = updater._generate_save_method('data_test_table', table_schema)
        
        # Verify method structure
        assert 'async def save_test_table_data(self, data: List[DataTestTable]) -> int:' in method_code
        assert 'INSERT INTO data_test_table' in method_code
        assert 'name, value, created_at' in method_code  # Should exclude identity column
        assert 'item.name' in method_code
        assert 'item.value' in method_code
        assert 'item.created_at' in method_code
        assert 'item.id' not in method_code  # Identity column should be excluded
        assert 'cursor.executemany(insert_query, rows)' in method_code
        assert 'DatabaseError' in method_code
    
    def test_update_database_handler_dry_run(self):
        """Test updating database handler in dry-run mode."""
        updater = ModelUpdater()
        
        # Create a temporary handler file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write('"""Test database handler."""\n')
            f.write('class DatabaseHandler:\n')
            f.write('    async def close(self):\n')
            f.write('        pass\n')
            temp_file = f.name
        
        try:
            # Create a simple schema
            schema = DatabaseSchema(
                tables={
                    'data_test_table': TableSchema(
                        name='data_test_table',
                        columns=[
                            ColumnSchema(name='id', data_type='int', nullable=False, is_identity=True),
                            ColumnSchema(name='name', data_type='nvarchar', nullable=False, max_length=100)
                        ]
                    )
                }
            )
            
            # Update in dry-run mode
            result = updater.update_database_handler(schema, temp_file, dry_run=True)
            
            assert result is True
            
            # Verify file wasn't modified
            with open(temp_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert 'save_test_table_data' not in content
        
        finally:
            # Clean up
            os.unlink(temp_file)
    
    def test_update_database_handler_actual(self):
        """Test actually updating database handler."""
        updater = ModelUpdater()
        
        # Create a temporary handler file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write('"""Test database handler."""\n')
            f.write('from typing import List\n\n')
            f.write('class DatabaseHandler:\n')
            f.write('    async def close(self):\n')
            f.write('        pass\n')
            temp_file = f.name
        
        try:
            # Create a simple schema
            schema = DatabaseSchema(
                tables={
                    'data_test_table': TableSchema(
                        name='data_test_table',
                        columns=[
                            ColumnSchema(name='id', data_type='int', nullable=False, is_identity=True),
                            ColumnSchema(name='name', data_type='nvarchar', nullable=False, max_length=100)
                        ]
                    )
                }
            )
            
            # Update file
            result = updater.update_database_handler(schema, temp_file, dry_run=False)
            
            assert result is True
            
            # Verify file was modified
            with open(temp_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert 'async def save_test_table_data(self, data: List[DataTestTable]) -> int:' in content
            assert 'INSERT INTO data_test_table' in content
            assert 'Structured Data Save Methods (Auto-generated)' in content
        
        finally:
            # Clean up
            os.unlink(temp_file)
    
    def test_update_database_handler_no_missing_methods(self):
        """Test updating database handler when all methods already exist."""
        updater = ModelUpdater()
        
        # Create a temporary handler file with existing method
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write('"""Test database handler."""\n')
            f.write('class DatabaseHandler:\n')
            f.write('    async def save_test_table_data(self, data):\n')
            f.write('        pass\n')
            f.write('    async def close(self):\n')
            f.write('        pass\n')
            temp_file = f.name
        
        try:
            # Create a simple schema
            schema = DatabaseSchema(
                tables={
                    'data_test_table': TableSchema(
                        name='data_test_table',
                        columns=[
                            ColumnSchema(name='id', data_type='int', nullable=False, is_identity=True)
                        ]
                    )
                }
            )
            
            # Update file
            result = updater.update_database_handler(schema, temp_file, dry_run=False)
            
            assert result is True
            
            # Verify file wasn't modified (no duplicate methods added)
            with open(temp_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Should only have one occurrence of the method
            assert content.count('async def save_test_table_data') == 1
        
        finally:
            # Clean up
            os.unlink(temp_file)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

