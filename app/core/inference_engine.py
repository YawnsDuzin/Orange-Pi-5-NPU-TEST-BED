"""
Inference Engine Module

Manages RKNN model lifecycle and executes inference on the NPU.
Supports model hot-swap, parameter tuning, and multiple model types.
Uses thread pool execution to avoid blocking the async event loop.
"""

import asyncio
import logging
import time
from collections import deque
from typing import Optional

import cv2
import numpy as np

from app.config import InferenceSettings
from app.models.inference import (
    BoundingBox,
    ClassificationResult,
    Detection,
    InferenceConfig,
    InferenceResult,
    InferenceStats,
    ModelInfo,
    ModelType,
    PoseKeypoint,
    PoseResult,
    SegmentationMask,
)

logger = logging.getLogger(__name__)


# RKNN NPU core mask constants
NPU_CORE_0 = 1
NPU_CORE_1 = 2
NPU_CORE_2 = 4
NPU_CORE_0_1 = 3
NPU_CORE_0_1_2 = 7


class RKNNModelWrapper:
    """
    Wrapper for an individual RKNN model.

    Handles model loading, inference, and type-specific pre/post-processing.
    Designed for thread-safe synchronous execution (called from thread pool).
    """

    # COCO 80-class names (default for YOLO models)
    COCO_CLASSES = [
        "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
        "truck", "boat", "traffic light", "fire hydrant", "stop sign",
        "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep",
        "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
        "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
        "sports ball", "kite", "baseball bat", "baseball glove", "skateboard",
        "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork",
        "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
        "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
        "couch", "potted plant", "bed", "dining table", "toilet", "tv",
        "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave",
        "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
        "scissors", "teddy bear", "hair drier", "toothbrush",
    ]

    # COCO keypoint names for pose estimation
    COCO_KEYPOINTS = [
        "nose", "left_eye", "right_eye", "left_ear", "right_ear",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_hip", "right_hip",
        "left_knee", "right_knee", "left_ankle", "right_ankle",
    ]

    def __init__(self, model_info: ModelInfo):
        self.info = model_info
        self._rknn = None
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self, core_mask: int = NPU_CORE_0_1_2) -> None:
        """Load model onto NPU. Must be called from thread pool."""
        try:
            from rknnlite.api import RKNNLite
        except ImportError:
            logger.warning("rknnlite not available - using mock mode")
            self._loaded = True
            return

        self._rknn = RKNNLite()

        model_path = self.info.filename
        ret = self._rknn.load_rknn(model_path)
        if ret != 0:
            raise RuntimeError(f"Failed to load RKNN model: {model_path} (code={ret})")

        ret = self._rknn.init_runtime(core_mask=core_mask)
        if ret != 0:
            self._rknn.release()
            self._rknn = None
            raise RuntimeError(f"Failed to init RKNN runtime (code={ret})")

        self._loaded = True
        logger.info(f"Model '{self.info.name}' loaded on NPU (core_mask={core_mask})")

    def infer(
        self,
        frame: np.ndarray,
        config: InferenceConfig,
    ) -> InferenceResult:
        """
        Run inference on a single frame. Must be called from thread pool.
        Returns structured result based on model type.
        """
        if not self._loaded:
            raise RuntimeError("Model not loaded")

        timestamp = time.time()

        # Preprocess
        t0 = time.perf_counter()
        input_data = self._preprocess(frame)
        preprocess_ms = (time.perf_counter() - t0) * 1000

        # Inference
        t1 = time.perf_counter()
        if self._rknn is not None:
            outputs = self._rknn.inference(inputs=[input_data])
        else:
            # Mock mode for development
            outputs = self._mock_inference(input_data)
        inference_ms = (time.perf_counter() - t1) * 1000

        # Postprocess
        t2 = time.perf_counter()
        result = self._postprocess(outputs, frame.shape, config)
        postprocess_ms = (time.perf_counter() - t2) * 1000

        total_ms = preprocess_ms + inference_ms + postprocess_ms

        result.model_id = self.info.id
        result.model_type = self.info.model_type
        result.timestamp = timestamp
        result.inference_time_ms = inference_ms
        result.preprocess_time_ms = preprocess_ms
        result.postprocess_time_ms = postprocess_ms
        result.total_time_ms = total_ms

        return result

    def release(self) -> None:
        """Release model resources."""
        if self._rknn is not None:
            try:
                self._rknn.release()
            except Exception as e:
                logger.error(f"Error releasing model '{self.info.name}': {e}")
            self._rknn = None
        self._loaded = False
        logger.info(f"Model '{self.info.name}' released")

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        """Preprocess frame for model input."""
        w, h = self.info.input_size
        img = cv2.resize(frame, (w, h))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        # Add batch dimension: [H, W, C] -> [1, H, W, C]
        img = np.expand_dims(img, axis=0)
        return img

    def _postprocess(
        self,
        outputs: list,
        original_shape: tuple,
        config: InferenceConfig,
    ) -> InferenceResult:
        """Route to type-specific postprocessing."""
        handlers = {
            ModelType.DETECTION: self._postprocess_detection,
            ModelType.SEGMENTATION: self._postprocess_segmentation,
            ModelType.POSE: self._postprocess_pose,
            ModelType.CLASSIFICATION: self._postprocess_classification,
            ModelType.FACE_DETECTION: self._postprocess_detection,
            ModelType.FACE_RECOGNITION: self._postprocess_classification,
            ModelType.OCR: self._postprocess_classification,
        }
        handler = handlers.get(self.info.model_type, self._postprocess_detection)
        return handler(outputs, original_shape, config)

    def _postprocess_detection(
        self,
        outputs: list,
        original_shape: tuple,
        config: InferenceConfig,
    ) -> InferenceResult:
        """Postprocess object detection outputs (YOLO format)."""
        result = InferenceResult(
            model_id="", model_type=ModelType.DETECTION,
            camera_id="", timestamp=0, inference_time_ms=0,
        )

        if not outputs or outputs[0] is None:
            return result

        classes = self.info.classes or self.COCO_CLASSES
        oh, ow = original_shape[:2]
        iw, ih = self.info.input_size
        scale_x, scale_y = ow / iw, oh / ih

        detections = []

        try:
            # Parse YOLO outputs (format depends on model version)
            boxes, scores, class_ids = self._parse_yolo_output(outputs, config)

            for i in range(len(boxes)):
                if len(detections) >= config.max_detections:
                    break

                class_id = int(class_ids[i])
                confidence = float(scores[i])

                if confidence < config.confidence_threshold:
                    continue

                class_name = classes[class_id] if class_id < len(classes) else f"class_{class_id}"

                # Apply class filter
                if config.class_filter and class_name not in config.class_filter:
                    continue

                x1, y1, x2, y2 = boxes[i]
                detections.append(Detection(
                    bbox=BoundingBox(
                        x1=float(x1 * scale_x),
                        y1=float(y1 * scale_y),
                        x2=float(x2 * scale_x),
                        y2=float(y2 * scale_y),
                    ),
                    class_name=class_name,
                    class_id=class_id,
                    confidence=confidence,
                ))
        except Exception as e:
            logger.error(f"Detection postprocess error: {e}")

        result.detections = detections
        result.object_count = len(detections)
        return result

    def _postprocess_segmentation(
        self,
        outputs: list,
        original_shape: tuple,
        config: InferenceConfig,
    ) -> InferenceResult:
        """Postprocess instance segmentation outputs."""
        # Start with detection postprocess
        result = self._postprocess_detection(outputs, original_shape, config)
        result.model_type = ModelType.SEGMENTATION

        # Add segmentation masks if available
        if len(outputs) > 1 and outputs[1] is not None:
            try:
                mask_output = outputs[1]
                for i, det in enumerate(result.detections):
                    if i < len(mask_output):
                        result.segmentations.append(SegmentationMask(
                            class_name=det.class_name,
                            class_id=det.class_id,
                            confidence=det.confidence,
                        ))
            except Exception as e:
                logger.error(f"Segmentation postprocess error: {e}")

        return result

    def _postprocess_pose(
        self,
        outputs: list,
        original_shape: tuple,
        config: InferenceConfig,
    ) -> InferenceResult:
        """Postprocess pose estimation outputs."""
        result = InferenceResult(
            model_id="", model_type=ModelType.POSE,
            camera_id="", timestamp=0, inference_time_ms=0,
        )

        if not outputs or outputs[0] is None:
            return result

        oh, ow = original_shape[:2]
        iw, ih = self.info.input_size
        scale_x, scale_y = ow / iw, oh / ih

        try:
            boxes, scores, class_ids = self._parse_yolo_output(outputs, config)

            # Keypoints are typically in the last output
            kpt_output = outputs[-1] if len(outputs) > 1 else None

            for i in range(len(boxes)):
                if scores[i] < config.confidence_threshold:
                    continue

                x1, y1, x2, y2 = boxes[i]
                keypoints = []

                if kpt_output is not None and i < len(kpt_output):
                    kpt_data = kpt_output[i]
                    num_kpts = len(kpt_data) // 3
                    for k in range(min(num_kpts, 17)):
                        kx = float(kpt_data[k * 3]) * scale_x
                        ky = float(kpt_data[k * 3 + 1]) * scale_y
                        kconf = float(kpt_data[k * 3 + 2])
                        name = self.COCO_KEYPOINTS[k] if k < len(self.COCO_KEYPOINTS) else None
                        keypoints.append(PoseKeypoint(
                            x=kx, y=ky, confidence=kconf, name=name,
                        ))

                result.poses.append(PoseResult(
                    bbox=BoundingBox(
                        x1=float(x1 * scale_x),
                        y1=float(y1 * scale_y),
                        x2=float(x2 * scale_x),
                        y2=float(y2 * scale_y),
                    ),
                    confidence=float(scores[i]),
                    keypoints=keypoints,
                ))

        except Exception as e:
            logger.error(f"Pose postprocess error: {e}")

        result.object_count = len(result.poses)
        return result

    def _postprocess_classification(
        self,
        outputs: list,
        original_shape: tuple,
        config: InferenceConfig,
    ) -> InferenceResult:
        """Postprocess classification outputs."""
        result = InferenceResult(
            model_id="", model_type=ModelType.CLASSIFICATION,
            camera_id="", timestamp=0, inference_time_ms=0,
        )

        if not outputs or outputs[0] is None:
            return result

        try:
            probs = outputs[0].flatten()
            # Apply softmax if not already probabilities
            if probs.max() > 1.0 or probs.min() < 0.0:
                exp_probs = np.exp(probs - probs.max())
                probs = exp_probs / exp_probs.sum()

            classes = self.info.classes or []
            top_k = min(5, len(probs))
            top_indices = np.argsort(probs)[::-1][:top_k]

            for idx in top_indices:
                conf = float(probs[idx])
                if conf < config.confidence_threshold:
                    continue
                class_name = classes[idx] if idx < len(classes) else f"class_{idx}"
                result.classifications.append(ClassificationResult(
                    class_name=class_name,
                    class_id=int(idx),
                    confidence=conf,
                ))
        except Exception as e:
            logger.error(f"Classification postprocess error: {e}")

        result.object_count = len(result.classifications)
        return result

    def _parse_yolo_output(
        self,
        outputs: list,
        config: InferenceConfig,
    ) -> tuple:
        """
        Parse YOLOv5 raw output (anchor-based) into boxes, scores, and class_ids.
        Handles format: [(1, 255, 80, 80), (1, 255, 40, 40), (1, 255, 20, 20)]
        """
        # Debug: log output shapes on first inference
        if not hasattr(self, '_output_shapes_logged'):
            logger.info(f"YOLO output format - {len(outputs)} outputs:")
            for i, out in enumerate(outputs):
                if out is not None:
                    logger.info(f"  Output[{i}]: shape={np.array(out).shape}, dtype={np.array(out).dtype}")
            self._output_shapes_logged = True

        all_boxes = []
        all_scores = []
        all_class_ids = []

        # YOLOv5 anchors for 640x640 input
        strides = [8, 16, 32]
        anchors = [
            [[10, 13], [16, 30], [33, 23]],      # stride 8
            [[30, 61], [62, 45], [59, 119]],     # stride 16
            [[116, 90], [156, 198], [373, 326]]  # stride 32
        ]

        input_size = self.info.input_size[0]  # Assume square input

        try:
            for idx, output in enumerate(outputs):
                if output is None:
                    continue

                output = np.array(output)
                stride = strides[idx]
                grid_size = input_size // stride
                anchor = np.array(anchors[idx], dtype=np.float32)

                # Reshape: (1, 255, gh, gw) -> (3, 85, gh, gw) -> (3, gh, gw, 85)
                output = output.reshape(3, 85, grid_size, grid_size).transpose(0, 2, 3, 1)

                # Apply sigmoid
                output = 1.0 / (1.0 + np.exp(-output))

                # Extract components
                obj_conf = output[..., 4]              # (3, gh, gw)
                cls_scores = output[..., 5:]           # (3, gh, gw, 80)
                cls_ids = np.argmax(cls_scores, axis=-1)  # (3, gh, gw)
                cls_conf = np.max(cls_scores, axis=-1)    # (3, gh, gw)
                conf = obj_conf * cls_conf             # (3, gh, gw)

                # Filter by confidence
                mask = conf > config.confidence_threshold
                if not np.any(mask):
                    continue

                # Create grid coordinates
                gy, gx = np.meshgrid(
                    np.arange(grid_size, dtype=np.float32),
                    np.arange(grid_size, dtype=np.float32),
                    indexing='ij'
                )
                gx = np.tile(gx, (3, 1, 1))
                gy = np.tile(gy, (3, 1, 1))

                # Broadcast anchors
                aw = anchor[:, 0].reshape(3, 1, 1)
                ah = anchor[:, 1].reshape(3, 1, 1)

                # Decode bounding boxes
                dx, dy = output[..., 0], output[..., 1]
                dw, dh = output[..., 2], output[..., 3]

                cx = (dx * 2 - 0.5 + gx) * stride
                cy = (dy * 2 - 0.5 + gy) * stride
                bw = (dw * 2) ** 2 * aw
                bh = (dh * 2) ** 2 * ah

                # Apply mask and convert to [x1, y1, x2, y2]
                cx_f, cy_f = cx[mask], cy[mask]
                bw_f, bh_f = bw[mask], bh[mask]

                x1 = cx_f - bw_f / 2
                y1 = cy_f - bh_f / 2
                x2 = cx_f + bw_f / 2
                y2 = cy_f + bh_f / 2

                all_boxes.append(np.stack([x1, y1, x2, y2], axis=-1))
                all_scores.append(conf[mask])
                all_class_ids.append(cls_ids[mask])

        except Exception as e:
            logger.error(f"YOLO output parsing error: {e}", exc_info=True)
            return np.array([]), np.array([]), np.array([])

        if not all_boxes:
            return np.array([]), np.array([]), np.array([])

        boxes = np.concatenate(all_boxes)
        scores = np.concatenate(all_scores)
        class_ids = np.concatenate(all_class_ids)

        # NMS
        if len(boxes) > 0:
            indices = self._nms(boxes, scores, config.nms_threshold)
            boxes = boxes[indices]
            scores = scores[indices]
            class_ids = class_ids[indices]

        return boxes, scores, class_ids

    @staticmethod
    def _nms(boxes: np.ndarray, scores: np.ndarray, threshold: float) -> list[int]:
        """Non-Maximum Suppression."""
        x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]
        keep = []

        while order.size > 0:
            i = order[0]
            keep.append(i)
            if order.size == 1:
                break
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            inter = w * h
            iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
            inds = np.where(iou <= threshold)[0]
            order = order[inds + 1]

        return keep

    def _mock_inference(self, input_data: np.ndarray) -> list:
        """Mock inference for development without NPU hardware."""
        # Return empty detections in correct format
        h, w = input_data.shape[:2]
        # Single detection output with no detections
        return [np.zeros((0, 85), dtype=np.float32)]


