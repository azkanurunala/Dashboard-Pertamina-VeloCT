"""
Inspect the structure of a column element in the BACPAC XML.
"""

import zipfile
import xml.etree.ElementTree as ET


def inspect_column_structure():
    """Inspect the structure of column elements."""
    bacpac_path = "pei-dashboard.bacpac"
    
    with zipfile.ZipFile(bacpac_path, 'r') as zip_file:
        with zip_file.open('model.xml') as f:
            xml_content = f.read().decode('utf-8')
        
        root = ET.fromstring(xml_content)
        
        # Find first table
        table = root.find(".//*[@Type='SqlTable'][@Name='[dbo].[data_biodiesel_hip]']")
        
        if not table:
            print("Table not found!")
            return
        
        print("=" * 80)
        print("Table: data_biodiesel_hip")
        print("=" * 80)
        print()
        
        # Find columns
        columns = table.findall(".//*[@Type='SqlSimpleColumn']")
        
        print(f"Found {len(columns)} columns")
        print()
        
        # Inspect first column in detail
        if columns:
            col = columns[0]
            print("First column structure:")
            print(f"  Tag: {col.tag}")
            print(f"  Attributes: {col.attrib}")
            print()
            
            def print_tree(elem, indent=0):
                """Recursively print element tree."""
                prefix = "  " * indent
                print(f"{prefix}- {elem.tag.split('}')[-1]} (attrib: {elem.attrib})")
                if elem.text and elem.text.strip():
                    print(f"{prefix}  Text: {elem.text.strip()}")
                for child in elem:
                    print_tree(child, indent + 1)
            
            print("Full tree:")
            print_tree(col)
            print()


if __name__ == "__main__":
    inspect_column_structure()
