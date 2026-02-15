"""Debug test to find the hanging issue."""

import sys
print("Starting import...")

try:
    print("Importing Path...")
    from pathlib import Path
    print("✓ Path imported")
    
    print("Importing CodeAuditor...")
    from azure_functions.tools.schema_audit.code_auditor import CodeAuditor
    print("✓ CodeAuditor imported")
    
    print("Creating auditor...")
    auditor = CodeAuditor()
    print("✓ Auditor created")
    
    print("Finding file...")
    db_handler_path = Path(__file__).parent.parent.parent / "shared" / "database_handler.py"
    print(f"✓ Path: {db_handler_path}")
    print(f"✓ Exists: {db_handler_path.exists()}")
    
    if db_handler_path.exists():
        print("Reading file...")
        with open(db_handler_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"✓ Read {len(content)} characters")
        
        print("Parsing AST...")
        import ast
        tree = ast.parse(content, filename=str(db_handler_path))
        print(f"✓ AST parsed, {len(list(ast.walk(tree)))} nodes")
        
        print("Calling extract_table_operations...")
        operations = auditor.extract_table_operations(str(db_handler_path))
        print(f"✓ Found {len(operations)} operations")
    
    print("\n✓✓✓ All tests passed!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
