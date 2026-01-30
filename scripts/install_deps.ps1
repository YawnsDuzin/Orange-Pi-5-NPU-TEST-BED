# =============================================================================
# NPU Inference Platform - Windows Dependency Installation Script (PowerShell)
# =============================================================================
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\install_deps.ps1
#
# Prerequisites:
#   - Python 3.10+ (https://python.org)
#   - Node.js 18+ (https://nodejs.org) [optional, for Tailwind CSS build]

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "NPU Inference Platform - Windows Setup" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

function Write-Info($msg)  { Write-Host "[INFO] $msg" -ForegroundColor Green }
function Write-Warn($msg)  { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg)   { Write-Host "[ERROR] $msg" -ForegroundColor Red }

# 1. Check Python
Write-Info "Checking Python installation..."
try {
    $pyVersion = python --version 2>&1
    Write-Info "Found: $pyVersion"
} catch {
    Write-Err "Python not found. Please install Python 3.10+ from https://python.org"
    Write-Err "Make sure to check 'Add Python to PATH' during installation."
    exit 1
}

# 2. Create virtual environment
Write-Info "Setting up Python virtual environment..."
$venvDir = ".venv"
if (-not (Test-Path $venvDir)) {
    python -m venv $venvDir
    Write-Info "Virtual environment created: $venvDir"
} else {
    Write-Info "Virtual environment already exists: $venvDir"
}

# 3. Activate and install dependencies
Write-Info "Installing Python packages..."
& "$venvDir\Scripts\python.exe" -m pip install --upgrade pip
& "$venvDir\Scripts\pip.exe" install -r requirements.txt

# 4. RKNN note
Write-Warn "RKNN Toolkit2 Lite is ARM64/Linux only and will NOT be installed on Windows."
Write-Warn "The platform will run in MOCK mode for NPU inference on Windows."
Write-Warn "This is expected for development and testing purposes."

# 5. Node.js / Tailwind CSS (optional)
Write-Info "Checking Node.js for Tailwind CSS build..."
try {
    $nodeVersion = node --version 2>&1
    Write-Info "Found Node.js: $nodeVersion"
    npm install
    npm run build:css
    Write-Info "Tailwind CSS built successfully"
} catch {
    Write-Warn "Node.js not found. Tailwind CSS build skipped."
    Write-Warn "The UI will still work using the pre-built CSS (if available)."
    Write-Warn "Install Node.js from https://nodejs.org if you need CSS customization."
}

# 6. Create data directories
Write-Info "Creating data directories..."
$dirs = @(
    "data\roi_presets",
    "data\snapshots",
    "data\logs",
    "models\detection",
    "models\segmentation",
    "models\pose",
    "models\face",
    "models\ocr",
    "models\classification"
)
foreach ($d in $dirs) {
    if (-not (Test-Path $d)) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
    }
}
Write-Info "Data directories ready"

# 7. Verify installation
Write-Info "Verifying installation..."
Write-Host ""
& "$venvDir\Scripts\python.exe" -c @"
import sys
print(f'Python: {sys.version}')
print(f'Platform: {sys.platform}')

try:
    import fastapi
    print(f'FastAPI: {fastapi.__version__}')
except: print('FastAPI: NOT INSTALLED')

try:
    import cv2
    print(f'OpenCV: {cv2.__version__}')
except: print('OpenCV: NOT INSTALLED')

try:
    import numpy
    print(f'NumPy: {numpy.__version__}')
except: print('NumPy: NOT INSTALLED')

try:
    import uvicorn
    print(f'Uvicorn: {uvicorn.__version__}')
except: print('Uvicorn: NOT INSTALLED')

try:
    import psutil
    print(f'psutil: {psutil.__version__}')
except: print('psutil: NOT INSTALLED')

try:
    from rknnlite.api import RKNNLite
    print('RKNN Lite: Available')
except: print('RKNN Lite: NOT AVAILABLE (expected on Windows)')
"@

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Info "Installation complete!"
Write-Host ""
Write-Info "To start the platform:"
Write-Info "  .venv\Scripts\activate"
Write-Info "  uvicorn app.main:app --host 127.0.0.1 --port 8000"
Write-Host ""
Write-Info "For development (with auto-reload):"
Write-Info "  uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
Write-Host ""
Write-Info "Then open http://127.0.0.1:8000 in your browser"
Write-Host "==============================================" -ForegroundColor Cyan
