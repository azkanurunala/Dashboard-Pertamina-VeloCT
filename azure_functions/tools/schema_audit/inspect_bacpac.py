"""
Inspect BACPAC file structure to understand XML format.
"""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


def inspect_bacpac():
    """Inspect the BACPAC file structure."""
    bacpac_path = "pei-dashboard.bacpac"
    
    print("=" * 80)
    print("BACPAC FILE INSPECTION")
    print("=" * 80)
    print()
    
    # List contents
    print("Files in BACPAC:")
    with zipfile.ZipFile(bacpac_path, 'r') as zip_file:
        for name in zip_file.namelist():
            info = zip_file.getinfo(name)
            print(f"  - {name} ({info.file_size} bytes)")
        print()
        
        # Read model.xml
        if 'model.xml' in zip_file.namelist():
            print("Reading model.xml...")
            with zip_file.open('model.xml') as f:
                xml_content = f.read().decode('utf-8')
            
            # Parse XML
            root = ET.fromstring(xml_content)
            
            print(f"Root tag: {root.tag}")
            print(f"Root attributes: {root.attrib}")
            print()
            
            # Show namespaces
            print("Namespaces found:")
            namespaces = dict([node for _, node in ET.iterparse(
                zip_file.open('model.xml'), events=['start-ns']
            )])
            for prefix, uri in namespaces.items():
                print(f"  {prefix}: {uri}")
            print()
            
            # Find all unique element types
            print("Unique element types in XML:")
            element_types = set()
            for elem in root.iter():
                if 'Type' in elem.attrib:
                    element_types.add(elem.attrib['Type'])
            
            for elem_type in sorted(element_types):
                count = len([e for e in root.iter() if e.attrib.get('Type') == elem_type])
                print(f"  - {elem_type}: {count} occurrences")
            print()
            
            # Find table elements
            print("Looking for table elements...")
            
            # Try different XPath patterns
            patterns = [
                ".//Element[@Type='SqlTable']",
                ".//*[@Type='SqlTable']",
                ".//SqlTable",
                ".//{http://schemas.microsoft.com/sqlserver/dac/Serialization/2012/02}Element[@Type='SqlTable']",
            ]
            
            for pattern in patterns:
                try:
                    if pattern.startswith(".//"):
                        # Without namespace
                        tables = root.findall(pattern)
                    else:
                        # With namespace
                        tables = root.findall(pattern)
                    
                    if tables:
                        print(f"  Pattern '{pattern}': Found {len(tables)} tables")
                        for table in tables[:3]:  # Show first 3
                            print(f"    - {table.attrib.get('Name', 'NO NAME')}")
                    else:
                        print(f"  Pattern '{pattern}': No tables found")
                except Exception as e:
                    print(f"  Pattern '{pattern}': Error - {e}")
            print()
            
            # Show first few elements with Type attribute
            print("First 10 elements with Type attribute:")
            count = 0
            for elem in root.iter():
                if 'Type' in elem.attrib:
                    print(f"  - Tag: {elem.tag}, Type: {elem.attrib['Type']}, Name: {elem.attrib.get('Name', 'N/A')}")
                    count += 1
                    if count >= 10:
                        break
            print()
            
            # Save a sample of the XML for inspection
            sample_path = Path("azure_functions/tools/schema_audit/output/model_sample.xml")
            sample_path.parent.mkdir(parents=True, exist_ok=True)
            with open(sample_path, 'w', encoding='utf-8') as f:
                # Write first 50000 characters
                f.write(xml_content[:50000])
            print(f"Saved XML sample to: {sample_path}")
            print()


if __name__ == "__main__":
    inspect_bacpac()
