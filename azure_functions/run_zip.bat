@echo off
cd /d c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions
echo Starting zip creation... > zip_output.txt
python create_deploy_zip.py >> zip_output.txt 2>&1
echo Done. >> zip_output.txt
