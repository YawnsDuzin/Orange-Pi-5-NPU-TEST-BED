"""
Event Handler Module

Central event bus for the application.
Manages event listeners, event history, and snapshot capture.
"""

import asyncio
import logging
import time
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

import cv2
import numpy as np

from app.models.system import EventRecord

logger = logging.getLogger(__name__)


class EventHandler:
    """
    Event Handler - central event bus.

    Manages:
    - Event listener registration
    - Event dispatching (async)
    - Event history with configurable retention
    - Snapshot capture on events
    """

    def __init__(self, max_history: int = 1000, snapshots_dir: Optional[Path] = None):
        self._listeners: list[Callable] = []
        self._history: deque[EventRecord] = deque(maxlen=max_history)
        self._snapshots_dir = snapshots_dir
        self._lock = asyncio.Lock()

    def register_listener(self, callback: Callable) -> None:
        """Register an event listener. Callback: async (event: EventRecord) -> None."""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable) -> None:
        """Remove an event listener."""
        self._listeners = [l for l in self._listeners if l != callback]

    async def emit(
        self,
        event_type: str,
        camera_id: str,
        data: dict[str, Any],
        frame: Optional[np.ndarray] = None,
    ) -> EventRecord:
        """
        Emit an event.

        Args:
            event_type: Type of event (e.g., "detection", "line_crossing", "roi_alert").
            camera_id: Associated camera ID.
            data: Event-specific data.
            frame: Optional frame for snapshot capture.

        Returns:
            The created EventRecord.
        """
        snapshot_path = None
        if frame is not None and self._snapshots_dir:
            snapshot_path = await self._save_snapshot(frame, event_type, camera_id)

        event = EventRecord(
            id=str(uuid.uuid4())[:12],
            event_type=event_type,
            camera_id=camera_id,
            timestamp=datetime.now(),
            data=data,
            snapshot_path=snapshot_path,
        )

        async with self._lock:
            self._history.append(event)

        # Notify listeners (fire and forget, don't block)
        for listener in self._listeners:
            try:
                result = listener(event)
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception as e:
                logger.error(f"Event listener error: {e}")

        logger.debug(f"Event emitted: {event_type} from camera {camera_id}")
        return event

    def get_history(
        self,
        camera_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[EventRecord]:
        """Get event history with optional filters."""
        events = list(self._history)
        events.reverse()  # newest first

        if camera_id:
            events = [e for e in events if e.camera_id == camera_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return events[:limit]

    def clear_history(self) -> int:
        """Clear event history. Returns number of cleared events."""
        count = len(self._history)
        self._history.clear()
        return count

    async def acknowledge_event(self, event_id: str) -> bool:
        """Mark an event as acknowledged."""
        for event in self._history:
            if event.id == event_id:
                event.acknowledged = True
                return True
        return False

    async def _save_snapshot(
        self,
        frame: np.ndarray,
        event_type: str,
        camera_id: str,
    ) -> Optional[str]:
        """Save a snapshot image for an event."""
        if self._snapshots_dir is None:
            return None

        try:
            self._snapshots_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{camera_id}_{event_type}_{timestamp}.jpg"
            filepath = self._snapshots_dir / filename

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: cv2.imwrite(
                    str(filepath), frame,
                    [cv2.IMWRITE_JPEG_QUALITY, 95],
                ),
            )

            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            return None
