"""
Camera Manager Module

Manages multiple camera streams (RTSP, USB, CSI, file).
Handles connection lifecycle, automatic reconnection, and frame delivery.
Designed for reliability with graceful error handling and resource cleanup.
"""

import asyncio
import logging
import platform
import time
from typing import Callable, Optional

import cv2
import numpy as np

from app.config import CameraSettings
from app.models.camera import CameraConfig, CameraState, CameraStatus, CameraType

IS_WINDOWS = platform.system() == "Windows"

logger = logging.getLogger(__name__)


class FPSCounter:
    """Sliding window FPS calculator for accurate measurement."""

    def __init__(self, window_size: int = 30):
        self._window_size = window_size
        self._timestamps: list[float] = []

    def update(self) -> float:
        now = time.monotonic()
        self._timestamps.append(now)
        if len(self._timestamps) > self._window_size:
            self._timestamps.pop(0)
        if len(self._timestamps) < 2:
            return 0.0
        elapsed = self._timestamps[-1] - self._timestamps[0]
        if elapsed <= 0:
            return 0.0
        return (len(self._timestamps) - 1) / elapsed

    def reset(self) -> None:
        self._timestamps.clear()


class CameraStream:
    """
    Individual camera stream handler.

    Manages the lifecycle of a single camera connection including
    automatic reconnection, frame capture, and callback notification.
    """

    def __init__(self, config: CameraConfig, settings: CameraSettings):
        self.config = config
        self._settings = settings
        self.state = CameraState(
            id=config.id,
            name=config.name,
            status=CameraStatus.DISCONNECTED,
        )
        self._cap: Optional[cv2.VideoCapture] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._frame_callbacks: list[Callable] = []
        self._fps_counter = FPSCounter()
        self._start_time: Optional[float] = None
        self._last_frame: Optional[np.ndarray] = None
        self._frame_lock = asyncio.Lock()

    @property
    def last_frame(self) -> Optional[np.ndarray]:
        return self._last_frame

    async def start(self) -> None:
        """Start the camera stream capture loop."""
        if self._running:
            return
        self._running = True
        self._start_time = time.monotonic()
        self._task = asyncio.create_task(self._capture_loop())
        logger.info(f"Camera '{self.config.name}' ({self.config.id}) stream started")

    async def stop(self) -> None:
        """Stop the camera stream and release resources."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._release_capture()
        self.state.status = CameraStatus.STOPPED
        self._fps_counter.reset()
        logger.info(f"Camera '{self.config.name}' ({self.config.id}) stream stopped")

    def on_frame(self, callback: Callable) -> None:
        """Register a frame callback. Callback signature: async (camera_id, frame)."""
        self._frame_callbacks.append(callback)

    def remove_callback(self, callback: Callable) -> None:
        """Remove a registered frame callback."""
        self._frame_callbacks = [cb for cb in self._frame_callbacks if cb != callback]

    def _connect(self) -> bool:
        """Attempt to connect to the camera source."""
        self.state.status = CameraStatus.CONNECTING
        self.state.error_message = ""

        try:
            source = self._resolve_source()
            self._cap = cv2.VideoCapture(source, self._get_backend())

            # Optimize capture settings
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, self.config.buffer_size)

            if self.config.camera_type == CameraType.RTSP:
                # Force TCP for RTSP stability
                if self._settings.rtsp_transport == "tcp":
                    self._cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, self._settings.capture_timeout_ms)
                    self._cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, self._settings.capture_timeout_ms)

            if not self._cap.isOpened():
                raise ConnectionError("Failed to open video capture")

            # Read resolution info
            w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.state.resolution = f"{w}x{h}"
            self.state.status = CameraStatus.CONNECTED
            logger.info(
                f"Camera '{self.config.name}' connected: {self.state.resolution}"
            )
            return True

        except Exception as e:
            self.state.status = CameraStatus.ERROR
            self.state.error_message = str(e)
            logger.error(f"Camera '{self.config.name}' connection failed: {e}")
            self._release_capture()
            return False

    def _resolve_source(self):
        """Resolve camera source from config."""
        if self.config.camera_type == CameraType.USB:
            try:
                return int(self.config.url)
            except ValueError:
                return self.config.url
        if self.config.camera_type == CameraType.CSI:
            # GStreamer pipeline for CSI cameras on RK3588
            return self.config.url
        return self.config.url

    def _get_backend(self) -> int:
        """Get appropriate OpenCV backend for the current platform."""
        if self.config.camera_type in (CameraType.RTSP, CameraType.FILE):
            return cv2.CAP_FFMPEG
        if self.config.camera_type == CameraType.CSI:
            if IS_WINDOWS:
                return cv2.CAP_FFMPEG  # GStreamer CSI is ARM/Linux only
            return cv2.CAP_GSTREAMER
        # USB cameras: platform-specific backend
        if IS_WINDOWS:
            return cv2.CAP_DSHOW  # DirectShow for Windows
        return cv2.CAP_V4L2  # Video4Linux for Linux

    async def _capture_loop(self) -> None:
        """Main capture loop with automatic reconnection."""
        reconnect_count = 0
        loop = asyncio.get_running_loop()

        while self._running:
            # Connect if not connected
            if self.state.status != CameraStatus.CONNECTED:
                connected = await loop.run_in_executor(None, self._connect)
                if not connected:
                    reconnect_count += 1
                    max_retries = self._settings.reconnect_max_retries
                    if max_retries > 0 and reconnect_count > max_retries:
                        logger.error(
                            f"Camera '{self.config.name}' max reconnect retries reached"
                        )
                        self.state.status = CameraStatus.ERROR
                        self.state.error_message = "Max reconnect retries exceeded"
                        break

                    wait_time = min(
                        self.config.reconnect_interval * (1.5 ** min(reconnect_count - 1, 5)),
                        60,
                    )
                    await asyncio.sleep(wait_time)
                    continue
                reconnect_count = 0

            # Read frame
            try:
                ret, frame = await loop.run_in_executor(None, self._cap.read)
            except Exception as e:
                logger.error(f"Camera '{self.config.name}' read error: {e}")
                self.state.status = CameraStatus.ERROR
                self.state.error_message = str(e)
                self._release_capture()
                await asyncio.sleep(1)
                continue

            if not ret or frame is None:
                # For file sources, stop at end
                if self.config.camera_type == CameraType.FILE:
                    logger.info(f"Camera '{self.config.name}' file playback ended")
                    self.state.status = CameraStatus.STOPPED
                    break
                logger.warning(f"Camera '{self.config.name}' frame read failed")
                self.state.status = CameraStatus.ERROR
                self.state.error_message = "Frame read failed"
                self._release_capture()
                await asyncio.sleep(1)
                continue

            # Update state
            self._last_frame = frame
            self.state.frame_count += 1
            self.state.fps = self._fps_counter.update()
            if self._start_time:
                self.state.uptime_seconds = time.monotonic() - self._start_time

            # Notify callbacks
            for callback in self._frame_callbacks:
                try:
                    await callback(self.config.id, frame)
                except Exception as e:
                    logger.error(f"Frame callback error: {e}")

            # Yield to event loop (prevent blocking)
            await asyncio.sleep(0.001)

    def _release_capture(self) -> None:
        """Release OpenCV capture resource."""
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None


class CameraManager:
    """
    Camera Manager - orchestrates multiple camera streams.

    Provides CRUD operations for cameras and manages their lifecycle.
    Thread-safe through asyncio locks.
    """

    def __init__(self, settings: CameraSettings):
        self._settings = settings
        self._cameras: dict[str, CameraStream] = {}
        self._lock = asyncio.Lock()

    @property
    def cameras(self) -> dict[str, CameraStream]:
        return dict(self._cameras)

    async def add_camera(self, config: CameraConfig) -> CameraStream:
        """Add and optionally start a camera stream."""
        async with self._lock:
            if len(self._cameras) >= self._settings.max_cameras:
                raise ValueError(
                    f"Maximum camera limit ({self._settings.max_cameras}) reached"
                )

            if config.id in self._cameras:
                await self._stop_camera_unlocked(config.id)

            stream = CameraStream(config, self._settings)
            self._cameras[config.id] = stream

            if config.enabled:
                await stream.start()

            logger.info(f"Camera added: {config.name} ({config.id})")
            return stream

    async def remove_camera(self, camera_id: str) -> bool:
        """Remove a camera and stop its stream."""
        async with self._lock:
            return await self._stop_camera_unlocked(camera_id, remove=True)

    async def start_camera(self, camera_id: str) -> None:
        """Start a stopped camera stream."""
        stream = self._get_stream(camera_id)
        await stream.start()

    async def stop_camera(self, camera_id: str) -> None:
        """Stop a running camera stream."""
        stream = self._get_stream(camera_id)
        await stream.stop()

    def get_frame(self, camera_id: str) -> Optional[np.ndarray]:
        """Get the latest frame from a camera."""
        stream = self._cameras.get(camera_id)
        if stream is None:
            return None
        return stream.last_frame

    def get_state(self, camera_id: str) -> Optional[CameraState]:
        """Get the state of a specific camera."""
        stream = self._cameras.get(camera_id)
        if stream is None:
            return None
        return stream.state

    def get_all_states(self) -> dict[str, CameraState]:
        """Get states of all cameras."""
        return {cid: cam.state for cid, cam in self._cameras.items()}

    def get_camera_ids(self) -> list[str]:
        """Get all registered camera IDs."""
        return list(self._cameras.keys())

    async def stop_all(self) -> None:
        """Stop all camera streams."""
        async with self._lock:
            for cam in self._cameras.values():
                await cam.stop()
            logger.info("All cameras stopped")

    def _get_stream(self, camera_id: str) -> CameraStream:
        """Get camera stream or raise error."""
        stream = self._cameras.get(camera_id)
        if stream is None:
            raise KeyError(f"Camera not found: {camera_id}")
        return stream

    async def _stop_camera_unlocked(self, camera_id: str, remove: bool = False) -> bool:
        """Internal: stop (and optionally remove) camera without lock."""
        stream = self._cameras.get(camera_id)
        if stream is None:
            return False
        await stream.stop()
        if remove:
            del self._cameras[camera_id]
            logger.info(f"Camera removed: {camera_id}")
        return True
