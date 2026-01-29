"""
Pytest Configuration and Shared Fixtures

Provides test client, mock services, and common test data.
"""

import asyncio
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import MagicMock

import numpy as np
import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.config import AppSettings, CameraSettings, InferenceSettings, StreamSettings
from app.core.camera_manager import CameraManager
from app.core.event_handler import EventHandler
from app.core.inference_engine import InferenceEngine
from app.core.model_registry import ModelRegistry
from app.core.roi_manager import ROIManager
from app.core.stream_publisher import StreamPublisher
from app.main import create_app
from app.services.system_monitor import SystemMonitor


@pytest.fixture
def app_settings(tmp_path: Path) -> AppSettings:
    """Create test application settings with temp directories."""
    settings = AppSettings(
        debug=True,
        app_name="NPU Platform Test",
    )
    settings.storage.data_dir = tmp_path / "data"
    settings.storage.models_dir = tmp_path / "models"
    settings.storage.data_dir.mkdir(parents=True, exist_ok=True)
    settings.storage.models_dir.mkdir(parents=True, exist_ok=True)
    (settings.storage.data_dir / "logs").mkdir(exist_ok=True)
    (settings.storage.data_dir / "roi_presets").mkdir(exist_ok=True)
    (settings.storage.data_dir / "snapshots").mkdir(exist_ok=True)
    return settings


@pytest.fixture
def camera_settings() -> CameraSettings:
    return CameraSettings(max_cameras=4)


@pytest.fixture
def inference_settings() -> InferenceSettings:
    return InferenceSettings()


@pytest.fixture
def stream_settings() -> StreamSettings:
    return StreamSettings()


@pytest.fixture
def camera_manager(camera_settings: CameraSettings) -> CameraManager:
    return CameraManager(camera_settings)


@pytest.fixture
def inference_engine(inference_settings: InferenceSettings) -> InferenceEngine:
    return InferenceEngine(inference_settings)


@pytest.fixture
def roi_manager(tmp_path: Path) -> ROIManager:
    presets_dir = tmp_path / "roi_presets"
    presets_dir.mkdir(exist_ok=True)
    return ROIManager(presets_dir)


@pytest.fixture
def stream_publisher(stream_settings: StreamSettings) -> StreamPublisher:
    return StreamPublisher(stream_settings)


@pytest.fixture
def event_handler() -> EventHandler:
    return EventHandler()


@pytest.fixture
def sample_frame() -> np.ndarray:
    """Create a sample test frame (640x480 BGR)."""
    return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)


@pytest.fixture
def test_client() -> TestClient:
    """Create FastAPI test client."""
    app = create_app()
    return TestClient(app)
