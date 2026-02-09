
import xml.etree.ElementTree as ET
import glob

def diagnose_sitemap(filepath):
    print(f"\n--- Diagnosing {filepath} ---")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse with ET
        try:
            parser = ET.XMLParser()
            parser.feed(content)
            print("Successfully parsed with ET.XMLParser")
        except ET.ParseError as e:
            print(f"ET ParseError: {e}")
            line_num, col_num = e.position
            lines = content.splitlines()
            if line_num <= len(lines):
                print(f"Error at line {line_num}, col {col_num}:")
                start = max(0, line_num - 3)
                end = min(len(lines), line_num + 2)
                for i in range(start, end):
                    prefix = ">>> " if i + 1 == line_num else "    "
                    print(f"{i+1:4}: {prefix}{lines[i]}")
            
    except Exception as e:
        print(f"Error reading file: {e}")

failed_files = glob.glob("failed_*.xml")
for f in sorted(failed_files):
    diagnose_sitemap(f)
