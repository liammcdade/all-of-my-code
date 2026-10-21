@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo  DASHBOARD BUILD SCRIPT
echo ============================================================
echo.

REM --- 1. Force Python 3.11 ---
set "PY_CMD=py -3.11"
%PY_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Python 3.11 not found via 'py' launcher. 
    echo Falling back to default 'python' on PATH.
    echo.
    set "PY_CMD=python"
) else (
    echo Using Python 3.11...
)

REM --- 2. Create/Reuse a clean build environment ---
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo Creating clean isolated build environment in .venv folder...
    %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo Activating .venv...
call ".venv\Scripts\activate.bat"

REM --- 3. Install ONLY what is strictly needed ---
echo Checking dependencies...
python -c "import PyQt5, numpy, tqdm" >nul 2>&1
if errorlevel 1 (
    echo.
    echo Installing minimal dependencies into .venv - this may take a minute...
    python -m pip install --upgrade pip >nul
    python -m pip install PyQt5 numpy tqdm pyinstaller==6.12.0
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

REM --- 4. Clean old builds ---
echo.
echo Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist"  rmdir /s /q "dist"
if exist "dashboard.spec" del /q "dashboard.spec"

REM --- 5. Build with --collect-all ---
echo.
echo Building dashboard.exe...
echo Using --collect-all to prevent the NumPy C-extension crash
echo.

python -m PyInstaller ^
  --onefile ^
  --windowed ^
  --noconfirm ^
  --clean ^
  --name dashboard ^
  --collect-all numpy ^
  --collect-all tqdm ^
  --exclude-module PySide6 ^
  --exclude-module PySide2 ^
  --exclude-module PyQt6 ^
  --exclude-module pandas ^
  --exclude-module scipy ^
  --exclude-module matplotlib ^
  --exclude-module PIL ^
  --exclude-module IPython ^
  --exclude-module pytest ^
  --exclude-module pygame ^
  --exclude-module tkinter ^
  main.py

if errorlevel 1 (
    echo.
    echo ============================================================
    echo  BUILD FAILED. Check the errors above.
    echo ============================================================
    pause
    exit /b 1
)

REM --- 6. Post-Build Verification ---
if not exist "dist\dashboard.exe" (
    echo.
    echo ============================================================
    echo  ERROR: PyInstaller succeeded, but dist\dashboard.exe is missing!
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  BUILD COMPLETE: dist\dashboard.exe
echo ============================================================
echo.
echo IMPORTANT REMINDER FOR DEPLOYMENT:
echo To run the exe, you must copy your league folders into the dist\ folder
echo next to dashboard.exe, OR run the exe from the source tree.
echo.
echo Folders needed next to dashboard.exe:
echo   - european_leagues\
echo   - premier-league\
echo   - worldcupwomens\
echo.
pause