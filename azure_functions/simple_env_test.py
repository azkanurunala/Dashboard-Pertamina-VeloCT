#!/usr/bin/env python3
"""Simple environment test script."""

import os
import sys

print("🧪 Simple Environment Test")
print("=" * 30)

# Test 1: Check if .env file exists
env_file = ".env"
if os.path.exists(env_file):
    print("✅ .env file exists")
else:
    print("❌ .env file not found")
    sys.exit(1)

# Test 2: Try to import required modules
print("\n📦 Testing imports...")
try:
    import azure.identity
    print("✅ azure.identity imported")
except ImportError as e:
    print(f"❌ azure.identity failed: {e}")

try:
    import azure.storage.blob
    print("✅ azure.storage.blob imported")
except ImportError as e:
    print(f"❌ azure.storage.blob failed: {e}")

try:
    import hypothesis
    print("✅ hypothesis imported")
except ImportError as e:
    print(f"❌ hypothesis failed: {e}")

# Test 3: Load environment variables
print("\n🔧 Loading environment...")
with open(env_file, 'r') as f:
    lines = f.readlines()
    print(f"✅ Read {len(lines)} lines from .env")

print("\n🎉 Basic environment test complete!")