
import os
from glob import glob

data_dir = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\references\data'
output_file = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\references\data\csv_inspection_results.txt'

files = glob(os.path.join(data_dir, '*.csv'))
results = []

for file_path in files:
    filename = os.path.basename(file_path)
    if filename.startswith('~$') or filename == 'csv_inspection_results.txt': continue
    
    res = f"[{filename}]\n"
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            res += f"Headers: {f.readline().strip()}\n"
            res += f"Line 2:  {f.readline().strip()}\n"
    except Exception as e:
        res += f"Error: {e}\n"
    
    results.append(res)

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("\n".join(results))

print(f"Results written to {output_file}")
