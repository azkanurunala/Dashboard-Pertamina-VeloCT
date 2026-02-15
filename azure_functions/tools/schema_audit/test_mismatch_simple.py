"""
Simple integration test for MismatchDetector.
"""

import sys
import os

# Add parent directory to path for proper imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from datetime import datetime
from azure_functions.tools.schema_audit.models import (
    DatabaseSchema,
    TableSchema,
    ColumnSchema,
    TableOperation,
    OperationType
)
from azure_functions.tools.schema_audit.mismatch_detector import MismatchDetector, CodeSchemaMap


def test_basic_functionality():
    """Test basic mismatch detection"""
    print("Testing MismatchDetector...")
    
    # Create reference schema
    ref_schema = DatabaseSchema(
        tables={
            'users': TableSchema(
                name='users',
                columns=[
                    ColumnSchema(name='id', data_type='INT'),
                    ColumnSchema(name='username', data_type='VARCHAR'),
                    ColumnSchema(name='email', data_type='VARCHAR')
                ]
            )
        }
    )
    
    # Create code schema with a missing column
    code_schema = CodeSchemaMap(
        table_operations={
            'users': [
                TableOperation(
                    operation_type=OperationType.INSERT,
                    table_name='users',
                    columns=['id', 'username', 'phone'],  # 'phone' doesn't exist, 'email' is missing
                    file_path='test.py',
                    line_number=10
                )
            ]
        }
    )
    
    # Run detection
    detector = MismatchDetector(ref_schema)
    mismatches = detector.compare_schemas(code_schema)
    
    print(f"✓ Found {len(mismatches)} mismatches")
    
    # Check for missing column
    missing_cols = [m for m in mismatches if m.column_name == 'phone']
    assert len(missing_cols) > 0, "Should detect missing column 'phone'"
    print(f"✓ Detected missing column: {missing_cols[0].column_name}")
    
    # Check for extra column
    extra_cols = [m for m in mismatches if m.column_name == 'email']
    assert len(extra_cols) > 0, "Should detect extra column 'email'"
    print(f"✓ Detected extra column: {extra_cols[0].column_name}")
    
    # Test categorization
    categorized = detector.categorize_by_severity()
    print(f"✓ Categorized: CRITICAL={len(categorized['CRITICAL'])}, WARNING={len(categorized['WARNING'])}, INFO={len(categorized['INFO'])}")
    
    # Test grouping
    grouped = detector.group_by_table()
    assert 'users' in grouped
    print(f"✓ Grouped by table: {list(grouped.keys())}")
    
    # Test summary
    summary = detector.get_summary()
    print(f"✓ Summary: {summary}")
    
    print("\n✅ All tests passed!")


if __name__ == '__main__':
    test_basic_functionality()
