import zipfile
import os

bacpac_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\pei-dashboard.bacpac'
dest_dir = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\temp_bacpac'

if not os.path.exists(dest_dir):
    os.makedirs(dest_dir)

print(f"Opening {bacpac_path}...")
try:
    with zipfile.ZipFile(bacpac_path, 'r') as zip_ref:
        model_file = 'model.xml'
        if model_file in zip_ref.namelist():
            print(f"Extracting {model_file}...")
            zip_ref.extract(model_file, dest_dir)
            print("✅ Extraction successful!")
        else:
            print(f"❌ '{model_file}' not found in bacpac. Contents: {zip_ref.namelist()[:10]}...")
except Exception as e:
    print(f"❌ Error: {e}")
