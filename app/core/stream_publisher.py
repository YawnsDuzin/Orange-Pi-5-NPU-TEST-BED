"""
Stream Publisher Module

Manages real-time video stream distribution to clients.
Supports both MJPEG (HTTP multipart) and WebSocket streams.
Handles frame encoding, overlay rendering, and client lifecycle.
"""

import asyncio
import base64
import logging
import time
from typing import Optional

import cv2
import numpy as np
from fastapi import WebSocket

from app.config import StreamSettings
from app.models.inference import InferenceResult, ModelType

logger = logging.getLogger(__name__)


class StreamPublisher:
    """
    Stream Publisher - distributes video frames to connected clients.

    Supports:
    - WebSocket clients with frame + metadata (JSON)
    - MJPEG clients via async queues
    - Configurable quality, FPS, and scale per stream
    - Automatic dead client cleanup
    """

    def __init__(self, settings: StreamSettings):
        self._settings = settings
        self._ws_clients: dict[str, set[WebSocket]] = {}
        self._mjpeg_queues: dict[str, set[asyncio.Queue]] = {}
        self._last_publish_time: dict[str, float] = {}

    # --- Client Management ---

    async def register_websocket(self, camera_id: str, ws: WebSocket) -> None:
        """Register a WebSocket client for a camera stream."""
        if camera_id not in self._ws_clients:
            self._ws_clients[camera_id] = set()

        if len(self._ws_clients[camera_id]) >= self._settings.max_ws_clients:
            logger.warning(f"Max WebSocket clients reached for camera {camera_id}")
            return

        self._ws_clients[camera_id].add(ws)
        logger.debug(f"WebSocket client registered for camera {camera_id}")

    async def unregister_websocket(self, camera_id: str, ws: WebSocket) -> None:
        """Unregister a WebSocket client."""
        if camera_id in self._ws_clients:
            self._ws_clients[camera_id].discard(ws)

    def create_mjpeg_queue(self, camera_id: str) -> asyncio.Queue:
        """Create an MJPEG stream queue for a client."""
        if camera_id not in self._mjpeg_queues:
            self._mjpeg_queues[camera_id] = set()

        queue: asyncio.Queue = asyncio.Queue(maxsize=2)
        self._mjpeg_queues[camera_id].add(queue)
        return queue

    def remove_mjpeg_queue(self, camera_id: str, queue: asyncio.Queue) -> None:
        """Remove an MJPEG queue."""
        if camera_id in self._mjpeg_queues:
            self._mjpeg_queues[camera_id].discard(queue)

    def get_client_count(self, camera_id: str) -> int:
        """Get total connected clients for a camera."""
        ws_count = len(self._ws_clients.get(camera_id, set()))
        mjpeg_count = len(self._mjpeg_queues.get(camera_id, set()))
        return ws_count + mjpeg_count

    # --- Frame Publishing ---

    async def publish_frame(
        self,
        camera_id: str,
        frame: np.ndarray,
        inference_result: Optional[InferenceResult] = None,
    ) -> None:
        """
        Publish a frame to all connected clients.

        Args:
            camera_id: Camera identifier.
            frame: BGR frame from OpenCV.
            inference_result: Optional inference results to overlay and send.
        """
        # Rate limiting
        now = time.monotonic()
        last = self._last_publish_time.get(camera_id, 0)
        min_interval = 1.0 / self._settings.mjpeg_max_fps
        if now - last < min_interval:
            return
        self._last_publish_time[camera_id] = now

        # No clients → skip encoding
        if not self._has_clients(camera_id):
            return

        # Draw overlay
        display_frame = self._draw_overlay(frame, inference_result)

        # Encode JPEG
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, self._settings.mjpeg_quality]
        _, jpeg_buffer = cv2.imencode(".jpg", display_frame, encode_params)
        jpeg_bytes = jpeg_buffer.tobytes()

        # Publish concurrently
        await asyncio.gather(
            self._publish_to_websockets(camera_id, jpeg_bytes, inference_result),
            self._publish_to_mjpeg(camera_id, jpeg_bytes),
            return_exceptions=True,
        )

    async def publish_preview(
        self,
        camera_id: str,
        frame: np.ndarray,
    ) -> bytes:
        """Generate a preview thumbnail."""
        scale = self._settings.preview_scale
        h, w = frame.shape[:2]
        new_size = (int(w * scale), int(h * scale))
        resized = cv2.resize(frame, new_size)

        _, jpeg_buffer = cv2.imencode(
            ".jpg", resized,
            [cv2.IMWRITE_JPEG_QUALITY, 60],
        )
        return jpeg_buffer.tobytes()

    # --- Internal Methods ---

    def _has_clients(self, camera_id: str) -> bool:
        """Check if any clients are connected for a camera."""
        ws = self._ws_clients.get(camera_id, set())
        mjpeg = self._mjpeg_queues.get(camera_id, set())
        return bool(ws) or bool(mjpeg)

    async def _publish_to_websockets(
        self,
        camera_id: str,
        jpeg_bytes: bytes,
        inference_result: Optional[InferenceResult],
    ) -> None:
        """Send frame and metadata to WebSocket clients."""
        clients = self._ws_clients.get(camera_id)
        if not clients:
            return

        # Build message
        message = {
            "type": "frame",
            "camera_id": camera_id,
            "image": base64.b64encode(jpeg_bytes).decode("ascii"),
            "timestamp": time.time(),
        }

        if inference_result:
            message["inference"] = {
                "model_type": inference_result.model_type.value,
                "inference_ms": round(inference_result.inference_time_ms, 1),
                "fps": round(inference_result.fps, 1),
                "object_count": inference_result.object_count,
                "detections": [
                    {
                        "class": d.class_name,
                        "confidence": round(d.confidence, 2),
                        "bbox": [d.bbox.x1, d.bbox.y1, d.bbox.x2, d.bbox.y2],
                    }
                    for d in inference_result.detections
                ],
            }

        dead_clients: set[WebSocket] = set()
        for ws in clients:
            try:
                await ws.send_json(message)
            except Exception:
                dead_clients.add(ws)

        # Cleanup disconnected clients
        if dead_clients:
            self._ws_clients[camera_id] -= dead_clients

    async def _publish_to_mjpeg(self, camera_id: str, jpeg_bytes: bytes) -> None:
        """Send frame to MJPEG stream queues."""
        queues = self._mjpeg_queues.get(camera_id)
        if not queues:
            return

        dead_queues: set[asyncio.Queue] = set()
        for queue in queues:
            try:
                # Drop oldest frame if queue is full (keep latest)
                if queue.full():
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                queue.put_nowait(jpeg_bytes)
            except Exception:
                dead_queues.add(queue)

        if dead_queues:
            self._mjpeg_queues[camera_id] -= dead_queues

    def _draw_overlay(
        self,
        frame: np.ndarray,
        result: Optional[InferenceResult],
    ) -> np.ndarray:
        """Draw inference results overlay on frame."""
        if result is None:
            return frame

        frame = frame.copy()

        # Detection boxes
        for det in result.detections:
            x1, y1 = int(det.bbox.x1), int(det.bbox.y1)
            x2, y2 = int(det.bbox.x2), int(det.bbox.y2)
            label = f"{det.class_name} {det.confidence:.2f}"
            color = (0, 255, 0)

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Label background
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw, y1), color, -1)
            cv2.putText(
                frame, label, (x1, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1,
            )

        # Pose skeletons
        skeleton_pairs = [
            (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
            (5, 11), (6, 12), (11, 12), (11, 13), (13, 15),
            (12, 14), (14, 16),
        ]
        for pose in result.poses:
            kpts = pose.keypoints
            for kpt in kpts:
                if kpt.confidence > 0.3:
                    cv2.circle(frame, (int(kpt.x), int(kpt.y)), 3, (0, 0, 255), -1)

            for i, j in skeleton_pairs:
                if i < len(kpts) and j < len(kpts):
                    if kpts[i].confidence > 0.3 and kpts[j].confidence > 0.3:
                        cv2.line(
                            frame,
                            (int(kpts[i].x), int(kpts[i].y)),
                            (int(kpts[j].x), int(kpts[j].y)),
                            (255, 255, 0), 2,
                        )

        # Performance overlay
        fps = result.fps
        inf_ms = result.inference_time_ms
        obj_count = result.object_count
        info_text = f"FPS: {fps:.1f} | Infer: {inf_ms:.1f}ms | Objects: {obj_count}"

        cv2.putText(
            frame, info_text, (10, 28),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2,
        )

        return frame
