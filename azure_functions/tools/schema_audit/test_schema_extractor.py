"""
Unit tests for SchemaExtractor export methods.
"""

import json
import sys
import tempfile
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from azure_functions.tools.schema_audit.schema_extractor import SchemaExtractor
from azure_functions.tools.schema_audit.models import DatabaseSchema, TableSchema, ColumnSchema, ForeignKeySchema, IndexSchema


def test_export_to_json():
    """Test JSON export functionality."""
    # Create a sample schema
    schema = DatabaseSchema(
        version="1.0",
        extracted_at=datetime(2024, 1, 1, 12, 0, 0),
        source_file="test.bacpac"
    )
    
    # Add a sample table
    table = TableSchema(name="test_table")
    table.columns.append(ColumnSchema(
        name="id",
        data_type="int",
        nullable=False,
        is_identity=True
    ))
    table.columns.append(ColumnSchema(
        name="name",
        data_type="nvarchar",
        nullable=True,
        max_length=100
    ))
    table.primary_key = ["id"]
    
    schema.tables["test_table"] = table
    
    # Export to JSON
    extractor = SchemaExtractor()
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "schema.json"
        extractor.export_to_json(schema, str(output_path))
        
        # Verify file was created
        assert output_path.exists()
        
        # Verify content
        with open(output_path, 'r') as f:
            data = json.load(f)
        
        assert data['version'] == "1.0"
        assert data['source_file'] == "test.bacpac"
        assert 'test_table' in data['tables']
        assert len(data['tables']['test_table']['columns']) == 2
        assert data['tables']['test_table']['columns'][0]['name'] == "id"
        assert data['tables']['test_table']['columns'][0]['is_identity'] is True
        assert data['tables']['test_table']['primary_key'] == ["id"]
    
    print("✓ test_export_to_json passed")


def test_export_to_markdown():
    """Test Markdown export functionality."""
    # Create a sample schema
    schema = DatabaseSchema(
        version="1.0",
        extracted_at=datetime(2024, 1, 1, 12, 0, 0),
        source_file="test.bacpac"
    )
    
    # Add a sample table (structured data table, not news table)
    table = TableSchema(name="data_test")
    table.columns.append(ColumnSchema(
        name="id",
        data_type="int",
        nullable=False,
        is_identity=True
    ))
    table.columns.append(ColumnSchema(
        name="value",
        data_type="decimal",
        nullable=True,
        precision=10,
        scale=2
    ))
    table.primary_key = ["id"]
    
    # Add a foreign key
    table.foreign_keys.append(ForeignKeySchema(
        name="FK_test",
        column="ref_id",
        referenced_table="other_table",
        referenced_column="id",
        on_delete="CASCADE"
    ))
    
    # Add an index
    table.indexes.append(IndexSchema(
        name="IX_value",
        columns=["value"],
        is_unique=False,
        is_clustered=False
    ))
    
    schema.tables["data_test"] = table
    
    # Export to Markdown
    extractor = SchemaExtractor()
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "schema.md"
        extractor.export_to_markdown(schema, str(output_path))
        
        # Verify file was created
        assert output_path.exists()
        
        # Verify content
        with open(output_path, 'r') as f:
            content = f.read()
        
        assert "# Database Schema Documentation" in content
        assert "data_test" in content
        assert "| id | int | No |" in content
        assert "| value | decimal(10,2) | Yes |" in content
        assert "### Primary Key" in content
        assert "### Foreign Keys" in content
        assert "FK_test" in content
        assert "### Indexes" in content
        assert "IX_value" in content
    
    print("✓ test_export_to_markdown passed")


def test_filter_structured_data_tables():
    """Test filtering of structured data tables."""
    # Create a schema with both news tables and structured data tables
    schema = DatabaseSchema()
    
    # Add news tables (should be filtered out)
    schema.tables["news_articles"] = TableSchema(name="news_articles")
    schema.tables["news_sources"] = TableSchema(name="news_sources")
    schema.tables["keywords"] = TableSchema(name="keywords")
    
    # Add structured data tables (should be included)
    schema.tables["data_biodiesel_hip"] = TableSchema(name="data_biodiesel_hip")
    schema.tables["data_bioetanol_hip"] = TableSchema(name="data_bioetanol_hip")
    
    # Filter
    extractor = SchemaExtractor()
    filtered = extractor._filter_structured_data_tables(schema)
    
    # Verify only structured data tables are included
    assert len(filtered) == 2
    assert "data_biodiesel_hip" in filtered
    assert "data_bioetanol_hip" in filtered
    assert "news_articles" not in filtered
    assert "news_sources" not in filtered
    assert "keywords" not in filtered
    
    print("✓ test_filter_structured_data_tables passed")


def test_markdown_excludes_news_tables():
    """Test that Markdown export excludes news tables."""
    # Create a schema with both types of tables
    schema = DatabaseSchema(
        version="1.0",
        extracted_at=datetime(2024, 1, 1, 12, 0, 0),
        source_file="test.bacpac"
    )
    
    # Add news table
    news_table = TableSchema(name="news_articles")
    news_table.columns.append(ColumnSchema(name="id", data_type="int", nullable=False))
    schema.tables["news_articles"] = news_table
    
    # Add structured data table
    data_table = TableSchema(name="data_test")
    data_table.columns.append(ColumnSchema(name="id", data_type="int", nullable=False))
    schema.tables["data_test"] = data_table
    
    # Export to Markdown
    extractor = SchemaExtractor()
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "schema.md"
        extractor.export_to_markdown(schema, str(output_path))
        
        # Verify content
        with open(output_path, 'r') as f:
            content = f.read()
        
        # Should include data_test but not news_articles
        assert "data_test" in content
        assert "news_articles" not in content
        assert "**Total Tables:** 1" in content  # Only 1 structured data table
    
    print("✓ test_markdown_excludes_news_tables passed")


if __name__ == "__main__":
    test_export_to_json()
    test_export_to_markdown()
    test_filter_structured_data_tables()
    test_markdown_excludes_news_tables()
    print("\n✅ All tests passed!")
