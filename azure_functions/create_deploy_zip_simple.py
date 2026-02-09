import zipfile
import os
import sys

# Use current directory
current_dir = os.getcwd()
zip_filename = "manual_deploy.zip"
zip_path = os.path.join(current_dir, zip_filename)

print(f"Creating zip in: {current_dir}")
print(f"Target file: {zip_path}")

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

try:
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        count = 0
        for root, dirs, files in os.walk(current_dir):
            # Modify dirs in-place to prune traversals
            dirs[:] = [d for d in dirs if d not in exclusions]
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, current_dir)
                
                # Check exclusions for file path parts
                if any(excl in rel_path.split(os.sep) for excl in exclusions):
                    continue
                    
                zipf.write(file_path, rel_path)
                count += 1
                
    print(f"Success! Created {zip_filename} with {count} files.")
    print(f"Size: {os.path.getsize(zip_path) / 1024 / 1024:.2f} MB")

except Exception as e:
    print(f"ERROR: {e}")
