# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Orange Pi 5 NPU Real-time Inference Platform - A FastAPI-based web application for running AI inference on RK3588's NPU with RTSP/USB camera streams. Supports object detection, segmentation, pose estimation, and more with real-time visualization.

**Key Technologies:** FastAPI, HTMX, Tailwind CSS, OpenCV, RKNN Toolkit2 Lite, Pydantic v2

## Common Commands

### Development Server

```bash
# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Run server (production mode)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run server with auto-reload (development)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**CRITICAL:** Always use `--workers 1` (or omit, defaults to 1). The NPU runtime does not support multi-process access. Multiple workers will cause NPU device conflicts.

### CSS Development

```bash
# Build CSS once (production)
npm run build:css

# Watch mode (development) - run in separate terminal
npm run watch:css
```

The CSS must be built after any Tailwind class changes in templates. Output: [app/static/css/app.css](app/static/css/app.css)

### Testing

```bash
# Run all tests
pytest

# Verbose output with full tracebacks
pytest -v --tb=long

# Run specific test file
pytest tests/test_api.py
pytest tests/test_inference.py

# Run specific test function
pytest tests/test_api.py::test_health_check
```

Configuration: [pytest.ini](pytest.ini) - Uses `asyncio_mode = auto` for async test support.

### Model Conversion (ONNX → RKNN)

```bash
# INT8 quantization (recommended for performance)
python scripts/convert_model.py \
    --input model.onnx \
    --output models/detection/model.rknn \
    --type detection \
    --quantize int8 \
    --dataset ./calibration_images/

# FP16 (better accuracy, slower)
python scripts/convert_model.py \
    --input model.onnx \
    --output models/detection/model.rknn \
    --quantize fp16
```

### Benchmarking

```bash
python scripts/benchmark.py \
    --model models/detection/yolov8n.rknn \
    --iterations 200 \
    --warmup 20 \
    --core-mask 7
```

## Critical Configuration Notes

### Environment Variables - Nested Format Required

**IMPORTANT:** Environment variables use a nested structure with `APP_` prefix and `__` delimiter.

❌ **WRONG:**
```bash
SERVER_HOST=0.0.0.0
CAMERA_MAX_CAMERAS=8
```

✅ **CORRECT:**
```bash
APP_SERVER__HOST=0.0.0.0
APP_CAMERA__MAX_CAMERAS=8
```

The AppSettings class ([app/config.py](app/config.py:122-143)) is configured with:
- `env_prefix="APP_"`
- `env_nested_delimiter="__"`

Each nested setting class (ServerSettings, CameraSettings, etc.) gets its own namespace:
- Server: `APP_SERVER__*`
- Camera: `APP_CAMERA__*`
- Inference: `APP_INFERENCE__*`
- Stream: `APP_STREAM__*`
- Storage: `APP_STORAGE__*`
- Notification: `APP_NOTIFICATION__*`
- Security: `APP_SECURITY__*`

Reference: [.env](.env) for examples.

## Architecture Overview

### Layered Design

1. **API Layer** ([app/api/](app/api/)) - FastAPI routers serving both JSON and HTMX partial HTML
2. **Core Layer** ([app/core/](app/core/)) - Business logic (camera management, inference, ROI, events)
3. **Service Layer** ([app/services/](app/services/)) - External integrations (RKNN, OpenCV, MQTT, system monitoring)
4. **Data Layer** ([app/models/](app/models/)) - Pydantic v2 models for validation and serialization

### Dependency Injection Pattern

Components are initialized in the `lifespan` context manager ([app/main.py](app/main.py:146)) and stored in `app.state`. API endpoints access them via dependency injection functions in [app/dependencies.py](app/dependencies.py).

Example:
```python
# In main.py lifespan:
app.state.camera_manager = CameraManager(settings)
app.state.inference_engine = InferenceEngine(...)

# In API route:
@router.post("/cameras/{id}/start")
async def start_camera(
    id: str,
    camera_manager: CameraManager = Depends(get_camera_manager)
):
    await camera_manager.start_camera(id)
