"""
Simple checkpoint test to verify code auditing works.
"""

from pathlib import Path
from azure_functions.tools.schema_audit.code_auditor import CodeAuditor


def test_database_handler():
    """Test scanning database_handler.py specifically."""
    auditor = CodeAuditor()
    
    # Scan database_handler.py
    db_handler_path = Path(__file__).parent.parent.parent / "shared" / "database_handler.py"
    
    print(f"\nScanning: {db_handler_path}")
    print(f"Exists: {db_handler_path.exists()}")
    
    if db_handler_path.exists():
        print(f"\nExtracting operations from database_handler.py...")
        
        operations = auditor.extract_table_operations(str(db_handler_path))
        print(f"Found {len(operations)} operations")
        
        # Show operations
        for op in operations[:10]:
            print(f"  - {op.operation_type} on {op.table_name} at line {op.line_number}")
        
        # Check for save_structured_data
        save_ops = [op for op in operations if 'save_structured_data' in op.code_snippet.lower()]
        print(f"\nFound {len(save_ops)} save_structured_data related operations")


def test_seed_script():
    """Test scanning a seed script."""
    auditor = CodeAuditor()
    
    # Scan a seed script
    seed_path = Path(__file__).parent.parent.parent / "scripts" / "seed_bioetanol_only.py"
    
    print(f"\n\nScanning: {seed_path}")
    print(f"Exists: {seed_path.exists()}")
    
    if seed_path.exists():
        print(f"\nExtracting operations from seed script...")
        
        operations = auditor.extract_table_operations(str(seed_path))
        print(f"Found {len(operations)} operations")
        
        # Show operations
        for op in operations:
            print(f"  - {op.operation_type} on {op.table_name} at line {op.line_number}")


if __name__ == "__main__":
    test_database_handler()
    test_seed_script()
