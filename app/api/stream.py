"""
Stream API

MJPEG and WebSocket streaming endpoints for real-time video.
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.core.camera_manager import CameraManager
from app.core.stream_publisher import StreamPublisher
from app.dependencies import get_camera_manager, get_stream_publisher
from app.services.opencv_service import frame_to_jpeg

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/{camera_id}/mjpeg")
async def mjpeg_stream(
    camera_id: str,
    camera_manager: CameraManager = Depends(get_camera_manager),
    stream_publisher: StreamPublisher = Depends(get_stream_publisher),
):
    """MJPEG video stream for a camera."""
    if camera_manager.get_state(camera_id) is None:
        raise HTTPException(status_code=404, detail="Camera not found")

    queue = stream_publisher.create_mjpeg_queue(camera_id)

    async def generate():
        try:
            while True:
                try:
                    jpeg_bytes = await asyncio.wait_for(queue.get(), timeout=10.0)
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n"
                        + jpeg_bytes
                        + b"\r\n"
                    )
                except asyncio.TimeoutError:
                    # Send keep-alive frame
                    frame = camera_manager.get_frame(camera_id)
                    if frame is not None:
                        jpeg_bytes = frame_to_jpeg(frame, quality=70)
                        yield (
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n\r\n"
                            + jpeg_bytes
                            + b"\r\n"
                        )
                    else:
                        # Send a minimal JPEG to keep connection alive
                        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n\r\n"
        except asyncio.CancelledError:
            pass
        finally:
            stream_publisher.remove_mjpeg_queue(camera_id, queue)

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
        },
    )


@router.websocket("/{camera_id}/ws")
async def websocket_stream(
    camera_id: str,
    websocket: WebSocket,
):
    """WebSocket video stream with inference metadata."""
    await websocket.accept()

    # Access app state
    camera_manager = websocket.app.state.camera_manager
    stream_publisher = websocket.app.state.stream_publisher

    if camera_manager.get_state(camera_id) is None:
        await websocket.close(code=4004, reason="Camera not found")
        return

    await stream_publisher.register_websocket(camera_id, websocket)

    try:
        while True:
            # Wait for client messages (e.g., config updates)
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                # Handle client commands
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        await stream_publisher.unregister_websocket(camera_id, websocket)


@router.get("/{camera_id}/snapshot")
async def get_snapshot(
    camera_id: str,
    quality: int = 90,
    camera_manager: CameraManager = Depends(get_camera_manager),
):
    """Get a single frame snapshot from a camera."""
    frame = camera_manager.get_frame(camera_id)
    if frame is None:
        raise HTTPException(status_code=404, detail="No frame available")

    quality = max(1, min(100, quality))
    jpeg_bytes = frame_to_jpeg(frame, quality=quality)

    return StreamingResponse(
        iter([jpeg_bytes]),
        media_type="image/jpeg",
        headers={"Content-Disposition": f"inline; filename=snapshot_{camera_id}.jpg"},
    )


@router.get("/{camera_id}/preview")
async def get_preview(
    camera_id: str,
    camera_manager: CameraManager = Depends(get_camera_manager),
    stream_publisher: StreamPublisher = Depends(get_stream_publisher),
):
    """Get a low-resolution preview thumbnail."""
    frame = camera_manager.get_frame(camera_id)
    if frame is None:
        raise HTTPException(status_code=404, detail="No frame available")

    preview_bytes = await stream_publisher.publish_preview(camera_id, frame)

    return StreamingResponse(
        iter([preview_bytes]),
        media_type="image/jpeg",
    )
