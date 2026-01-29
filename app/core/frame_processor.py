"""
Frame Processor Module

Orchestrates the real-time inference pipeline:
Camera Frame → Preprocess → Inference → ROI Filter → Event Check → Publish

Manages per-camera processing pipelines with configurable parameters.
"""

import asyncio
import logging
import time
from typing import Optional

import numpy as np

from app.core.camera_manager import CameraManager
from app.core.event_handler import EventHandler
from app.core.inference_engine import InferenceEngine
from app.core.roi_manager import ROIManager
from app.core.stream_publisher import StreamPublisher
from app.models.inference import InferenceConfig, InferenceResult

logger = logging.getLogger(__name__)


class PipelineConfig:
    """Per-camera pipeline configuration."""

    def __init__(
        self,
        camera_id: str,
        model_id: str,
        inference_config: Optional[InferenceConfig] = None,
        enable_roi_filter: bool = True,
        enable_events: bool = True,
        skip_frames: int = 0,
    ):
        self.camera_id = camera_id
        self.model_id = model_id
        self.inference_config = inference_config or InferenceConfig()
        self.enable_roi_filter = enable_roi_filter
        self.enable_events = enable_events
        self.skip_frames = skip_frames


class FrameProcessor:
    """
    Frame Processor - orchestrates per-camera inference pipelines.

    Each camera can have an active processing pipeline that:
    1. Captures frames from the camera
    2. Runs inference on the NPU
    3. Applies ROI filtering
    4. Checks for events
    5. Publishes results to stream clients
    """

    def __init__(
        self,
        camera_manager: CameraManager,
        inference_engine: InferenceEngine,
        roi_manager: ROIManager,
        stream_publisher: StreamPublisher,
        event_handler: EventHandler,
    ):
        self._camera_manager = camera_manager
        self._inference_engine = inference_engine
        self._roi_manager = roi_manager
        self._stream_publisher = stream_publisher
        self._event_handler = event_handler

        self._pipelines: dict[str, PipelineConfig] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._running: dict[str, bool] = {}
        self._prev_positions: dict[str, dict[int, tuple]] = {}

    async def start_pipeline(self, config: PipelineConfig) -> None:
        """Start an inference pipeline for a camera."""
        camera_id = config.camera_id

        # Stop existing pipeline
        await self.stop_pipeline(camera_id)

        self._pipelines[camera_id] = config
        self._running[camera_id] = True
        self._tasks[camera_id] = asyncio.create_task(
            self._pipeline_loop(camera_id)
        )
        logger.info(f"Pipeline started for camera {camera_id} with model {config.model_id}")

    async def stop_pipeline(self, camera_id: str) -> None:
        """Stop an inference pipeline."""
        self._running[camera_id] = False
        task = self._tasks.pop(camera_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._pipelines.pop(camera_id, None)
        self._prev_positions.pop(camera_id, None)
        logger.info(f"Pipeline stopped for camera {camera_id}")

    async def stop_all(self) -> None:
        """Stop all pipelines."""
        for camera_id in list(self._tasks.keys()):
            await self.stop_pipeline(camera_id)

    def is_running(self, camera_id: str) -> bool:
        """Check if a pipeline is running for a camera."""
        return self._running.get(camera_id, False)

    def get_pipeline_config(self, camera_id: str) -> Optional[PipelineConfig]:
        """Get pipeline configuration for a camera."""
        return self._pipelines.get(camera_id)

    async def update_config(self, camera_id: str, inference_config: InferenceConfig) -> None:
        """Update inference config for a running pipeline."""
        pipeline = self._pipelines.get(camera_id)
        if pipeline:
            pipeline.inference_config = inference_config

    async def _pipeline_loop(self, camera_id: str) -> None:
        """Main processing loop for a camera pipeline."""
        frame_count = 0
        fps_times: list[float] = []

        while self._running.get(camera_id, False):
            try:
                pipeline = self._pipelines.get(camera_id)
                if pipeline is None:
                    break

                # Get latest frame
                frame = self._camera_manager.get_frame(camera_id)
                if frame is None:
                    await asyncio.sleep(0.01)
                    continue

                frame_count += 1

                # Frame skipping for performance
                if pipeline.skip_frames > 0 and frame_count % (pipeline.skip_frames + 1) != 0:
                    # Still publish frame without inference
                    await self._stream_publisher.publish_frame(camera_id, frame)
                    await asyncio.sleep(0.001)
                    continue

                # Run inference
                result = await self._inference_engine.infer(
                    frame,
                    config=pipeline.inference_config,
                    camera_id=camera_id,
                )

                if result is not None:
                    # Calculate FPS
                    now = time.monotonic()
                    fps_times.append(now)
                    fps_times = [t for t in fps_times if now - t < 1.0]
                    result.fps = len(fps_times)
                    result.frame_id = frame_count

                    # ROI filtering
                    if pipeline.enable_roi_filter:
                        result = await self._apply_roi_filter(camera_id, result, frame)

                    # Event checking
                    if pipeline.enable_events:
                        await self._check_events(camera_id, result, frame)

                # Publish to stream
                await self._stream_publisher.publish_frame(
                    camera_id, frame, result
                )

                await asyncio.sleep(0.001)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Pipeline error for camera {camera_id}: {e}")
                await asyncio.sleep(0.1)

    async def _apply_roi_filter(
        self,
        camera_id: str,
        result: InferenceResult,
        frame: np.ndarray,
    ) -> InferenceResult:
        """Apply ROI-based filtering to inference results."""
        rois = self._roi_manager.get_active_rois(camera_id)
        if not rois:
            return result

        h, w = frame.shape[:2]
        frame_size = (w, h)

        # Convert detections to dict format for ROI manager
        det_dicts = [
            {
                "bbox": {
                    "x1": d.bbox.x1, "y1": d.bbox.y1,
                    "x2": d.bbox.x2, "y2": d.bbox.y2,
                },
                "class_name": d.class_name,
                "class_id": d.class_id,
                "confidence": d.confidence,
            }
            for d in result.detections
        ]

        filtered = self._roi_manager.filter_detections(det_dicts, rois, frame_size)

        # Update result with filtered detections
        from app.models.inference import BoundingBox, Detection
        result.detections = [
            Detection(
                bbox=BoundingBox(**d["bbox"]),
                class_name=d["class_name"],
                class_id=d["class_id"],
                confidence=d["confidence"],
            )
            for d in filtered
        ]
        result.object_count = len(result.detections)

        return result

    async def _check_events(
        self,
        camera_id: str,
        result: InferenceResult,
        frame: np.ndarray,
    ) -> None:
        """Check for events based on inference results."""
        rois = self._roi_manager.get_active_rois(camera_id)
        if not rois:
            return

        h, w = frame.shape[:2]
        frame_size = (w, h)

        det_dicts = [
            {
                "bbox": [d.bbox.x1, d.bbox.y1, d.bbox.x2, d.bbox.y2],
                "class_name": d.class_name,
            }
            for d in result.detections
        ]

        # Check ROI alerts
        alerts = self._roi_manager.check_roi_alerts(
            det_dicts, rois, frame_size, camera_id
        )
        for alert in alerts:
            await self._event_handler.emit(
                "roi_alert", camera_id,
                alert.model_dump(),
                frame=frame,
            )

        # Check line crossings (if tracking available)
        if any(d.track_id is not None for d in result.detections):
            curr_positions = {}
            for d in result.detections:
                if d.track_id is not None:
                    cx = (d.bbox.x1 + d.bbox.x2) / 2
                    cy = (d.bbox.y1 + d.bbox.y2) / 2
                    curr_positions[d.track_id] = (cx, cy)

            prev = self._prev_positions.get(camera_id, {})
            crossings = self._roi_manager.check_line_crossings(
                prev, curr_positions, rois, frame_size, camera_id
            )
            for crossing in crossings:
                await self._event_handler.emit(
                    "line_crossing", camera_id,
                    crossing.model_dump(),
                    frame=frame,
                )

            self._prev_positions[camera_id] = curr_positions
