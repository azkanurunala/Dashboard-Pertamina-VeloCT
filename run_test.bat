@echo off
set PYTHONUNBUFFERED=1
python azure_functions/tests/test_e2e_pipeline.py
echo %ERRORLEVEL% > status.txt
