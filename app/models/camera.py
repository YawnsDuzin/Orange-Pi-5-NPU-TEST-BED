"""
Camera Data Models

Pydantic schemas for camera configuration, state, and API payloads.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CameraType(str, Enum):
    """Supported camera types."""
    RTSP = "rtsp"
    USB = "usb"
    CSI = "csi"
    FILE = "file"


class CameraStatus(str, Enum):
    """Camera connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    STOPPED = "stopped"


class CameraCreate(BaseModel):
    """Schema for creating a new camera."""
    name: str = Field(..., min_length=1, max_length=100, description="Camera display name")
    url: str = Field(..., min_length=1, description="Camera URL (RTSP) or device path")
    camera_type: CameraType = Field(default=CameraType.RTSP, description="Camera type")
    enabled: bool = Field(default=True, description="Enable camera on creation")
    reconnect_interval: int = Field(default=5, ge=1, le=300, description="Reconnect interval (seconds)")
    description: Optional[str] = Field(default=None, max_length=500, description="Camera description")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str, info) -> str:
        v = v.strip()
        if not v:
            raise ValueError("URL cannot be empty")
        return v


class CameraUpdate(BaseModel):
    """Schema for updating a camera."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    url: Optional[str] = Field(default=None, min_length=1)
    camera_type: Optional[CameraType] = None
    enabled: Optional[bool] = None
    reconnect_interval: Optional[int] = Field(default=None, ge=1, le=300)
    description: Optional[str] = Field(default=None, max_length=500)


class CameraConfig(BaseModel):
    """Full camera configuration."""
    id: str = Field(..., description="Unique camera identifier")
    name: str = Field(..., description="Camera display name")
    url: str = Field(..., description="Camera URL or device path")
    camera_type: CameraType = Field(default=CameraType.RTSP)
    enabled: bool = Field(default=True)
    reconnect_interval: int = Field(default=5)
    buffer_size: int = Field(default=1)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CameraState(BaseModel):
    """Camera runtime state."""
    id: str
    name: str
    status: CameraStatus = CameraStatus.DISCONNECTED
    fps: float = 0.0
    frame_count: int = 0
    resolution: Optional[str] = None
    error_message: str = ""
    last_frame_time: Optional[datetime] = None
    uptime_seconds: float = 0.0


class CameraResponse(BaseModel):
    """API response for camera info."""
    config: CameraConfig
    state: CameraState


class CameraListResponse(BaseModel):
    """API response for camera list."""
    cameras: list[CameraResponse]
    total: int
