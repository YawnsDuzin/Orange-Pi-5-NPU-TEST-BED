"""
Application Configuration Module

Centralized configuration management using Pydantic Settings.
Supports environment variables, .env files, and runtime overrides.
"""

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"


class ServerSettings(BaseSettings):
    """Server configuration."""

    host: str = Field(default="0.0.0.0", description="Server bind address")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of workers (must be 1 for NPU)")
    reload: bool = Field(default=False, description="Auto-reload on code changes")
    log_level: str = Field(default="info", description="Logging level")

    model_config = SettingsConfigDict(env_prefix="SERVER_")


class CameraSettings(BaseSettings):
    """Camera/stream configuration."""

    max_cameras: int = Field(default=8, description="Maximum concurrent cameras")
    reconnect_interval: int = Field(default=5, description="Reconnect interval in seconds")
    reconnect_max_retries: int = Field(default=0, description="Max reconnect retries (0=unlimited)")
    frame_buffer_size: int = Field(default=1, description="Frame buffer size per camera")
    default_fps_limit: int = Field(default=30, description="Default FPS limit")
    rtsp_transport: str = Field(default="tcp", description="RTSP transport protocol (tcp/udp)")
    capture_timeout_ms: int = Field(default=5000, description="Capture read timeout in ms")

    model_config = SettingsConfigDict(env_prefix="CAMERA_")


class InferenceSettings(BaseSettings):
    """NPU inference configuration."""

    default_confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Default confidence threshold")
    default_nms_threshold: float = Field(default=0.45, ge=0.0, le=1.0, description="Default NMS threshold")
    default_core_mask: int = Field(default=7, description="NPU core mask (7=all cores)")
    max_loaded_models: int = Field(default=3, description="Maximum simultaneously loaded models")
    inference_timeout_ms: int = Field(default=1000, description="Inference timeout in ms")
    enable_frame_skip: bool = Field(default=True, description="Skip frames when inference is slow")

    model_config = SettingsConfigDict(env_prefix="INFERENCE_")

    @field_validator("default_core_mask")
    @classmethod
    def validate_core_mask(cls, v: int) -> int:
        valid_masks = {1, 2, 4, 3, 5, 6, 7}  # NPU core combinations
        if v not in valid_masks:
            raise ValueError(f"Invalid core mask {v}. Valid: {valid_masks}")
        return v


class StreamSettings(BaseSettings):
    """Stream output configuration."""

    mjpeg_quality: int = Field(default=80, ge=1, le=100, description="MJPEG JPEG quality")
    mjpeg_max_fps: int = Field(default=30, description="MJPEG max FPS")
    ws_max_fps: int = Field(default=30, description="WebSocket max FPS")
    preview_scale: float = Field(default=0.5, ge=0.1, le=1.0, description="Preview thumbnail scale")
    max_ws_clients: int = Field(default=10, description="Max WebSocket clients per stream")

    model_config = SettingsConfigDict(env_prefix="STREAM_")


class StorageSettings(BaseSettings):
    """Storage and data configuration."""

    data_dir: Path = Field(default=DATA_DIR, description="Data directory path")
    models_dir: Path = Field(default=MODELS_DIR, description="Models directory path")
    config_file: str = Field(default="config.json", description="Main config filename")
    max_snapshots: int = Field(default=1000, description="Max stored snapshots")
    max_log_size_mb: int = Field(default=100, description="Max log file size in MB")
    snapshot_quality: int = Field(default=95, ge=1, le=100, description="Snapshot JPEG quality")

    model_config = SettingsConfigDict(env_prefix="STORAGE_")


class NotificationSettings(BaseSettings):
    """Notification/alert configuration."""

    mqtt_enabled: bool = Field(default=False, description="Enable MQTT notifications")
    mqtt_broker: str = Field(default="localhost", description="MQTT broker address")
    mqtt_port: int = Field(default=1883, description="MQTT broker port")
    mqtt_topic_prefix: str = Field(default="npu-platform", description="MQTT topic prefix")
    webhook_enabled: bool = Field(default=False, description="Enable webhook notifications")
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL")
    webhook_timeout: int = Field(default=10, description="Webhook timeout in seconds")

    model_config = SettingsConfigDict(env_prefix="NOTIFY_")


class SecuritySettings(BaseSettings):
    """Security configuration."""

    enable_auth: bool = Field(default=False, description="Enable authentication")
    api_key: Optional[str] = Field(default=None, description="API key for authentication")
    cors_origins: list[str] = Field(default=["*"], description="Allowed CORS origins")
    max_upload_size_mb: int = Field(default=500, description="Max upload file size in MB")
    allowed_model_extensions: list[str] = Field(
        default=[".rknn"], description="Allowed model file extensions"
    )

    model_config = SettingsConfigDict(env_prefix="SECURITY_")


class AppSettings(BaseSettings):
    """Root application settings aggregating all sub-settings."""

    app_name: str = Field(default="NPU Inference Platform", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")

    server: ServerSettings = Field(default_factory=ServerSettings)
    camera: CameraSettings = Field(default_factory=CameraSettings)
    inference: InferenceSettings = Field(default_factory=InferenceSettings)
    stream: StreamSettings = Field(default_factory=StreamSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    notification: NotificationSettings = Field(default_factory=NotificationSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
    )


def get_settings() -> AppSettings:
    """Get application settings singleton."""
    return AppSettings()
