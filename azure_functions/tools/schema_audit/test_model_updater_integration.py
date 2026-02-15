"""
Integration test for ModelUpdater with realistic schema.
"""

import pytest
from datetime import datetime
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


def test_model_updater_with_realistic_schema():
    """Test ModelUpdater with a realistic structured data table schema."""
    
    # Create a realistic schema similar to data_biodiesel_hip or data_harga_ebt
    schema = DatabaseSchema(
        tables={
            # Standard news table (should be excluded)
            'news_articles': TableSchema(
                name='news_articles',
                columns=[
                    ColumnSchema(name='id', data_type='uniqueidentifier', nullable=False),
                    ColumnSchema(name='title', data_type='nvarchar', nullable=False, max_length=500)
                ]
            ),
            # Structured data table (should be included)
            'data_biodiesel_hip': TableSchema(
                name='data_biodiesel_hip',
                columns=[
                    ColumnSchema(name='id', data_type='int', nullable=False, is_identity=True),
                    ColumnSchema(name='tanggal', data_type='date', nullable=False),
                    ColumnSchema(name='harga', data_type='decimal', nullable=False, precision=18, scale=2),
                    ColumnSchema(name='volume', data_type='float', nullable=True),
                    ColumnSchema(name='keterangan', data_type='nvarchar', nullable=True, max_length=500),
                    ColumnSchema(name='created_at', data_type='datetime2', nullable=False, 
                               default_value='GETUTCDATE()'),
                    ColumnSchema(name='updated_at', data_type='datetime2', nullable=False,
                               default_value='GETUTCDATE()')
                ],
                primary_key=['id']
            ),
            # Another structured data table
            'data_harga_ebt': TableSchema(
                name='data_harga_ebt',
                columns=[
                    ColumnSchema(name='id', data_type='int', nullable=False, is_identity=True),
                    ColumnSchema(name='jenis_energi', data_type='nvarchar', nullable=False, max_length=100),
                    ColumnSchema(name='harga_per_kwh', data_type='decimal', nullable=False, precision=10, scale=4),
                    ColumnSchema(name='tanggal_berlaku', data_type='date', nullable=False),
                    ColumnSchema(name='wilayah', data_type='nvarchar', nullable=True, max_length=200),
                    ColumnSchema(name='is_active', data_type='bit', nullable=False, default_value='1'),
                    ColumnSchema(name='created_at', data_type='datetime2', nullable=False,
                               default_value='GETUTCDATE()')
                ],
                primary_key=['id']
            )
        }
    )
    
    updater = ModelUpdater()
    
    # Test 1: Verify structured data tables are correctly identified
    structured_tables = updater._get_structured_data_tables(schema)
    assert len(structured_tables) == 2
    assert 'data_biodiesel_hip' in structured_tables
    assert 'data_harga_ebt' in structured_tables
    assert 'news_articles' not in structured_tables
    
    # Test 2: Generate dataclass for data_biodiesel_hip
    biodiesel_dataclass = updater._generate_dataclass(
        'data_biodiesel_hip',
        schema.tables['data_biodiesel_hip']
    )
    
    print("\n=== Generated DataBiodieselHip Dataclass ===")
    print(biodiesel_dataclass)
    
    assert '@dataclass' in biodiesel_dataclass
    assert 'class DataBiodieselHip:' in biodiesel_dataclass
    assert 'id: Optional[int]' in biodiesel_dataclass
    assert 'tanggal: datetime' in biodiesel_dataclass
    assert 'harga: float' in biodiesel_dataclass
    assert 'volume: Optional[float]' in biodiesel_dataclass
    assert 'keterangan: Optional[str]' in biodiesel_dataclass
    
    # Test 3: Generate CREATE TABLE SQL for data_harga_ebt
    harga_ebt_sql = updater._generate_create_table_sql(
        'data_harga_ebt',
        schema.tables['data_harga_ebt']
    )
    
    print("\n=== Generated data_harga_ebt CREATE TABLE ===")
    print(harga_ebt_sql)
    
    assert 'CREATE TABLE data_harga_ebt' in harga_ebt_sql
    assert 'id INT IDENTITY(1,1) NOT NULL' in harga_ebt_sql
    assert 'jenis_energi NVARCHAR(100) NOT NULL' in harga_ebt_sql
    assert 'harga_per_kwh DECIMAL(10,4) NOT NULL' in harga_ebt_sql
    assert 'is_active BIT NOT NULL DEFAULT 1' in harga_ebt_sql
    assert 'CONSTRAINT PK_data_harga_ebt PRIMARY KEY (id)' in harga_ebt_sql
    
    # Test 4: Test full models.py update
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write('"""Shared data models."""\n')
        f.write('from dataclasses import dataclass, field\n')
        f.write('from datetime import datetime\n')
        f.write('from typing import Optional\n\n')
        f.write('# Existing models\n')
        f.write('@dataclass\n')
        f.write('class NewsArticle:\n')
        f.write('    title: str\n')
        f.write('    content: str\n')
        models_file = f.name
    
    try:
        result = updater.update_models_file(schema, models_file, dry_run=False)
        assert result is True
        
        with open(models_file, 'r', encoding='utf-8') as f:
            models_content = f.read()
        
        print("\n=== Updated models.py content (excerpt) ===")
        # Print only the auto-generated section
        if 'Structured Data Models' in models_content:
            auto_gen_section = models_content.split('Structured Data Models')[1]
            print(auto_gen_section[:500])
        
        assert 'class DataBiodieselHip:' in models_content
        assert 'class DataHargaEbt:' in models_content
        assert 'NewsArticle' in models_content  # Existing class preserved
        
    finally:
        os.unlink(models_file)
    
    # Test 5: Test full database_schema.sql update
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False, encoding='utf-8') as f:
        f.write('-- Existing SQL schema\n')
        f.write('CREATE TABLE news_articles (\n')
        f.write('    id UNIQUEIDENTIFIER PRIMARY KEY,\n')
        f.write('    title NVARCHAR(500) NOT NULL\n')
        f.write(');\n')
        sql_file = f.name
    
    try:
        result = updater.update_database_schema_sql(schema, sql_file, dry_run=False)
        assert result is True
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        print("\n=== Updated database_schema.sql content (excerpt) ===")
        # Print only the auto-generated section
        if 'Structured Data Tables' in sql_content:
            auto_gen_section = sql_content.split('Structured Data Tables')[1]
            print(auto_gen_section[:500])
        
        assert 'CREATE TABLE data_biodiesel_hip' in sql_content
        assert 'CREATE TABLE data_harga_ebt' in sql_content
        assert 'CREATE TABLE news_articles' in sql_content  # Existing table preserved
        
    finally:
        os.unlink(sql_file)
    
    print("\n=== Integration test completed successfully ===")


if __name__ == '__main__':
    test_model_updater_with_realistic_schema()
