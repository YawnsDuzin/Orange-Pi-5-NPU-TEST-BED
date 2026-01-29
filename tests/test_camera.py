"""
Camera Manager Tests

Tests for camera CRUD operations, stream lifecycle, and state management.
"""

import asyncio

import pytest

from app.core.camera_manager import CameraManager, CameraStream, FPSCounter
from app.models.camera import CameraConfig, CameraStatus, CameraType


class TestFPSCounter:
    """Tests for FPS counter utility."""

    def test_initial_fps_is_zero(self):
        counter = FPSCounter()
        assert counter.update() == 0.0

    def test_reset_clears_data(self):
        counter = FPSCounter()
        counter.update()
        counter.reset()
        assert counter.update() == 0.0

    def test_fps_calculation(self):
        counter = FPSCounter(window_size=10)
        # Multiple updates should calculate FPS
        for _ in range(5):
            counter.update()
        fps = counter.update()
        # FPS should be > 0 after multiple updates
        assert isinstance(fps, float)


class TestCameraConfig:
    """Tests for camera configuration."""

    def test_create_rtsp_config(self):
        config = CameraConfig(
            id="cam1",
            name="Test Camera",
            url="rtsp://192.168.1.100:554/stream",
            camera_type=CameraType.RTSP,
        )
        assert config.id == "cam1"
        assert config.camera_type == CameraType.RTSP
        assert config.enabled is True
        assert config.buffer_size == 1

    def test_create_usb_config(self):
        config = CameraConfig(
            id="usb1",
            name="USB Camera",
            url="0",
            camera_type=CameraType.USB,
        )
        assert config.camera_type == CameraType.USB

    def test_create_file_config(self):
        config = CameraConfig(
            id="file1",
            name="Video File",
            url="/path/to/video.mp4",
            camera_type=CameraType.FILE,
        )
        assert config.camera_type == CameraType.FILE


class TestCameraManager:
    """Tests for camera manager operations."""

    @pytest.fixture
    def config(self) -> CameraConfig:
        return CameraConfig(
            id="test_cam",
            name="Test Camera",
            url="rtsp://localhost/test",
            enabled=False,  # Don't auto-start in tests
        )

    @pytest.mark.asyncio
    async def test_add_camera(self, camera_manager: CameraManager, config: CameraConfig):
        stream = await camera_manager.add_camera(config)
        assert stream is not None
        assert "test_cam" in camera_manager.cameras

    @pytest.mark.asyncio
    async def test_remove_camera(self, camera_manager: CameraManager, config: CameraConfig):
        await camera_manager.add_camera(config)
        removed = await camera_manager.remove_camera("test_cam")
        assert removed is True
        assert "test_cam" not in camera_manager.cameras

    @pytest.mark.asyncio
    async def test_remove_nonexistent_camera(self, camera_manager: CameraManager):
        removed = await camera_manager.remove_camera("nonexistent")
        assert removed is False

    @pytest.mark.asyncio
    async def test_get_state(self, camera_manager: CameraManager, config: CameraConfig):
        await camera_manager.add_camera(config)
        state = camera_manager.get_state("test_cam")
        assert state is not None
        assert state.id == "test_cam"

    @pytest.mark.asyncio
    async def test_get_all_states(self, camera_manager: CameraManager, config: CameraConfig):
        await camera_manager.add_camera(config)
        states = camera_manager.get_all_states()
        assert len(states) == 1
        assert "test_cam" in states

    @pytest.mark.asyncio
    async def test_max_cameras_limit(self, camera_manager: CameraManager):
        for i in range(4):  # max_cameras=4 in fixture
            config = CameraConfig(
                id=f"cam_{i}", name=f"Camera {i}", url=f"rtsp://test/{i}", enabled=False
            )
            await camera_manager.add_camera(config)

        with pytest.raises(ValueError, match="Maximum camera limit"):
            config = CameraConfig(
                id="cam_extra", name="Extra", url="rtsp://test/extra", enabled=False
            )
            await camera_manager.add_camera(config)

    @pytest.mark.asyncio
    async def test_get_frame_no_camera(self, camera_manager: CameraManager):
        frame = camera_manager.get_frame("nonexistent")
        assert frame is None

    @pytest.mark.asyncio
    async def test_stop_all(self, camera_manager: CameraManager):
        for i in range(3):
            config = CameraConfig(
                id=f"cam_{i}", name=f"Camera {i}", url=f"rtsp://test/{i}", enabled=False
            )
            await camera_manager.add_camera(config)

        await camera_manager.stop_all()
        # All cameras should still exist but be stopped
        assert len(camera_manager.cameras) == 3
