"""
Script to fix relative imports in all Azure Functions to use absolute imports.
This resolves the import path issues in Azure Functions runtime.
"""

import os
import re
from pathlib import Path

# Define the import fix template
IMPORT_FIX_TEMPLATE = """import sys
import os

# Add parent directory to Python path for absolute imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
"""

def fix_imports_in_file(file_path: Path) -> bool:
    """
    Fix relative imports in a single __init__.py file.
    
    Args:
        file_path: Path to the __init__.py file
        
    Returns:
        True if file was modified, False otherwise
    """
    print(f"\nProcessing: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already fixed
    if 'sys.path.insert(0, parent_dir)' in content:
        print(f"  ✓ Already fixed")
        return False
    
    # Check if has relative imports
    if 'from ..' not in content:
        print(f"  - No relative imports found")
        return False
    
    # Find the position after the initial imports (before the first "from .." import)
    lines = content.split('\n')
    insert_position = 0
    first_relative_import = -1
    
    for i, line in enumerate(lines):
        # Find first relative import
        if 'from ..' in line and first_relative_import == -1:
            first_relative_import = i
        
        # Find position after standard library imports
        if first_relative_import == -1 and (
            line.startswith('import ') or 
            line.startswith('from ') and 'from ..' not in line
        ):
            insert_position = i + 1
    
    if first_relative_import == -1:
        print(f"  - No relative imports to fix")
        return False
    
    # Insert sys.path manipulation before first relative import
    if insert_position == 0:
        insert_position = first_relative_import
    
    # Add the import fix
    lines.insert(insert_position, IMPORT_FIX_TEMPLATE.strip())
    lines.insert(insert_position + 1, '')
    
    # Replace all relative imports with absolute imports
    modified_lines = []
    for line in lines:
        if 'from ..' in line:
            # Replace ..scrapers with scrapers
            # Replace ..shared with shared
            # Replace ..processing with processing
            # Replace ..orchestration with orchestration
            modified_line = line.replace('from ..scrapers', 'from scrapers')
            modified_line = modified_line.replace('from ..shared', 'from shared')
            modified_line = modified_line.replace('from ..processing', 'from processing')
            modified_line = modified_line.replace('from ..orchestration', 'from orchestration')
            modified_lines.append(modified_line)
        else:
            modified_lines.append(line)
    
    # Write back
    new_content = '\n'.join(modified_lines)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"  ✓ Fixed imports")
    return True


def main():
    """Main function to fix all Azure Functions."""
    azure_functions_dir = Path(__file__).parent
    
    # Find all __init__.py files in function directories
    function_dirs = [
        d for d in azure_functions_dir.iterdir()
        if d.is_dir() and d.name.endswith('_function')
    ]
    
    print(f"Found {len(function_dirs)} function directories")
    
    modified_count = 0
    for func_dir in sorted(function_dirs):
        init_file = func_dir / '__init__.py'
        if init_file.exists():
            if fix_imports_in_file(init_file):
                modified_count += 1
    
    print(f"\n{'='*60}")
    print(f"Summary: Modified {modified_count} files")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
