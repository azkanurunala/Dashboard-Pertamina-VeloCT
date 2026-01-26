#!/usr/bin/env python3
"""
Run the property-based test for data integrity.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv('.env.azure')

from tests.test_data_integrity_properties import TestDataIntegrityProperties

async def run_property_test():
    """Run the data integrity property-based test."""
    
    print("🧪 Running Property-Based Test for Data Integrity...")
    print("**Property 12: Data Integrity Maintenance**")
    print("**Validates: Requirements 4.3, 12.2**")
    print()
    
    try:
        # Create test instance
        test_instance = TestDataIntegrityProperties()
        
        # Run the property test
        print("📡 Connecting to Azure SQL Server...")
        result = await test_instance.test_property_12_referential_integrity_maintenance()
        
        if result:
            print("\n🎉 Property-based test PASSED!")
            print("✅ Data integrity constraints are properly maintained")
            return True
        else:
            print("\n❌ Property-based test FAILED!")
            print("💥 Data integrity constraints are not properly maintained")
            return False
            
    except Exception as e:
        print(f"\n💥 Property-based test ERROR: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        
        # Check if it's a connection error
        if "connection" in str(e).lower() or "login" in str(e).lower():
            print("\n🔍 This appears to be a database connection issue.")
            print("Please verify:")
            print("1. Azure SQL Server is accessible")
            print("2. Credentials are correct")
            print("3. Database exists and user has permissions")
        
        return False

if __name__ == "__main__":
    success = asyncio.run(run_property_test())
    if success:
        print("\n✅ Property-based test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Property-based test failed!")
        sys.exit(1)