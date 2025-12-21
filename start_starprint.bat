@echo off
echo ========================================
echo    StarPrint - Star Citizen 3D Exporter
echo ========================================
echo.
echo Starting server...
echo.
echo Once loaded, open your browser to:
echo    http://127.0.0.1:8000
echo.
echo Press Ctrl+C to stop the server.
echo ========================================
echo.

cd /d "%~dp0"
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

pause