class InferenceEngine:
    """
    Inference Engine - manages model pool and coordinates inference.

    Supports loading multiple models, hot-swapping active model,
    and tracking inference statistics.
    """

    def __init__(self, settings: InferenceSettings):
        self._settings = settings
        self._models: dict[str, RKNNModelWrapper] = {}
        self._active_model_id: Optional[str] = None
        self._lock = asyncio.Lock()
        self._stats: dict[str, _InferenceStatsTracker] = {}

    @property
    def active_model_id(self) -> Optional[str]:
        return self._active_model_id

    @property
    def loaded_model_ids(self) -> list[str]:
        return [mid for mid, m in self._models.items() if m.is_loaded]

    async def load_model(
        self,
        model_info: ModelInfo,
        core_mask: Optional[int] = None,
    ) -> None:
        """Load a model onto the NPU."""
        async with self._lock:
            if core_mask is None:
                core_mask = self._settings.default_core_mask

            # Check model limit
            loaded_count = sum(1 for m in self._models.values() if m.is_loaded)
            if (
                model_info.id not in self._models
                and loaded_count >= self._settings.max_loaded_models
            ):
                raise ValueError(
                    f"Max loaded models ({self._settings.max_loaded_models}) reached. "
                    "Unload a model first."
                )

            # Unload existing if reloading
            if model_info.id in self._models and self._models[model_info.id].is_loaded:
                await self._unload_model_unlocked(model_info.id)

            wrapper = RKNNModelWrapper(model_info)

            loop = asyncio.get_running_loop()
            t0 = time.perf_counter()
            await loop.run_in_executor(None, wrapper.load, core_mask)
            load_time_ms = (time.perf_counter() - t0) * 1000

            self._models[model_info.id] = wrapper
            self._stats[model_info.id] = _InferenceStatsTracker()

            logger.info(f"Model '{model_info.name}' loaded in {load_time_ms:.1f}ms")

    async def set_active_model(self, model_id: str) -> None:
        """Set the active model for inference."""
        if model_id not in self._models or not self._models[model_id].is_loaded:
            raise ValueError(f"Model '{model_id}' not loaded")
        self._active_model_id = model_id
        logger.info(f"Active model set to '{model_id}'")

    async def infer(
        self,
        frame: np.ndarray,
        config: Optional[InferenceConfig] = None,
        camera_id: str = "",
    ) -> Optional[InferenceResult]:
        """Run inference using the active model."""
        if self._active_model_id is None:
            return None

        model = self._models.get(self._active_model_id)
        if model is None or not model.is_loaded:
            return None

        if config is None:
            config = InferenceConfig(
                confidence_threshold=self._settings.default_confidence,
                nms_threshold=self._settings.default_nms_threshold,
            )

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, model.infer, frame, config)
        result.camera_id = camera_id

        # Update stats
        tracker = self._stats.get(self._active_model_id)
        if tracker:
            tracker.record(result.inference_time_ms, result.object_count)

        return result

    async def unload_model(self, model_id: str) -> None:
        """Unload a model from the NPU."""
        async with self._lock:
            await self._unload_model_unlocked(model_id)

    async def unload_all(self) -> None:
        """Unload all models."""
        async with self._lock:
            for model_id in list(self._models.keys()):
                await self._unload_model_unlocked(model_id)
            logger.info("All models unloaded")

    def get_stats(self, model_id: str, camera_id: str = "") -> Optional[InferenceStats]:
        """Get inference statistics for a model."""
        tracker = self._stats.get(model_id)
        if tracker is None:
            return None
        return tracker.to_stats(model_id, camera_id)

    async def _unload_model_unlocked(self, model_id: str) -> None:
        """Internal: unload model without lock."""
        model = self._models.get(model_id)
        if model is None:
            return

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, model.release)
        del self._models[model_id]

        if self._active_model_id == model_id:
            self._active_model_id = None

        logger.info(f"Model '{model_id}' unloaded")


