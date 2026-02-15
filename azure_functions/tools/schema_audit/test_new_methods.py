"""
Test the newly implemented methods: _determine_severity() and generate_mismatch_report()
"""

import pytest
from datetime import datetime

from .models import (
    DatabaseSchema,
    TableSchema,
    ColumnSchema,
    TableOperation,
    OperationType,
    MismatchType,
    Severity,
    CodeLocation
)
from .mismatch_detector import MismatchDetector, CodeSchemaMap


def test_determine_severity():
    """Test the _determine_severity method"""
    ref_schema = DatabaseSchema(
        tables={},
        version='1.0',
        extracted_at=datetime.now(),
        source_file='test.bacpac'
    )
    detector = MismatchDetector(ref_schema)
    
    # Test critical types
    assert detector._determine_severity(MismatchType.MISSING_TABLE) == Severity.CRITICAL
    assert detector._determine_severity(MismatchType.MISSING_COLUMN) == Severity.CRITICAL
    assert detector._determine_severity(MismatchType.COLUMN_TYPE_MISMATCH) == Severity.CRITICAL
    
    # Test warning types
    assert detector._determine_severity(MismatchType.EXTRA_COLUMN) == Severity.WARNING
    assert detector._determine_severity(MismatchType.COLUMN_NAME_MISMATCH) == Severity.WARNING
    
    # Test info types
    assert detector._determine_severity(MismatchType.EXTRA_TABLE) == Severity.INFO


def test_generate_mismatch_report():
    """Test the generate_mismatch_report method"""
    ref_schema = DatabaseSchema(
        tables={
            'users': TableSchema(
                name='users',
                columns=[
                    ColumnSchema(name='id', data_type='INT', nullable=False),
                    ColumnSchema(name='username', data_type='VARCHAR', max_length=50, nullable=False),
                    ColumnSchema(name='email', data_type='VARCHAR', max_length=100, nullable=False),
                ]
            )
        },
        version='1.0',
        extracted_at=datetime.now(),
        source_file='test.bacpac'
    )
    
    code_schema = CodeSchemaMap(
        table_operations={
            'users': [
                TableOperation(
                    operation_type=OperationType.INSERT,
                    table_name='users',
                    columns=['id', 'username', 'phone'],  # 'phone' doesn't exist, 'email' missing
                    file_path='test.py',
                    line_number=10,
                    code_snippet='INSERT INTO users...'
                )
            ],
            'orders': [  # Table doesn't exist in reference
                TableOperation(
                    operation_type=OperationType.INSERT,
                    table_name='orders',
                    columns=['id', 'total'],
                    file_path='test.py',
                    line_number=20,
                    code_snippet='INSERT INTO orders...'
                )
            ]
        }
    )
    
    detector = MismatchDetector(ref_schema)
    mismatches = detector.compare_schemas(code_schema)
    
    # Generate report
    report = detector.generate_mismatch_report()
    
    # Verify report contains expected sections
    assert 'SCHEMA MISMATCH REPORT' in report
    assert 'Total Mismatches:' in report
    assert 'CRITICAL' in report
    assert 'WARNING' in report
    assert 'orders' in report  # Missing table
    assert 'phone' in report   # Missing column
    assert 'email' in report   # Extra column
    assert 'test.py' in report # File location
    
    # Verify report is not empty
    assert len(report) > 100
    
    # Test with no mismatches
    empty_schema = CodeSchemaMap(table_operations={})
    detector2 = MismatchDetector(ref_schema)
    detector2.compare_schemas(empty_schema)
    empty_report = detector2.generate_mismatch_report()
    assert 'No schema mismatches detected' in empty_report or len(detector2.mismatches) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
