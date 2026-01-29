"""
Model Registry Module

Manages the catalog of available RKNN models.
Handles model discovery, metadata management, and file operations.
"""

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

import aiofiles

from app.config import InferenceSettings
from app.models.inference import ModelInfo, ModelState, ModelStatus, ModelType

logger = logging.getLogger(__name__)

# Default model metadata mapping (filename pattern → model type)
MODEL_TYPE_HINTS: dict[str, ModelType] = {
    "yolov5": ModelType.DETECTION,
    "yolov8": ModelType.DETECTION,
    "yolov8n": ModelType.DETECTION,
    "yolov8s": ModelType.DETECTION,
    "yolov11": ModelType.DETECTION,
    "yolo": ModelType.DETECTION,
    "ssd": ModelType.DETECTION,
    "seg": ModelType.SEGMENTATION,
    "pose": ModelType.POSE,
    "resnet": ModelType.CLASSIFICATION,
    "mobilenet": ModelType.CLASSIFICATION,
    "efficientnet": ModelType.CLASSIFICATION,
    "retinaface": ModelType.FACE_DETECTION,
    "scrfd": ModelType.FACE_DETECTION,
    "arcface": ModelType.FACE_RECOGNITION,
    "ppocr": ModelType.OCR,
    "paddle": ModelType.OCR,
}

# Subdirectory to model type mapping
SUBDIR_TYPE_MAP: dict[str, ModelType] = {
    "detection": ModelType.DETECTION,
    "segmentation": ModelType.SEGMENTATION,
    "pose": ModelType.POSE,
    "classification": ModelType.CLASSIFICATION,
    "face": ModelType.FACE_DETECTION,
    "ocr": ModelType.OCR,
}

METADATA_FILENAME = "model_metadata.json"


