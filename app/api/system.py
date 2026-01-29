"""
System API

System monitoring, health checks, configuration, and log access.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_DIR, AppSettings
from app.core.camera_manager import CameraManager
from app.core.event_handler import EventHandler
from app.core.inference_engine import InferenceEngine
from app.dependencies import (
    get_app_settings,
    get_camera_manager,
    get_event_handler,
    get_inference_engine,
    get_system_monitor,
)
from app.models.system import (
    HealthCheck,
    LogEntry,
    LogResponse,
    SystemStatus,
)
from app.services.system_monitor import SystemMonitor

router = APIRouter()
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthCheck)
async def health_check(
    settings: AppSettings = Depends(get_app_settings),
    camera_manager: CameraManager = Depends(get_camera_manager),
    inference_engine: InferenceEngine = Depends(get_inference_engine),
    system_monitor: SystemMonitor = Depends(get_system_monitor),
):
    """Application health check."""
    status_data = system_monitor.status
    connected = sum(
        1
        for s in camera_manager.get_all_states().values()
        if s.status.value == "connected"
    )

    return HealthCheck(
        status="ok",
        version=settings.app_version,
        uptime_seconds=status_data.uptime_seconds,
        cameras_connected=connected,
        models_loaded=len(inference_engine.loaded_model_ids),
        npu_available=status_data.npu.available,
    )


@router.get("/status", response_model=SystemStatus)
async def system_status(
    system_monitor: SystemMonitor = Depends(get_system_monitor),
):
    """Get full system status."""
    return await system_monitor.get_status()


@router.get("/status/panel", response_class=HTMLResponse)
async def status_panel_html(
    request: Request,
    system_monitor: SystemMonitor = Depends(get_system_monitor),
):
    """System status panel as HTMX partial."""
    status = system_monitor.status
    return templates.TemplateResponse(
        request, "components/stats_panel.html",
        {"status": status},
    )


@router.get("/events")
async def list_events(
    camera_id: str = "",
    event_type: str = "",
    limit: int = 50,
    event_handler: EventHandler = Depends(get_event_handler),
):
    """List recent events."""
    events = event_handler.get_history(
        camera_id=camera_id or None,
        event_type=event_type or None,
        limit=limit,
    )
    return {
        "events": [e.model_dump(mode="json") for e in events],
        "total": len(events),
    }


@router.post("/events/{event_id}/acknowledge")
async def acknowledge_event(
    event_id: str,
    event_handler: EventHandler = Depends(get_event_handler),
):
    """Acknowledge an event."""
    success = await event_handler.acknowledge_event(event_id)
    if not success:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"status": "ok", "event_id": event_id}


@router.get("/logs", response_model=LogResponse)
async def get_logs(
    level: str = "",
    limit: int = 100,
    offset: int = 0,
    settings: AppSettings = Depends(get_app_settings),
):
    """Get application log entries."""
    log_file = settings.storage.data_dir / "logs" / "app.log"
    if not log_file.exists():
        return LogResponse(entries=[], total=0)

    entries = []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Parse log lines
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                # Parse format: "2024-01-01 12:00:00 [INFO] module: message"
                parts = line.split(" ", 3)
                if len(parts) < 4:
                    continue

                timestamp_str = f"{parts[0]} {parts[1]}"
                level_str = parts[2].strip("[]")

                if level and level_str.upper() != level.upper():
                    continue

                remaining = parts[3]
                logger_name, _, message = remaining.partition(": ")

                entries.append(LogEntry(
                    timestamp=datetime.fromisoformat(timestamp_str.replace(",", ".")),
                    level=level_str,
                    logger=logger_name.strip(),
                    message=message.strip(),
                ))

                if len(entries) >= offset + limit:
                    break

            except (ValueError, IndexError):
                continue

    except Exception as e:
        logger.error(f"Error reading logs: {e}")

    paginated = entries[offset : offset + limit]
    return LogResponse(
        entries=paginated,
        total=len(entries),
        has_more=len(entries) > offset + limit,
    )


@router.get("/logs/viewer", response_class=HTMLResponse)
async def log_viewer_html(
    request: Request,
):
    """Log viewer as HTMX partial."""
    return templates.TemplateResponse(
        request, "components/log_viewer.html",
    )


@router.get("/info")
async def system_info(
    settings: AppSettings = Depends(get_app_settings),
):
    """Get application and system information."""
    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "debug": settings.debug,
        "max_cameras": settings.camera.max_cameras,
        "max_loaded_models": settings.inference.max_loaded_models,
        "npu_core_mask": settings.inference.default_core_mask,
    }
