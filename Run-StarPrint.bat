@echo off
echo ============================================
echo     StarPrint - SC 3D Print Extractor
echo ============================================
echo.

:: Change to script directory
cd /d "%~dp0"

:: Check for Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

:: Create venv if not exists
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

:: Activate venv and install requirements
echo Installing dependencies...
call .venv\Scripts\activate.bat
pip install -q --disable-pip-version-check -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install dependencies. Check requirements.txt
    pause
    exit /b 1
)

:: Check for cgf-converter.exe
if not exist "tools\cgf-converter.exe" (
    echo.
    echo Downloading cgf-converter.exe (this may take a moment)...
    if not exist "tools" mkdir tools
    
    :: Download the exe directly from latest release
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/Markemp/Cryengine-Converter/releases/download/v1.7.1/cgf-converter.exe' -OutFile 'tools\cgf-converter.exe'}"
    
    if exist "tools\cgf-converter.exe" (
        echo cgf-converter.exe downloaded successfully!
    ) else (
        echo WARNING: Failed to download cgf-converter.exe
        echo Please download manually from: https://github.com/Markemp/Cryengine-Converter/releases
        echo and place it in the tools folder.
    )
)

:: Start server
echo.
echo Starting StarPrint server...
echo Opening browser at http://localhost:8000
echo.
echo Press Ctrl+C to stop the server.
echo.

:: Open browser after a short delay
start "" "http://localhost:8000"

:: Run the server using python -m to ensure it works
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

pause
