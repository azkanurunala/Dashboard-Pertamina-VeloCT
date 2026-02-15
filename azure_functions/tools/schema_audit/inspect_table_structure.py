"""
Inspect the structure of a table element in the BACPAC XML.
"""

import zipfile
import xml.etree.ElementTree as ET


def inspect_table_structure():
    """Inspect the structure of table elements."""
    bacpac_path = "pei-dashboard.bacpac"
    
    with zipfile.ZipFile(bacpac_path, 'r') as zip_file:
        with zip_file.open('model.xml') as f:
            xml_content = f.read().decode('utf-8')
        
        root = ET.fromstring(xml_content)
        
        # Find first table
        tables = root.findall(".//*[@Type='SqlTable']")
        
        if not tables:
            print("No tables found!")
            return
        
        print(f"Found {len(tables)} tables")
        print()
        
        # Inspect first table (data_biodiesel_hip)
        for table in tables[:3]:
            table_name = table.get('Name', 'UNKNOWN')
            print("=" * 80)
            print(f"Table: {table_name}")
            print("=" * 80)
            print()
            
            # Show table structure
            print("Table element structure:")
            print(f"  Tag: {table.tag}")
            print(f"  Attributes: {table.attrib}")
            print()
            
            # Show all child elements
            print("Direct children:")
            for child in table:
                print(f"  - {child.tag} (attrib: {child.attrib})")
                
                # Show grandchildren
                for grandchild in child:
                    print(f"      - {grandchild.tag} (attrib: {grandchild.attrib})")
                    
                    # Show great-grandchildren for Relationship elements
                    if 'Name' in grandchild.attrib:
                        rel_name = grandchild.attrib['Name']
                        if rel_name in ['Columns', 'PrimaryKeyConstraint']:
                            for ggchild in grandchild:
                                print(f"          - {ggchild.tag} (attrib: {ggchild.attrib})")
                                for gggchild in ggchild:
                                    print(f"              - {gggchild.tag} (attrib: {gggchild.attrib})")
            print()
            
            # Try to find columns
            print("Looking for columns...")
            
            # Method 1: Direct search
            columns = table.findall(".//*[@Type='SqlSimpleColumn']")
            print(f"  Method 1 (.//*[@Type='SqlSimpleColumn']): Found {len(columns)} columns")
            for col in columns[:3]:
                print(f"    - {col.get('Name', 'NO NAME')}")
            print()
            
            # Method 2: Through Relationship
            rel_columns = table.findall(".//Relationship[@Name='Columns']")
            print(f"  Method 2 (Relationship[@Name='Columns']): Found {len(rel_columns)} relationships")
            for rel in rel_columns:
                entries = rel.findall(".//Entry")
                print(f"    - Entries: {len(entries)}")
                for entry in entries[:3]:
                    elements = entry.findall(".//Element")
                    print(f"      - Elements: {len(elements)}")
                    for elem in elements:
                        print(f"        - Type: {elem.get('Type')}, Name: {elem.get('Name', 'N/A')}")
            print()


if __name__ == "__main__":
    inspect_table_structure()
