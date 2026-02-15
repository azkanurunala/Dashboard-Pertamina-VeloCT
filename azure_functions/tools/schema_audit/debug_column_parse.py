"""
Debug column parsing to see why data types aren't being extracted.
"""

import zipfile
import xml.etree.ElementTree as ET


def debug_column_parse():
    """Debug column parsing."""
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
        
        # Find first column
        column = table.find(".//*[@Type='SqlSimpleColumn']")
        
        if not column:
            print("Column not found!")
            return
        
        print("Column:", column.get('Name'))
        print()
        
        # Try to find TypeSpecifier
        print("Looking for TypeSpecifier...")
        type_spec_rel = column.find(".//Relationship[@Name='TypeSpecifier']")
        print(f"  type_spec_rel: {type_spec_rel}")
        
        if type_spec_rel is not None:
            print("  Found TypeSpecifier relationship")
            type_spec_elem = type_spec_rel.find(".//Element[@Type='SqlTypeSpecifier']")
            print(f"  type_spec_elem: {type_spec_elem}")
            
            if type_spec_elem is not None:
                print("  Found SqlTypeSpecifier element")
                datatype_ref = type_spec_elem.find(".//References")
                print(f"  datatype_ref: {datatype_ref}")
                
                if datatype_ref is not None:
                    datatype_name = datatype_ref.get('Name', '')
                    print(f"  datatype_name: {datatype_name}")
                else:
                    print("  No References found")
            else:
                print("  No SqlTypeSpecifier element found")
        else:
            print("  No TypeSpecifier relationship found")
        
        print()
        print("All Relationship elements in column:")
        for rel in column.findall(".//*"):
            if 'Relationship' in rel.tag:
                print(f"  - Tag: {rel.tag}, Attrib: {rel.attrib}")


if __name__ == "__main__":
    debug_column_parse()
