"""
OpenCV Service Module

Utility functions for image processing, format conversion,
and visualization. Provides reusable image manipulation helpers.
"""

import logging
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def resize_with_aspect_ratio(
    image: np.ndarray,
    target_width: Optional[int] = None,
    target_height: Optional[int] = None,
    interpolation: int = cv2.INTER_LINEAR,
) -> np.ndarray:
    """Resize image maintaining aspect ratio."""
    h, w = image.shape[:2]

    if target_width is None and target_height is None:
        return image

    if target_width is not None and target_height is not None:
        return cv2.resize(image, (target_width, target_height), interpolation=interpolation)

    if target_width is not None:
        ratio = target_width / w
        new_h = int(h * ratio)
        return cv2.resize(image, (target_width, new_h), interpolation=interpolation)

    ratio = target_height / h
    new_w = int(w * ratio)
    return cv2.resize(image, (new_w, target_height), interpolation=interpolation)


def letterbox(
    image: np.ndarray,
    target_size: tuple[int, int] = (640, 640),
    color: tuple[int, int, int] = (114, 114, 114),
) -> tuple[np.ndarray, float, tuple[int, int]]:
    """
    Resize image with letterboxing (padding) to target size.

    Returns:
        Tuple of (padded_image, scale_ratio, (pad_w, pad_h)).
    """
    h, w = image.shape[:2]
    tw, th = target_size

    scale = min(tw / w, th / h)
    new_w, new_h = int(w * scale), int(h * scale)

    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    pad_w = (tw - new_w) // 2
    pad_h = (th - new_h) // 2

    padded = cv2.copyMakeBorder(
        resized,
        pad_h, th - new_h - pad_h,
        pad_w, tw - new_w - pad_w,
        cv2.BORDER_CONSTANT, value=color,
    )

    return padded, scale, (pad_w, pad_h)


def frame_to_jpeg(
    frame: np.ndarray,
    quality: int = 80,
) -> bytes:
    """Encode frame to JPEG bytes."""
    _, buffer = cv2.imencode(
        ".jpg", frame,
        [cv2.IMWRITE_JPEG_QUALITY, quality],
    )
    return buffer.tobytes()


def frame_to_png(frame: np.ndarray) -> bytes:
    """Encode frame to PNG bytes."""
    _, buffer = cv2.imencode(".png", frame)
    return buffer.tobytes()


def draw_bounding_boxes(
    frame: np.ndarray,
    detections: list[dict],
    color: tuple[int, int, int] = (0, 255, 0),
    thickness: int = 2,
    font_scale: float = 0.5,
) -> np.ndarray:
    """Draw bounding boxes with labels on frame."""
    result = frame.copy()

    for det in detections:
        bbox = det.get("bbox", {})
        if isinstance(bbox, dict):
            x1, y1, x2, y2 = int(bbox["x1"]), int(bbox["y1"]), int(bbox["x2"]), int(bbox["y2"])
        else:
            x1, y1, x2, y2 = [int(v) for v in bbox]

        label = det.get("class_name", det.get("class", ""))
        conf = det.get("confidence", 0)
        text = f"{label} {conf:.2f}" if label else f"{conf:.2f}"

        cv2.rectangle(result, (x1, y1), (x2, y2), color, thickness)

        # Label background
        (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
        cv2.rectangle(result, (x1, y1 - th - baseline - 4), (x1 + tw, y1), color, -1)
        cv2.putText(
            result, text, (x1, y1 - baseline - 2),
            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 1,
        )

    return result


def draw_segmentation_mask(
    frame: np.ndarray,
    mask: np.ndarray,
    color: tuple[int, int, int] = (0, 128, 255),
    alpha: float = 0.4,
) -> np.ndarray:
    """Overlay a segmentation mask on frame."""
    result = frame.copy()
    colored_mask = np.zeros_like(frame)
    colored_mask[mask > 0] = color
    result = cv2.addWeighted(result, 1.0, colored_mask, alpha, 0)
    return result


def draw_pose_skeleton(
    frame: np.ndarray,
    keypoints: list[tuple[float, float, float]],
    skeleton_pairs: Optional[list[tuple[int, int]]] = None,
    point_color: tuple[int, int, int] = (0, 0, 255),
    line_color: tuple[int, int, int] = (255, 255, 0),
    conf_threshold: float = 0.3,
) -> np.ndarray:
    """Draw pose skeleton on frame."""
    result = frame.copy()

    if skeleton_pairs is None:
        skeleton_pairs = [
            (0, 1), (0, 2), (1, 3), (2, 4),  # Head
            (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),  # Arms
            (5, 11), (6, 12), (11, 12),  # Torso
            (11, 13), (13, 15), (12, 14), (14, 16),  # Legs
        ]

    # Draw lines
    for i, j in skeleton_pairs:
        if i < len(keypoints) and j < len(keypoints):
            kp1, kp2 = keypoints[i], keypoints[j]
            if kp1[2] > conf_threshold and kp2[2] > conf_threshold:
                pt1 = (int(kp1[0]), int(kp1[1]))
                pt2 = (int(kp2[0]), int(kp2[1]))
                cv2.line(result, pt1, pt2, line_color, 2)

    # Draw points
    for kp in keypoints:
        if kp[2] > conf_threshold:
            cv2.circle(result, (int(kp[0]), int(kp[1])), 4, point_color, -1)

    return result


def create_grid_view(
    frames: list[np.ndarray],
    cols: int = 2,
    cell_size: tuple[int, int] = (640, 480),
    bg_color: tuple[int, int, int] = (30, 30, 30),
) -> np.ndarray:
    """Create a grid view of multiple frames."""
    if not frames:
        return np.full((*cell_size[::-1], 3), bg_color, dtype=np.uint8)

    rows = (len(frames) + cols - 1) // cols
    grid_w = cell_size[0] * cols
    grid_h = cell_size[1] * rows
    grid = np.full((grid_h, grid_w, 3), bg_color, dtype=np.uint8)

    for idx, frame in enumerate(frames):
        row, col = divmod(idx, cols)
        resized = cv2.resize(frame, cell_size)
        y = row * cell_size[1]
        x = col * cell_size[0]
        grid[y:y + cell_size[1], x:x + cell_size[0]] = resized

    return grid
