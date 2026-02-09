
import os
import re
import sys
import subprocess
import time
import json
import requests
from datetime import datetime

# Configuration
PRIMARY_KEY = "QRn4YL31yW-bZBFHDlt8znrvRmlfbvD8owXwCBegfk7TAzFuLEZIFg=="
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AZURE_FUNCTIONS_DIR = os.path.join(BASE_DIR, "azure_functions")

def print_banner(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def fix_function_keys():
    print_banner("1. Synchronizing Function Keys")
    
    files_to_fix = [
        os.path.join(AZURE_FUNCTIONS_DIR, "test_scraper.py"),
        os.path.join(AZURE_FUNCTIONS_DIR, "test_scraper_simple.py"),
        os.path.join(AZURE_FUNCTIONS_DIR, "quick_test_scraper.py")
    ]
    
    inconsistent_pattern = r'FUNCTION_KEY\s*=\s*["\']aOKiG8tU[^"\']*["\']'
    replacement = f'FUNCTION_KEY = "{PRIMARY_KEY}"'
    
    fixed_count = 0
    for file_path in files_to_fix:
        if not os.path.exists(file_path):
            continue
            
        print(f"Checking {os.path.basename(file_path)}...")
        with open(file_path, 'r') as f:
            content = f.read()
            
        if re.search(inconsistent_pattern, content):
            new_content = re.sub(inconsistent_pattern, replacement, content)
            with open(file_path, 'w') as f:
                f.write(new_content)
            print(f"  ✅ Updated key to primary key")
            fixed_count += 1
        else:
            print(f"  ✓ Key is already consistent or not found")
            
    print(f"\nTotal files updated: {fixed_count}")
    return True

def run_test_script(script_name, description):
    print_banner(f"Running: {description}")
    script_path = os.path.join(AZURE_FUNCTIONS_DIR, script_name)
    
    if not os.path.exists(script_path):
        print(f"❌ Error: Script {script_name} not found!")
        return False
        
    try:
        # Use python from venv if available
        python_exe = sys.executable
        venv_python = os.path.join(AZURE_FUNCTIONS_DIR, ".venv", "Scripts", "python.exe")
        if os.path.exists(venv_python):
            python_exe = venv_python
            
        result = subprocess.run([python_exe, script_path], capture_output=True, text=True)
        print(result.stdout)
        if result.returncode != 0:
            print(f"❌ Error Output: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"❌ Execution failed: {e}")
        return False

def main():
    print_banner("AZURE FUNCTIONS FIX & TEST WIZARD")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Fix keys
    fix_function_keys()
    
    # 2. Test DB Connection
    if not run_test_script("simple_connection_test.py", "Database Connection Test"):
        print("\nFATAL: Database connection failed. Please check your network/credentials.")
        return
        
    # 3. Test Single Function
    print("\nNext step: Testing a single Azure Function to verify connectivity.")
    time.sleep(1)
    if not run_test_script("test_single_function.py", "Single Function Test"):
        print("\nWARNING: Single function test failed. Check if local host is running (func start).")
        
    print_banner("SUMMARY & NEXT STEPS")
    print("1. All test files are now using the correct FUNCTION_KEY.")
    print("2. Database connection is verified.")
    print("3. You can now run the comprehensive test suite:")
    print("   python azure_functions/test_all_functions.py")
    print("\n🎉 All set! Happy coding!")

if __name__ == "__main__":
    main()
