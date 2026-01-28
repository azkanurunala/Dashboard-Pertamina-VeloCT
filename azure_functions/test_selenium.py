"""
Quick test script for Selenium helper.
Run this to verify Selenium is working correctly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_import():
    """Test importing Selenium helper."""
    print("Testing import...")
    try:
        from shared.selenium_helper import SeleniumHelper, get_selenium_helper, fetch_with_selenium
        print("✓ Import successful!")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_driver_creation():
    """Test creating a Chrome driver."""
    print("\nTesting driver creation...")
    try:
        from shared.selenium_helper import SeleniumHelper
        helper = SeleniumHelper(headless=True)
        with helper.get_driver() as driver:
            print(f"✓ Driver created successfully!")
            print(f"  Browser: {driver.capabilities.get('browserName', 'unknown')}")
            print(f"  Version: {driver.capabilities.get('browserVersion', 'unknown')}")
        return True
    except Exception as e:
        print(f"✗ Driver creation failed: {e}")
        return False

def test_fetch_page():
    """Test fetching a page."""
    print("\nTesting page fetch...")
    try:
        from shared.selenium_helper import SeleniumHelper
        helper = SeleniumHelper(headless=True, page_load_timeout=15)
        
        # Test with a simple page
        url = "https://httpbin.org/html"
        content = helper.fetch_page_sync(url)
        
        if content and len(content) > 100:
            print(f"✓ Page fetched successfully!")
            print(f"  Content length: {len(content)} characters")
            return True
        else:
            print(f"✗ Page content too short: {len(content)} characters")
            return False
            
    except Exception as e:
        print(f"✗ Page fetch failed: {e}")
        return False

def test_news_site():
    """Test fetching from a news site that typically blocks."""
    print("\nTesting news site fetch (CNBC)...")
    try:
        from shared.selenium_helper import SeleniumHelper
        helper = SeleniumHelper(headless=True, page_load_timeout=30)
        
        url = "https://www.cnbc.com/sitemap_news.xml"
        content = helper.fetch_sitemap_sync(url)
        
        if content and ("xml" in content.lower() or "url" in content.lower() or "loc" in content.lower()):
            print(f"✓ CNBC sitemap fetched successfully!")
            print(f"  Content length: {len(content)} characters")
            return True
        else:
            print(f"✗ Content doesn't look like a sitemap")
            print(f"  First 500 chars: {content[:500]}...")
            return False
            
    except Exception as e:
        print(f"✗ News site fetch failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Selenium Helper Test Suite")
    print("=" * 50)
    
    results = []
    
    # Run tests
    results.append(("Import", test_import()))
    results.append(("Driver Creation", test_driver_creation()))
    results.append(("Page Fetch", test_fetch_page()))
    results.append(("News Site Fetch", test_news_site()))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Selenium is ready to use.")
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
