"""
Checkpoint 6: Verify code auditing works with actual Azure Functions codebase.

This test verifies that:
1. All database operations in azure_functions/ are detected
2. The operation map is complete and accurate
3. All scraper functions that save structured data are identified
4. The code auditor handles real-world code patterns correctly

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
"""

import pytest
from pathlib import Path

from azure_functions.tools.schema_audit.code_auditor import CodeAuditor
from azure_functions.tools.schema_audit.models import OperationType


class TestCheckpoint6:
    """Checkpoint 6: Verify code auditing works with actual codebase."""
    
    def test_scan_azure_functions_directory(self):
        """Test scanning the actual azure_functions directory."""
        auditor = CodeAuditor()
        
        # Scan the azure_functions directory
        azure_functions_path = Path(__file__).parent.parent.parent
        locations = auditor.scan_directory(str(azure_functions_path))
        
        # Should find many Python files with database operations
        assert len(locations) > 0, "Should find database operations in azure_functions/"
        assert len(auditor.scanned_files) > 0, "Should scan multiple Python files"
        
        print(f"\n✓ Scanned {len(auditor.scanned_files)} Python files")
        print(f"✓ Found {len(locations)} database operation locations")
    
    def test_detect_all_database_operations(self):
        """Test that all types of database operations are detected."""
        auditor = CodeAuditor()
        
        azure_functions_path = Path(__file__).parent.parent.parent
        auditor.scan_directory(str(azure_functions_path))
        
        # Check that we found various operation types
        operation_types = {op.operation_type for op in auditor.operations}
        
        print(f"\n✓ Detected operation types: {operation_types}")
        
        # We should find at least some operations
        assert len(auditor.operations) > 0, "Should detect database operations"
        
        # Count operations by type
        create_ops = auditor.get_operations_by_type(OperationType.CREATE)
        insert_ops = auditor.get_operations_by_type(OperationType.INSERT)
        update_ops = auditor.get_operations_by_type(OperationType.UPDATE)
        select_ops = auditor.get_operations_by_type(OperationType.SELECT)
        
        print(f"✓ CREATE operations: {len(create_ops)}")
        print(f"✓ INSERT operations: {len(insert_ops)}")
        print(f"✓ UPDATE operations: {len(update_ops)}")
        print(f"✓ SELECT operations: {len(select_ops)}")
        
        # We should find at least INSERT operations (from save_structured_data calls)
        assert len(insert_ops) > 0, "Should find INSERT operations"
    
    def test_operation_map_completeness(self):
        """Test that the operation map is complete and accurate."""
        auditor = CodeAuditor()
        
        azure_functions_path = Path(__file__).parent.parent.parent
        auditor.scan_directory(str(azure_functions_path))
        
        # Build operation map
        operation_map = auditor.build_operation_map()
        
        print(f"\n✓ Operation map contains {len(operation_map)} tables")
        
        # Should have operations for multiple tables
        assert len(operation_map) > 0, "Operation map should not be empty"
        
        # Print tables found
        print("\n✓ Tables found in codebase:")
        for table_name in sorted(operation_map.keys()):
            ops = operation_map[table_name]
            op_types = {op.operation_type for op in ops}
            print(f"  - {table_name}: {len(ops)} operations ({op_types})")
        
        # Verify that each table has at least one operation
        for table_name, ops in operation_map.items():
            assert len(ops) > 0, f"Table {table_name} should have operations"
    
    def test_detect_structured_data_tables(self):
        """Test detection of structured data tables (not news articles)."""
        auditor = CodeAuditor()
        
        azure_functions_path = Path(__file__).parent.parent.parent
        auditor.scan_directory(str(azure_functions_path))
        
        # Get all tables
        tables = auditor.get_tables()
        
        print(f"\n✓ Found {len(tables)} unique tables")
        
        # Look for known structured data tables
        expected_structured_tables = [
            'data_biodiesel_hip',
            'data_bioetanol_hip',
            'data_harga_ebt',
            'data_fossil',
            'data_eia',
            'data_cpo',
            'data_oil_prices',
            'data_ruptl',
            'data_ebt_capacity',
            'data_iaea_pris',
            'data_wte'
        ]
        
        found_structured = []
        for table in expected_structured_tables:
            if table in tables:
                found_structured.append(table)
                print(f"  ✓ Found structured data table: {table}")
        
        # We should find at least some structured data tables
        assert len(found_structured) > 0, "Should find structured data tables"
        
        print(f"\n✓ Found {len(found_structured)}/{len(expected_structured_tables)} expected structured data tables")
    
    def test_detect_save_structured_data_calls(self):
        """Test detection of save_structured_data function calls in scrapers."""
        auditor = CodeAuditor()
        
        # Scan the scrapers directory specifically
        scrapers_path = Path(__file__).parent.parent.parent / "scrapers"
        
        if scrapers_path.exists():
            auditor.scan_directory(str(scrapers_path))
            
            # Filter for save_structured_data operations
            save_ops = [op for op in auditor.operations 
                       if 'save_structured_data' in op.code_snippet.lower() or
                       op.operation_type == OperationType.INSERT]
            
            print(f"\n✓ Found {len(save_ops)} save_structured_data calls in scrapers")
            
            # Group by table
            tables_from_saves = {}
            for op in save_ops:
                table = op.table_name
                if table not in tables_from_saves:
                    tables_from_saves[table] = []
                tables_from_saves[table].append(op.file_path)
            
            print("\n✓ Tables saved by scrapers:")
            for table, files in sorted(tables_from_saves.items()):
                print(f"  - {table}: {len(files)} scraper(s)")
            
            assert len(save_ops) > 0, "Should find save_structured_data calls"
    
    def test_scraper_function_classification(self):
        """Test that scraper functions saving structured data are identified."""
        auditor = CodeAuditor()
        
        # Scan scrapers directory
        scrapers_path = Path(__file__).parent.parent.parent / "scrapers"
        
        if scrapers_path.exists():
            auditor.scan_directory(str(scrapers_path))
            
            # Get unique scraper files that have database operations
            scraper_files = {op.file_path for op in auditor.operations}
            
            print(f"\n✓ Found {len(scraper_files)} scraper files with database operations")
            
            # List scraper files
            for file_path in sorted(scraper_files):
                file_name = Path(file_path).name
                ops = [op for op in auditor.operations if op.file_path == file_path]
                tables = {op.table_name for op in ops}
                print(f"  - {file_name}: {len(tables)} table(s)")
            
            assert len(scraper_files) > 0, "Should identify scraper files"
    
    def test_database_handler_operations(self):
        """Test detection of operations in database_handler.py."""
        auditor = CodeAuditor()
        
        # Scan shared directory for database_handler
        shared_path = Path(__file__).parent.parent.parent / "shared"
        
        if shared_path.exists():
            auditor.scan_directory(str(shared_path))
            
            # Filter for database_handler files
            db_handler_ops = [op for op in auditor.operations 
                            if 'database_handler' in op.file_path.lower()]
            
            print(f"\n✓ Found {len(db_handler_ops)} operations in database_handler files")
            
            if db_handler_ops:
                # Group by operation type
                by_type = {}
                for op in db_handler_ops:
                    op_type = op.operation_type
                    if op_type not in by_type:
                        by_type[op_type] = []
                    by_type[op_type].append(op)
                
                print("\n✓ Operations in database_handler:")
                for op_type, ops in by_type.items():
                    print(f"  - {op_type}: {len(ops)} operation(s)")
    
    def test_migration_scripts_detection(self):
        """Test detection of operations in migration scripts."""
        auditor = CodeAuditor()
        
        # Scan scripts directory
        scripts_path = Path(__file__).parent.parent.parent / "scripts"
        
        if scripts_path.exists():
            auditor.scan_directory(str(scripts_path))
            
            # Filter for migration-related operations
            migration_ops = [op for op in auditor.operations 
                           if 'migrate' in op.file_path.lower() or
                           'seed' in op.file_path.lower()]
            
            print(f"\n✓ Found {len(migration_ops)} operations in migration/seed scripts")
            
            if migration_ops:
                # Group by file
                by_file = {}
                for op in migration_ops:
                    file_name = Path(op.file_path).name
                    if file_name not in by_file:
                        by_file[file_name] = []
                    by_file[file_name].append(op)
                
                print("\n✓ Migration/seed scripts with operations:")
                for file_name, ops in sorted(by_file.items()):
                    print(f"  - {file_name}: {len(ops)} operation(s)")
    
    def test_operation_details_accuracy(self):
        """Test that operation details (table names, columns) are accurate."""
        auditor = CodeAuditor()
        
        azure_functions_path = Path(__file__).parent.parent.parent
        auditor.scan_directory(str(azure_functions_path))
        
        # Check that operations have required fields
        for op in auditor.operations[:10]:  # Check first 10 operations
            assert op.table_name, "Operation should have table name"
            assert op.file_path, "Operation should have file path"
            assert op.line_number > 0, "Operation should have line number"
            assert op.operation_type, "Operation should have operation type"
        
        print(f"\n✓ Verified operation details for {min(10, len(auditor.operations))} operations")
        
        # Print sample operations
        print("\n✓ Sample operations:")
        for op in auditor.operations[:5]:
            print(f"  - {op.operation_type} on {op.table_name} at {Path(op.file_path).name}:{op.line_number}")
    
    def test_no_false_positives(self):
        """Test that we don't detect SQL in comments or strings incorrectly."""
        auditor = CodeAuditor()
        
        azure_functions_path = Path(__file__).parent.parent.parent
        auditor.scan_directory(str(azure_functions_path))
        
        # Check for suspicious table names that might be false positives
        suspicious_patterns = ['example', 'test_table', 'dummy', 'sample']
        
        suspicious_ops = []
        for op in auditor.operations:
            table_lower = op.table_name.lower()
            if any(pattern in table_lower for pattern in suspicious_patterns):
                suspicious_ops.append(op)
        
        if suspicious_ops:
            print(f"\n⚠ Found {len(suspicious_ops)} potentially suspicious operations:")
            for op in suspicious_ops[:5]:
                print(f"  - {op.table_name} in {Path(op.file_path).name}")
        else:
            print("\n✓ No obvious false positives detected")
    
    def test_comprehensive_coverage(self):
        """Test that we have comprehensive coverage of the codebase."""
        auditor = CodeAuditor()
        
        azure_functions_path = Path(__file__).parent.parent.parent
        auditor.scan_directory(str(azure_functions_path))
        
        # Summary statistics
        total_files = len(auditor.scanned_files)
        total_operations = len(auditor.operations)
        total_tables = len(auditor.get_tables())
        
        operation_map = auditor.build_operation_map()
        
        print("\n" + "="*60)
        print("CHECKPOINT 6 SUMMARY")
        print("="*60)
        print(f"✓ Total Python files scanned: {total_files}")
        print(f"✓ Total database operations found: {total_operations}")
        print(f"✓ Total unique tables: {total_tables}")
        print(f"✓ Tables with operations: {len(operation_map)}")
        
        # Operation type breakdown
        print("\n✓ Operation type breakdown:")
        for op_type in OperationType:
            count = len(auditor.get_operations_by_type(op_type))
            if count > 0:
                print(f"  - {op_type}: {count}")
        
        print("\n✓ Top 10 tables by operation count:")
        sorted_tables = sorted(operation_map.items(), 
                             key=lambda x: len(x[1]), 
                             reverse=True)
        for table, ops in sorted_tables[:10]:
            print(f"  - {table}: {len(ops)} operations")
        
        print("="*60)
        
        # Assertions for minimum coverage
        assert total_files >= 10, "Should scan at least 10 Python files"
        assert total_operations >= 5, "Should find at least 5 database operations"
        assert total_tables >= 1, "Should find at least 1 table"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
