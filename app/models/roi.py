"""
ROI (Region of Interest) Data Models

Pydantic schemas for ROI configuration, presets, and event data.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ROIType(str, Enum):
    """ROI shape types."""
    POLYGON = "polygon"
    RECTANGLE = "rectangle"
    LINE = "line"


class ROIAction(str, Enum):
    """ROI action types."""
    INCLUDE = "include"   # Process only inside this ROI
    EXCLUDE = "exclude"   # Skip detections in this ROI
    ALERT = "alert"       # Trigger alert on entry/presence


class Point(BaseModel):
    """Normalized 2D point (0.0 ~ 1.0)."""
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)


class ROICreate(BaseModel):
    """Schema for creating a new ROI."""
    name: str = Field(..., min_length=1, max_length=100, description="ROI display name")
    roi_type: ROIType = Field(..., description="ROI shape type")
    points: list[Point] = Field(..., min_length=2, description="ROI vertices (normalized)")
    action: ROIAction = Field(default=ROIAction.INCLUDE, description="ROI action")
    color: str = Field(default="#00ff00", description="Display color (hex)")
    enabled: bool = Field(default=True, description="Enable ROI")

    @field_validator("points")
    @classmethod
    def validate_points(cls, v: list[Point], info) -> list[Point]:
        roi_type = info.data.get("roi_type")
        if roi_type == ROIType.LINE and len(v) != 2:
            raise ValueError("Line ROI must have exactly 2 points")
        if roi_type == ROIType.RECTANGLE and len(v) != 2:
            raise ValueError("Rectangle ROI must have exactly 2 points (top-left, bottom-right)")
        if roi_type == ROIType.POLYGON and len(v) < 3:
            raise ValueError("Polygon ROI must have at least 3 points")
        return v


class ROIConfig(BaseModel):
    """Full ROI configuration."""
    id: str = Field(..., description="Unique ROI identifier")
    name: str
    roi_type: ROIType
    points: list[Point]
    action: ROIAction = ROIAction.INCLUDE
    color: str = "#00ff00"
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.now)


class ROIUpdate(BaseModel):
    """Schema for updating an ROI."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    points: Optional[list[Point]] = None
    action: Optional[ROIAction] = None
    color: Optional[str] = None
    enabled: Optional[bool] = None


class ROIPreset(BaseModel):
    """ROI preset - a saved collection of ROIs for a camera."""
    id: str = Field(..., description="Preset identifier")
    camera_id: str = Field(..., description="Associated camera ID")
    name: str = Field(..., min_length=1, max_length=100, description="Preset name")
    rois: list[ROIConfig] = Field(default_factory=list, description="ROI list")
    is_active: bool = Field(default=False, description="Currently active preset")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ROIPresetCreate(BaseModel):
    """Schema for creating a ROI preset."""
    camera_id: str
    name: str = Field(..., min_length=1, max_length=100)
    rois: list[ROICreate] = Field(default_factory=list)


class ROIPresetResponse(BaseModel):
    """API response for ROI preset."""
    preset: ROIPreset
    camera_id: str


class ROIListResponse(BaseModel):
    """API response for ROI presets list."""
    presets: list[ROIPreset]
    total: int


class LineCrossingEvent(BaseModel):
    """Line crossing event data."""
    track_id: int
    roi_id: str
    roi_name: str
    direction: str  # "in" or "out"
    timestamp: float
    camera_id: str


class ROIAlertEvent(BaseModel):
    """ROI alert event data."""
    roi_id: str
    roi_name: str
    camera_id: str
    object_count: int
    class_names: list[str]
    timestamp: float
    snapshot_path: Optional[str] = None
