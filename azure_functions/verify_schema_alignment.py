"""
Script untuk memverifikasi alignment antara schema database (bacpac) 
dengan kode Azure Functions
"""
import zipfile
import xml.etree.ElementTree as ET
import json
import os
import re
from pathlib import Path
from collections import defaultdict

# ===== STEP 1: Extract schema from bacpac =====
print("=" * 80)
print("STEP 1: Extracting schema from pei-dashboard.bacpac")
print("=" * 80)

with zipfile.ZipFile('pei-dashboard.bacpac', 'r') as z:
    with z.open('model.xml') as f:
        content = f.read()

root = ET.fromstring(content)
ns = {'ds': 'http://schemas.microsoft.com/sqlserver/dac/Serialization/2012/02'}

# Extract all tables
bacpac_tables = set()
for table_elem in root.findall('.//ds:Element[@Type="SqlTable"]', ns):
    table_name = table_elem.get('Name', '')
    if table_name:
        clean_name = table_name.replace('[dbo].[', '').replace('[', '').replace(']', '')
        bacpac_tables.add(clean_name)

print(f"\nFound {len(bacpac_tables)} tables in bacpac:")
for table in sorted(bacpac_tables):
    print(f"  - {table}")

# ===== STEP 2: Scan code for table references =====
print("\n" + "=" * 80)
print("STEP 2: Scanning code for database table references")
print("=" * 80)

code_table_refs = defaultdict(list)

# Patterns to find table references
patterns = [
    (r'FROM\s+(\w+)', 'SQL FROM'),
    (r'INTO\s+(\w+)', 'SQL INSERT INTO'),
    (r'UPDATE\s+(\w+)', 'SQL UPDATE'),
    (r'JOIN\s+(\w+)', 'SQL JOIN'),
    (r'TABLE\s+(\w+)', 'SQL CREATE/ALTER TABLE'),
    (r'["\'](\w+)["\'].*table', 'String literal with "table"'),
    (r'table_name\s*=\s*["\'](\w+)["\']', 'table_name assignment'),
]

# Files to scan
scan_dirs = [
    'shared',
    'scrapers',
    'processing',
    'scripts',
    'backup',
    'orchestration',
]

# Scan Python files
for scan_dir in scan_dirs:
    if not os.path.exists(scan_dir):
        continue
    
    for root_dir, dirs, files in os.walk(scan_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root_dir, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Look for table references
                        for pattern, desc in patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            for match in matches:
                                if match and len(match) > 3:  # Filter out very short matches
                                    code_table_refs[match.lower()].append({
                                        'file': file_path,
                                        'pattern': desc
                                    })
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

# Scan SQL files
for root_dir, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.sql'):
            file_path = os.path.join(root_dir, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    for pattern, desc in patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        for match in matches:
                            if match and len(match) > 3:
                                code_table_refs[match.lower()].append({
                                    'file': file_path,
                                    'pattern': desc
                                })
            except Exception as e:
                print(f"Error reading {file_path}: {e}")

print(f"\nFound {len(code_table_refs)} unique table references in code")

# ===== STEP 3: Compare and find mismatches =====
print("\n" + "=" * 80)
print("STEP 3: Comparing schema with code references")
print("=" * 80)

bacpac_tables_lower = {t.lower() for t in bacpac_tables}
code_tables_lower = set(code_table_refs.keys())

# Tables in code but not in bacpac
missing_in_bacpac = code_tables_lower - bacpac_tables_lower
# Tables in bacpac but not referenced in code
unused_in_code = bacpac_tables_lower - code_tables_lower

print("\n" + "-" * 80)
print("TABLES REFERENCED IN CODE BUT NOT IN BACPAC SCHEMA:")
print("-" * 80)
if missing_in_bacpac:
    for table in sorted(missing_in_bacpac):
        print(f"\n❌ {table}")
        refs = code_table_refs[table]
        print(f"   Referenced in {len(refs)} location(s):")
        for ref in refs[:5]:  # Show first 5 references
            print(f"     - {ref['file']} ({ref['pattern']})")
        if len(refs) > 5:
            print(f"     ... and {len(refs) - 5} more")
else:
    print("✅ No mismatches found - all code references match bacpac schema")

print("\n" + "-" * 80)
print("TABLES IN BACPAC BUT NOT REFERENCED IN CODE:")
print("-" * 80)
if unused_in_code:
    for table in sorted(unused_in_code):
        print(f"⚠️  {table}")
else:
    print("✅ All tables in bacpac are referenced in code")

# ===== STEP 4: Check specific critical tables =====
print("\n" + "=" * 80)
print("STEP 4: Verifying critical tables")
print("=" * 80)

critical_tables = [
    'news_articles',
    'news_sources',
    'sentiment_analyses',
    'keywords',
    'article_keywords',
    'execution_logs',
    'configuration',
    'data_biodiesel_hip',
    'data_bioetanol_hip',
    'data_cpo_prices',
    'data_eia_market',
    'data_fossil',
    'data_oil_prices',
    'data_ruptl_projects',
]

print("\nChecking critical tables:")
for table in critical_tables:
    in_bacpac = table.lower() in bacpac_tables_lower
    in_code = table.lower() in code_tables_lower
    
    status = "✅" if in_bacpac and in_code else "❌"
    bacpac_status = "✓" if in_bacpac else "✗"
    code_status = "✓" if in_code else "✗"
    
    print(f"{status} {table:40} | Bacpac: {bacpac_status} | Code: {code_status}")

# ===== STEP 5: Generate report =====
print("\n" + "=" * 80)
print("SUMMARY REPORT")
print("=" * 80)

report = {
    'bacpac_tables': sorted(list(bacpac_tables)),
    'code_table_references': {k: len(v) for k, v in code_table_refs.items()},
    'missing_in_bacpac': sorted(list(missing_in_bacpac)),
    'unused_in_code': sorted(list(unused_in_code)),
    'critical_tables_status': {
        table: {
            'in_bacpac': table.lower() in bacpac_tables_lower,
            'in_code': table.lower() in code_tables_lower
        }
        for table in critical_tables
    }
}

with open('schema_verification_report.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(f"\n📊 Statistics:")
print(f"   - Tables in bacpac: {len(bacpac_tables)}")
print(f"   - Tables referenced in code: {len(code_table_refs)}")
print(f"   - Mismatches (in code, not in bacpac): {len(missing_in_bacpac)}")
print(f"   - Unused tables (in bacpac, not in code): {len(unused_in_code)}")

print(f"\n📄 Full report saved to: schema_verification_report.json")

if missing_in_bacpac:
    print(f"\n⚠️  WARNING: Found {len(missing_in_bacpac)} table(s) referenced in code but missing from bacpac!")
    print("   This may cause runtime errors. Please review the report.")
else:
    print("\n✅ SUCCESS: All table references in code match the bacpac schema!")
