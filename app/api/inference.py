"""
Inference Control API

Start/stop inference pipelines, configure parameters, and retrieve results.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_DIR
from app.core.camera_manager import CameraManager
from app.core.frame_processor import FrameProcessor, PipelineConfig
from app.core.inference_engine import InferenceEngine
from app.core.model_registry import ModelRegistry
from app.dependencies import (
    get_camera_manager,
    get_inference_engine,
    get_model_registry,
)
from app.models.inference import InferenceConfig, InferenceControl, InferenceStats

router = APIRouter()
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

# Frame processor will be initialized as a dependency
_frame_processor = None


def get_frame_processor(request: Request) -> FrameProcessor:
    """Get or create frame processor."""
    global _frame_processor
    if _frame_processor is None:
        app = request.app
        _frame_processor = FrameProcessor(
            camera_manager=app.state.camera_manager,
            inference_engine=app.state.inference_engine,
            roi_manager=app.state.roi_manager,
            stream_publisher=app.state.stream_publisher,
            event_handler=app.state.event_handler,
        )
    return _frame_processor


@router.post("/start")
async def start_inference(
    data: InferenceControl,
    camera_manager: CameraManager = Depends(get_camera_manager),
    inference_engine: InferenceEngine = Depends(get_inference_engine),
    model_registry: ModelRegistry = Depends(get_model_registry),
    frame_processor: FrameProcessor = Depends(get_frame_processor),
):
    """Start inference pipeline for a camera."""
    # Validate camera
    if camera_manager.get_state(data.camera_id) is None:
        raise HTTPException(status_code=404, detail="Camera not found")

    # Validate model
    model_info = model_registry.get_model(data.model_id)
    if model_info is None:
        raise HTTPException(status_code=404, detail="Model not found")

    # Auto-load and activate model
    if data.model_id not in inference_engine.loaded_model_ids:
        try:
            await inference_engine.load_model(model_info)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load model: {e}")

    await inference_engine.set_active_model(data.model_id)

    # Start pipeline
    pipeline_config = PipelineConfig(
        camera_id=data.camera_id,
        model_id=data.model_id,
        inference_config=data.config,
    )
    await frame_processor.start_pipeline(pipeline_config)

    return {
        "status": "ok",
        "camera_id": data.camera_id,
        "model_id": data.model_id,
        "message": "Inference started",
    }


@router.post("/stop/{camera_id}")
async def stop_inference(
    camera_id: str,
    frame_processor: FrameProcessor = Depends(get_frame_processor),
):
    """Stop inference pipeline for a camera."""
    await frame_processor.stop_pipeline(camera_id)
    return {"status": "ok", "camera_id": camera_id, "message": "Inference stopped"}


@router.put("/config/{camera_id}")
async def update_inference_config(
    camera_id: str,
    config: InferenceConfig,
    frame_processor: FrameProcessor = Depends(get_frame_processor),
):
    """Update inference parameters for a running pipeline."""
    if not frame_processor.is_running(camera_id):
        raise HTTPException(status_code=400, detail="No active pipeline for this camera")

    await frame_processor.update_config(camera_id, config)
    return {"status": "ok", "camera_id": camera_id, "message": "Config updated"}


@router.get("/status/{camera_id}")
async def inference_status(
    camera_id: str,
    inference_engine: InferenceEngine = Depends(get_inference_engine),
    frame_processor: FrameProcessor = Depends(get_frame_processor),
):
    """Get inference status for a camera."""
    is_running = frame_processor.is_running(camera_id)
    pipeline = frame_processor.get_pipeline_config(camera_id)

    result = {
        "camera_id": camera_id,
        "running": is_running,
        "model_id": pipeline.model_id if pipeline else None,
        "config": pipeline.inference_config.model_dump() if pipeline else None,
    }

    # Add stats if available
    if pipeline:
        stats = inference_engine.get_stats(pipeline.model_id, camera_id)
        if stats:
            result["stats"] = stats.model_dump()

    return result


@router.get("/stats/{model_id}", response_model=InferenceStats)
async def get_inference_stats(
    model_id: str,
    camera_id: str = "",
    inference_engine: InferenceEngine = Depends(get_inference_engine),
):
    """Get inference statistics for a model."""
    stats = inference_engine.get_stats(model_id, camera_id)
    if stats is None:
        raise HTTPException(status_code=404, detail="No stats available")
    return stats


@router.get("/panel", response_class=HTMLResponse)
async def inference_panel_html(
    request: Request,
    camera_id: str = "",
    inference_engine: InferenceEngine = Depends(get_inference_engine),
    frame_processor: FrameProcessor = Depends(get_frame_processor),
):
    """Inference settings panel as HTMX partial."""
    is_running = frame_processor.is_running(camera_id) if camera_id else False
    pipeline = frame_processor.get_pipeline_config(camera_id) if camera_id else None
    config = pipeline.inference_config if pipeline else InferenceConfig()

    return templates.TemplateResponse(
        "components/inference_panel.html",
        {
            "request": request,
            "camera_id": camera_id,
            "is_running": is_running,
            "config": config,
            "active_model_id": inference_engine.active_model_id,
        },
    )
