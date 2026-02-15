
import os
import pandas as pd
import glob

data_dir = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\references\data'
output_log = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\data_audit.txt'

audit_results = []

files = glob.glob(os.path.join(data_dir, "*"))

for f in files:
    filename = os.path.basename(f)
    audit_results.append(f"=== {filename} ===")
    try:
        if filename.endswith('.csv'):
            # Try a few encodings
            df = None
            for enc in ['utf-8-sig', 'latin-1', 'cp1252']:
                try:
                    df = pd.read_csv(f, nrows=5, encoding=enc)
                    break
                except:
                    continue
            if df is not None:
                audit_results.append(f"Columns: {list(df.columns)}")
                audit_results.append("Sample:\n" + df.to_string())
            else:
                audit_results.append("Error: Could not read CSV with standard encodings")
        elif filename.endswith('.xlsx'):
            xls = pd.ExcelFile(f)
            audit_results.append(f"Sheets: {xls.sheet_names}")
            for sheet in xls.sheet_names:
                df = pd.read_excel(f, sheet_name=sheet, nrows=5)
                audit_results.append(f"--- Sheet: {sheet} ---")
                audit_results.append(f"Columns: {list(df.columns)}")
                audit_results.append("Sample:\n" + df.to_string())
        else:
            audit_results.append("Skip: Not a supported data file")
    except Exception as e:
        audit_results.append(f"Error: {e}")
    audit_results.append("\n" + "="*30 + "\n")

with open(output_log, 'w', encoding='utf-8') as f:
    f.write("\n".join(audit_results))

print(f"Audit completed: {output_log}")
