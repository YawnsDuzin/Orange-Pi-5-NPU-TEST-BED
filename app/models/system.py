"""
System Data Models

Pydantic schemas for system monitoring, health, and configuration.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class CPUInfo(BaseModel):
    """CPU usage information."""
    usage_percent: float = Field(default=0.0, description="CPU usage percentage")
    frequency_mhz: float = Field(default=0.0, description="Current frequency in MHz")
    core_count: int = Field(default=0, description="Number of CPU cores")
    per_core_usage: list[float] = Field(default_factory=list, description="Per-core usage")


class NPUInfo(BaseModel):
    """NPU usage information."""
    usage_percent: float = Field(default=0.0, description="NPU usage percentage")
    available: bool = Field(default=False, description="NPU available")
    core_count: int = Field(default=3, description="Number of NPU cores")
    driver_version: str = Field(default="", description="NPU driver version")


class MemoryInfo(BaseModel):
    """Memory usage information."""
    total_mb: float = 0.0
    used_mb: float = 0.0
    available_mb: float = 0.0
    usage_percent: float = 0.0


class TemperatureInfo(BaseModel):
    """Temperature sensor information."""
    cpu_temp: float = Field(default=0.0, description="CPU temperature (°C)")
    npu_temp: float = Field(default=0.0, description="NPU temperature (°C)")
    gpu_temp: float = Field(default=0.0, description="GPU temperature (°C)")


class DiskInfo(BaseModel):
    """Disk usage information."""
    total_gb: float = 0.0
    used_gb: float = 0.0
    free_gb: float = 0.0
    usage_percent: float = 0.0


class NetworkInfo(BaseModel):
    """Network interface information."""
    interface: str = ""
    ip_address: str = ""
    bytes_sent: int = 0
    bytes_recv: int = 0


class SystemStatus(BaseModel):
    """Complete system status."""
    cpu: CPUInfo = Field(default_factory=CPUInfo)
    npu: NPUInfo = Field(default_factory=NPUInfo)
    memory: MemoryInfo = Field(default_factory=MemoryInfo)
    temperature: TemperatureInfo = Field(default_factory=TemperatureInfo)
    disk: DiskInfo = Field(default_factory=DiskInfo)
    network: list[NetworkInfo] = Field(default_factory=list)
    uptime_seconds: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)


class HealthCheck(BaseModel):
    """Application health check."""
    status: str = "ok"
    version: str = ""
    uptime_seconds: float = 0.0
    cameras_connected: int = 0
    models_loaded: int = 0
    npu_available: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)


class LogEntry(BaseModel):
    """Log entry for the log viewer."""
    timestamp: datetime
    level: str
    logger: str
    message: str


class LogResponse(BaseModel):
    """API response for log entries."""
    entries: list[LogEntry]
    total: int
    has_more: bool = False


class AppConfig(BaseModel):
    """Exportable application configuration."""
    cameras: list[dict[str, Any]] = Field(default_factory=list)
    models: list[dict[str, Any]] = Field(default_factory=list)
    roi_presets: list[dict[str, Any]] = Field(default_factory=list)
    inference_configs: list[dict[str, Any]] = Field(default_factory=list)
    exported_at: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"


class EventRecord(BaseModel):
    """Recorded event."""
    id: str
    event_type: str
    camera_id: str
    timestamp: datetime
    data: dict[str, Any] = Field(default_factory=dict)
    snapshot_path: Optional[str] = None
    acknowledged: bool = False
