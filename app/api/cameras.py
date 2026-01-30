"""
Camera Management API

CRUD operations for cameras and stream control.
Supports HTMX partial responses and JSON API.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_DIR
from app.core.camera_manager import CameraManager
from app.dependencies import get_camera_manager
from app.models.camera import (
    CameraConfig,
    CameraCreate,
    CameraListResponse,
    CameraResponse,
    CameraState,
    CameraStatus,
    CameraUpdate,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))


@router.get("", response_model=CameraListResponse)
async def list_cameras(
    camera_manager: CameraManager = Depends(get_camera_manager),
):
    """List all registered cameras."""
    states = camera_manager.get_all_states()
    cameras = []
    for cid, stream in camera_manager.cameras.items():
        state = states.get(cid, CameraState(id=cid, name=stream.config.name))
        cameras.append(CameraResponse(config=stream.config, state=state))
    return CameraListResponse(cameras=cameras, total=len(cameras))


@router.get("/list", response_class=HTMLResponse)
async def list_cameras_html(
    request: Request,
    camera_manager: CameraManager = Depends(get_camera_manager),
):
    """List cameras as HTMX partial HTML."""
    states = camera_manager.get_all_states()
    cameras = []
    for cid, stream in camera_manager.cameras.items():
        state = states.get(cid, CameraState(id=cid, name=stream.config.name))
        cameras.append({"config": stream.config, "state": state})
    return templates.TemplateResponse(
        request, "components/camera_list.html",
        {"cameras": cameras},
    )


@router.post("", response_model=CameraResponse, status_code=201)
async def create_camera(
    data: CameraCreate,
    camera_manager: CameraManager = Depends(get_camera_manager),
):
    """Register a new camera."""
    camera_id = str(uuid.uuid4())[:8]
    config = CameraConfig(
        id=camera_id,
        name=data.name,
        url=data.url,
        camera_type=data.camera_type,
        enabled=data.enabled,
        reconnect_interval=data.reconnect_interval,
        description=data.description,
    )

    try:
        stream = await camera_manager.add_camera(config)
        return CameraResponse(config=config, state=stream.state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(
    camera_id: str,
    camera_manager: CameraManager = Depends(get_camera_manager),
):
    """Get camera details."""
    state = camera_manager.get_state(camera_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    stream = camera_manager.cameras.get(camera_id)
    return CameraResponse(config=stream.config, state=state)


@router.put("/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: str,
    data: CameraUpdate,
    camera_manager: CameraManager = Depends(get_camera_manager),
):
    """Update camera configuration."""
    stream = camera_manager.cameras.get(camera_id)
    if stream is None:
        raise HTTPException(status_code=404, detail="Camera not found")

    # Update config fields
    config = stream.config
    if data.name is not None:
        config.name = data.name
    if data.url is not None:
        config.url = data.url
    if data.camera_type is not None:
        config.camera_type = data.camera_type
    if data.enabled is not None:
        config.enabled = data.enabled
    if data.reconnect_interval is not None:
        config.reconnect_interval = data.reconnect_interval
    if data.description is not None:
        config.description = data.description
    config.updated_at = datetime.now()

    # Restart if URL changed
    if data.url is not None:
        await camera_manager.remove_camera(camera_id)
        await camera_manager.add_camera(config)

    stream = camera_manager.cameras.get(camera_id)
    return CameraResponse(config=config, state=stream.state)


@router.delete("/{camera_id}")
async def delete_camera(
    camera_id: str,
    camera_manager: CameraManager = Depends(get_camera_manager),
):
    """Remove a camera."""
    removed = await camera_manager.remove_camera(camera_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Camera not found")
    return {"status": "ok", "camera_id": camera_id}


@router.post("/{camera_id}/start")
async def start_camera(
    camera_id: str,
    camera_manager: CameraManager = Depends(get_camera_manager),
):
    """Start camera stream."""
    try:
        await camera_manager.start_camera(camera_id)
        return {"status": "ok", "camera_id": camera_id}
    except KeyError:
        raise HTTPException(status_code=404, detail="Camera not found")


@router.post("/{camera_id}/stop")
async def stop_camera(
    camera_id: str,
    camera_manager: CameraManager = Depends(get_camera_manager),
):
    """Stop camera stream."""
    try:
        await camera_manager.stop_camera(camera_id)
        return {"status": "ok", "camera_id": camera_id}
    except KeyError:
        raise HTTPException(status_code=404, detail="Camera not found")


@router.get("/{camera_id}/status")
async def camera_status(
    camera_id: str,
    camera_manager: CameraManager = Depends(get_camera_manager),
):
    """Get camera status (for HTMX polling)."""
    state = camera_manager.get_state(camera_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    return state
