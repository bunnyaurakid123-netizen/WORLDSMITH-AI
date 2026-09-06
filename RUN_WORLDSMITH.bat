@echo off
setlocal
cd /d "%~dp0"

if exist "dist\WorldSmithAI.exe" (
    start "WorldSmith AI" "dist\WorldSmithAI.exe"
    exit /b 0
)

if not exist ".venv\Scripts\python.exe" (
    call "%~dp0BUILD_WORLDSMITH.bat"
    if errorlevel 1 exit /b 1
)

.venv\Scripts\python.exe run_worldsmith.py
