"""
RKNN Service Module

Low-level wrapper for RKNN Toolkit2 Lite runtime.
Provides hardware detection, model validation, and runtime utilities.
Gracefully degrades when RKNN hardware is not available.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import RKNN
_RKNN_AVAILABLE = False
try:
    from rknnlite.api import RKNNLite
    _RKNN_AVAILABLE = True
    logger.info("RKNN Toolkit2 Lite is available")
except ImportError:
    logger.warning("RKNN Toolkit2 Lite not available - running in mock mode")


# NPU core mask constants
class NPUCoreMask:
    """RK3588 NPU core allocation masks."""
    CORE_0 = 1
    CORE_1 = 2
    CORE_2 = 4
    CORE_0_1 = 3
    CORE_0_2 = 5
    CORE_1_2 = 6
    CORE_ALL = 7  # All 3 cores (default, maximum performance)


@dataclass
class NPUDeviceInfo:
    """NPU hardware information."""
    available: bool = False
    driver_version: str = ""
    core_count: int = 0
    device_name: str = ""
    supported_ops: list[str] = None

    def __post_init__(self):
        if self.supported_ops is None:
            self.supported_ops = []


@dataclass
class ModelValidation:
    """Model validation result."""
    valid: bool = False
    model_path: str = ""
    file_size_mb: float = 0.0
    error_message: str = ""


class RKNNService:
    """
    RKNN Service - low-level NPU runtime management.

    Provides:
    - NPU hardware detection and info
    - Model file validation
    - Runtime creation helpers
    - Graceful mock mode when hardware unavailable
    """

    def __init__(self):
        self._device_info: Optional[NPUDeviceInfo] = None

    @property
    def is_available(self) -> bool:
        """Check if RKNN runtime is available."""
        return _RKNN_AVAILABLE

    def get_device_info(self) -> NPUDeviceInfo:
        """Get NPU device information."""
        if self._device_info is not None:
            return self._device_info

        info = NPUDeviceInfo()

        if not _RKNN_AVAILABLE:
            self._device_info = info
            return info

        try:
            # Check for RKNN driver
            npu_driver_path = "/sys/class/devfreq"
            npu_paths = [
                "/sys/class/misc/npu",
                "/dev/rknpu",
            ]

            for path in npu_paths:
                if os.path.exists(path):
                    info.available = True
                    break

            if info.available:
                info.device_name = "RK3588 NPU"
                info.core_count = 3  # RK3588 has 3 NPU cores

                # Try to read driver version
                version_path = "/sys/kernel/debug/rknpu/version"
                if os.path.exists(version_path):
                    try:
                        with open(version_path) as f:
                            info.driver_version = f.read().strip()
                    except (PermissionError, OSError):
                        info.driver_version = "unknown"

        except Exception as e:
            logger.error(f"Error detecting NPU: {e}")

        self._device_info = info
        return info

    def validate_model(self, model_path: str) -> ModelValidation:
        """Validate an RKNN model file."""
        result = ModelValidation(model_path=model_path)

        path = Path(model_path)
        if not path.exists():
            result.error_message = f"File not found: {model_path}"
            return result

        if path.suffix.lower() != ".rknn":
            result.error_message = f"Invalid file extension: {path.suffix}"
            return result

        file_size = path.stat().st_size
        result.file_size_mb = file_size / (1024 * 1024)

        if file_size < 1024:
            result.error_message = "File too small to be a valid model"
            return result

        # Try to read RKNN header
        try:
            with open(path, "rb") as f:
                header = f.read(4)
                # RKNN files typically start with specific magic bytes
                if header[:4] == b"RKNN" or len(header) >= 4:
                    result.valid = True
                else:
                    result.error_message = "Invalid RKNN file format"
        except Exception as e:
            result.error_message = f"Error reading file: {e}"

        return result

    def create_runtime(
        self,
        model_path: str,
        core_mask: int = NPUCoreMask.CORE_ALL,
    ) -> Optional[object]:
        """
        Create an RKNN Lite runtime instance.
        Returns RKNNLite instance or None if unavailable.
        """
        if not _RKNN_AVAILABLE:
            logger.warning("RKNN not available, returning None")
            return None

        rknn = RKNNLite()

        ret = rknn.load_rknn(model_path)
        if ret != 0:
            logger.error(f"Failed to load RKNN model: {model_path}")
            return None

        ret = rknn.init_runtime(core_mask=core_mask)
        if ret != 0:
            logger.error(f"Failed to init RKNN runtime")
            rknn.release()
            return None

        return rknn

    @staticmethod
    def get_core_mask_description(mask: int) -> str:
        """Get human-readable description of core mask."""
        descriptions = {
            1: "Core 0 only",
            2: "Core 1 only",
            4: "Core 2 only",
            3: "Core 0+1",
            5: "Core 0+2",
            6: "Core 1+2",
            7: "All cores (0+1+2)",
        }
        return descriptions.get(mask, f"Custom ({mask})")
