#!/usr/bin/env python3
"""
Simple database test validation script.
Runs database tests without complex dependencies.
"""

import os
import sys
import asyncio
import traceback
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_test_module(module_name, test_description):
    """Run a test module and return success status."""
    print(f"\n{'='*60}")
    print(f"RUNNING: {test_description}")
    print(f"Module: {module_name}")
    print(f"{'='*60}")
    
    try:
        # Import the module
        if module_name == "test_database_properties":
            from tests.test_database_properties import main
        elif module_name == "test_migration_integrity_properties":
            from tests.test_migration_integrity_properties import main
        elif module_name == "test_data_integrity_properties":
            from tests.test_data_integrity_properties import main
        elif module_name == "test_excel_migration":
            from tests.test_excel_migration import main
        else:
            print(f"❌ Unknown test module: {module_name}")
            return False
        
        # Run the test
        result = asyncio.run(main())
        
        if result:
            print(f"✅ {test_description} - PASSED")
            return True
        else:
            print(f"❌ {test_description} - FAILED")
            return False
            
    except ImportError as e:
        print(f"❌ Failed to import {module_name}: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error running {module_name}: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return False


def main():
    """Main validation function."""
    print("DATABASE LAYER VALIDATION")
    print("=" * 60)
    print("Validating all database-related tests for checkpoint task 3")
    print()
    
    # Test modules to run
    test_modules = [
        ("test_database_properties", "Database Schema Compliance & Data Integrity"),
        ("test_migration_integrity_properties", "Migration Integrity Properties"),
        ("test_excel_migration", "Excel Migration Functionality"),
    ]
    
    # Try to run data integrity properties if available
    data_integrity_path = Path("tests/test_data_integrity_properties.py")
    if data_integrity_path.exists():
        test_modules.append(("test_data_integrity_properties", "Data Integrity Properties (Azure SQL)"))
    
    results = []
    
    for module_name, description in test_modules:
        success = run_test_module(module_name, description)
        results.append((description, success))
    
    # Summary
    print(f"\n{'='*60}")
    print("DATABASE LAYER VALIDATION SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for description, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {description}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL DATABASE TESTS PASSED!")
        print("\nDatabase layer validation completed successfully.")
        print("\nThe following components have been validated:")
        print("- Database schema compliance")
        print("- Data integrity maintenance")
        print("- Migration integrity properties")
        print("- Excel migration functionality")
        print("\nNext steps:")
        print("1. Proceed to implement core utility functions (Task 4)")
        print("2. Configure Azure SQL Database connection if not already done")
        print("3. Deploy database schema to production environment")
        return True
    else:
        print(f"\n❌ {total - passed} DATABASE TESTS FAILED!")
        print("\nIssues found in database layer implementation.")
        print("Please review and fix the failing tests before proceeding.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)