class ModelRegistry:
    """
    Model Registry - catalog of available RKNN models.

    Scans the models directory, maintains metadata, and provides
    model discovery and upload capabilities.
    """

    def __init__(self, models_dir: Path, settings: InferenceSettings):
        self._models_dir = models_dir
        self._settings = settings
        self._models: dict[str, ModelInfo] = {}
        self._states: dict[str, ModelState] = {}
        self._metadata_path = models_dir / METADATA_FILENAME

    @property
    def models(self) -> dict[str, ModelInfo]:
        return dict(self._models)

    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """Get model info by ID."""
        return self._models.get(model_id)

    def get_state(self, model_id: str) -> Optional[ModelState]:
        """Get model state by ID."""
        return self._states.get(model_id)

    def get_all(self) -> list[tuple[ModelInfo, ModelState]]:
        """Get all models with their states."""
        result = []
        for mid, info in self._models.items():
            state = self._states.get(mid, ModelState(id=mid))
            result.append((info, state))
        return result

    async def scan_models(self) -> int:
        """Scan models directory and register discovered models."""
        logger.info(f"Scanning models directory: {self._models_dir}")

        # Load saved metadata
        saved_metadata = await self._load_metadata()

        count = 0
        for subdir in self._models_dir.iterdir():
            if not subdir.is_dir() or subdir.name.startswith("."):
                continue

            for model_file in subdir.glob("*.rknn"):
                model_id = self._generate_model_id(model_file)

                # Use saved metadata if available
                if model_id in saved_metadata:
                    info = ModelInfo(**saved_metadata[model_id])
                else:
                    info = self._create_model_info(model_file, subdir.name)

                self._models[info.id] = info
                self._states[info.id] = ModelState(id=info.id, status=ModelStatus.AVAILABLE)
                count += 1

        # Also scan root level
        for model_file in self._models_dir.glob("*.rknn"):
            model_id = self._generate_model_id(model_file)
            if model_id not in self._models:
                info = self._create_model_info(model_file, "")
                self._models[info.id] = info
                self._states[info.id] = ModelState(id=info.id, status=ModelStatus.AVAILABLE)
                count += 1

        logger.info(f"Found {count} models")
        await self._save_metadata()
        return count

    async def register_model(
        self,
        filename: str,
        model_type: ModelType,
        name: Optional[str] = None,
        classes: Optional[list[str]] = None,
        input_size: Optional[list[int]] = None,
        description: Optional[str] = None,
    ) -> ModelInfo:
        """Register a new model with explicit metadata."""
        model_path = self._find_model_file(filename)
        if model_path is None:
            raise FileNotFoundError(f"Model file not found: {filename}")

        model_id = self._generate_model_id(model_path)
        file_size = os.path.getsize(model_path) / (1024 * 1024)

        info = ModelInfo(
            id=model_id,
            name=name or model_path.stem,
            filename=str(model_path),
            model_type=model_type,
            input_size=input_size or [640, 640],
            classes=classes or [],
            num_classes=len(classes) if classes else 0,
            description=description,
            file_size_mb=round(file_size, 2),
        )

        self._models[model_id] = info
        self._states[model_id] = ModelState(id=model_id, status=ModelStatus.AVAILABLE)
        await self._save_metadata()

        logger.info(f"Model registered: {info.name} ({model_id})")
        return info

    async def upload_model(
        self,
        file_content: bytes,
        filename: str,
        model_type: ModelType,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ModelInfo:
        """Upload and register a new model file."""
        # Validate extension
        if not filename.endswith(".rknn"):
            raise ValueError("Only .rknn files are supported")

        # Determine target directory
        type_dir = self._models_dir / model_type.value
        type_dir.mkdir(parents=True, exist_ok=True)

        target_path = type_dir / filename
        if target_path.exists():
            # Add suffix to avoid overwrite
            stem = target_path.stem
            suffix = target_path.suffix
            counter = 1
            while target_path.exists():
                target_path = type_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        # Write file
        async with aiofiles.open(target_path, "wb") as f:
            await f.write(file_content)

        logger.info(f"Model file uploaded: {target_path}")

        return await self.register_model(
            filename=str(target_path),
            model_type=model_type,
            name=name,
            description=description,
        )

    async def remove_model(self, model_id: str, delete_file: bool = False) -> bool:
        """Remove a model from the registry."""
        info = self._models.get(model_id)
        if info is None:
            return False

        if delete_file:
            model_path = Path(info.filename)
            if model_path.exists():
                model_path.unlink()
                logger.info(f"Model file deleted: {model_path}")

        del self._models[model_id]
        self._states.pop(model_id, None)
        await self._save_metadata()

        logger.info(f"Model removed from registry: {model_id}")
        return True

    def update_state(self, model_id: str, **kwargs) -> None:
        """Update model runtime state."""
        state = self._states.get(model_id)
        if state:
            for key, value in kwargs.items():
                if hasattr(state, key):
                    setattr(state, key, value)

    def _create_model_info(self, model_path: Path, subdir_name: str) -> ModelInfo:
        """Create ModelInfo from file path with inferred metadata."""
        model_id = self._generate_model_id(model_path)
        model_type = self._infer_model_type(model_path, subdir_name)
        file_size = os.path.getsize(model_path) / (1024 * 1024)

        return ModelInfo(
            id=model_id,
            name=model_path.stem,
            filename=str(model_path),
            model_type=model_type,
            file_size_mb=round(file_size, 2),
        )

    def _infer_model_type(self, model_path: Path, subdir_name: str) -> ModelType:
        """Infer model type from filename and directory."""
        # Check subdirectory
        if subdir_name in SUBDIR_TYPE_MAP:
            return SUBDIR_TYPE_MAP[subdir_name]

        # Check filename patterns
        name_lower = model_path.stem.lower()
        for pattern, model_type in MODEL_TYPE_HINTS.items():
            if pattern in name_lower:
                return model_type

        return ModelType.DETECTION  # default

    def _find_model_file(self, filename: str) -> Optional[Path]:
        """Find a model file by name, searching all subdirectories."""
        path = Path(filename)
        if path.is_absolute() and path.exists():
            return path

        # Search in models directory
        for f in self._models_dir.rglob("*.rknn"):
            if f.name == filename or str(f) == filename:
                return f
        return None

    @staticmethod
    def _generate_model_id(model_path: Path) -> str:
        """Generate a stable model ID from file path."""
        # Use relative path hash for stability
        return model_path.stem.lower().replace(" ", "_").replace("-", "_")

    async def _load_metadata(self) -> dict:
        """Load saved model metadata."""
        if not self._metadata_path.exists():
            return {}
        try:
            async with aiofiles.open(self._metadata_path, "r") as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.warning(f"Failed to load model metadata: {e}")
            return {}

    async def _save_metadata(self) -> None:
        """Save model metadata."""
        try:
            metadata = {}
            for mid, info in self._models.items():
                metadata[mid] = info.model_dump(mode="json")

            self._metadata_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(self._metadata_path, "w") as f:
                await f.write(json.dumps(metadata, indent=2, default=str))
        except Exception as e:
            logger.error(f"Failed to save model metadata: {e}")
