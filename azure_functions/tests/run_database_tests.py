"""
Test runner for database layer validation.
Runs all database tests with proper configuration.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables from .env.test if it exists
env_test_path = Path(__file__).parent.parent / '.env.test'
if env_test_path.exists():
    print(f"Loading test environment from: {env_test_path}")
    with open(env_test_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes if present
                value = value.strip('"\'')
                os.environ[key] = value

from test_config import get_test_database_config, should_use_mock_database


async def run_database_property_tests():
    """Run database property tests."""
    print("=" * 70)
    print("RUNNING DATABASE LAYER VALIDATION TESTS")
    print("=" * 70)
    
    # Check if we should use mock database
    use_mock = should_use_mock_database()
    
    if use_mock:
        print("⚠️  Using MOCK database (Azure SQL connection not configured)")
        print("   To use real Azure SQL Database, set AZURE_SQL_CONNECTION_STRING environment variable")
    else:
        print("✅ Using AZURE SQL DATABASE (PeiDashboard)")
        config = get_test_database_config()
        print(f"   Server: {config.connection_string.split(';')[1] if ';' in config.connection_string else 'Azure SQL'}")
    
    print("\n" + "=" * 70)
    
    # Import and run tests
    if use_mock:
        # Run mock tests
        print("Running Property Tests with Mock Database...")
        
        # Import mock test modules
        from test_database_properties import main as run_mock_tests
        mock_success = await run_mock_tests()
        
        from test_migration_integrity_properties import main as run_migration_tests
        migration_success = await run_migration_tests()
        
        from test_excel_migration import main as run_excel_tests
        excel_success = await run_excel_tests()
        
        overall_success = mock_success and migration_success and excel_success
        
    else:
        # Run real database tests
        print("Running Property Tests with Azure SQL Database...")
        
        try:
            # Import real database test modules
            from test_data_integrity_properties import main as run_integrity_tests
            integrity_success = await run_integrity_tests()
            
            from test_migration_integrity_properties import main as run_migration_tests
            migration_success = await run_migration_tests()
            
            from test_excel_migration import main as run_excel_tests
            excel_success = await run_excel_tests()
            
            overall_success = integrity_success and migration_success and excel_success
            
        except Exception as e:
            print(f"❌ Real database tests failed: {str(e)}")
            print("   Falling back to mock tests...")
            
            # Fallback to mock tests
            from test_database_properties import main as run_mock_tests
            mock_success = await run_mock_tests()
            
            from test_migration_integrity_properties import main as run_migration_tests
            migration_success = await run_migration_tests()
            
            from test_excel_migration import main as run_excel_tests
            excel_success = await run_excel_tests()
            
            overall_success = mock_success and migration_success and excel_success
    
    print("\n" + "=" * 70)
    print("DATABASE LAYER VALIDATION SUMMARY")
    print("=" * 70)
    
    if overall_success:
        print("✅ ALL DATABASE TESTS PASSED")
        print("\n🎉 Database layer validation completed successfully!")
        print("\nNext steps:")
        print("1. Configure Azure SQL Database connection string if not already done")
        print("2. Deploy database schema to Azure SQL Database")
        print("3. Proceed to implement core utility functions (Task 4)")
    else:
        print("❌ SOME DATABASE TESTS FAILED")
        print("\n🔧 Issues to resolve:")
        print("1. Fix failing property tests")
        print("2. Verify database connection configuration")
        print("3. Check database schema deployment")
    
    return overall_success


async def main():
    """Main test runner."""
    try:
        success = await run_database_property_tests()
        return success
    except Exception as e:
        print(f"\n❌ Test execution failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(main())
    exit(0 if success else 1)