```

### Async/Threading Model

**Single-process, single event loop** architecture:
- API handlers run on the asyncio event loop
- Long-running tasks: `CameraStream._capture_loop()`, `FrameProcessor._pipeline_loop()`, `SystemMonitor._monitor_loop()`
- Blocking operations (OpenCV, NPU inference) run in ThreadPoolExecutor via `run_in_executor(None, ...)`

**Blocking operations moved to threads:**
- `cv2.VideoCapture.read()` - camera frame capture
- `rknn.inference()` - NPU inference execution
- `rknn.load_rknn()` / `init_runtime()` - model loading
- `cv2.imencode()`, `cv2.imwrite()` - image encoding/saving
- System monitoring file I/O (`/proc`, `/sys` reads)

See [ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md#5-비동기-처리-전략) for detailed async patterns.

### Core Components

**CameraManager** ([app/core/camera_manager.py](app/core/camera_manager.py))
- Manages multiple camera streams (RTSP, USB, CSI, file)
- Auto-reconnect with exponential backoff
- Frame callbacks for pipeline integration
- Uses `cv2.VideoCapture` with platform-specific backends

**InferenceEngine** ([app/core/inference_engine.py](app/core/inference_engine.py))
- RKNN model lifecycle (load/unload/hot-swap)
- NPU inference execution with preprocessing/postprocessing
- Supports: detection, segmentation, pose, classification, face, OCR
- Mock mode when RKNN not available (development on non-ARM platforms)

**FrameProcessor** ([app/core/frame_processor.py](app/core/frame_processor.py))
- Orchestrates the inference pipeline per camera
- Coordinates: frame capture → inference → ROI filtering → event detection → stream publishing
- Manages pipeline tasks and runtime configuration updates

**ROIManager** ([app/core/roi_manager.py](app/core/roi_manager.py))
- ROI preset management with JSON persistence
- Spatial operations: point-in-polygon, line crossing detection
- Normalized coordinates (0.0-1.0) for resolution independence

**StreamPublisher** ([app/core/stream_publisher.py](app/core/stream_publisher.py))
- MJPEG stream (`multipart/x-mixed-replace`)
- WebSocket streams (base64 JPEG + inference metadata JSON)
- Rate limiting and dead client cleanup

**EventHandler** ([app/core/event_handler.py](app/core/event_handler.py))
- Event bus pattern with listener registration
- Circular buffer history (max 1000 events)
- Snapshot capture on events
- Async listener dispatch

### Data Flow: Single Frame Inference

```
CameraStream → FrameProcessor → InferenceEngine → ROIManager → StreamPublisher
                                      ↓                ↓
                                  [NPU Thread]    EventHandler → NotificationService
```

1. Camera captures frame (blocking, runs in thread)
2. FrameProcessor gets latest frame (drop old frames)
3. InferenceEngine runs NPU inference (blocking, runs in thread)
4. ROIManager filters detections by active ROIs
5. EventHandler checks for alerts/line crossings
6. StreamPublisher encodes and broadcasts to MJPEG/WebSocket clients

See [ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md#4-데이터-흐름) for sequence diagrams.

## Development Guidelines

### Adding New Model Types

To support a new model type (e.g., depth estimation):

1. Add enum value to `ModelType` in [app/models/inference.py](app/models/inference.py)
2. Create result model class (e.g., `DepthResult`)
3. Implement `_postprocess_depth()` in [app/core/inference_engine.py](app/core/inference_engine.py)
4. Add type hints to `MODEL_TYPE_HINTS` in [app/core/model_registry.py](app/core/model_registry.py)
5. Add overlay rendering in `StreamPublisher._draw_overlay()` ([app/core/stream_publisher.py](app/core/stream_publisher.py))
6. Create model directory: `models/depth/`

### Adding New Notification Backends

To add a new notification channel (e.g., Slack, Telegram):

1. Add config fields to `NotificationSettings` in [app/config.py](app/config.py)
2. Implement `_send_<backend>()` method in [app/services/notification.py](app/services/notification.py)
3. Add to `handle_event()` task list with `asyncio.gather()`

### Alpine.js v3 Usage (HTMX Partials)

**IMPORTANT:** This project uses **Alpine.js v3** (`alpinejs@3.14.3`). Do NOT use Alpine.js v2 patterns.

❌ **WRONG (v2 pattern):**
```javascript
// __x.$data is Alpine.js v2 internal API — does not exist in v3
onclick="document.querySelector('[x-data]').__x.$data.selectCamera('id')"
```

✅ **CORRECT (v3 pattern):**
```html
<!-- Use Alpine directives — works on HTMX-injected partials too -->
@click="selectCamera('{{ camera.config.id }}')"
:class="selectedCamera === '{{ camera.config.id }}' ? 'active-class' : ''"
```

- Alpine.js v3 uses MutationObserver, so `@click`, `:class` etc. work on dynamically inserted HTML (HTMX partials)
- HTMX partial templates rendered inside an `x-data` scope automatically inherit the Alpine.js component context
- Never use raw `onclick` with Alpine internals; always use `@click` directives

### Cross-Platform Considerations

**Windows Support:**
- NPU inference runs in mock mode (RKNN is ARM64 Linux only)
- Use `CAP_DSHOW` backend for USB cameras on Windows
- System monitoring uses `psutil` (cross-platform)
- Event loop policy: `WindowsSelectorEventLoopPolicy` auto-configured in [app/main.py](app/main.py)

**Testing on non-ARM:**
- Mock mode allows full development/testing without NPU hardware
- All features work except actual NPU inference

### Memory Management

- **Frame dropping:** CameraStream keeps only latest frame (`_last_frame`), old frames auto-GC'd
- **Zero-copy:** Frames passed by reference until overlay rendering requires copy
- **MJPEG queue:** `maxsize=2` prevents unbounded memory growth
- **JPEG encoding:** Single encoding shared across all clients (WebSocket/MJPEG)

### Performance Tuning

**NPU Core Mask:**
- `7` (binary `111`) = all 3 cores, maximum performance (default)
- `1/2/4` = single core, for running 3 independent models in parallel
- Set via `INFERENCE_DEFAULT_CORE_MASK` or per-model in API

**Frame Skip:**
- `INFERENCE_ENABLE_FRAME_SKIP=true` - drop frames when inference can't keep up
- `skip_frames` in PipelineConfig - explicit N-frame skip (0 = every frame)

**Stream Optimization:**
- `STREAM_MJPEG_QUALITY=80` - balance quality vs bandwidth (1-100)
- `STREAM_MJPEG_MAX_FPS=30` - rate limit to reduce CPU load
- `STREAM_MAX_WS_CLIENTS=10` - limit concurrent WebSocket connections per stream

## File Structure Highlights

```
app/
├── main.py                 # App factory, lifespan, route registration
├── config.py               # Nested Pydantic settings (APP_* env vars)
├── dependencies.py         # DI providers (get_* functions)
├── api/                    # FastAPI routers (REST + HTMX)
│   ├── cameras.py          # Camera CRUD, start/stop
│   ├── models.py           # Model upload/load/activate
│   ├── inference.py        # Pipeline start/stop/config
│   ├── roi.py              # ROI preset management
│   ├── stream.py           # MJPEG/WebSocket/snapshot
│   └── system.py           # Health, status, events, logs
├── core/                   # Business logic
│   ├── camera_manager.py   # Camera lifecycle, frame callbacks
│   ├── inference_engine.py # NPU model management, inference
│   ├── frame_processor.py  # Pipeline orchestration
│   ├── roi_manager.py      # ROI filtering, line crossing
│   ├── stream_publisher.py # MJPEG/WS broadcasting
│   ├── event_handler.py    # Event bus, history, snapshots
│   └── model_registry.py   # Model discovery, metadata
├── services/               # External integrations
│   ├── rknn_service.py     # RKNN runtime wrapper
│   ├── opencv_service.py   # OpenCV utilities
│   ├── notification.py     # MQTT + Webhook
│   └── system_monitor.py   # CPU/NPU/memory monitoring
├── models/                 # Pydantic schemas
│   ├── camera.py
│   ├── inference.py
│   ├── roi.py
│   └── system.py
├── templates/              # Jinja2 templates (HTMX)
│   ├── base.html
│   ├── pages/
│   └── components/         # HTMX partial components
└── static/
    ├── css/app.css         # Tailwind build output
    └── js/                 # Alpine.js components

