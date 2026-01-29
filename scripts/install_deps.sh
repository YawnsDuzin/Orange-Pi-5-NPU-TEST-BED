#!/bin/bash
# =============================================================================
# NPU Inference Platform - Dependency Installation Script
# For Orange Pi 5 Plus (RK3588) running Ubuntu/Debian
# =============================================================================

set -e

echo "=============================================="
echo "NPU Inference Platform - Dependency Installer"
echo "=============================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running on ARM64 (Orange Pi 5)
ARCH=$(uname -m)
info "Architecture: $ARCH"

# 1. System packages
info "Installing system packages..."
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    libopencv-dev \
    python3-opencv \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    ffmpeg \
    v4l-utils \
    nodejs \
    npm

# 2. Python virtual environment
info "Setting up Python virtual environment..."
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv $VENV_DIR
fi
source $VENV_DIR/bin/activate

# 3. Python packages
info "Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. RKNN Toolkit2 Lite (for Orange Pi 5 / RK3588)
if [ "$ARCH" = "aarch64" ]; then
    info "Installing RKNN Toolkit2 Lite for ARM64..."

    # Check if already installed
    if python3 -c "import rknnlite" 2>/dev/null; then
        info "RKNN Toolkit2 Lite already installed"
    else
        warn "RKNN Toolkit2 Lite not found."
        echo "Please install it manually from:"
        echo "  https://github.com/rockchip-linux/rknn-toolkit2"
        echo ""
        echo "Example (for Python 3.10):"
        echo "  pip install rknn_toolkit_lite2-2.0.0b0-cp310-cp310-linux_aarch64.whl"
    fi
else
    warn "Not running on ARM64. RKNN Lite will not be installed."
    warn "RKNN Toolkit2 (x86) can be used for model conversion."
fi

# 5. Node.js / Tailwind CSS
info "Installing Tailwind CSS..."
if command -v npm &> /dev/null; then
    npm install
    npm run build:css
    info "Tailwind CSS built successfully"
else
    warn "npm not found. Tailwind CSS build skipped."
fi

# 6. Create data directories
info "Creating data directories..."
mkdir -p data/{roi_presets,snapshots,logs}
mkdir -p models/{detection,segmentation,pose,face,ocr,classification}

# 7. Verify installation
info "Verifying installation..."
echo ""
python3 -c "
import sys
print(f'Python: {sys.version}')

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
    from rknnlite.api import RKNNLite
    print('RKNN Lite: Available')
except: print('RKNN Lite: NOT AVAILABLE (expected on non-ARM)')
"

echo ""
info "=============================================="
info "Installation complete!"
info ""
info "To start the platform:"
info "  source .venv/bin/activate"
info "  uvicorn app.main:app --host 0.0.0.0 --port 8000"
info ""
info "For development (with auto-reload):"
info "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
info "=============================================="
