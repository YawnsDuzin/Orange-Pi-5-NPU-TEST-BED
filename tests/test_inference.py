"""
Inference Engine Tests

Tests for model loading, inference execution, and statistics tracking.
"""

import pytest
import numpy as np

from app.core.inference_engine import InferenceEngine, RKNNModelWrapper
from app.models.inference import (
    InferenceConfig,
    InferenceResult,
    ModelInfo,
    ModelType,
    ModelStatus,
)


class TestInferenceConfig:
    """Tests for inference configuration validation."""

    def test_default_config(self):
        config = InferenceConfig()
        assert config.confidence_threshold == 0.5
        assert config.nms_threshold == 0.45
        assert config.max_detections == 100

    def test_custom_config(self):
        config = InferenceConfig(
            confidence_threshold=0.3,
            nms_threshold=0.6,
            class_filter=["person", "car"],
            max_detections=50,
        )
        assert config.confidence_threshold == 0.3
        assert len(config.class_filter) == 2

    def test_config_bounds(self):
        with pytest.raises(Exception):
            InferenceConfig(confidence_threshold=1.5)


class TestModelInfo:
    """Tests for model metadata."""

    def test_create_detection_model(self):
        info = ModelInfo(
            id="yolov8n",
            name="YOLOv8n",
            filename="/models/detection/yolov8n.rknn",
            model_type=ModelType.DETECTION,
            input_size=[640, 640],
            num_classes=80,
        )
        assert info.model_type == ModelType.DETECTION
        assert info.input_size == [640, 640]

    def test_create_pose_model(self):
        info = ModelInfo(
            id="yolov8n_pose",
            name="YOLOv8n-Pose",
            filename="/models/pose/yolov8n-pose.rknn",
            model_type=ModelType.POSE,
        )
        assert info.model_type == ModelType.POSE


class TestInferenceEngine:
    """Tests for inference engine operations."""

    @pytest.fixture
    def model_info(self, tmp_path) -> ModelInfo:
        # Create a dummy model file
        model_file = tmp_path / "test_model.rknn"
        model_file.write_bytes(b"RKNN" + b"\x00" * 1000)

        return ModelInfo(
            id="test_model",
            name="Test Model",
            filename=str(model_file),
            model_type=ModelType.DETECTION,
            input_size=[640, 640],
        )

    @pytest.mark.asyncio
    async def test_engine_initial_state(self, inference_engine: InferenceEngine):
        assert inference_engine.active_model_id is None
        assert len(inference_engine.loaded_model_ids) == 0

    @pytest.mark.asyncio
    async def test_infer_without_model(
        self, inference_engine: InferenceEngine, sample_frame: np.ndarray
    ):
        result = await inference_engine.infer(sample_frame)
        assert result is None

    @pytest.mark.asyncio
    async def test_set_active_model_not_loaded(self, inference_engine: InferenceEngine):
        with pytest.raises(ValueError, match="not loaded"):
            await inference_engine.set_active_model("nonexistent")

    @pytest.mark.asyncio
    async def test_unload_all(self, inference_engine: InferenceEngine):
        await inference_engine.unload_all()
        assert len(inference_engine.loaded_model_ids) == 0

    @pytest.mark.asyncio
    async def test_get_stats_none(self, inference_engine: InferenceEngine):
        stats = inference_engine.get_stats("nonexistent")
        assert stats is None


class TestRKNNModelWrapper:
    """Tests for RKNN model wrapper."""

    def test_wrapper_initial_state(self):
        info = ModelInfo(
            id="test", name="Test", filename="test.rknn", model_type=ModelType.DETECTION
        )
        wrapper = RKNNModelWrapper(info)
        assert not wrapper.is_loaded

    def test_infer_not_loaded(self):
        info = ModelInfo(
            id="test", name="Test", filename="test.rknn", model_type=ModelType.DETECTION
        )
        wrapper = RKNNModelWrapper(info)
        with pytest.raises(RuntimeError, match="not loaded"):
            wrapper.infer(np.zeros((480, 640, 3), dtype=np.uint8), InferenceConfig())

    def test_nms(self):
        """Test NMS implementation."""
        boxes = np.array([
            [10, 10, 50, 50],
            [12, 12, 52, 52],  # Overlapping
            [100, 100, 150, 150],  # Non-overlapping
        ], dtype=np.float32)
        scores = np.array([0.9, 0.8, 0.7])

        keep = RKNNModelWrapper._nms(boxes, scores, threshold=0.5)
        assert 0 in keep  # Highest score kept
        assert 2 in keep  # Non-overlapping kept
        assert len(keep) == 2  # Overlapping one removed
