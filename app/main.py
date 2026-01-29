"""
NPU Inference Platform - FastAPI Application Entry Point

Orange Pi 5 Plus (RK3588) NPU real-time inference test platform.
Provides a web-based interface for managing cameras, models, ROI, and inference.
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import cameras, inference, models, roi, stream, system
from app.config import APP_DIR, AppSettings, get_settings
from app.core.camera_manager import CameraManager
from app.core.event_handler import EventHandler
from app.core.frame_processor import FrameProcessor
from app.core.inference_engine import InferenceEngine
from app.core.model_registry import ModelRegistry
from app.core.roi_manager import ROIManager
from app.core.stream_publisher import StreamPublisher
from app.services.notification import NotificationService
from app.services.system_monitor import SystemMonitor

logger = logging.getLogger(__name__)


def setup_logging(settings: AppSettings) -> None:
    """Configure application logging."""
    log_level = getattr(logging, settings.server.log_level.upper(), logging.INFO)
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                settings.storage.data_dir / "logs" / "app.log",
                encoding="utf-8",
            ),
        ],
    )

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def ensure_directories(settings: AppSettings) -> None:
    """Ensure required data directories exist."""
    dirs = [
        settings.storage.data_dir,
        settings.storage.data_dir / "roi_presets",
        settings.storage.data_dir / "snapshots",
        settings.storage.data_dir / "logs",
        settings.storage.models_dir,
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    settings = get_settings()

    setup_logging(settings)
    ensure_directories(settings)

    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")

    # Initialize core components
    camera_manager = CameraManager(settings.camera)
    model_registry = ModelRegistry(settings.storage.models_dir, settings.inference)
    inference_engine = InferenceEngine(settings.inference)
    roi_manager = ROIManager(settings.storage.data_dir / "roi_presets")
    stream_publisher = StreamPublisher(settings.stream)
    event_handler = EventHandler(
        max_history=1000,
        snapshots_dir=settings.storage.data_dir / "snapshots",
    )
    notification_service = NotificationService(settings.notification)
    system_monitor = SystemMonitor()

    # Create frame processor (pipeline orchestrator)
    frame_processor = FrameProcessor(
        camera_manager=camera_manager,
        inference_engine=inference_engine,
        roi_manager=roi_manager,
        stream_publisher=stream_publisher,
        event_handler=event_handler,
    )

    # Store in app state for dependency injection
    app.state.settings = settings
    app.state.camera_manager = camera_manager
    app.state.model_registry = model_registry
    app.state.inference_engine = inference_engine
    app.state.roi_manager = roi_manager
    app.state.stream_publisher = stream_publisher
    app.state.event_handler = event_handler
    app.state.frame_processor = frame_processor
    app.state.notification_service = notification_service
    app.state.system_monitor = system_monitor

    # Load persisted configuration
    await model_registry.scan_models()
    await roi_manager.load_presets()

    # Start system monitor
    await system_monitor.start()

    # Connect event handler to notification service
    event_handler.register_listener(notification_service.handle_event)

    logger.info("All services initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down services...")
    await frame_processor.stop_all()
    await camera_manager.stop_all()
    await inference_engine.unload_all()
    await system_monitor.stop()
    await notification_service.close()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="RKNN NPU real-time inference test and validation platform",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Static files
    static_dir = APP_DIR / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # API routes
    app.include_router(cameras.router, prefix="/api/cameras", tags=["Cameras"])
    app.include_router(models.router, prefix="/api/models", tags=["Models"])
    app.include_router(inference.router, prefix="/api/inference", tags=["Inference"])
    app.include_router(roi.router, prefix="/api/roi", tags=["ROI"])
    app.include_router(stream.router, prefix="/api/stream", tags=["Stream"])
    app.include_router(system.router, prefix="/api/system", tags=["System"])

    # Template engine
    templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Main dashboard page."""
        return templates.TemplateResponse(
            request, "index.html",
            {
                "app_name": settings.app_name,
                "app_version": settings.app_version,
            },
        )

    @app.get("/cameras", response_class=HTMLResponse)
    async def cameras_page(request: Request):
        """Camera management page."""
        return templates.TemplateResponse(
            request, "pages/cameras.html",
            {"app_name": settings.app_name},
        )

    @app.get("/models", response_class=HTMLResponse)
    async def models_page(request: Request):
        """Model management page."""
        return templates.TemplateResponse(
            request, "pages/models.html",
            {"app_name": settings.app_name},
        )

    @app.get("/monitor", response_class=HTMLResponse)
    async def monitor_page(request: Request):
        """Real-time monitoring page."""
        return templates.TemplateResponse(
            request, "pages/monitor.html",
            {"app_name": settings.app_name},
        )

    @app.get("/settings", response_class=HTMLResponse)
    async def settings_page(request: Request):
        """System settings page."""
        return templates.TemplateResponse(
            request, "pages/settings.html",
            {"app_name": settings.app_name},
        )

    return app


# Application instance
app = create_app()
