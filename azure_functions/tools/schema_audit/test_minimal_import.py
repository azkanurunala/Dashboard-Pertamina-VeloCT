"""Minimal import test."""
import sys
print("Python path:")
for p in sys.path[:5]:
    print(f"  {p}")

print("\nTrying to import models...")
try:
    from azure_functions.tools.schema_audit.models import OperationType
    print("✓ Models imported successfully")
    print(f"✓ OperationType: {OperationType.CREATE}")
except Exception as e:
    print(f"❌ Failed to import models: {e}")
    import traceback
    traceback.print_exc()

print("\nDone!")
