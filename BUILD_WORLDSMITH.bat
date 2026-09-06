@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "PYTHON=py"
where py >nul 2>nul || set "PYTHON=python"

if not exist "build_logs" mkdir "build_logs"
set "LOG=build_logs\worldsmith_build.log"

echo ============================================================ > "%LOG%"
echo WorldSmith AI - Windows build >> "%LOG%"
echo ============================================================ >> "%LOG%"
echo.
echo [1/6] Checking Python...
echo [1/6] Checking Python... >> "%LOG%"
%PYTHON% --version >> "%LOG%" 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.10+ is required.
    echo Install Python from python.org, then run this file again.
    echo ERROR: Python unavailable. >> "%LOG%"
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [2/6] Creating virtual environment...
    echo [2/6] Creating virtual environment... >> "%LOG%"
    %PYTHON% -m venv .venv >> "%LOG%" 2>&1
    if errorlevel 1 goto :error
) else (
    echo [2/6] Virtual environment already exists.
)

set "VENV_PY=.venv\Scripts\python.exe"
set "VENV_PIP=.venv\Scripts\python.exe -m pip"

echo [3/6] Updating build tools...
echo [3/6] Updating build tools... >> "%LOG%"
%VENV_PIP% install --upgrade pip setuptools wheel >> "%LOG%" 2>&1
if errorlevel 1 goto :error

echo [4/6] Installing WorldSmith dependencies...
echo [4/6] Installing WorldSmith dependencies... >> "%LOG%"
%VENV_PIP% install -r requirements.txt pyinstaller >> "%LOG%" 2>&1
if errorlevel 1 goto :error

echo [5/6] Running tests...
echo [5/6] Running tests... >> "%LOG%"
%VENV_PY% -m pytest -q >> "%LOG%" 2>&1
if errorlevel 1 (
    echo ERROR: Tests failed. The EXE was NOT built.
    echo See %LOG% for details.
    goto :error_no_pause
)

%VENV_PY% -m compileall -q worldsmith >> "%LOG%" 2>&1
if errorlevel 1 goto :error

echo [6/6] Building WorldSmithAI.exe...
echo [6/6] Building WorldSmithAI.exe... >> "%LOG%"
%VENV_PY% -m PyInstaller --noconfirm --clean worldsmith.spec >> "%LOG%" 2>&1
if errorlevel 1 goto :error

if not exist "dist\WorldSmithAI.exe" (
    echo ERROR: PyInstaller finished without creating dist\WorldSmithAI.exe
    goto :error
)

echo.
echo ============================================================
echo BUILD SUCCESSFUL
echo ============================================================
echo EXE: %CD%\dist\WorldSmithAI.exe
echo Log: %CD%\%LOG%
echo.
echo You can now double-click WorldSmithAI.exe.
echo API keys are entered by each user inside WorldSmith Settings.
echo.
pause
exit /b 0

:error
echo.
echo ============================================================
echo BUILD FAILED
 echo ============================================================
echo See %LOG% for the full error log.
:error_no_pause
pause
exit /b 1
