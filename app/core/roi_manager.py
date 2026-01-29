"""
ROI (Region of Interest) Manager Module

Manages ROI definitions, presets, and spatial filtering operations.
Supports polygon, rectangle, and line crossing ROI types.
Handles persistence of ROI presets to disk.
"""

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Optional

import aiofiles
import cv2
import numpy as np

from app.models.roi import (
    LineCrossingEvent,
    Point,
    ROIAction,
    ROIAlertEvent,
    ROIConfig,
    ROICreate,
    ROIPreset,
    ROIPresetCreate,
    ROIType,
)

logger = logging.getLogger(__name__)


class ROIManager:
    """
    ROI Manager - manages ROI definitions, presets, and spatial operations.

    Provides:
    - CRUD operations for ROI presets and individual ROIs
    - Spatial filtering of detections against ROIs
    - Line crossing detection
    - ROI overlay rendering
    - Preset persistence to disk
    """

    def __init__(self, presets_dir: Path):
        self._presets_dir = presets_dir
        self._presets: dict[str, ROIPreset] = {}
        self._active_presets: dict[str, str] = {}  # camera_id → preset_id

    @property
    def presets(self) -> dict[str, ROIPreset]:
        return dict(self._presets)

    async def load_presets(self) -> int:
        """Load all presets from disk."""
        self._presets_dir.mkdir(parents=True, exist_ok=True)
        count = 0
        for preset_file in self._presets_dir.glob("*.json"):
            try:
                async with aiofiles.open(preset_file, "r") as f:
                    data = json.loads(await f.read())
                    preset = ROIPreset(**data)
                    self._presets[preset.id] = preset
                    if preset.is_active:
                        self._active_presets[preset.camera_id] = preset.id
                    count += 1
            except Exception as e:
                logger.error(f"Failed to load ROI preset {preset_file}: {e}")
        logger.info(f"Loaded {count} ROI presets")
        return count

    async def create_preset(self, data: ROIPresetCreate) -> ROIPreset:
        """Create a new ROI preset."""
        preset_id = str(uuid.uuid4())[:8]
        rois = []
        for roi_data in data.rois:
            roi = ROIConfig(
                id=str(uuid.uuid4())[:8],
                name=roi_data.name,
                roi_type=roi_data.roi_type,
                points=roi_data.points,
                action=roi_data.action,
                color=roi_data.color,
                enabled=roi_data.enabled,
            )
            rois.append(roi)

        preset = ROIPreset(
            id=preset_id,
            camera_id=data.camera_id,
            name=data.name,
            rois=rois,
        )
        self._presets[preset_id] = preset
        await self._save_preset(preset)
        logger.info(f"ROI preset created: {preset.name} ({preset_id})")
        return preset

    async def update_preset(self, preset_id: str, **kwargs) -> Optional[ROIPreset]:
        """Update an existing preset."""
        preset = self._presets.get(preset_id)
        if preset is None:
            return None

        for key, value in kwargs.items():
            if hasattr(preset, key) and value is not None:
                setattr(preset, key, value)

        await self._save_preset(preset)
        return preset

    async def delete_preset(self, preset_id: str) -> bool:
        """Delete a preset."""
        if preset_id not in self._presets:
            return False

        preset = self._presets.pop(preset_id)

        # Remove from active presets
        for cam_id, pid in list(self._active_presets.items()):
            if pid == preset_id:
                del self._active_presets[cam_id]

        # Delete file
        preset_file = self._presets_dir / f"{preset_id}.json"
        if preset_file.exists():
            preset_file.unlink()

        logger.info(f"ROI preset deleted: {preset.name} ({preset_id})")
        return True

    def get_preset(self, preset_id: str) -> Optional[ROIPreset]:
        """Get a preset by ID."""
        return self._presets.get(preset_id)

    def get_camera_presets(self, camera_id: str) -> list[ROIPreset]:
        """Get all presets for a camera."""
        return [p for p in self._presets.values() if p.camera_id == camera_id]

    async def set_active_preset(self, camera_id: str, preset_id: str) -> bool:
        """Set the active preset for a camera."""
        preset = self._presets.get(preset_id)
        if preset is None or preset.camera_id != camera_id:
            return False

        # Deactivate previous
        old_id = self._active_presets.get(camera_id)
        if old_id and old_id in self._presets:
            self._presets[old_id].is_active = False
            await self._save_preset(self._presets[old_id])

        # Activate new
        self._active_presets[camera_id] = preset_id
        preset.is_active = True
        await self._save_preset(preset)

        return True

    def get_active_rois(self, camera_id: str) -> list[ROIConfig]:
        """Get active ROIs for a camera."""
        preset_id = self._active_presets.get(camera_id)
        if preset_id and preset_id in self._presets:
            return [r for r in self._presets[preset_id].rois if r.enabled]
        return []

    async def add_roi_to_preset(
        self, preset_id: str, roi_data: ROICreate
    ) -> Optional[ROIConfig]:
        """Add a new ROI to an existing preset."""
        preset = self._presets.get(preset_id)
        if preset is None:
            return None

        roi = ROIConfig(
            id=str(uuid.uuid4())[:8],
            name=roi_data.name,
            roi_type=roi_data.roi_type,
            points=roi_data.points,
            action=roi_data.action,
            color=roi_data.color,
            enabled=roi_data.enabled,
        )
        preset.rois.append(roi)
        await self._save_preset(preset)
        return roi

    async def remove_roi_from_preset(self, preset_id: str, roi_id: str) -> bool:
        """Remove an ROI from a preset."""
        preset = self._presets.get(preset_id)
        if preset is None:
            return False

        original_len = len(preset.rois)
        preset.rois = [r for r in preset.rois if r.id != roi_id]
        if len(preset.rois) == original_len:
            return False

        await self._save_preset(preset)
        return True

    # --- Spatial Operations ---

    def filter_detections(
        self,
        detections: list[dict],
        rois: list[ROIConfig],
        frame_size: tuple[int, int],
    ) -> list[dict]:
        """
        Filter detections based on ROI regions.

        Args:
            detections: List of detection dicts with 'bbox' key [x1,y1,x2,y2].
            rois: Active ROI configurations.
            frame_size: (width, height) of the frame.

        Returns:
            Filtered list of detections.
        """
        if not rois:
            return detections

        include_rois = [r for r in rois if r.action == ROIAction.INCLUDE]
        exclude_rois = [r for r in rois if r.action == ROIAction.EXCLUDE]

        filtered = []
        for det in detections:
            bbox = det.get("bbox", [0, 0, 0, 0])
            if isinstance(bbox, dict):
                center = ((bbox["x1"] + bbox["x2"]) / 2, (bbox["y1"] + bbox["y2"]) / 2)
            else:
                center = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)

            # INCLUDE check
            if include_rois:
                included = any(
                    self._point_in_roi(center, roi, frame_size)
                    for roi in include_rois
                )
                if not included:
                    continue

            # EXCLUDE check
            excluded = any(
                self._point_in_roi(center, roi, frame_size)
                for roi in exclude_rois
            )
            if excluded:
                continue

            filtered.append(det)

        return filtered

    def check_line_crossings(
        self,
        prev_positions: dict[int, tuple[float, float]],
        curr_positions: dict[int, tuple[float, float]],
        rois: list[ROIConfig],
        frame_size: tuple[int, int],
        camera_id: str = "",
    ) -> list[LineCrossingEvent]:
        """Check for line crossing events."""
        line_rois = [r for r in rois if r.roi_type == ROIType.LINE and r.enabled]
        if not line_rois:
            return []

        events = []
        for line_roi in line_rois:
            pts = self._denormalize_points(line_roi.points, frame_size)
            if len(pts) < 2:
                continue

            p3, p4 = pts[0], pts[1]

            for track_id, curr_pos in curr_positions.items():
                if track_id not in prev_positions:
                    continue

                prev_pos = prev_positions[track_id]

                if self._segments_intersect(prev_pos, curr_pos, p3, p4):
                    direction = self._get_crossing_direction(prev_pos, curr_pos, p3, p4)
                    events.append(LineCrossingEvent(
                        track_id=track_id,
                        roi_id=line_roi.id,
                        roi_name=line_roi.name,
                        direction=direction,
                        timestamp=time.time(),
                        camera_id=camera_id,
                    ))

        return events

    def check_roi_alerts(
        self,
        detections: list[dict],
        rois: list[ROIConfig],
        frame_size: tuple[int, int],
        camera_id: str = "",
    ) -> list[ROIAlertEvent]:
        """Check for objects inside alert ROIs."""
        alert_rois = [r for r in rois if r.action == ROIAction.ALERT and r.enabled]
        if not alert_rois:
            return []

        events = []
        for roi in alert_rois:
            inside = []
            for det in detections:
                bbox = det.get("bbox", [0, 0, 0, 0])
                if isinstance(bbox, dict):
                    center = ((bbox["x1"] + bbox["x2"]) / 2, (bbox["y1"] + bbox["y2"]) / 2)
                else:
                    center = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)

                if self._point_in_roi(center, roi, frame_size):
                    inside.append(det.get("class_name", det.get("class", "unknown")))

            if inside:
                events.append(ROIAlertEvent(
                    roi_id=roi.id,
                    roi_name=roi.name,
                    camera_id=camera_id,
                    object_count=len(inside),
                    class_names=list(set(inside)),
                    timestamp=time.time(),
                ))

        return events

    def draw_rois(
        self,
        frame: np.ndarray,
        rois: list[ROIConfig],
        alpha: float = 0.3,
    ) -> np.ndarray:
        """Draw ROI overlays on a frame."""
        if not rois:
            return frame

        overlay = frame.copy()
        h, w = frame.shape[:2]

        for roi in rois:
            if not roi.enabled:
                continue

            color = self._hex_to_bgr(roi.color)
            pts = self._denormalize_points(roi.points, (w, h))
            pts_array = np.array(pts, np.int32)

            if roi.roi_type == ROIType.LINE:
                if len(pts) >= 2:
                    cv2.line(overlay, pts[0], pts[1], color, 2)
                    # Draw direction arrow
                    mid = ((pts[0][0] + pts[1][0]) // 2, (pts[0][1] + pts[1][1]) // 2)
                    cv2.putText(overlay, roi.name, mid, cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            else:
                # Fill with transparency
                cv2.fillPoly(overlay, [pts_array], color)
                cv2.polylines(frame, [pts_array], True, color, 2)
                # Label
                if len(pts) > 0:
                    cv2.putText(
                        frame, roi.name, pts[0],
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1,
                    )

        return cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    # --- Private Helpers ---

    def _point_in_roi(
        self,
        point: tuple[float, float],
        roi: ROIConfig,
        frame_size: tuple[int, int],
    ) -> bool:
        """Check if a point is inside an ROI polygon."""
        pts = self._denormalize_points(roi.points, frame_size)

        if roi.roi_type == ROIType.RECTANGLE and len(pts) == 2:
            # For rectangle, expand to 4 corners
            x1, y1 = pts[0]
            x2, y2 = pts[1]
            pts = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]

        pts_array = np.array(pts, np.int32)
        result = cv2.pointPolygonTest(pts_array.astype(np.float32), point, False)
        return result >= 0

    @staticmethod
    def _denormalize_points(
        points: list[Point],
        frame_size: tuple[int, int],
    ) -> list[tuple[int, int]]:
        """Convert normalized points (0-1) to pixel coordinates."""
        w, h = frame_size
        return [(int(p.x * w), int(p.y * h)) for p in points]

    @staticmethod
    def _segments_intersect(
        p1: tuple, p2: tuple, p3: tuple, p4: tuple
    ) -> bool:
        """Check if line segment (p1,p2) intersects (p3,p4)."""
        def ccw(a, b, c):
            return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])

        return (
            ccw(p1, p3, p4) != ccw(p2, p3, p4)
            and ccw(p1, p2, p3) != ccw(p1, p2, p4)
        )

    @staticmethod
    def _get_crossing_direction(
        p1: tuple, p2: tuple, line_start: tuple, line_end: tuple
    ) -> str:
        """Determine crossing direction relative to the line."""
        # Cross product to determine which side the point moved to
        dx = line_end[0] - line_start[0]
        dy = line_end[1] - line_start[1]
        cross = dx * (p2[1] - line_start[1]) - dy * (p2[0] - line_start[0])
        return "in" if cross > 0 else "out"

    @staticmethod
    def _hex_to_bgr(hex_color: str) -> tuple[int, int, int]:
        """Convert hex color string to BGR tuple."""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return (0, 255, 0)
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return (b, g, r)

    async def _save_preset(self, preset: ROIPreset) -> None:
        """Save preset to disk."""
        try:
            self._presets_dir.mkdir(parents=True, exist_ok=True)
            preset_file = self._presets_dir / f"{preset.id}.json"
            async with aiofiles.open(preset_file, "w") as f:
                await f.write(preset.model_dump_json(indent=2))
        except Exception as e:
            logger.error(f"Failed to save ROI preset: {e}")
