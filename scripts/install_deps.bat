@echo off
REM =============================================================================
REM NPU Inference Platform - Windows Dependency Installation Script (Batch)
REM =============================================================================
REM
REM Usage: scripts\install_deps.bat
REM
REM Prerequisites:
REM   - Python 3.10+ (https://python.org)
REM   - Node.js 18+ (https://nodejs.org) [optional, for Tailwind CSS build]

echo ==============================================
echo NPU Inference Platform - Windows Setup
echo ==============================================
echo.

REM 1. Check Python
echo [INFO] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ from https://python.org
    echo [ERROR] Make sure to check 'Add Python to PATH' during installation.
    exit /b 1
)
python --version

REM 2. Create virtual environment
echo [INFO] Setting up Python virtual environment...
if not exist ".venv" (
    python -m venv .venv
    echo [INFO] Virtual environment created: .venv
) else (
    echo [INFO] Virtual environment already exists: .venv
)

REM 3. Install Python packages
echo [INFO] Installing Python packages...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\pip.exe install -r requirements.txt

REM 4. RKNN note
echo.
echo [WARN] RKNN Toolkit2 Lite is ARM64/Linux only - will NOT be installed on Windows.
echo [WARN] The platform will run in MOCK mode for NPU inference.
echo.

REM 5. Node.js / Tailwind CSS
echo [INFO] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [WARN] Node.js not found. Tailwind CSS build skipped.
    echo [WARN] Install from https://nodejs.org if you need CSS customization.
) else (
    echo [INFO] Installing npm packages and building CSS...
    call npm install
    call npm run build:css
    echo [INFO] Tailwind CSS built successfully
)

REM 6. Create data directories
echo [INFO] Creating data directories...
if not exist "data\roi_presets" mkdir "data\roi_presets"
if not exist "data\snapshots" mkdir "data\snapshots"
if not exist "data\logs" mkdir "data\logs"
if not exist "models\detection" mkdir "models\detection"
if not exist "models\segmentation" mkdir "models\segmentation"
if not exist "models\pose" mkdir "models\pose"
if not exist "models\face" mkdir "models\face"
if not exist "models\ocr" mkdir "models\ocr"
if not exist "models\classification" mkdir "models\classification"

REM 7. Verify
echo.
echo [INFO] Verifying installation...
.venv\Scripts\python.exe -c "import sys; print(f'Python: {sys.version}')"
.venv\Scripts\python.exe -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')" 2>nul || echo FastAPI: NOT INSTALLED
.venv\Scripts\python.exe -c "import cv2; print(f'OpenCV: {cv2.__version__}')" 2>nul || echo OpenCV: NOT INSTALLED
.venv\Scripts\python.exe -c "import uvicorn; print(f'Uvicorn: {uvicorn.__version__}')" 2>nul || echo Uvicorn: NOT INSTALLED
.venv\Scripts\python.exe -c "import psutil; print(f'psutil: {psutil.__version__}')" 2>nul || echo psutil: NOT INSTALLED

echo.
echo ==============================================
echo [INFO] Installation complete!
echo.
echo [INFO] To start the platform:
echo        .venv\Scripts\activate
echo        uvicorn app.main:app --host 127.0.0.1 --port 8000
echo.
echo [INFO] Then open http://127.0.0.1:8000 in your browser
echo ==============================================
