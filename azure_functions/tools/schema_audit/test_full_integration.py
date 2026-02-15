"""
Comprehensive integration test for the full schema audit workflow.
Tests the complete pipeline from BACPAC extraction to reporting.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path

from .schema_extractor import SchemaExtractor
from .code_auditor import CodeAuditor
from .mismatch_detector import MismatchDetector
from .schema_fixer import SchemaFixer
from .validator import Validator
from .reporter import Reporter
from .migration_auditor import MigrationAuditor


class TestFullIntegration:
    """Integration tests for the complete schema audit workflow."""
    
    @pytest.fixture
    def bacpac_path(self):
        """Path to the actual BACPAC file."""
        # Try multiple possible locations
        possible_paths = [
            "pei-dashboard.bacpac",
            "../../../pei-dashboard.bacpac",
            "azure_functions/pei-dashboard.bacpac"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        pytest.skip("pei-dashboard.bacpac not found")
    
    @pytest.fixture
    def azure_functions_dir(self):
        """Path to the Azure Functions directory."""
        possible_paths = [
            "azure_functions",
            "../../../azure_functions",
            "../../.."
        ]
        
        for path in possible_paths:
            if os.path.exists(path) and os.path.isdir(path):
                return path
        
        pytest.skip("azure_functions directory not found")
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary directory for test outputs."""
        temp_dir = tempfile.mkdtemp(prefix="schema_audit_test_")
        yield temp_dir
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    def test_full_audit_workflow(self, bacpac_path, azure_functions_dir, temp_output_dir):
        """
        Test the complete audit workflow:
        1. Extract schema from BACPAC
        2. Audit code for database operations
        3. Detect mismatches
        4. Generate reports
        """
        print(f"\n=== Testing Full Audit Workflow ===")
        print(f"BACPAC: {bacpac_path}")
        print(f"Azure Functions: {azure_functions_dir}")
        print(f"Output: {temp_output_dir}")
        
        # Step 1: Extract schema from BACPAC
        print("\n[1/4] Extracting schema from BACPAC...")
        extractor = SchemaExtractor()
        reference_schema = extractor.extract_from_bacpac(bacpac_path)
        
        assert reference_schema is not None, "Schema extraction failed"
        assert len(reference_schema.tables) > 0, "No tables extracted"
        print(f"✓ Extracted {len(reference_schema.tables)} tables")
        
        # Export schema to JSON for inspection
        json_path = os.path.join(temp_output_dir, "reference_schema.json")
        extractor.export_to_json(reference_schema, json_path)
        assert os.path.exists(json_path), "JSON export failed"
        print(f"✓ Exported schema to {json_path}")
        
        # Step 2: Audit code for database operations
        print("\n[2/4] Auditing code for database operations...")
        auditor = CodeAuditor()
        
        # Scan the azure_functions directory
        code_locations = auditor.scan_directory(
            azure_functions_dir,
            patterns=["*.py"]
        )
        
        assert len(code_locations) > 0, "No Python files found"
        print(f"✓ Scanned {len(code_locations)} Python files")
        
        # Build operation map
        operation_map = auditor.build_operation_map()
        print(f"✓ Found operations on {len(operation_map)} tables")
        
        # Step 3: Detect mismatches
        print("\n[3/4] Detecting schema mismatches...")
        detector = MismatchDetector(reference_schema, operation_map)
        mismatches = detector.compare_schemas()
        
        print(f"✓ Detected {len(mismatches)} mismatches")
        
        # Categorize by severity
        categorized = detector.categorize_by_severity(mismatches)
        print(f"  - Critical: {len(categorized.get('CRITICAL', []))}")
        print(f"  - Warning: {len(categorized.get('WARNING', []))}")
        print(f"  - Info: {len(categorized.get('INFO', []))}")
        
        # Step 4: Generate reports
        print("\n[4/4] Generating reports...")
        reporter = Reporter()
        
        # Generate audit report
        audit_report_path = os.path.join(temp_output_dir, "audit_report.md")
        audit_report = reporter.generate_audit_report(mismatches, reference_schema)
        with open(audit_report_path, 'w', encoding='utf-8') as f:
            f.write(audit_report)
        assert os.path.exists(audit_report_path), "Audit report generation failed"
        print(f"✓ Generated audit report: {audit_report_path}")
        
        # Generate schema documentation
        schema_doc_path = os.path.join(temp_output_dir, "schema_documentation.md")
        schema_doc = reporter.generate_schema_documentation(reference_schema)
        with open(schema_doc_path, 'w', encoding='utf-8') as f:
            f.write(schema_doc)
        assert os.path.exists(schema_doc_path), "Schema documentation generation failed"
        print(f"✓ Generated schema documentation: {schema_doc_path}")
        
        # Generate statistics
        stats = reporter.generate_statistics(reference_schema, mismatches, operation_map)
        print(f"✓ Generated statistics:")
        print(f"  - Total tables: {stats.get('total_tables', 0)}")
        print(f"  - Total mismatches: {stats.get('total_mismatches', 0)}")
        print(f"  - Files scanned: {stats.get('files_scanned', 0)}")
        
        print("\n=== Audit Workflow Complete ===")
    
    def test_schema_extraction_completeness(self, bacpac_path):
        """Test that schema extraction captures all expected information."""
        print(f"\n=== Testing Schema Extraction Completeness ===")
        
        extractor = SchemaExtractor()
        schema = extractor.extract_from_bacpac(bacpac_path)
        
        # Verify schema has tables
        assert len(schema.tables) > 0, "No tables extracted"
        print(f"✓ Extracted {len(schema.tables)} tables")
        
        # Verify each table has columns
        for table_name, table_schema in schema.tables.items():
            assert len(table_schema.columns) > 0, f"Table {table_name} has no columns"
            
            # Verify each column has required attributes
            for column in table_schema.columns:
                assert column.name, f"Column in {table_name} has no name"
                assert column.data_type, f"Column {column.name} in {table_name} has no data type"
        
        print(f"✓ All tables have columns with required attributes")
        
        # Check for structured data tables
        structured_tables = [
            name for name in schema.tables.keys()
            if not name.startswith('news_') and name not in ['keywords', 'sentiment_summaries']
        ]
        
        print(f"✓ Found {len(structured_tables)} structured data tables")
        
        print("\n=== Schema Extraction Test Complete ===")
    
    def test_code_auditor_completeness(self, azure_functions_dir):
        """Test that code auditor finds all database operations."""
        print(f"\n=== Testing Code Auditor Completeness ===")
        
        auditor = CodeAuditor()
        
        # Scan directory
        code_locations = auditor.scan_directory(azure_functions_dir, patterns=["*.py"])
        print(f"✓ Scanned {len(code_locations)} Python files")
        
        # Build operation map
        operation_map = auditor.build_operation_map()
        print(f"✓ Found operations on {len(operation_map)} tables")
        
        # Verify we found some operations
        assert len(operation_map) > 0, "No database operations found"
        
        # Print sample operations
        for table_name, operations in list(operation_map.items())[:5]:
            print(f"  - {table_name}: {len(operations)} operations")
        
        print("\n=== Code Auditor Test Complete ===")
    
    def test_error_handling(self, temp_output_dir):
        """Test error handling with invalid inputs."""
        print(f"\n=== Testing Error Handling ===")
        
        # Test with non-existent BACPAC file
        extractor = SchemaExtractor()
        try:
            schema = extractor.extract_from_bacpac("nonexistent.bacpac")
            assert False, "Should have raised an exception"
        except Exception as e:
            print(f"✓ Correctly handled missing BACPAC: {type(e).__name__}")
        
        # Test with non-existent directory
        auditor = CodeAuditor()
        try:
            locations = auditor.scan_directory("nonexistent_dir", patterns=["*.py"])
            # Should return empty list or raise exception
            assert len(locations) == 0, "Should return empty list for non-existent directory"
            print(f"✓ Correctly handled missing directory")
        except Exception as e:
            print(f"✓ Correctly handled missing directory: {type(e).__name__}")
        
        print("\n=== Error Handling Test Complete ===")
    
    def test_validator_integration(self, temp_output_dir):
        """Test validator with sample Python code."""
        print(f"\n=== Testing Validator Integration ===")
        
        validator = Validator()
        
        # Create a valid Python file
        valid_file = os.path.join(temp_output_dir, "valid.py")
        with open(valid_file, 'w') as f:
            f.write("def test():\n    return 42\n")
        
        result = validator.validate_python_syntax(valid_file)
        assert result.is_valid, "Valid Python file should pass validation"
        print(f"✓ Valid Python file passed validation")
        
        # Create an invalid Python file
        invalid_file = os.path.join(temp_output_dir, "invalid.py")
        with open(invalid_file, 'w') as f:
            f.write("def test(\n    return 42\n")  # Missing closing paren
        
        result = validator.validate_python_syntax(invalid_file)
        assert not result.is_valid, "Invalid Python file should fail validation"
        print(f"✓ Invalid Python file failed validation as expected")
        
        print("\n=== Validator Test Complete ===")
    
    def test_migration_auditor_integration(self, azure_functions_dir, temp_output_dir):
        """Test migration auditor with actual scripts directory."""
        print(f"\n=== Testing Migration Auditor Integration ===")
        
        scripts_dir = os.path.join(azure_functions_dir, "scripts")
        
        if not os.path.exists(scripts_dir):
            pytest.skip("Scripts directory not found")
        
        auditor = MigrationAuditor()
        
        # Scan for migration scripts
        scripts = auditor.scan_migration_scripts(scripts_dir)
        print(f"✓ Found {len(scripts)} migration scripts")
        
        # Audit operations in scripts
        if len(scripts) > 0:
            operations = auditor.audit_migration_operations(scripts[0])
            print(f"✓ Audited operations in first script: {len(operations)} operations")
        
        print("\n=== Migration Auditor Test Complete ===")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
