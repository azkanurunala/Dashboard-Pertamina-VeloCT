
import os
import pandas as pd
import csv
from glob import glob

data_dir = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\references\data'
files = glob(os.path.join(data_dir, '*.*'))

print(f"Inspecting {len(files)} files in {data_dir}...")

for file_path in files:
    filename = os.path.basename(file_path)
    print(f"\n--- {filename} ---")
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(file_path, nrows=3)
            print(f"Columns: {list(df.columns)}")
            print(df.head(2))
        elif filename.endswith('.xlsx') or filename.endswith('.xls'):
            xl = pd.ExcelFile(file_path)
            print(f"Sheets: {xl.sheet_names}")
            for sheet in xl.sheet_names:
                print(f"  Sheet: {sheet}")
                df = pd.read_excel(file_path, sheet_name=sheet, nrows=3)
                print(f"  Columns: {list(df.columns)}")
                print(df.head(1))
        else:
            print(f"Skipping unknown file type: {filename}")
    except Exception as e:
        print(f"Error reading {filename}: {e}")
