"""
Simple integration test to verify components work together.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from azure_functions.tools.schema_audit.schema_extractor import SchemaExtractor
from azure_functions.tools.schema_audit.code_auditor import CodeAuditor
from azure_functions.tools.schema_audit.mismatch_detector import MismatchDetector
from azure_functions.tools.schema_audit.reporter import Reporter


def test_schema_extraction():
    """Test schema extraction from BACPAC."""
    print("\n=== Test 1: Schema Extraction ===")
    
    bacpac_path = "pei-dashboard.bacpac"
    if not os.path.exists(bacpac_path):
        print(f"❌ BACPAC file not found: {bacpac_path}")
        return False
    
    try:
        extractor = SchemaExtractor()
        schema = extractor.extract_from_bacpac(bacpac_path)
        
        print(f"✓ Extracted {len(schema.tables)} tables")
        print(f"✓ Schema version: {schema.version}")
        print(f"✓ Source file: {schema.source_file}")
        
        # Show sample tables
        print("\nSample tables:")
        for i, (table_name, table_schema) in enumerate(list(schema.tables.items())[:5]):
            print(f"  - {table_name}: {len(table_schema.columns)} columns")
        
        return True
    except Exception as e:
        print(f"❌ Schema extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_code_auditor():
    """Test code auditor on a specific file."""
    print("\n=== Test 2: Code Auditor ===")
    
    # Test with a specific scraper file
    test_file = "azure_functions/scrapers/bank_indonesia_scraper.py"
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False
    
    try:
        auditor = CodeAuditor()
        
        # Extract operations from the specific file
        operations = auditor.extract_table_operations(test_file)
        
        print(f"✓ Found {len(operations)} operations in {test_file}")
        
        # Show sample operations
        if operations:
            print("\nSample operations:")
            for op in operations[:3]:
                print(f"  - {op.operation_type.value}: {op.table_name} at line {op.location.line_number}")
        
        # Now scan a directory
        print("\nScanning scrapers directory...")
        auditor2 = CodeAuditor()
        locations = auditor2.scan_directory("azure_functions/scrapers", patterns=["*.py"])
        
        print(f"✓ Scanned directory, found {len(locations)} operation locations")
        print(f"✓ Total operations stored: {len(auditor2.operations)}")
        
        # Build operation map
        operation_map = auditor2.build_operation_map()
        print(f"✓ Operation map has {len(operation_map)} tables")
        
        # Show sample tables
        if operation_map:
            print("\nSample tables from operation map:")
            for i, (table_name, ops) in enumerate(list(operation_map.items())[:5]):
                print(f"  - {table_name}: {len(ops)} operations")
        
        return True
    except Exception as e:
        print(f"❌ Code auditor failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mismatch_detection():
    """Test mismatch detection."""
    print("\n=== Test 3: Mismatch Detection ===")
    
    try:
        # Extract schema
        extractor = SchemaExtractor()
        schema = extractor.extract_from_bacpac("pei-dashboard.bacpac")
        
        # Audit code
        auditor = CodeAuditor()
        auditor.scan_directory("azure_functions/scrapers", patterns=["*.py"])
        operation_map = auditor.build_operation_map()
        
        # Detect mismatches
        detector = MismatchDetector(schema, operation_map)
        mismatches = detector.compare_schemas()
        
        print(f"✓ Detected {len(mismatches)} mismatches")
        
        # Categorize by severity
        categorized = detector.categorize_by_severity(mismatches)
        print(f"  - Critical: {len(categorized.get('CRITICAL', []))}")
        print(f"  - Warning: {len(categorized.get('WARNING', []))}")
        print(f"  - Info: {len(categorized.get('INFO', []))}")
        
        # Show sample mismatches
        if mismatches:
            print("\nSample mismatches:")
            for mismatch in mismatches[:3]:
                print(f"  - [{mismatch.severity}] {mismatch.mismatch_type}: {mismatch.table_name}")
                if mismatch.column_name:
                    print(f"    Column: {mismatch.column_name}")
        
        return True
    except Exception as e:
        print(f"❌ Mismatch detection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_reporter():
    """Test report generation."""
    print("\n=== Test 4: Reporter ===")
    
    try:
        # Extract schema
        extractor = SchemaExtractor()
        schema = extractor.extract_from_bacpac("pei-dashboard.bacpac")
        
        # Audit code
        auditor = CodeAuditor()
        auditor.scan_directory("azure_functions/scrapers", patterns=["*.py"])
        operation_map = auditor.build_operation_map()
        
        # Detect mismatches
        detector = MismatchDetector(schema, operation_map)
        mismatches = detector.compare_schemas()
        
        # Generate reports
        reporter = Reporter()
        
        # Audit report
        audit_report = reporter.generate_audit_report(mismatches, schema)
        print(f"✓ Generated audit report ({len(audit_report)} characters)")
        
        # Schema documentation
        schema_doc = reporter.generate_schema_documentation(schema)
        print(f"✓ Generated schema documentation ({len(schema_doc)} characters)")
        
        # Statistics
        stats = reporter.generate_statistics(schema, mismatches, operation_map)
        print(f"✓ Generated statistics:")
        print(f"  - Total tables: {stats.get('total_tables', 0)}")
        print(f"  - Total mismatches: {stats.get('total_mismatches', 0)}")
        print(f"  - Tables with operations: {stats.get('tables_with_operations', 0)}")
        
        return True
    except Exception as e:
        print(f"❌ Reporter failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("INTEGRATION TESTING - Database Schema Audit System")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Schema Extraction", test_schema_extraction()))
    results.append(("Code Auditor", test_code_auditor()))
    results.append(("Mismatch Detection", test_mismatch_detection()))
    results.append(("Reporter", test_reporter()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All integration tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
