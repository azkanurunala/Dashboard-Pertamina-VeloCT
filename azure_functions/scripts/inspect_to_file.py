
import os
import pandas as pd
from glob import glob

data_dir = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\references\data'
output_file = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\references\data\inspection_results.txt'

files = glob(os.path.join(data_dir, '*.*'))
results = []

for file_path in files:
    filename = os.path.basename(file_path)
    if filename.startswith('~$') or filename == 'inspection_results.txt': continue
    
    res = f"[{filename}]\n"
    try:
        if filename.endswith('.csv'):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                res += f"Headers: {f.readline().strip()}\n"
                res += f"Line 2:  {f.readline().strip()}\n"
        elif filename.endswith('.xlsx') or filename.endswith('.xls'):
            xl = pd.ExcelFile(file_path)
            for sheet in xl.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet, nrows=2)
                res += f"Sheet '{sheet}' Columns: {list(df.columns)}\n"
                res += f"Sample: {df.head(1).to_dict('records')}\n"
    except Exception as e:
        res += f"Error: {e}\n"
    
    results.append(res)

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("\n".join(results))

print(f"Results written to {output_file}")
