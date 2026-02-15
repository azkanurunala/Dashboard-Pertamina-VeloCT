
import pandas as pd
import os

file_path = r'azure_functions\references\data\(Data)RUPTL.csv'
encodings = ['utf-8', 'latin-1', 'cp1252']

for encoding in encodings:
    try:
        print(f"Trying encoding: {encoding}")
        df = pd.read_csv(file_path, encoding=encoding)
        print("Success!")
        print("Columns:", list(df.columns))
        print("First row:", df.iloc[0].to_dict())
        break
    except Exception as e:
        print(f"Error with {encoding}: {e}")
