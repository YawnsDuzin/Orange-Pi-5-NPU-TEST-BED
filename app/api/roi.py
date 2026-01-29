"""
ROI Management API

CRUD operations for ROI presets and individual ROI regions.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_DIR
from app.core.roi_manager import ROIManager
from app.dependencies import get_roi_manager
from app.models.roi import (
    ROICreate,
    ROIListResponse,
    ROIPresetCreate,
    ROIPresetResponse,
    ROIUpdate,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))


@router.get("/presets", response_model=ROIListResponse)
async def list_presets(
    camera_id: str = "",
    roi_manager: ROIManager = Depends(get_roi_manager),
):
    """List ROI presets, optionally filtered by camera."""
    if camera_id:
        presets = roi_manager.get_camera_presets(camera_id)
    else:
        presets = list(roi_manager.presets.values())
    return ROIListResponse(presets=presets, total=len(presets))


@router.post("/presets", response_model=ROIPresetResponse, status_code=201)
async def create_preset(
    data: ROIPresetCreate,
    roi_manager: ROIManager = Depends(get_roi_manager),
):
    """Create a new ROI preset."""
    preset = await roi_manager.create_preset(data)
    return ROIPresetResponse(preset=preset, camera_id=data.camera_id)


@router.get("/presets/{preset_id}")
async def get_preset(
    preset_id: str,
    roi_manager: ROIManager = Depends(get_roi_manager),
):
    """Get a specific ROI preset."""
    preset = roi_manager.get_preset(preset_id)
    if preset is None:
        raise HTTPException(status_code=404, detail="Preset not found")
    return ROIPresetResponse(preset=preset, camera_id=preset.camera_id)


@router.delete("/presets/{preset_id}")
async def delete_preset(
    preset_id: str,
    roi_manager: ROIManager = Depends(get_roi_manager),
):
    """Delete an ROI preset."""
    deleted = await roi_manager.delete_preset(preset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Preset not found")
    return {"status": "ok", "preset_id": preset_id}


@router.post("/presets/{preset_id}/activate")
async def activate_preset(
    preset_id: str,
    camera_id: str,
    roi_manager: ROIManager = Depends(get_roi_manager),
):
    """Activate a preset for a camera."""
    success = await roi_manager.set_active_preset(camera_id, preset_id)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid preset or camera mismatch")
    return {"status": "ok", "preset_id": preset_id, "camera_id": camera_id}


@router.post("/presets/{preset_id}/rois")
async def add_roi(
    preset_id: str,
    data: ROICreate,
    roi_manager: ROIManager = Depends(get_roi_manager),
):
    """Add an ROI to a preset."""
    roi = await roi_manager.add_roi_to_preset(preset_id, data)
    if roi is None:
        raise HTTPException(status_code=404, detail="Preset not found")
    return {"status": "ok", "roi": roi.model_dump(mode="json")}


@router.delete("/presets/{preset_id}/rois/{roi_id}")
async def remove_roi(
    preset_id: str,
    roi_id: str,
    roi_manager: ROIManager = Depends(get_roi_manager),
):
    """Remove an ROI from a preset."""
    removed = await roi_manager.remove_roi_from_preset(preset_id, roi_id)
    if not removed:
        raise HTTPException(status_code=404, detail="ROI or preset not found")
    return {"status": "ok", "roi_id": roi_id}


@router.get("/editor", response_class=HTMLResponse)
async def roi_editor_html(
    request: Request,
    camera_id: str = "",
    roi_manager: ROIManager = Depends(get_roi_manager),
):
    """ROI editor component as HTMX partial."""
    presets = roi_manager.get_camera_presets(camera_id) if camera_id else []
    active_rois = roi_manager.get_active_rois(camera_id) if camera_id else []

    return templates.TemplateResponse(
        request, "components/roi_editor.html",
        {
            "camera_id": camera_id,
            "presets": presets,
            "active_rois": active_rois,
        },
    )
