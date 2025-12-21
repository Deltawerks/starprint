@echo off
:: Wrapper to run PowerShell script (bypasses execution policy issues)
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0Run-StarPrint.ps1"
pause
