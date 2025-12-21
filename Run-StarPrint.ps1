<#
.SYNOPSIS
    Automated launcher for StarPrint.

.DESCRIPTION
    This script sets up a local Python environment, installs dependencies, 
    downloads cgf-converter, and runs the StarPrint server.

.NOTES
    Author: Gemini
    Date: 2025-12-21
#>

$ErrorActionPreference = "Stop"

trap {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "AN ERROR OCCURRED" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Details:" -ForegroundColor Yellow
    Write-Host $_.ScriptStackTrace -ForegroundColor Gray
    Write-Host ""
    Write-Host "If this is a Python error, scroll up to see the full traceback." -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Red
    Pause
    exit 1
}

$ScriptDir = $PSScriptRoot
$VenvDir = Join-Path $ScriptDir ".venv"
$PythonExec = "python"
$PipExec = Join-Path $VenvDir "Scripts/pip.exe"
$ToolsDir = Join-Path $ScriptDir "tools"

# ANSI Colors
$Green = "[32m"
$Yellow = "[33m"
$Red = "[31m"
$Reset = "[0m"

function Write-Log {
    param([string]$Message, [string]$Color = $Reset)
    Write-Host "$([char]27)$Color$Message$([char]27)$Reset"
}

function Test-Command {
    param([string]$Name)
    try {
        Get-Command $Name -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

Write-Log "=== StarPrint - SC 3D Print Extractor ===" $Green

# 1. Check for Git (REQUIRED for scdatatools)
if (-not (Test-Command "git")) {
    Write-Log "Error: Git is not installed or not in your PATH." $Red
    Write-Log "StarPrint requires Git to download core libraries." $Yellow
    Write-Log "Please install Git for Windows: https://git-scm.com/download/win" $Yellow
    Write-Log "IMPORTANT: Select 'Git from the command line and also from 3rd-party software' during install." $Yellow
    Pause
    exit 1
}
Write-Log "Git found." $Green

# 2. Check for Python
Write-Log "Checking for Python..." $Yellow
try {
    $PyVersion = & $PythonExec --version 2>&1
    if ($PyVersion -match "3\.(10|11|12|13)") {
        Write-Log "Found $PyVersion" $Green
    }
    else {
        throw "Python 3.10+ not found. Found: $PyVersion"
    }
}
catch {
    Write-Log "Python 3.10 or newer not found." $Red
    Write-Log "Please install Python from: https://python.org" $Yellow
    Write-Log "Make sure to check 'Add Python to PATH' during installation." $Yellow
    Pause
    exit 1
}

# 3. Create Virtual Environment
if (-not (Test-Path $VenvDir)) {
    Write-Log "Creating virtual environment in .venv..." $Yellow
    & $PythonExec -m venv $VenvDir
    if (-not $?) {
        Write-Log "Failed to create virtual environment." $Red
        Pause
        exit 1
    }
    Write-Log "Virtual environment created." $Green
}
else {
    Write-Log "Virtual environment already exists." $Green
}

# 4. Install Dependencies
Write-Log "Installing dependencies (this may take a few minutes on first run)..." $Yellow

# Upgrade pip first
$VenvPython = Join-Path $VenvDir "Scripts/python.exe"
& $VenvPython -m pip install --upgrade pip --quiet 2>$null

# Install requirements (VERBOSELY)
& $PipExec install -r (Join-Path $ScriptDir "requirements.txt")
if (-not $?) {
    Write-Log "ERROR: Failed to install dependencies." $Red
    Write-Log "Common issues:" $Yellow
    Write-Log "1. Git not installed correctly (reinstall Git for Windows)" $Yellow
    Write-Log "2. Firewall blocking pip/git" $Yellow
    Write-Log "3. Python version mismatch" $Yellow
    Pause
    exit 1
}

# Double check scdatatools specifically (don't let trap catch this)
Write-Log "Verifying scdatatools installation..." $Yellow
$ErrorActionPreference = "Continue"  # Temporarily disable trap
& $VenvPython -c "import scdatatools; print('scdatatools OK')"
$scResult = $LASTEXITCODE
$ErrorActionPreference = "Stop"  # Re-enable trap

if ($scResult -ne 0) {
    Write-Log "ERROR: scdatatools import failed. See error above." $Red
    Write-Log "This usually means a dependency version conflict." $Yellow
    Write-Log "Trying to force reinstall..." $Yellow
    & $PipExec install "git+https://gitlab.com/scmodding/frameworks/scdatatools.git@devel" --force-reinstall
    if (-not $?) {
        Write-Log "Still failed. Please check your internet/git connection." $Red
        Pause
        exit 1
    }
}

Write-Log "Dependencies installed and verified." $Green

# 5. Download cgf-converter if not present
if (-not (Test-Path $ToolsDir)) {
    New-Item -ItemType Directory -Path $ToolsDir -Force | Out-Null
}

$CgfConverterPath = Join-Path $ToolsDir "cgf-converter.exe"
if (-not (Test-Path $CgfConverterPath)) {
    Write-Log "Downloading cgf-converter.exe (this may take a minute)..." $Yellow
    $CgfConverterUrl = "https://github.com/Markemp/Cryengine-Converter/releases/download/v1.7.1/cgf-converter.exe"
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $CgfConverterUrl -OutFile $CgfConverterPath -UseBasicParsing
        Write-Log "cgf-converter.exe downloaded successfully." $Green
    }
    catch {
        Write-Log "Warning: Failed to download cgf-converter.exe." $Yellow
        Write-Log "Please download manually from: https://github.com/Markemp/Cryengine-Converter/releases" $Yellow
    }
}
else {
    Write-Log "cgf-converter.exe already present." $Green
}

Write-Log "Setup complete!" $Green

# 6. Start the server
Write-Log "---------------------------------------------------"
Write-Log "Starting StarPrint server..." $Green
Write-Log "Opening browser at http://localhost:8000" $Yellow
Write-Log "Press Ctrl+C to stop the server." $Yellow
Write-Log "---------------------------------------------------"

# Open browser
Start-Process "http://localhost:8000"

# Run server
& $VenvPython -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

if (-not $?) {
    Write-Log "Server exited with an error." $Red
}

Write-Log "---------------------------------------------------"
Pause
