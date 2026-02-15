
import os
import pandas as pd
p = r"c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\references\data\(Data)CPO.csv"
try:
    df = pd.read_csv(p, nrows=5, encoding='latin-1')
    print("COLUMNS:")
    print(df.columns.tolist())
    print("SAMPLE:")
    print(df.head(1).to_dict('records'))
except Exception as e:
    print(f"Error: {e}")
