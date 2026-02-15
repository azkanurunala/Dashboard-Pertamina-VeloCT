
import os
import pandas as pd
from glob import glob

data_dir = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\references\data'
files = glob(os.path.join(data_dir, '*.*'))

print(f"Inspecting {len(files)} files...")

for file_path in files:
    filename = os.path.basename(file_path)
    if filename.startswith('~$'): continue # Skip temp files
    print(f"\n[{filename}]")
    try:
        if filename.endswith('.csv'):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline().strip()
                print(f"Headers: {first_line}")
        elif filename.endswith('.xlsx') or filename.endswith('.xls'):
            xl = pd.ExcelFile(file_path)
            for sheet in xl.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet, nrows=0)
                print(f"Sheet '{sheet}' Headers: {list(df.columns)}")
    except Exception as e:
        print(f"Error: {e}")
