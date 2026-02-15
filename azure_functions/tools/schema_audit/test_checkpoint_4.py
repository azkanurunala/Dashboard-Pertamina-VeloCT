"""
Checkpoint 4: Verify schema extraction works with actual BACPAC file.

This test script:
1. Extracts schema from pei-dashboard.bacpac
2. Verifies extracted schema completeness
3. Generates documentation
4. Reports findings
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from azure_functions.tools.schema_audit.schema_extractor import SchemaExtractor
from azure_functions.tools.schema_audit.models import DatabaseSchema


def test_bacpac_extraction():
    """Test extraction from actual pei-dashboard.bacpac file."""
    print("=" * 80)
    print("CHECKPOINT 4: Schema Extraction Verification")
    print("=" * 80)
    print()
    
    # Path to BACPAC file
    bacpac_path = "pei-dashboard.bacpac"
    
    if not Path(bacpac_path).exists():
        print(f"❌ ERROR: BACPAC file not found at {bacpac_path}")
        return False
    
    print(f"✓ Found BACPAC file: {bacpac_path}")
    print()
    
    # Create extractor
    extractor = SchemaExtractor()
    
    # Extract schema
    print("Extracting schema from BACPAC...")
    try:
        schema = extractor.extract_from_bacpac(bacpac_path)
        print(f"✓ Successfully extracted schema")
        print()
    except Exception as e:
        print(f"❌ ERROR: Failed to extract schema: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Verify schema completeness
    print("=" * 80)
    print("SCHEMA COMPLETENESS VERIFICATION")
    print("=" * 80)
    print()
    
    print(f"Total tables extracted: {len(schema.tables)}")
    print(f"Source file: {schema.source_file}")
    print(f"Extracted at: {schema.extracted_at}")
    print(f"Version: {schema.version}")
    print()
    
    # List all tables
    print("All tables:")
    for table_name in sorted(schema.tables.keys()):
        table = schema.tables[table_name]
        print(f"  - {table_name} ({len(table.columns)} columns)")
    print()
    
    # Get structured data tables
    structured_tables = schema.get_structured_data_tables()
    print(f"Structured data tables (excluding news tables): {len(structured_tables)}")
    for table_name in sorted(structured_tables.keys()):
        table = structured_tables[table_name]
        print(f"  - {table_name} ({len(table.columns)} columns)")
    print()
    
    # Verify table details for a few key tables
    print("=" * 80)
    print("DETAILED TABLE VERIFICATION")
    print("=" * 80)
    print()
    
    # Check for expected structured data tables
    expected_tables = [
        "data_biodiesel_hip",
        "data_bioetanol_hip",
        "data_harga_ebt"
    ]
    
    for table_name in expected_tables:
        if table_name in schema.tables:
            table = schema.tables[table_name]
            print(f"✓ Table '{table_name}' found")
            print(f"  Columns: {len(table.columns)}")
            print(f"  Primary key: {table.primary_key}")
            print(f"  Foreign keys: {len(table.foreign_keys)}")
            print(f"  Indexes: {len(table.indexes)}")
            print(f"  Constraints: {len(table.constraints)}")
            
            # Show column details
            print(f"  Column details:")
            for col in table.columns[:5]:  # Show first 5 columns
                type_str = col.data_type
                if col.max_length:
                    type_str += f"({col.max_length})"
                elif col.precision and col.scale is not None:
                    type_str += f"({col.precision},{col.scale})"
                nullable = "NULL" if col.nullable else "NOT NULL"
                identity = " IDENTITY" if col.is_identity else ""
                print(f"    - {col.name}: {type_str} {nullable}{identity}")
            if len(table.columns) > 5:
                print(f"    ... and {len(table.columns) - 5} more columns")
            print()
        else:
            print(f"⚠ Table '{table_name}' not found in schema")
            print()
    
    # Generate documentation
    print("=" * 80)
    print("DOCUMENTATION GENERATION")
    print("=" * 80)
    print()
    
    output_dir = Path("azure_functions/tools/schema_audit/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Export to JSON
    json_path = output_dir / "schema.json"
    print(f"Exporting schema to JSON: {json_path}")
    try:
        extractor.export_to_json(schema, str(json_path))
        print(f"✓ JSON export successful ({json_path.stat().st_size} bytes)")
    except Exception as e:
        print(f"❌ ERROR: JSON export failed: {e}")
        return False
    print()
    
    # Export to Markdown
    md_path = output_dir / "schema.md"
    print(f"Exporting schema to Markdown: {md_path}")
    try:
        extractor.export_to_markdown(schema, str(md_path))
        print(f"✓ Markdown export successful ({md_path.stat().st_size} bytes)")
    except Exception as e:
        print(f"❌ ERROR: Markdown export failed: {e}")
        return False
    print()
    
    # Validate schema
    print("=" * 80)
    print("SCHEMA VALIDATION")
    print("=" * 80)
    print()
    
    if schema.validate():
        print("✓ Schema validation passed")
    else:
        print("❌ Schema validation failed")
        return False
    print()
    
    # Summary
    print("=" * 80)
    print("CHECKPOINT 4 SUMMARY")
    print("=" * 80)
    print()
    print(f"✓ Schema extraction: SUCCESS")
    print(f"✓ Total tables: {len(schema.tables)}")
    print(f"✓ Structured data tables: {len(structured_tables)}")
    print(f"✓ JSON documentation: {json_path}")
    print(f"✓ Markdown documentation: {md_path}")
    print(f"✓ Schema validation: PASSED")
    print()
    print("=" * 80)
    print("✅ CHECKPOINT 4: ALL TESTS PASSED")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    success = test_bacpac_extraction()
    sys.exit(0 if success else 1)
