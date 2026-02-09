import zipfile
import os
import sys

bacpac_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\pei-dashboard.bacpac'
dest_dir = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\temp_bacpac'

if not os.path.exists(dest_dir):
    os.makedirs(dest_dir)

print(f"Opening {bacpac_path}...")
try:
    with zipfile.ZipFile(bacpac_path, 'r') as zip_ref:
        print("Scaning file list...")
        namelist = zip_ref.namelist()
        print(f"Found {len(namelist)} files.")
        
        model_file = 'model.xml'
        if model_file in namelist:
            print(f"Extracting {model_file} to {dest_dir}...")
            zip_ref.extract(model_file, dest_dir)
            print("✅ Extraction successful!")
        else:
            # Maybe it's in a subdirectory
            matches = [f for f in namelist if f.endswith('model.xml')]
            if matches:
                 print(f"Extracting {matches[0]} to {dest_dir}...")
                 zip_ref.extract(matches[0], dest_dir)
                 print("✅ Extraction successful!")
            else:
                print(f"❌ 'model.xml' not found in bacpac. Contents: {namelist[:10]}...")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
