import zipfile
import os
import sys

log_file = r"c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\debug_zip.log"

def log(msg):
    with open(log_file, "a") as f:
        f.write(msg + "\n")
    print(msg)

source_dir = r"c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions"
zip_path = r"c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions\manual_deploy.zip"

exclusions = [
    "deploy.zip",
    "manual_deploy.zip",
    ".venv",
    ".python_packages",
    "__pycache__",
    ".git",
    ".vscode",
    "bin",
    "obj",
    "tests",
    "local.settings.json"
]

log("Starting zip process...")
try:
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        count = 0
        for root, dirs, files in os.walk(source_dir):
            if ".venv" in dirs:
                dirs.remove(".venv") # Optimization
            if ".python_packages" in dirs:
                dirs.remove(".python_packages")
                
            dirs[:] = [d for d in dirs if d not in exclusions]
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, source_dir)
                if not any(excl in rel_path.split(os.sep) for excl in exclusions):
                     zipf.write(file_path, rel_path)
                     count += 1
                     if count % 100 == 0:
                         log(f"Zipped {count} files...")

    log(f"Created {zip_path}, size: {os.path.getsize(zip_path) / 1024 / 1024:.2f} MB")
except Exception as e:
    log(f"Error: {e}")
    sys.exit(1)