class _InferenceStatsTracker:
    """Internal helper for tracking inference statistics."""

    def __init__(self, window_size: int = 100):
        self._window_size = window_size
        self._inference_times: deque = deque(maxlen=window_size)
        self._object_counts: deque = deque(maxlen=window_size)
        self._total_frames = 0
        self._start_time = time.monotonic()
        self._fps_counter = FPSCounter(window_size)

    def record(self, inference_ms: float, object_count: int) -> None:
        self._inference_times.append(inference_ms)
        self._object_counts.append(object_count)
        self._total_frames += 1
        self._fps_counter.update()

    def to_stats(self, model_id: str, camera_id: str) -> InferenceStats:
        times = list(self._inference_times)
        objects = list(self._object_counts)
        return InferenceStats(
            model_id=model_id,
            camera_id=camera_id,
            total_frames=self._total_frames,
            avg_inference_ms=sum(times) / len(times) if times else 0,
            min_inference_ms=min(times) if times else 0,
            max_inference_ms=max(times) if times else 0,
            avg_fps=self._fps_counter.get_fps(),
            avg_objects_per_frame=sum(objects) / len(objects) if objects else 0,
            uptime_seconds=time.monotonic() - self._start_time,
        )


class FPSCounter:
    """Reusable FPS counter."""

    def __init__(self, window_size: int = 30):
        self._timestamps: deque = deque(maxlen=window_size)

    def update(self) -> float:
        """Record a new timestamp and return current FPS."""
        now = time.monotonic()
        self._timestamps.append(now)
        return self.get_fps()

    def get_fps(self) -> float:
        """Calculate current FPS without recording a new timestamp."""
        if len(self._timestamps) < 2:
            return 0.0
        elapsed = self._timestamps[-1] - self._timestamps[0]
        if elapsed <= 0:
            return 0.0
        return (len(self._timestamps) - 1) / elapsed

    def reset(self) -> None:
        """Clear all timestamps."""
        self._timestamps.clear()
