"""
Unit tests for MismatchDetector.

Tests the detection of schema mismatches between reference schema and code usage.
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


class TestMismatchDetector:
    """Test suite for MismatchDetector"""
    
    def setup_method(self):
        """Setup test fixtures"""
        # Create a reference schema with two tables
        self.ref_schema = DatabaseSchema(
            tables={
                'users': TableSchema(
                    name='users',
                    columns=[
                        ColumnSchema(name='id', data_type='INT', nullable=False),
                        ColumnSchema(name='username', data_type='VARCHAR', max_length=50, nullable=False),
                        ColumnSchema(name='email', data_type='VARCHAR', max_length=100, nullable=False),
                        ColumnSchema(name='created_at', data_type='DATETIME', nullable=False)
                    ]
                ),
                'products': TableSchema(
                    name='products',
                    columns=[
                        ColumnSchema(name='id', data_type='INT', nullable=False),
                        ColumnSchema(name='name', data_type='VARCHAR', max_length=100, nullable=False),
                        ColumnSchema(name='price', data_type='DECIMAL', precision=10, scale=2, nullable=False)
                    ]
                )
            },
            version='1.0',
            extracted_at=datetime.now(),
            source_file='test.bacpac'
        )
        
        self.detector = MismatchDetector(self.ref_schema)
    
    def test_no_mismatches_when_schemas_match(self):
        """Test that no mismatches are found when code matches reference"""
        code_schema = CodeSchemaMap(
            table_operations={
                'users': [
                    TableOperation(
                        operation_type=OperationType.INSERT,
                        table_name='users',
                        columns=['id', 'username', 'email', 'created_at'],
                        file_path='test.py',
                        line_number=10
                    )
                ],
                'products': [
                    TableOperation(
                        operation_type=OperationType.INSERT,
                        table_name='products',
                        columns=['id', 'name', 'price'],
                        file_path='test.py',
                        line_number=20
                    )
                ]
            }
        )
        
        mismatches = self.detector.compare_schemas(code_schema)
        
        # Should have no critical mismatches (only INFO for unused columns if any)
        critical = [m for m in mismatches if m.severity == Severity.CRITICAL]
        assert len(critical) == 0
    
    def test_detect_missing_table(self):
        """Test detection of table in code but not in reference"""
        code_schema = CodeSchemaMap(
            table_operations={
                'users': [
                    TableOperation(
                        operation_type=OperationType.INSERT,
                        table_name='users',
                        columns=['id', 'username'],
                        file_path='test.py',
                        line_number=10
                    )
                ],
                'orders': [  # This table doesn't exist in reference
                    TableOperation(
                        operation_type=OperationType.INSERT,
                        table_name='orders',
                        columns=['id', 'user_id', 'total'],
                        file_path='test.py',
                        line_number=20
                    )
                ]
            }
        )
        
        mismatches = self.detector.compare_schemas(code_schema)
        
        # Should detect missing table
        missing_tables = [m for m in mismatches if m.mismatch_type == MismatchType.MISSING_TABLE]
        assert len(missing_tables) == 1
        assert missing_tables[0].table_name == 'orders'
        assert missing_tables[0].severity == Severity.CRITICAL
    
    def test_detect_extra_table(self):
        """Test detection of table in reference but not used in code"""
        code_schema = CodeSchemaMap(
            table_operations={
                'users': [
                    TableOperation(
                        operation_type=OperationType.INSERT,
                        table_name='users',
                        columns=['id', 'username'],
                        file_path='test.py',
                        line_number=10
                    )
                ]
                # 'products' table is not used
            }
        )
        
        mismatches = self.detector.compare_schemas(code_schema)
        
        # Should detect extra table
        extra_tables = [m for m in mismatches if m.mismatch_type == MismatchType.EXTRA_TABLE]
        assert len(extra_tables) == 1
        assert extra_tables[0].table_name == 'products'
        assert extra_tables[0].severity == Severity.INFO
    
    def test_detect_missing_column(self):
        """Test detection of column in code but not in reference"""
        code_schema = CodeSchemaMap(
            table_operations={
                'users': [
                    TableOperation(
                        operation_type=OperationType.INSERT,
                        table_name='users',
                        columns=['id', 'username', 'email', 'phone'],  # 'phone' doesn't exist
                        file_path='test.py',
                        line_number=10
                    )
                ]
            }
        )
        
        mismatches = self.detector.compare_schemas(code_schema)
        
        # Should detect missing column
        missing_cols = [m for m in mismatches if m.mismatch_type == MismatchType.MISSING_COLUMN]
        assert len(missing_cols) == 1
        assert missing_cols[0].column_name == 'phone'
        assert missing_cols[0].table_name == 'users'
        assert missing_cols[0].severity == Severity.CRITICAL
    
    def test_detect_extra_column(self):
        """Test detection of column in reference but not used in code"""
        code_schema = CodeSchemaMap(
            table_operations={
                'users': [
                    TableOperation(
                        operation_type=OperationType.INSERT,
                        table_name='users',
                        columns=['id', 'username'],  # Missing 'email' and 'created_at'
                        file_path='test.py',
                        line_number=10
                    )
                ]
            }
        )
        
        mismatches = self.detector.compare_schemas(code_schema)
        
        # Should detect extra columns
        extra_cols = [m for m in mismatches if m.mismatch_type == MismatchType.EXTRA_COLUMN]
        assert len(extra_cols) == 2  # 'email' and 'created_at'
        extra_col_names = {m.column_name for m in extra_cols}
        assert 'email' in extra_col_names
        assert 'created_at' in extra_col_names
        assert all(m.severity == Severity.WARNING for m in extra_cols)
    
    def test_case_insensitive_comparison(self):
        """Test that table and column comparisons are case-insensitive"""
        code_schema = CodeSchemaMap(
            table_operations={
                'USERS': [  # Different case
                    TableOperation(
                        operation_type=OperationType.INSERT,
                        table_name='USERS',
                        columns=['ID', 'USERNAME', 'EMAIL', 'CREATED_AT'],  # Different case
                        file_path='test.py',
                        line_number=10
                    )
                ]
            }
        )
        
        mismatches = self.detector.compare_schemas(code_schema)
        
        # Should not detect mismatches due to case differences
        critical = [m for m in mismatches if m.severity == Severity.CRITICAL]
        assert len(critical) == 0
    
    def test_categorize_by_severity(self):
        """Test categorization of mismatches by severity"""
        code_schema = CodeSchemaMap(
            table_operations={
                'users': [
                    TableOperation(
                        operation_type=OperationType.INSERT,
                        table_name='users',
                        columns=['id', 'username', 'phone'],  # 'phone' is missing (CRITICAL)
                        file_path='test.py',
                        line_number=10
                    )
                ],
                'orders': [  # Missing table (CRITICAL)
                    TableOperation(
                        operation_type=OperationType.INSERT,
                        table_name='orders',
                        columns=['id'],
                        file_path='test.py',
                        line_number=20
                    )
                ]
                # 'products' not used (INFO)
            }
        )
        
        mismatches = self.detector.compare_schemas(code_schema)
        categorized = self.detector.categorize_by_severity(mismatches)
        
        assert len(categorized['CRITICAL']) >= 2  # Missing table + missing column
        assert len(categorized['INFO']) >= 1  # Extra table
    
    def test_group_by_table(self):
        """Test grouping of mismatches by table"""
        code_schema = CodeSchemaMap(
            table_operations={
                'users': [
                    TableOperation(
                        operation_type=OperationType.INSERT,
                        table_name='users',
                        columns=['id', 'username', 'phone'],  # Missing column
                        file_path='test.py',
                        line_number=10
                    )
                ]
            }
        )
        
        mismatches = self.detector.compare_schemas(code_schema)
        grouped = self.detector.group_by_table(mismatches)
        
        assert 'users' in grouped
        assert len(grouped['users']) >= 1
    
    def test_get_critical_mismatches(self):
        """Test retrieval of only critical mismatches"""
        code_schema = CodeSchemaMap(
            table_operations={
                'users': [
                    TableOperation(
                        operation_type=OperationType.INSERT,
                        table_name='users',
                        columns=['id', 'username', 'phone'],  # Missing column (CRITICAL)
                        file_path='test.py',
                        line_number=10
                    )
                ]
                # 'products' not used (INFO)
            }
        )
        
        self.detector.compare_schemas(code_schema)
        critical = self.detector.get_critical_mismatches()
        
        assert all(m.severity == Severity.CRITICAL for m in critical)
        assert len(critical) >= 1
    
    def test_get_summary(self):
        """Test summary statistics generation"""
        code_schema = CodeSchemaMap(
            table_operations={
                'users': [
                    TableOperation(
                        operation_type=OperationType.INSERT,
                        table_name='users',
                        columns=['id', 'username', 'phone'],
                        file_path='test.py',
                        line_number=10
                    )
                ]
            }
        )
        
        self.detector.compare_schemas(code_schema)
        summary = self.detector.get_summary()
        
        assert 'total' in summary
        assert 'critical' in summary
        assert 'warning' in summary
        assert 'info' in summary
        assert summary['total'] >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
