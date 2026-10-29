@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m coursepulse.cli report --data data/demo --as-of 2026-10-29T18:00:00+03:00 --output reports/current
if errorlevel 1 goto fail
start "" "%~dp0reports\current\report.html"
pause
exit /b 0
:fail
echo Failed. Read the error above.
pause
exit /b 1
