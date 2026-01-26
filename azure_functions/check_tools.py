"""
Check if all required tools are installed
"""
import subprocess
import sys

def check_tool(command, name):
    """Check if a tool is installed."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"✅ {name}: Installed")
            return True
        else:
            print(f"❌ {name}: Not working")
            return False
    except Exception:
        print(f"❌ {name}: Not found")
        return False

def main():
    """Check all tools."""
    print("🔧 Checking Required Tools")
    print("=" * 40)
    
    tools = [
        (["python", "--version"], "Python"),
        (["az", "--version"], "Azure CLI"),
        (["func", "--version"], "Azure Functions Core Tools"),
        (["node", "--version"], "Node.js"),
        (["npm", "--version"], "npm")
    ]
    
    results = []
    for command, name in tools:
        result = check_tool(command, name)
        results.append((name, result))
    
    print("\n" + "=" * 40)
    print("📋 Summary:")
    
    installed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"Installed: {installed}/{total}")
    
    if installed == total:
        print("🎉 All tools are ready!")
        print("\n💡 Next steps:")
        print("1. az login")
        print("2. Deploy functions")
    else:
        print("⚠️ Some tools are missing:")
        for name, result in results:
            if not result:
                print(f"  - {name}")
        
        print("\n💡 Install missing tools:")
        print("- Azure CLI: https://aka.ms/installazurecliwindows")

if __name__ == "__main__":
    main()