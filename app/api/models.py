"""
Model Management API

Handles model listing, upload, deletion, and metadata management.
"""

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_DIR, AppSettings
from app.core.inference_engine import InferenceEngine
from app.core.model_registry import ModelRegistry
from app.dependencies import get_app_settings, get_inference_engine, get_model_registry
from app.models.inference import (
    ModelInfo,
    ModelListResponse,
    ModelResponse,
    ModelState,
    ModelStatus,
    ModelType,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))


@router.get("", response_model=ModelListResponse)
async def list_models(
    model_registry: ModelRegistry = Depends(get_model_registry),
    inference_engine: InferenceEngine = Depends(get_inference_engine),
):
    """List all available models."""
    models = []
    for info, state in model_registry.get_all():
        # Update state with runtime info
        if info.id in inference_engine.loaded_model_ids:
            state.status = ModelStatus.LOADED
        state.is_active = info.id == inference_engine.active_model_id
        models.append(ModelResponse(info=info, state=state))

    return ModelListResponse(
        models=models,
        total=len(models),
        active_model_id=inference_engine.active_model_id,
    )


@router.get("/list", response_class=HTMLResponse)
async def list_models_html(
    request: Request,
    model_registry: ModelRegistry = Depends(get_model_registry),
    inference_engine: InferenceEngine = Depends(get_inference_engine),
):
    """List models as HTMX partial HTML."""
    models = []
    for info, state in model_registry.get_all():
        if info.id in inference_engine.loaded_model_ids:
            state.status = ModelStatus.LOADED
        state.is_active = info.id == inference_engine.active_model_id
        models.append({"info": info, "state": state})

    return templates.TemplateResponse(
        request, "components/model_selector.html",
        {
            "models": models,
            "active_model_id": inference_engine.active_model_id,
        },
    )


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: str,
    model_registry: ModelRegistry = Depends(get_model_registry),
    inference_engine: InferenceEngine = Depends(get_inference_engine),
):
    """Get model details."""
    info = model_registry.get_model(model_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Model not found")

    state = model_registry.get_state(model_id) or ModelState(id=model_id)
    if model_id in inference_engine.loaded_model_ids:
        state.status = ModelStatus.LOADED
    state.is_active = model_id == inference_engine.active_model_id

    return ModelResponse(info=info, state=state)


@router.post("/upload", response_model=ModelResponse, status_code=201)
async def upload_model(
    file: UploadFile = File(...),
    name: str = Form(None),
    model_type: ModelType = Form(ModelType.DETECTION),
    description: str = Form(None),
    settings: AppSettings = Depends(get_app_settings),
    model_registry: ModelRegistry = Depends(get_model_registry),
):
    """Upload a new RKNN model file."""
    # Validate file
    if not file.filename or not file.filename.endswith(".rknn"):
        raise HTTPException(status_code=400, detail="Only .rknn files are supported")

    # Check file size
    content = await file.read()
    file_size_mb = len(content) / (1024 * 1024)
    if file_size_mb > settings.security.max_upload_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({file_size_mb:.1f}MB). Max: {settings.security.max_upload_size_mb}MB",
        )

    try:
        info = await model_registry.upload_model(
            file_content=content,
            filename=file.filename,
            model_type=model_type,
            name=name,
            description=description,
        )
        state = model_registry.get_state(info.id) or ModelState(id=info.id)
        return ModelResponse(info=info, state=state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{model_id}/load")
async def load_model(
    model_id: str,
    model_registry: ModelRegistry = Depends(get_model_registry),
    inference_engine: InferenceEngine = Depends(get_inference_engine),
):
    """Load a model onto the NPU."""
    info = model_registry.get_model(model_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Model not found")

    try:
        await inference_engine.load_model(info)
        model_registry.update_state(model_id, status=ModelStatus.LOADED)
        return {"status": "ok", "model_id": model_id, "message": "Model loaded"}
    except Exception as e:
        model_registry.update_state(
            model_id, status=ModelStatus.ERROR, error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{model_id}/unload")
async def unload_model(
    model_id: str,
    model_registry: ModelRegistry = Depends(get_model_registry),
    inference_engine: InferenceEngine = Depends(get_inference_engine),
):
    """Unload a model from the NPU."""
    try:
        await inference_engine.unload_model(model_id)
        model_registry.update_state(model_id, status=ModelStatus.AVAILABLE)
        return {"status": "ok", "model_id": model_id, "message": "Model unloaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{model_id}/activate")
async def activate_model(
    model_id: str,
    model_registry: ModelRegistry = Depends(get_model_registry),
    inference_engine: InferenceEngine = Depends(get_inference_engine),
):
    """Set model as active for inference (auto-loads if needed)."""
    info = model_registry.get_model(model_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Model not found")

    try:
        # Auto-load if not loaded
        if model_id not in inference_engine.loaded_model_ids:
            await inference_engine.load_model(info)
            model_registry.update_state(model_id, status=ModelStatus.LOADED)

        await inference_engine.set_active_model(model_id)
        return {"status": "ok", "model_id": model_id, "message": "Model activated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{model_id}")
async def delete_model(
    model_id: str,
    delete_file: bool = False,
    model_registry: ModelRegistry = Depends(get_model_registry),
    inference_engine: InferenceEngine = Depends(get_inference_engine),
):
    """Remove model from registry (optionally delete file)."""
    # Unload if loaded
    if model_id in inference_engine.loaded_model_ids:
        await inference_engine.unload_model(model_id)

    removed = await model_registry.remove_model(model_id, delete_file=delete_file)
    if not removed:
        raise HTTPException(status_code=404, detail="Model not found")

    return {"status": "ok", "model_id": model_id}


@router.post("/scan")
async def scan_models(
    model_registry: ModelRegistry = Depends(get_model_registry),
):
    """Rescan models directory."""
    count = await model_registry.scan_models()
    return {"status": "ok", "models_found": count}
