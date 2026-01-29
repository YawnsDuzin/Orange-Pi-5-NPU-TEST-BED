"""
FastAPI Dependency Injection

Provides access to shared application services through FastAPI's
dependency injection system. This ensures clean separation of concerns
and testability.
"""

from fastapi import Depends, Request

from app.config import AppSettings
from app.core.camera_manager import CameraManager
from app.core.event_handler import EventHandler
from app.core.inference_engine import InferenceEngine
from app.core.model_registry import ModelRegistry
from app.core.roi_manager import ROIManager
from app.core.stream_publisher import StreamPublisher
from app.services.notification import NotificationService
from app.services.system_monitor import SystemMonitor


def get_app_settings(request: Request) -> AppSettings:
    """Get application settings."""
    return request.app.state.settings


def get_camera_manager(request: Request) -> CameraManager:
    """Get camera manager instance."""
    return request.app.state.camera_manager


def get_model_registry(request: Request) -> ModelRegistry:
    """Get model registry instance."""
    return request.app.state.model_registry


def get_inference_engine(request: Request) -> InferenceEngine:
    """Get inference engine instance."""
    return request.app.state.inference_engine


def get_roi_manager(request: Request) -> ROIManager:
    """Get ROI manager instance."""
    return request.app.state.roi_manager


def get_stream_publisher(request: Request) -> StreamPublisher:
    """Get stream publisher instance."""
    return request.app.state.stream_publisher


def get_event_handler(request: Request) -> EventHandler:
    """Get event handler instance."""
    return request.app.state.event_handler


def get_notification_service(request: Request) -> NotificationService:
    """Get notification service instance."""
    return request.app.state.notification_service


def get_system_monitor(request: Request) -> SystemMonitor:
    """Get system monitor instance."""
    return request.app.state.system_monitor
