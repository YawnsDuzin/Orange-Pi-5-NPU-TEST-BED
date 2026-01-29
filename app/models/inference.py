"""
Inference Data Models

Pydantic schemas for model management, inference configuration,
and inference results.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ModelType(str, Enum):
    """Supported model types."""
    DETECTION = "detection"
    SEGMENTATION = "segmentation"
    POSE = "pose"
    CLASSIFICATION = "classification"
    FACE_DETECTION = "face_detection"
    FACE_RECOGNITION = "face_recognition"
    OCR = "ocr"


class ModelStatus(str, Enum):
    """Model loading status."""
    AVAILABLE = "available"
    LOADING = "loading"
    LOADED = "loaded"
    ERROR = "error"
    UNLOADING = "unloading"


class ModelInfo(BaseModel):
    """Model metadata information."""
    id: str = Field(..., description="Unique model identifier")
    name: str = Field(..., description="Model display name")
    filename: str = Field(..., description="Model filename")
    model_type: ModelType = Field(..., description="Model type")
    input_size: list[int] = Field(default=[640, 640], description="Input dimensions [w, h]")
    classes: list[str] = Field(default_factory=list, description="Class label list")
    num_classes: int = Field(default=0, description="Number of classes")
    description: Optional[str] = Field(default=None, description="Model description")
    file_size_mb: float = Field(default=0.0, description="File size in MB")
    quantization: str = Field(default="int8", description="Quantization type")
    created_at: datetime = Field(default_factory=datetime.now)


class ModelState(BaseModel):
    """Model runtime state."""
    id: str
    status: ModelStatus = ModelStatus.AVAILABLE
    is_active: bool = False
    load_time_ms: float = 0.0
    total_inferences: int = 0
    avg_inference_ms: float = 0.0
    error_message: str = ""


class ModelResponse(BaseModel):
    """API response for model info."""
    info: ModelInfo
    state: ModelState


class ModelListResponse(BaseModel):
    """API response for model list."""
    models: list[ModelResponse]
    total: int
    active_model_id: Optional[str] = None


class InferenceConfig(BaseModel):
    """Inference configuration parameters."""
    confidence_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence threshold"
    )
    nms_threshold: float = Field(
        default=0.45, ge=0.0, le=1.0, description="NMS threshold"
    )
    class_filter: list[str] = Field(
        default_factory=list, description="Filter specific classes (empty = all)"
    )
    max_detections: int = Field(
        default=100, ge=1, le=1000, description="Maximum detections per frame"
    )


class InferenceControl(BaseModel):
    """Inference control commands."""
    camera_id: str = Field(..., description="Target camera ID")
    model_id: str = Field(..., description="Model to use")
    enabled: bool = Field(default=True, description="Enable/disable inference")
    config: InferenceConfig = Field(default_factory=InferenceConfig)


class BoundingBox(BaseModel):
    """Detection bounding box."""
    x1: float
    y1: float
    x2: float
    y2: float


class Detection(BaseModel):
    """Single object detection result."""
    bbox: BoundingBox
    class_name: str
    class_id: int
    confidence: float
    track_id: Optional[int] = None


class SegmentationMask(BaseModel):
    """Segmentation mask data."""
    class_name: str
    class_id: int
    confidence: float
    mask_rle: Optional[str] = None  # Run-length encoded mask


class PoseKeypoint(BaseModel):
    """Single pose keypoint."""
    x: float
    y: float
    confidence: float
    name: Optional[str] = None


class PoseResult(BaseModel):
    """Pose estimation result for one person."""
    bbox: BoundingBox
    confidence: float
    keypoints: list[PoseKeypoint]


class ClassificationResult(BaseModel):
    """Classification result."""
    class_name: str
    class_id: int
    confidence: float


class InferenceResult(BaseModel):
    """Complete inference result for a single frame."""
    model_id: str
    model_type: ModelType
    camera_id: str
    frame_id: int = 0
    timestamp: float
    inference_time_ms: float
    preprocess_time_ms: float = 0.0
    postprocess_time_ms: float = 0.0
    total_time_ms: float = 0.0

    # Results by type (only relevant field populated)
    detections: list[Detection] = Field(default_factory=list)
    segmentations: list[SegmentationMask] = Field(default_factory=list)
    poses: list[PoseResult] = Field(default_factory=list)
    classifications: list[ClassificationResult] = Field(default_factory=list)

    # Aggregate metrics
    object_count: int = 0
    fps: float = 0.0


class InferenceStats(BaseModel):
    """Inference performance statistics."""
    model_id: str
    camera_id: str
    total_frames: int = 0
    avg_inference_ms: float = 0.0
    min_inference_ms: float = 0.0
    max_inference_ms: float = 0.0
    avg_fps: float = 0.0
    avg_objects_per_frame: float = 0.0
    uptime_seconds: float = 0.0
