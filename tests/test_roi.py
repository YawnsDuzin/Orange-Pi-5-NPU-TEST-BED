"""
ROI Manager Tests

Tests for ROI operations including spatial filtering, line crossing,
and preset management.
"""

import pytest
import numpy as np

from app.core.roi_manager import ROIManager
from app.models.roi import (
    Point,
    ROIAction,
    ROIConfig,
    ROICreate,
    ROIPresetCreate,
    ROIType,
)


class TestROIManager:
    """Tests for ROI manager operations."""

    @pytest.mark.asyncio
    async def test_create_preset(self, roi_manager: ROIManager):
        data = ROIPresetCreate(
            camera_id="cam1",
            name="Test Preset",
            rois=[
                ROICreate(
                    name="Zone A",
                    roi_type=ROIType.RECTANGLE,
                    points=[Point(x=0.1, y=0.1), Point(x=0.9, y=0.9)],
                    action=ROIAction.INCLUDE,
                ),
            ],
        )
        preset = await roi_manager.create_preset(data)
        assert preset.name == "Test Preset"
        assert len(preset.rois) == 1

    @pytest.mark.asyncio
    async def test_delete_preset(self, roi_manager: ROIManager):
        data = ROIPresetCreate(camera_id="cam1", name="Delete Me")
        preset = await roi_manager.create_preset(data)
        deleted = await roi_manager.delete_preset(preset.id)
        assert deleted is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_preset(self, roi_manager: ROIManager):
        deleted = await roi_manager.delete_preset("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_activate_preset(self, roi_manager: ROIManager):
        data = ROIPresetCreate(camera_id="cam1", name="Active Preset")
        preset = await roi_manager.create_preset(data)
        success = await roi_manager.set_active_preset("cam1", preset.id)
        assert success is True
        assert roi_manager.get_active_rois("cam1") == []

    @pytest.mark.asyncio
    async def test_get_active_rois(self, roi_manager: ROIManager):
        data = ROIPresetCreate(
            camera_id="cam1",
            name="Active",
            rois=[
                ROICreate(
                    name="Zone",
                    roi_type=ROIType.POLYGON,
                    points=[Point(x=0.1, y=0.1), Point(x=0.5, y=0.1), Point(x=0.5, y=0.5)],
                    action=ROIAction.INCLUDE,
                ),
            ],
        )
        preset = await roi_manager.create_preset(data)
        await roi_manager.set_active_preset("cam1", preset.id)
        rois = roi_manager.get_active_rois("cam1")
        assert len(rois) == 1
        assert rois[0].name == "Zone"


class TestROIFiltering:
    """Tests for spatial detection filtering."""

    @pytest.fixture
    def include_roi(self) -> ROIConfig:
        return ROIConfig(
            id="r1",
            name="Include Zone",
            roi_type=ROIType.RECTANGLE,
            points=[Point(x=0.2, y=0.2), Point(x=0.8, y=0.8)],
            action=ROIAction.INCLUDE,
        )

    @pytest.fixture
    def exclude_roi(self) -> ROIConfig:
        return ROIConfig(
            id="r2",
            name="Exclude Zone",
            roi_type=ROIType.RECTANGLE,
            points=[Point(x=0.4, y=0.4), Point(x=0.6, y=0.6)],
            action=ROIAction.EXCLUDE,
        )

    def test_filter_with_include(self, roi_manager: ROIManager, include_roi: ROIConfig):
        detections = [
            {"bbox": [300, 300, 400, 400], "class_name": "person"},  # Inside
            {"bbox": [10, 10, 50, 50], "class_name": "car"},  # Outside
        ]
        filtered = roi_manager.filter_detections(
            detections, [include_roi], frame_size=(640, 480)
        )
        assert len(filtered) == 1
        assert filtered[0]["class_name"] == "person"

    def test_filter_no_rois(self, roi_manager: ROIManager):
        detections = [
            {"bbox": [100, 100, 200, 200], "class_name": "person"},
        ]
        filtered = roi_manager.filter_detections(detections, [], frame_size=(640, 480))
        assert len(filtered) == 1

    def test_draw_rois(self, roi_manager: ROIManager, include_roi: ROIConfig):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = roi_manager.draw_rois(frame, [include_roi])
        assert result.shape == (480, 640, 3)
        # Frame should be modified (not all zeros)
        assert np.any(result > 0)


class TestLineCrossing:
    """Tests for line crossing detection."""

    @pytest.fixture
    def line_roi(self) -> ROIConfig:
        return ROIConfig(
            id="line1",
            name="Cross Line",
            roi_type=ROIType.LINE,
            points=[Point(x=0.5, y=0.0), Point(x=0.5, y=1.0)],
            action=ROIAction.ALERT,
        )

    def test_line_crossing_detected(self, roi_manager: ROIManager, line_roi: ROIConfig):
        prev = {1: (100, 240)}  # Left side
        curr = {1: (500, 240)}  # Right side (crossed the vertical line)
        events = roi_manager.check_line_crossings(
            prev, curr, [line_roi], (640, 480), "cam1"
        )
        assert len(events) == 1
        assert events[0].track_id == 1

    def test_no_crossing(self, roi_manager: ROIManager, line_roi: ROIConfig):
        prev = {1: (100, 240)}
        curr = {1: (200, 240)}  # Same side
        events = roi_manager.check_line_crossings(
            prev, curr, [line_roi], (640, 480), "cam1"
        )
        assert len(events) == 0
