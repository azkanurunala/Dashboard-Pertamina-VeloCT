"""
Quick Python 3.11 Compatibility Check
Verifies that all dependencies support Python 3.11
"""

import sys
import subprocess
import json
from typing import Dict, List, Tuple

# Known Python 3.11 compatible versions (minimum)
KNOWN_COMPATIBLE = {
    'azure-functions': '1.18.0',
    'azure-identity': '1.15.0',
    'azure-keyvault-secrets': '4.7.0',
    'azure-storage-blob': '12.19.0',
    'azure-monitor-opentelemetry': '1.2.0',
    'pyodbc': '5.0.0',  # 5.0+ supports Python 3.11
    'sqlalchemy': '2.0.0',  # 2.0+ supports Python 3.11
    'alembic': '1.13.0',
    'aiohttp': '3.9.0',  # 3.9+ supports Python 3.11
    'beautifulsoup4': '4.12.0',
    'lxml': '4.9.0',
    'requests': '2.31.0',
    'selenium': '4.16.0',
    'feedparser': '6.0.0',
    'webdriver-manager': '4.0.0',
    'pandas': '2.0.0',  # 2.0+ supports Python 3.11
    'numpy': '1.24.0',  # 1.24+ supports Python 3.11
    'openpyxl': '3.1.0',
    'openai': '1.0.0',
    'httpx': '0.25.0',
    'python-dateutil': '2.8.0',
    'pytz': '2023.3',
    'pydantic': '2.0.0',  # 2.0+ supports Python 3.11
    'tenacity': '8.2.0',
    'pytest': '7.4.0',
    'pytest-asyncio': '0.21.0',
    'pytest-mock': '3.12.0',
    'hypothesis': '6.92.0',
    'black': '23.0.0',
    'flake8': '6.0.0',
    'mypy': '1.0.0',
}

# Packages known to have issues with Python 3.11
KNOWN_ISSUES = {
    # Add any packages with known Python 3.11 issues here
}


def check_python_version() -> Tuple[bool, str]:
    """Check if running Python 3.11+"""
    version = sys.version_info
    is_compatible = version.major == 3 and version.minor >= 11
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    return is_compatible, version_str


def parse_requirements(file_path: str = 'requirements.txt') -> List[Tuple[str, str]]:
    """Parse requirements.txt file"""
    requirements = []
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse package name and version
            if '>=' in line:
                package, version = line.split('>=')
                requirements.append((package.strip(), version.strip()))
            elif '==' in line:
                package, version = line.split('==')
                requirements.append((package.strip(), version.strip()))
            else:
                requirements.append((line.strip(), 'any'))
    
    return requirements


def check_package_compatibility(package: str, version: str) -> Dict[str, any]:
    """Check if a package version is compatible with Python 3.11"""
    result = {
        'package': package,
        'version': version,
        'compatible': True,
        'status': 'unknown',
        'notes': []
    }
    
    # Check against known compatible versions
    if package in KNOWN_COMPATIBLE:
        min_version = KNOWN_COMPATIBLE[package]
        if version != 'any':
            # Simple version comparison (works for most cases)
            if version >= min_version:
                result['status'] = 'verified_compatible'
                result['notes'].append(f"✓ Version {version} >= minimum {min_version}")
            else:
                result['compatible'] = False
                result['status'] = 'needs_update'
                result['notes'].append(f"⚠ Version {version} < minimum {min_version}")
                result['notes'].append(f"  Recommended: >={min_version}")
        else:
            result['status'] = 'likely_compatible'
            result['notes'].append(f"✓ No version pinned, minimum is {min_version}")
    
    # Check against known issues
    if package in KNOWN_ISSUES:
        result['compatible'] = False
        result['status'] = 'known_issue'
        result['notes'].append(f"✗ Known issue: {KNOWN_ISSUES[package]}")
    
    return result


def main():
    """Main compatibility check"""
    print("=" * 70)
    print("Python 3.11 Compatibility Check")
    print("=" * 70)
    print()
    
    # Check Python version
    is_py311, version_str = check_python_version()
    print(f"Current Python Version: {version_str}")
    
    if is_py311:
        print("✓ Running Python 3.11+")
    else:
        print("⚠ Not running Python 3.11 (some checks may be limited)")
    print()
    
    # Parse requirements
    print("Checking requirements.txt...")
    requirements = parse_requirements()
    print(f"Found {len(requirements)} packages")
    print()
    
    # Check each package
    compatible_count = 0
    needs_update_count = 0
    unknown_count = 0
    
    print("-" * 70)
    print("Package Compatibility Report")
    print("-" * 70)
    
    for package, version in requirements:
        result = check_package_compatibility(package, version)
        
        # Print result
        status_icon = "✓" if result['compatible'] else "✗"
        print(f"\n{status_icon} {package} ({version})")
        
        for note in result['notes']:
            print(f"  {note}")
        
        # Count results
        if result['status'] == 'verified_compatible' or result['status'] == 'likely_compatible':
            compatible_count += 1
        elif result['status'] == 'needs_update':
            needs_update_count += 1
        else:
            unknown_count += 1
    
    # Summary
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Total packages: {len(requirements)}")
    print(f"✓ Compatible: {compatible_count}")
    print(f"⚠ Needs update: {needs_update_count}")
    print(f"? Unknown: {unknown_count}")
    print()
    
    if needs_update_count > 0:
        print("⚠ Some packages need updating for Python 3.11 compatibility")
        print("  Run the full audit for detailed recommendations:")
        print("  python -m azure_functions.audit_python311")
    elif unknown_count > 0:
        print("ℹ Some packages have unknown compatibility status")
        print("  Run the full audit for comprehensive checks:")
        print("  python -m azure_functions.audit_python311")
    else:
        print("✓ All packages appear compatible with Python 3.11!")
    
    print()
    print("Note: This is a quick check. For comprehensive analysis,")
    print("      use the full Python 3.11 Compatibility Audit spec.")
    print()


if __name__ == '__main__':
    main()
