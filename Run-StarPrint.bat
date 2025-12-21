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

:: Check for cgf-converter.exe
if not exist "tools\cgf-converter.exe" (
    echo.
    echo Downloading cgf-converter.exe...
    if not exist "tools" mkdir tools
    
    :: Download the latest release zip from GitHub
    powershell -Command "& {Invoke-WebRequest -Uri 'https://github.com/Markemp/Cryengine-Converter/releases/download/1.0.2.7/cgf-converter_1.0.2.7.zip' -OutFile 'tools\cgf-converter.zip'}"
    
    :: Extract just the exe
    powershell -Command "& {Expand-Archive -Path 'tools\cgf-converter.zip' -DestinationPath 'tools' -Force}"
    
    :: Clean up zip
    del "tools\cgf-converter.zip" 2>nul
    
    echo cgf-converter.exe downloaded successfully!
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

:: Run the server
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

pause
