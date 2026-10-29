@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m coursepulse.cli gui --data data/demo
if errorlevel 1 goto fail
exit /b 0
:fail
echo Startup failed. Check the message above. Python 3.11 or 3.12 with Tkinter is required.
pause
exit /b 1
