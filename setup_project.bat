@echo off
setlocal enabledelayedexpansion

REM ----------------------------------------------
REM One-click project setup (Windows CMD .bat)
REM - Creates .venv if missing
REM - Activates it for this script
REM - Upgrades pip
REM - Installs requirements.txt (if present)
REM - Runs a small smoke test
REM - Optionally opens VS Code
REM ----------------------------------------------

REM Jump to the folder this script is in
cd /d "%~dp0"

echo.
echo === Checking for Python on PATH ===
where python >nul 2>&1
if errorlevel 1 (
  echo.
  echo Python is NOT installed or not on PATH.
  echo 1) Install Python from: https://www.python.org/downloads/
  echo 2) IMPORTANT: Check "Add Python to PATH" during install.
  echo.
  pause
  goto :eof
)

echo.
echo === Creating virtual environment (.venv) if needed ===
if not exist ".venv" (
  python -m venv .venv
  if errorlevel 1 (
    echo Failed to create virtual environment.
    pause
    goto :eof
  )
) else (
  echo .venv already exists. Skipping creation.
)

echo.
echo === Activating .venv for this script ===
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
  echo Failed to activate .venv
  pause
  goto :eof
)

echo.
echo === Upgrading pip ===
python -m pip install --upgrade pip

echo.
if exist "requirements.txt" (
  echo === Installing requirements.txt ===
  python -m pip install -r requirements.txt
) else (
  echo No requirements.txt found. Skipping dependency install.
)

echo.
echo === Smoke test: run a tiny experiment (optional) ===
if exist "src\run_experiment.py" (
  python -m src.run_experiment --scenario adaptive --runs 1 --steps 50
) else (
  echo src\run_experiment.py not found. Skipping smoke test.
)

echo.
echo === All set! ===
echo If you want to open this folder in VS Code now, press any key.
pause >nul
where code >nul 2>&1 && code .

endlocal
