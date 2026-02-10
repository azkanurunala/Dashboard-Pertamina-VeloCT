import os
import csv

def check_csv_headers(directory):
    print(f"\nAudit for: {directory}")
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist.")
        return
    files = [f for f in os.listdir(directory) if f.endswith('.csv')]
    for file in files:
        path = os.path.join(directory, file)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader)
                print(f"File: {file} | Columns: {headers}")
        except Exception as e:
            try:
                # Try latin-1 if utf-8 fails
                with open(path, 'r', encoding='latin-1') as f:
                    reader = csv.reader(f)
                    headers = next(reader)
                    print(f"File: {file} | Columns: {headers}")
            except Exception as e2:
                print(f"Error reading {file}: {e2}")

check_csv_headers(r'azure_functions\references\news')
check_csv_headers(r'azure_functions\references\sentiment')
check_csv_headers(r'azure_functions\references\data')
