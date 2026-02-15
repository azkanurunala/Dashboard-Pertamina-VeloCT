import csv
import os

file_path = r'azure_functions\references\sentiment\(Summary)All.csv'
if os.path.exists(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        first_row = next(reader)
        print(f"Header: {header}")
        print(f"First Row: {first_row}")
else:
    print(f"File not found: {file_path}")
