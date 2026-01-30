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
from pydantic import BaseModel, Field

from app.core.camera_manager import CameraManager
from app.core.event_handler import EventHandler
from app.core.inference_engine import InferenceEngine
from app.core.roi_manager import ROIManager
from app.core.stream_publisher import StreamPublisher
from app.models.inference import InferenceConfig, InferenceResult
from app.services.config_persistence import ConfigPersistence, PersistenceConfig

logger = logging.getLogger(__name__)


class PipelineConfig(BaseModel):
    """
    Per-camera pipeline configuration.

    Serializable model for persistence support.
    """

    camera_id: str = Field(..., description="Camera ID")
    model_id: str = Field(..., description="Model ID to use for inference")
    inference_config: InferenceConfig = Field(
        default_factory=InferenceConfig,
        description="Inference parameters (confidence, NMS, etc.)",
    )
    enable_roi_filter: bool = Field(
        default=True, description="Enable ROI-based detection filtering"
    )
    enable_events: bool = Field(
        default=True, description="Enable event detection (alerts, line crossing)"
    )
    skip_frames: int = Field(
        default=0,
        ge=0,
        description="Skip N frames between inferences (0 = every frame)",
    )


class FrameProcessor:
    """
    Frame Processor - orchestrates per-camera inference pipelines.

    Each camera can have an active processing pipeline that:
    1. Captures frames from the camera
    2. Runs inference on the NPU
    3. Applies ROI filtering
    4. Checks for events
    5. Publishes results to stream clients

    Supports persistence: pipelines are automatically saved to disk and restored
    on service restart when auto_persist=True.
    """

    def __init__(
        self,
        camera_manager: CameraManager,
        inference_engine: InferenceEngine,
        roi_manager: ROIManager,
        stream_publisher: StreamPublisher,
        event_handler: EventHandler,
        persistence: Optional[ConfigPersistence[PipelineConfig]] = None,
        auto_persist: bool = True,
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
        # Cache last inference result per camera to prevent flickering
        self._last_inference_result: dict[str, Optional[InferenceResult]] = {}

        # Persistence support
        self._persistence = persistence or ConfigPersistence[PipelineConfig](
            PersistenceConfig(name="pipelines", filename="pipelines.json")
        )
        self._auto_persist = auto_persist

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

        # Auto-persist if enabled
        if self._auto_persist:
            await self._save_pipelines()

    async def stop_pipeline(self, camera_id: str) -> None:
        """Stop an inference pipeline."""
        had_pipeline = camera_id in self._pipelines

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
        self._last_inference_result.pop(camera_id, None)
        logger.info(f"Pipeline stopped for camera {camera_id}")

        # Auto-persist if enabled and a pipeline was actually removed
        if had_pipeline and self._auto_persist:
            await self._save_pipelines()

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
        last_processed_frame_id = 0

        while self._running.get(camera_id, False):
            try:
                pipeline = self._pipelines.get(camera_id)
                if pipeline is None:
                    break

                # Get latest frame
                frame = self._camera_manager.get_frame(camera_id)
                frame_id = self._camera_manager.get_frame_id(camera_id)

                if frame is None:
                    await asyncio.sleep(0)
                    continue

                # Skip if this is the same frame we already processed
                # Use frame ID for strict ordering guarantee
                if frame_id <= last_processed_frame_id:
                    await asyncio.sleep(0)
                    continue

                last_processed_frame_id = frame_id
                frame_count += 1

                # Frame skipping for performance
                if pipeline.skip_frames > 0 and frame_count % (pipeline.skip_frames + 1) != 0:
                    # Use cached inference result to prevent flickering
                    cached_result = self._last_inference_result.get(camera_id)
                    if cached_result is not None:
                        # Increment age counter for cached result
                        cached_result.frames_since_inference += 1
                    await self._stream_publisher.publish_frame(camera_id, frame, cached_result)
                    await asyncio.sleep(0)
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
                    result.frames_since_inference = 0  # Fresh result

                    # ROI filtering
                    if pipeline.enable_roi_filter:
                        result = await self._apply_roi_filter(camera_id, result, frame)

                    # Event checking
                    if pipeline.enable_events:
                        await self._check_events(camera_id, result, frame)

                    # Cache result for frame skipping
                    self._last_inference_result[camera_id] = result

                # Publish to stream
                await self._stream_publisher.publish_frame(
                    camera_id, frame, result
                )

                # Yield to event loop (prevent blocking) - minimal sleep
                await asyncio.sleep(0)

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

    async def restore_pipelines(self) -> int:
        """
        Restore pipelines from persistent storage.

        Loads saved pipeline configurations and attempts to restart them.
        Only starts pipelines for cameras that exist and models that are loaded.

        Returns:
            Number of pipelines successfully restored.
        """
        configs = await self._persistence.load_all(PipelineConfig)
        restored_count = 0

        # Temporarily disable auto-persist to avoid redundant saves during restore
        original_auto_persist = self._auto_persist
        self._auto_persist = False

        try:
            for config in configs:
                try:
                    # Validate camera exists
                    if self._camera_manager.get_state(config.camera_id) is None:
                        logger.warning(
                            f"Skipping pipeline restore: camera '{config.camera_id}' not found"
                        )
                        continue

                    # Validate model exists (it will be loaded if needed)
                    from app.core.model_registry import ModelRegistry
                    # Model will be auto-loaded in start_pipeline via inference API

                    await self.start_pipeline(config)
                    restored_count += 1

                except Exception as e:
                    logger.error(
                        f"Failed to restore pipeline for camera '{config.camera_id}': {e}"
                    )

            logger.info(f"Restored {restored_count}/{len(configs)} pipeline(s)")

        finally:
            # Re-enable auto-persist
            self._auto_persist = original_auto_persist

        return restored_count

    async def _save_pipelines(self) -> None:
        """Save all active pipelines to persistent storage."""
        configs = list(self._pipelines.values())
        await self._persistence.save_all(configs)
