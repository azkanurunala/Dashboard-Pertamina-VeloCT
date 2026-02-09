
import os
import json

def quick_fix_auth():
    print("🔧 Quick Fix for HTTP 401 Unauthorized")
    print("This script will change all function auth levels to 'anonymous' for testing.")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    fixed_count = 0
    
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path):
            func_json_path = os.path.join(item_path, "function.json")
            if os.path.exists(func_json_path):
                print(f"Checking {item}...")
                with open(func_json_path, 'r') as f:
                    config = json.load(f)
                
                modified = False
                for binding in config.get('bindings', []):
                    if binding.get('type') == 'httpTrigger' and binding.get('authLevel') != 'anonymous':
                        binding['authLevel'] = 'anonymous'
                        modified = True
                
                if modified:
                    with open(func_json_path, 'w') as f:
                        json.dump(config, f, indent=2)
                    print(f"  ✅ Updated {item} to 'anonymous' auth")
                    fixed_count += 1
                else:
                    print(f"  ✓ {item} is already anonymous or not an HTTP trigger")
    
    print(f"\nTotal functions updated: {fixed_count}")
    print("\nNext step: Restart your functions host (func start) then run tests.")

if __name__ == "__main__":
    quick_fix_auth()
