import zipfile
import os

bacpac_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\pei-dashboard.bacpac'

print(f"Reading {bacpac_path}...")
try:
    with zipfile.ZipFile(bacpac_path, 'r') as zip_ref:
        print("Files in bacpac:")
        for name in zip_ref.namelist():
            print(f" - {name}")
            if 'model.xml' in name.lower():
                print(f"--- CONTENT OF {name} ---")
                with zip_ref.open(name) as f:
                    print(f.read().decode('utf-8'))
                print("--- END OF CONTENT ---")
except Exception as e:
    print(f"❌ Error: {e}")
