bacpac_path = r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\pei-dashboard_copy.bacpac'
try:
    with open(bacpac_path, 'rb') as f:
        header = f.read(4)
        print(f"Header: {header.hex()}")
        if header == b'PK\x03\x04':
            print("✅ File is a valid ZIP/BACPAC")
        else:
            print("❌ File is NOT a standard ZIP/BACPAC")
except Exception as e:
    print(f"❌ Error: {e}")