data/                       # Runtime data (persistent)
├── config.json             # App config
├── roi_presets/            # ROI preset JSON files
├── snapshots/              # Event snapshots
└── logs/                   # Application logs

models/                     # RKNN model files
├── detection/
├── segmentation/
├── pose/
├── classification/
├── face/
└── ocr/
```

## Troubleshooting

**NPU not found:**
- Check `/dev/dri` exists (Linux only)
- Verify RKNN Toolkit2 Lite installed: `python -c "from rknnlite.api import RKNNLite"`
- On non-ARM: system auto-switches to mock mode

**Model load fails:**
- Ensure model is `.rknn` format (not `.onnx` or `.pt`)
- Check model was converted for `rk3588` target platform
- Unload other models if hitting `INFERENCE_MAX_LOADED_MODELS` limit

**CSS not applied:**
- Run `npm run build:css` to build Tailwind CSS
- Check [app/static/css/app.css](app/static/css/app.css) exists and is not empty

**Environment variable errors:**
- Use nested format: `APP_SERVER__HOST` not `SERVER_HOST`
- See [.env](.env) for correct examples

**Port already in use:**
- Linux: `lsof -i :8000` or `fuser -k 8000/tcp`
- Windows: `netstat -ano | findstr :8000` then `taskkill /PID <PID> /F`
- Or change `APP_SERVER__PORT` in `.env`

**WebSocket disconnect:**
- Check `STREAM_MAX_WS_CLIENTS` limit
- Verify no firewall blocking WebSocket upgrade
- Browser console may show error details

## API Documentation

When `APP_DEBUG=true`:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

In production (`APP_DEBUG=false`), API docs are disabled for security.

## Additional Resources

- [README.md](README.md) - Installation, setup, usage guide
- [ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) - Detailed system architecture
- [API_REFERENCE.md](docs/api/API_REFERENCE.md) - Complete API endpoint documentation
- [USER_GUIDE.md](docs/guides/USER_GUIDE.md) - End-user feature guide
- [DEPLOYMENT.md](docs/guides/DEPLOYMENT.md) - Production deployment guide
