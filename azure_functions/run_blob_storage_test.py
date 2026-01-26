#!/usr/bin/env python3
"""
Simple test runner for blob storage usage property tests.
"""

import sys
import os
import asyncio

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def run_blob_storage_test():
    """Run the blob storage usage property test."""
    try:
        from tests.test_blob_storage_usage_properties import TestBlobStorageUsageProperties
        
        print("Starting Blob Storage Usage Property Test...")
        print("=" * 60)
        
        # Create test instance
        tester = TestBlobStorageUsageProperties()
        
        # Run the property test
        success = await tester.run_all_tests()
        
        print("\n" + "=" * 60)
        
        if success:
            print("✓ All blob storage usage property tests PASSED")
            return True
        else:
            print("✗ Some blob storage usage property tests FAILED")
            return False
            
    except Exception as e:
        print(f"Test execution failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(run_blob_storage_test())
    sys.exit(0 if success else 1)