# NPU Inference Platform - Architecture Documentation

> Orange Pi 5 Plus (RK3588) NPU Real-time Inference Test Platform

**Version:** 1.0.0
**Target Hardware:** Orange Pi 5 Plus (Rockchip RK3588, 3-core NPU, 6 TOPS)
**Last Updated:** 2026-01-29

---

## 목차 (Table of Contents)

1. [시스템 아키텍처 개요](#1-시스템-아키텍처-개요)
2. [계층 구조](#2-계층-구조)
3. [핵심 컴포넌트 상세](#3-핵심-컴포넌트-상세)
4. [데이터 흐름](#4-데이터-흐름)
5. [비동기 처리 전략](#5-비동기-처리-전략)
6. [보안 아키텍처](#6-보안-아키텍처)
7. [성능 최적화](#7-성능-최적화)
8. [확장 가능성](#8-확장-가능성)

---

## 1. 시스템 아키텍처 개요

### 1.1 High-Level Architecture

본 플랫폼은 Orange Pi 5 Plus (RK3588 SoC)의 내장 NPU를 활용하여 실시간 비디오
스트림에 대한 AI inference를 수행하는 web 기반 시스템이다. FastAPI를 기반으로 한
비동기 서버가 카메라 입력, NPU inference, 스트림 배포, 이벤트 처리를 통합적으로
관리한다.

```
+================================================================+
|                    Client (Web Browser)                         |
|  +------------------+  +------------------+  +---------------+ |
|  |  HTMX + Alpine.js|  |  WebSocket Client|  |  MJPEG <img>  | |
|  |  (UI Interaction)|  |  (Real-time Data)|  |  (Video Feed) | |
|  +--------+---------+  +--------+---------+  +-------+-------+ |
+===========|========================|==================|=========+
            |                        |                  |
            v                        v                  v
+================================================================+
|                   FastAPI Application Server                    |
|  +----------------------------------------------------------+  |
|  |                   API Layer (Routers)                     |  |
|  |  /api/cameras  /api/models  /api/inference  /api/stream   |  |
|  |  /api/roi      /api/system                                |  |
|  +---------------------------+------------------------------+  |
|  |                   Dependency Injection                    |  |
|  +---------------------------+------------------------------+  |
|  |               Business Logic (Core)                       |  |
|  |  +-------------+ +--------------+ +--------------------+  |  |
|  |  |CameraManager| |InferenceEngine| |  FrameProcessor   |  |  |
|  |  +-------------+ +--------------+ +--------------------+  |  |
|  |  +-------------+ +--------------+ +--------------------+  |  |
|  |  | ROIManager  | |StreamPublisher| |   EventHandler    |  |  |
|  |  +-------------+ +--------------+ +--------------------+  |  |
|  |  +----------------------------------------------------+  |  |
|  |  |              ModelRegistry                          |  |  |
|  |  +----------------------------------------------------+  |  |
|  +---------------------------+------------------------------+  |
|  |                  Service Layer                            |  |
|  |  +-----------+ +------------+ +-------------------------+ |  |
|  |  |RKNNService| |OpenCV Svc  | |NotificationService     | |  |
|  |  +-----------+ +------------+ | (MQTT / Webhook)        | |  |
|  |  +-----------+                +-------------------------+ |  |
|  |  |SystemMonitor|                                         |  |
|  |  +-----------+                                           |  |
|  +----------------------------------------------------------+  |
+================================================================+
            |                        |                  |
            v                        v                  v
+================================================================+
|                    Hardware / OS Layer                          |
|  +-----------+  +-----------+  +----------------------------+  |
|  | RK3588 NPU|  | USB/CSI   |  | Linux sysfs (/proc, /sys) |  |
|  | (RKNN     |  | Cameras   |  | Temperature, CPU, Memory   |  |
|  |  Toolkit) |  | RTSP Feeds|  +----------------------------+  |
|  +-----------+  +-----------+                                  |
|  +-----------+  +-----------+                                  |
|  | /dev/rknpu|  | /dev/video|                                  |
|  +-----------+  +-----------+                                  |
+================================================================+
```

### 1.2 Component Interaction Flow

시스템 시작 시 `lifespan` context manager가 모든 core component를 초기화하고
`app.state`에 저장한다. FastAPI의 dependency injection 시스템이 각 API endpoint에
필요한 component 인스턴스를 제공한다.

```
                    Application Startup
                          |
                          v
              +-------------------------+
              |    create_app()         |
              |  - FastAPI instance     |
              |  - CORS middleware      |
              |  - Router registration  |
              |  - Static files mount   |
              +------------+------------+
                           |
                           v
              +-------------------------+
              |    lifespan() handler   |
              |  1. setup_logging()     |
              |  2. ensure_directories()|
              |  3. Initialize:         |
              |     - CameraManager     |
              |     - ModelRegistry     |
              |     - InferenceEngine   |
              |     - ROIManager        |
              |     - StreamPublisher   |
              |     - EventHandler      |
              |     - NotificationSvc   |
              |     - SystemMonitor     |
              |  4. scan_models()       |
              |  5. load_presets()      |
              |  6. start monitoring    |
              |  7. connect events to   |
              |     notifications       |
              +------------+------------+
                           |
                           v
              +-------------------------+
              | app.state (Singleton    |
              | Registry for DI)        |
              +-------------------------+
                           |
                           v
              +-------------------------+
              |  dependencies.py        |
              |  Request -> app.state   |
              |  -> Component Instance  |
              +-------------------------+
```

---

## 2. 계층 구조

본 시스템은 5개의 명확한 계층으로 분리되어 있으며, 각 계층은 아래 계층에만 의존한다.
상위 계층이 하위 계층에 접근하되, 역방향 의존은 허용하지 않는 단방향 의존 원칙을 따른다.

### 2.1 Presentation Layer (HTMX + Tailwind CSS + Alpine.js)

```
app/templates/
  +-- base.html                          # Base layout (Tailwind, HTMX, Alpine.js CDN)
  +-- index.html                         # Dashboard 메인 페이지
  +-- pages/
  |     +-- cameras.html                 # 카메라 관리 페이지
  |     +-- models.html                  # 모델 관리 페이지
  |     +-- monitor.html                 # 실시간 모니터링 페이지
  |     +-- settings.html                # 시스템 설정 페이지
  +-- components/
        +-- camera_card.html             # 개별 카메라 카드 (HTMX partial)
        +-- camera_list.html             # 카메라 목록 (HTMX partial)
        +-- inference_panel.html         # Inference 제어 패널
        +-- model_selector.html          # 모델 선택 UI
        +-- roi_editor.html              # ROI 편집기 (Canvas 기반)
        +-- stats_panel.html             # 시스템 상태 패널
        +-- log_viewer.html              # 실시간 로그 뷰어

app/static/
  +-- css/app.css                        # Custom CSS (Tailwind 확장)
  +-- js/
        +-- roi-canvas.js               # ROI Canvas 인터랙션 (Alpine.js)
        +-- stats-chart.js              # 성능 차트 렌더링
        +-- stream-viewer.js            # 스트림 뷰어 (WebSocket/MJPEG)
```

**UI 통신 패턴:**

| 패턴 | 용도 | 기술 |
|------|------|------|
| HTMX Partial Swap | 서버 렌더링 UI 업데이트 | `hx-get`, `hx-swap`, `hx-trigger` |
| HTMX Polling | 주기적 상태 업데이트 (카메라, 시스템) | `hx-trigger="every 2s"` |
| WebSocket | 실시간 비디오 프레임 + inference 메타데이터 | base64 JPEG + JSON payload |
| MJPEG Stream | 저지연 비디오 표시 (`<img>` 태그 호환) | `multipart/x-mixed-replace` |
| Alpine.js | 클라이언트 사이드 상호작용 (ROI 편집 등) | `x-data`, `x-on`, `x-show` |

### 2.2 API Layer (FastAPI Routers)

모든 API endpoint는 `/api/` prefix 하위에 resource 단위로 분리된다.
각 router는 JSON API와 HTMX partial HTML 응답을 모두 제공하는
dual-format 설계를 따른다.

```
app/api/
  +-- cameras.py       /api/cameras/*       카메라 CRUD, 시작/정지, 상태 조회
  +-- models.py        /api/models/*        모델 목록, 업로드, 로드/언로드, 활성화
  +-- inference.py     /api/inference/*     Pipeline 시작/정지, 설정 변경, 통계
  +-- roi.py           /api/roi/*           ROI Preset CRUD, ROI 추가/삭제, 활성화
  +-- stream.py        /api/stream/*        MJPEG 스트림, WebSocket, Snapshot
  +-- system.py        /api/system/*        Health check, 시스템 상태, 이벤트, 로그
```

**Router별 Endpoint 요약:**

```
/api/cameras
  GET    /                   카메라 목록 (JSON)
  GET    /list               카메라 목록 (HTMX partial)
  POST   /                   카메라 등록
  GET    /{id}               카메라 상세
  PUT    /{id}               카메라 설정 수정
  DELETE /{id}               카메라 삭제
  POST   /{id}/start         스트림 시작
  POST   /{id}/stop          스트림 정지
  GET    /{id}/status         상태 조회 (polling용)

/api/models
  GET    /                   모델 목록 (JSON)
  GET    /list               모델 목록 (HTMX partial)
  GET    /{id}               모델 상세
  POST   /upload             .rknn 파일 업로드
  POST   /{id}/load          NPU에 모델 로드
  POST   /{id}/unload        NPU에서 모델 언로드
  POST   /{id}/activate      활성 모델 설정
  DELETE /{id}               모델 삭제
  POST   /scan               모델 디렉토리 재스캔

/api/inference
  POST   /start              Inference pipeline 시작
  POST   /stop/{camera_id}   Pipeline 정지
  PUT    /config/{camera_id} 파라미터 실시간 변경
  GET    /status/{camera_id} Pipeline 상태
  GET    /stats/{model_id}   Inference 통계
  GET    /panel              제어 패널 (HTMX partial)

/api/roi
  GET    /presets             Preset 목록
  POST   /presets             Preset 생성
  GET    /presets/{id}        Preset 상세
  DELETE /presets/{id}        Preset 삭제
  POST   /presets/{id}/activate    Preset 활성화
  POST   /presets/{id}/rois        ROI 추가
  DELETE /presets/{id}/rois/{rid}  ROI 제거
  GET    /editor              ROI 편집기 (HTMX partial)

/api/stream
  GET    /{id}/mjpeg          MJPEG 비디오 스트림
  WS     /{id}/ws             WebSocket 스트림 (프레임 + 메타데이터)
  GET    /{id}/snapshot        단일 프레임 스냅샷
  GET    /{id}/preview         저해상도 미리보기

/api/system
  GET    /health              Health check
  GET    /status              시스템 리소스 상태
  GET    /status/panel         상태 패널 (HTMX partial)
  GET    /events              이벤트 히스토리
  POST   /events/{id}/acknowledge  이벤트 확인
  GET    /logs                로그 조회
  GET    /logs/viewer          로그 뷰어 (HTMX partial)
  GET    /info                시스템 정보
```

### 2.3 Business Logic Layer (Core Modules)

핵심 비즈니스 로직을 담당하는 계층이다. 각 모듈은 단일 책임 원칙(SRP)을 따르며,
asyncio 기반으로 비동기 작업을 처리한다.

```
app/core/
  +-- camera_manager.py    CameraManager, CameraStream, FPSCounter
  +-- inference_engine.py  InferenceEngine, RKNNModelWrapper, _InferenceStatsTracker
  +-- roi_manager.py       ROIManager (spatial ops, line crossing, preset persistence)
  +-- stream_publisher.py  StreamPublisher (MJPEG queue, WebSocket broadcast)
  +-- frame_processor.py   FrameProcessor, PipelineConfig (pipeline orchestration)
  +-- event_handler.py     EventHandler (event bus, history, snapshot)
  +-- model_registry.py    ModelRegistry (discovery, metadata, upload)
```

### 2.4 Service Layer (External Integrations)

외부 시스템 및 하드웨어와의 인터페이스를 제공하는 계층이다.
Core 모듈이 직접 하드웨어에 접근하지 않고, Service Layer를 통해 추상화된 접근을
수행한다.

```
app/services/
  +-- rknn_service.py      RKNN Toolkit2 Lite wrapper (NPU 하드웨어 감지, 모델 검증)
  +-- opencv_service.py    OpenCV 유틸리티 (resize, letterbox, encoding, drawing)
  +-- notification.py      NotificationService (MQTT publish, Webhook POST)
  +-- system_monitor.py    SystemMonitor (CPU, NPU, Memory, Temperature, Disk, Network)
```

### 2.5 Data Layer (Pydantic Models + File Storage)

모든 데이터 구조는 Pydantic v2 모델로 정의되며, 입출력 검증과 직렬화를 자동으로
수행한다. 영속 데이터는 JSON 파일 기반으로 저장된다.

```
app/models/                               data/
  +-- camera.py                             +-- config.json
  |   CameraType, CameraStatus,            +-- roi_presets/
  |   CameraCreate, CameraUpdate,          |     +-- {preset_id}.json
  |   CameraConfig, CameraState,           +-- snapshots/
  |   CameraResponse, CameraListResponse   |     +-- {camera}_{event}_{ts}.jpg
  |                                         +-- logs/
  +-- inference.py                                +-- app.log
  |   ModelType, ModelStatus,
  |   ModelInfo, ModelState,              models/
  |   InferenceConfig, InferenceControl,    +-- detection/
  |   BoundingBox, Detection,               |     +-- *.rknn
  |   SegmentationMask, PoseKeypoint,       +-- segmentation/
  |   PoseResult, ClassificationResult,     +-- pose/
  |   InferenceResult, InferenceStats       +-- classification/
  |                                         +-- face/
  +-- roi.py                                +-- ocr/
  |   ROIType, ROIAction, Point,            +-- model_metadata.json
  |   ROICreate, ROIConfig, ROIUpdate,
  |   ROIPreset, ROIPresetCreate,
  |   LineCrossingEvent, ROIAlertEvent
  |
  +-- system.py
      CPUInfo, NPUInfo, MemoryInfo,
      TemperatureInfo, DiskInfo, NetworkInfo,
      SystemStatus, HealthCheck,
      LogEntry, EventRecord, AppConfig
```

**설정 관리 구조 (`app/config.py`):**

```
AppSettings                        (.env, 환경 변수)
  +-- server: ServerSettings       SERVER_* prefix
  |     host, port, workers, log_level
  +-- camera: CameraSettings       CAMERA_* prefix
  |     max_cameras, reconnect_interval, frame_buffer_size
  +-- inference: InferenceSettings INFERENCE_* prefix
  |     default_confidence, default_nms_threshold, default_core_mask
  +-- stream: StreamSettings       STREAM_* prefix
  |     mjpeg_quality, mjpeg_max_fps, ws_max_fps, max_ws_clients
  +-- storage: StorageSettings     STORAGE_* prefix
  |     data_dir, models_dir, max_snapshots
  +-- notification: NotificationSettings  NOTIFY_* prefix
  |     mqtt_enabled, mqtt_broker, webhook_enabled, webhook_url
  +-- security: SecuritySettings   SECURITY_* prefix
        cors_origins, max_upload_size_mb, allowed_model_extensions
```

---

## 3. 핵심 컴포넌트 상세

### 3.1 CameraManager

**파일:** `app/core/camera_manager.py`
**역할:** 다중 카메라 스트림의 lifecycle 관리, 자동 재연결, 프레임 전달

```
CameraManager
  |
  +-- cameras: dict[str, CameraStream]    # camera_id -> CameraStream 매핑
  +-- _lock: asyncio.Lock                 # 동시성 보호
  |
  +-- add_camera(config) -> CameraStream
  +-- remove_camera(camera_id) -> bool
  +-- start_camera(camera_id)
  +-- stop_camera(camera_id)
  +-- get_frame(camera_id) -> np.ndarray   # 최신 프레임 즉시 반환
  +-- get_state(camera_id) -> CameraState
  +-- stop_all()

CameraStream
  |
  +-- config: CameraConfig               # RTSP/USB/CSI/FILE 설정
  +-- state: CameraState                 # 실시간 상태 (FPS, 해상도, 에러)
  +-- _cap: cv2.VideoCapture             # OpenCV 캡처 핸들
  +-- _frame_callbacks: list[Callable]   # 프레임 수신 콜백 목록
  +-- _last_frame: np.ndarray            # 최신 프레임 버퍼
  |
  +-- start() -> asyncio.Task           # 캡처 루프 시작
  +-- stop()                            # 리소스 해제
  +-- on_frame(callback)                # 콜백 등록
```

**카메라 소스 및 Backend 매핑:**

| CameraType | Source 예시 | OpenCV Backend | 비고 |
|-----------|------------|---------------|------|
| RTSP | `rtsp://192.168.1.100:554/stream` | `CAP_FFMPEG` | TCP 전송 기본, timeout 설정 |
| USB | `0` 또는 `/dev/video0` | `CAP_V4L2` | Video4Linux2 직접 접근 |
| CSI | GStreamer pipeline 문자열 | `CAP_GSTREAMER` | RK3588 ISP 파이프라인 |
| FILE | `/path/to/video.mp4` | `CAP_FFMPEG` | 파일 끝 도달 시 자동 정지 |

**재연결 전략:**

```
연결 시도 실패 시:
  reconnect_count++
  wait_time = min(reconnect_interval * 1.5^(count-1), 60초)
                  (Exponential backoff, 최대 60초)

  if max_retries > 0 AND reconnect_count > max_retries:
      status = ERROR ("Max reconnect retries exceeded")
      break
  else:
      sleep(wait_time)
      retry

연결 성공 시:
  reconnect_count = 0
  status = CONNECTED
```

**프레임 전달 메커니즘:**

`_capture_loop()`는 `asyncio.Task`로 실행되며, OpenCV의 blocking `cap.read()` 호출을
`run_in_executor(None, ...)`를 통해 기본 ThreadPoolExecutor에서 수행한다.
프레임 획득 후 등록된 모든 callback을 await로 호출하고, `asyncio.sleep(0.001)`로
이벤트 루프에 제어를 양보한다.

### 3.2 InferenceEngine

**파일:** `app/core/inference_engine.py`
**역할:** RKNN 모델 lifecycle 관리, NPU inference 실행, 통계 추적

```
InferenceEngine
  |
  +-- _models: dict[str, RKNNModelWrapper]   # 로드된 모델 풀
  +-- _active_model_id: Optional[str]        # 현재 활성 모델
  +-- _stats: dict[str, _InferenceStatsTracker]
  +-- _lock: asyncio.Lock
  |
  +-- load_model(model_info, core_mask)      # NPU에 모델 로드
  +-- set_active_model(model_id)             # 활성 모델 전환 (hot-swap)
  +-- infer(frame, config, camera_id)        # inference 실행
  +-- unload_model(model_id)                 # 모델 언로드
  +-- unload_all()
  +-- get_stats(model_id) -> InferenceStats

RKNNModelWrapper
  |
  +-- info: ModelInfo                         # 모델 메타데이터
  +-- _rknn: RKNNLite                        # RKNN Toolkit2 Lite 인스턴스
  |
  +-- load(core_mask)     # rknn.load_rknn() + init_runtime()
  +-- infer(frame, config) -> InferenceResult
  +-- release()           # rknn.release()
  |
  [Internal Pipeline]
  +-- _preprocess(frame)
  |     - cv2.resize -> input_size (e.g. 640x640)
  |     - cv2.cvtColor BGR -> RGB
  |
  +-- _postprocess(outputs, shape, config)
  |     Detection:       _postprocess_detection    (YOLO output parsing + NMS)
  |     Segmentation:    _postprocess_segmentation (detection + mask overlay)
  |     Pose:            _postprocess_pose         (keypoint extraction)
  |     Classification:  _postprocess_classification (softmax + top-k)
  |     Face Detection:  _postprocess_detection    (동일 파이프라인)
  |     Face Recognition: _postprocess_classification
  |     OCR:             _postprocess_classification
  |
  +-- _parse_yolo_output(outputs, config)
  |     - Multi-head output 병합
  |     - center format -> corner format 변환
  |     - confidence threshold 필터링
  |     - Non-Maximum Suppression (NMS)
  |
  +-- _nms(boxes, scores, threshold)
        - IoU 기반 중복 제거
```

**NPU Core Mask 상수:**

| Mask | 바이너리 | 사용 코어 | 용도 |
|------|---------|----------|------|
| 1 | `001` | Core 0만 | 단일 모델 경량 추론 |
| 2 | `010` | Core 1만 | 단일 모델 경량 추론 |
| 4 | `100` | Core 2만 | 단일 모델 경량 추론 |
| 3 | `011` | Core 0+1 | 중간 성능 |
| 7 | `111` | Core 0+1+2 (전체) | 최대 성능 (기본값) |

**Mock Mode:**

`rknnlite` 패키지가 설치되지 않은 개발 환경에서는 자동으로 mock mode로 전환되어
빈 inference 결과를 반환한다. 이를 통해 NPU 하드웨어 없이도 전체 파이프라인을
테스트할 수 있다.

### 3.3 ROIManager

**파일:** `app/core/roi_manager.py`
**역할:** ROI 정의 관리, 공간 연산, line crossing 검출, preset 영속화

```
ROIManager
  |
  +-- _presets: dict[str, ROIPreset]         # 전체 preset 저장소
  +-- _active_presets: dict[str, str]        # camera_id -> preset_id
  +-- _presets_dir: Path                     # 디스크 저장 경로
  |
  [Preset CRUD]
  +-- load_presets()           # 디스크에서 JSON 파일 로드
  +-- create_preset(data)      # 새 preset 생성 + 저장
  +-- update_preset(id, ...)   # preset 수정 + 저장
  +-- delete_preset(id)        # preset 삭제 + 파일 삭제
  +-- set_active_preset(camera_id, preset_id)
  +-- get_active_rois(camera_id) -> list[ROIConfig]
  |
  [Spatial Operations]
  +-- filter_detections(detections, rois, frame_size) -> list[dict]
  |     - INCLUDE ROI: 중심점이 ROI 내부인 detection만 통과
  |     - EXCLUDE ROI: 중심점이 ROI 내부인 detection 제거
  |
  +-- check_line_crossings(prev_pos, curr_pos, rois, ...) -> list[LineCrossingEvent]
  |     - 두 프레임 간 track 이동 경로와 라인 ROI의 교차 판정
  |     - cross product 기반 방향(in/out) 결정
  |
  +-- check_roi_alerts(detections, rois, ...) -> list[ROIAlertEvent]
  |     - ALERT 타입 ROI 내부 객체 존재 여부 확인
  |
  +-- draw_rois(frame, rois, alpha) -> np.ndarray
        - ROI 오버레이 렌더링 (반투명 다각형, 라인, 레이블)
```

**ROI 좌표 체계:**

모든 ROI 좌표는 정규화된 값(0.0~1.0)으로 저장된다. 실제 프레임에 적용할 때
`_denormalize_points()`를 통해 pixel 좌표로 변환된다. 이 방식은 해상도 독립적인
ROI 정의를 가능하게 한다.

```
정규화 좌표: Point(x=0.5, y=0.3)
프레임 크기: 1920x1080

픽셀 좌표: (int(0.5 * 1920), int(0.3 * 1080)) = (960, 324)
```

**Line Crossing 알고리즘:**

```
두 선분 (P1,P2)와 (P3,P4)의 교차 판정:
  CCW(A,B,C) = (C.y - A.y)(B.x - A.x) > (B.y - A.y)(C.x - A.x)

  교차 = CCW(P1,P3,P4) != CCW(P2,P3,P4)
       AND CCW(P1,P2,P3) != CCW(P1,P2,P4)

방향 결정:
  dx = P4.x - P3.x
  dy = P4.y - P3.y
  cross = dx * (P2.y - P3.y) - dy * (P2.x - P3.x)
  direction = "in" if cross > 0 else "out"
```

**Preset 영속화:**

각 preset은 `data/roi_presets/{preset_id}.json`에 개별 파일로 저장된다.
`aiofiles`를 사용하여 비동기 파일 I/O를 수행하고, 서버 시작 시 `load_presets()`로
모든 preset을 메모리에 로드한다.

### 3.4 StreamPublisher

**파일:** `app/core/stream_publisher.py`
**역할:** MJPEG/WebSocket 기반 실시간 프레임 배포, 클라이언트 lifecycle 관리

```
StreamPublisher
  |
  +-- _ws_clients: dict[str, set[WebSocket]]   # camera_id -> WebSocket 클라이언트
  +-- _mjpeg_queues: dict[str, set[Queue]]     # camera_id -> MJPEG 큐
  +-- _last_publish_time: dict[str, float]      # Rate limiting
  |
  [Client Management]
  +-- register_websocket(camera_id, ws)
  +-- unregister_websocket(camera_id, ws)
  +-- create_mjpeg_queue(camera_id) -> Queue    # maxsize=2 (최신 프레임 유지)
  +-- remove_mjpeg_queue(camera_id, queue)
  +-- get_client_count(camera_id) -> int
  |
  [Frame Publishing]
  +-- publish_frame(camera_id, frame, inference_result)
  |     1. Rate limiting (min_interval = 1/max_fps)
  |     2. 클라이언트 존재 확인 (없으면 encoding 스킵)
  |     3. Overlay 렌더링 (detection boxes, pose skeleton, 성능 정보)
  |     4. JPEG encoding (cv2.imencode)
  |     5. 동시 전송: WebSocket + MJPEG (asyncio.gather)
  |
  +-- publish_preview(camera_id, frame) -> bytes
        - 축소 썸네일 생성 (scale factor 적용)
```

**MJPEG vs WebSocket 비교:**

```
+------------------+---------------------------+---------------------------+
|                  |        MJPEG              |       WebSocket           |
+------------------+---------------------------+---------------------------+
| 프로토콜         | HTTP multipart            | WS (full-duplex)          |
| Content-Type     | multipart/x-mixed-replace | binary + JSON             |
| 데이터 형식      | 순수 JPEG 바이트          | base64 JPEG + 메타데이터  |
| 클라이언트 구현  | <img> 태그만으로 가능     | JavaScript WebSocket API  |
| 양방향 통신      | X (서버 -> 클라이언트만)  | O (ping/pong, 설정 변경)  |
| Inference 메타   | X (이미지에 overlay만)    | O (JSON으로 전송)         |
| 호환성           | 모든 브라우저/디바이스     | 모던 브라우저만            |
| 오버헤드         | 낮음                      | base64 인코딩 (~33% 증가) |
| 클라이언트 제한  | Queue 기반 (무제한)       | max_ws_clients (기본 10)  |
+------------------+---------------------------+---------------------------+
```

**Dead Client Cleanup:**

WebSocket과 MJPEG 모두 전송 실패 시 자동으로 dead client를 감지하고 제거한다.
WebSocket은 `send_json()` 예외로, MJPEG는 Queue 예외로 감지한다.

### 3.5 FrameProcessor

**파일:** `app/core/frame_processor.py`
**역할:** 카메라별 inference pipeline 오케스트레이션

```
FrameProcessor
  |
  [Dependencies - 생성자 주입]
  +-- _camera_manager: CameraManager
  +-- _inference_engine: InferenceEngine
  +-- _roi_manager: ROIManager
  +-- _stream_publisher: StreamPublisher
  +-- _event_handler: EventHandler
  |
  [Pipeline Management]
  +-- _pipelines: dict[str, PipelineConfig]    # camera_id -> config
  +-- _tasks: dict[str, asyncio.Task]          # camera_id -> 실행 task
  +-- _running: dict[str, bool]                # camera_id -> 실행 상태
  +-- _prev_positions: dict[str, dict]         # line crossing 추적용
  |
  +-- start_pipeline(config)
  +-- stop_pipeline(camera_id)
  +-- stop_all()
  +-- update_config(camera_id, inference_config)  # 런타임 설정 변경
  |
  [Pipeline Loop - _pipeline_loop(camera_id)]
  +-- 1. get_frame()        카메라에서 최신 프레임 획득
  +-- 2. Frame skip 체크    (skip_frames > 0이면 N프레임마다 inference)
  +-- 3. infer()            NPU inference 실행
  +-- 4. FPS 계산           1초 윈도우 내 프레임 수
  +-- 5. _apply_roi_filter  ROI 기반 detection 필터링
  +-- 6. _check_events      ROI alert + line crossing 검사
  +-- 7. publish_frame      스트림 클라이언트에 배포
```

**PipelineConfig:**

```python
PipelineConfig(
    camera_id="cam01",           # 대상 카메라
    model_id="yolov8n",          # 사용 모델
    inference_config=InferenceConfig(
        confidence_threshold=0.5,
        nms_threshold=0.45,
        class_filter=["person", "car"],
        max_detections=100,
    ),
    enable_roi_filter=True,      # ROI 필터링 활성화
    enable_events=True,          # 이벤트 검출 활성화
    skip_frames=0,               # 0=모든 프레임, 1=매 2번째 프레임
)
```

### 3.6 EventHandler

**파일:** `app/core/event_handler.py`
**역할:** 중앙 이벤트 버스, 이벤트 히스토리, 스냅샷 캡처

```
EventHandler
  |
  +-- _listeners: list[Callable]               # 이벤트 리스너 목록
  +-- _history: deque[EventRecord]             # maxlen=1000 (circular buffer)
  +-- _snapshots_dir: Path                     # 스냅샷 저장 경로
  +-- _lock: asyncio.Lock
  |
  +-- register_listener(callback)    # 리스너 등록
  +-- remove_listener(callback)      # 리스너 해제
  +-- emit(event_type, camera_id, data, frame)  # 이벤트 발행
  +-- get_history(camera_id, event_type, limit)  # 히스토리 조회
  +-- clear_history() -> int
  +-- acknowledge_event(event_id) -> bool
```

**Event Bus 패턴:**

```
emit("roi_alert", "cam01", {...}, frame)
  |
  +--1-> EventRecord 생성 (id, timestamp, data)
  |
  +--2-> 스냅샷 저장 (frame이 제공된 경우)
  |        data/snapshots/cam01_roi_alert_20260129_143022_123456.jpg
  |
  +--3-> history에 추가 (deque, 최대 1000건 유지)
  |
  +--4-> 등록된 리스너에 통지 (fire-and-forget)
           +-> NotificationService.handle_event()
                 +-> MQTT publish (비동기)
                 +-> Webhook POST (비동기)
```

**이벤트 타입:**

| Event Type | 발생 조건 | Data 내용 |
|-----------|----------|----------|
| `roi_alert` | ALERT 타입 ROI 내 객체 감지 | roi_id, object_count, class_names |
| `line_crossing` | 라인 ROI 교차 감지 | track_id, direction(in/out), roi_name |
| `detection` | 일반 객체 감지 | 커스텀 트리거 시 사용 가능 |

**리스너 비동기 처리:**

리스너가 coroutine을 반환하면 `asyncio.create_task()`로 비동기 실행하여
이벤트 발행 경로를 블로킹하지 않는다. 리스너 에러는 개별적으로 로깅되며
다른 리스너에 영향을 주지 않는다.

### 3.7 ModelRegistry

**파일:** `app/core/model_registry.py`
**역할:** RKNN 모델 카탈로그 관리, 자동 검색, 메타데이터 관리, 파일 업로드

```
ModelRegistry
  |
  +-- _models: dict[str, ModelInfo]            # 등록된 모델 카탈로그
  +-- _states: dict[str, ModelState]           # 모델별 런타임 상태
  +-- _models_dir: Path                        # 모델 디렉토리 루트
  +-- _metadata_path: Path                     # model_metadata.json 경로
  |
  [Discovery]
  +-- scan_models() -> int
  |     1. 저장된 메타데이터 로드 (model_metadata.json)
  |     2. 서브디렉토리 순회 (detection/, pose/ 등)
  |     3. *.rknn 파일 발견 시 모델 타입 추론
  |     4. ModelInfo 생성 + 등록
  |     5. 루트 레벨 *.rknn도 스캔
  |     6. 메타데이터 저장
  |
  [Model Type Inference]
  +-- _infer_model_type(path, subdir_name)
  |     우선순위:
  |     1. 서브디렉토리 이름 (detection/ -> DETECTION)
  |     2. 파일명 패턴 매칭 (yolov8 -> DETECTION, pose -> POSE)
  |     3. 기본값: DETECTION
  |
  [Upload]
  +-- upload_model(content, filename, model_type, ...)
  |     1. .rknn 확장자 검증
  |     2. 타입별 서브디렉토리에 저장
  |     3. 파일명 충돌 시 자동 번호 부여 (model_1.rknn)
  |     4. register_model() 호출
  |
  [Persistence]
  +-- _save_metadata()   # models/model_metadata.json에 전체 카탈로그 저장
  +-- _load_metadata()   # 저장된 메타데이터 복원
```

**모델 디렉토리 구조:**

```
models/
  +-- detection/
  |     +-- yolov8n.rknn
  |     +-- yolov8s.rknn
  +-- segmentation/
  |     +-- yolov8n-seg.rknn
  +-- pose/
  |     +-- yolov8n-pose.rknn
  +-- classification/
  |     +-- mobilenetv2.rknn
  +-- face/
  |     +-- retinaface.rknn
  +-- ocr/
  |     +-- ppocr_det.rknn
  +-- model_metadata.json               # 자동 생성되는 메타데이터 캐시
```

**Model ID 생성:**

파일 경로의 stem을 정규화하여 안정적인 ID를 생성한다:
`yolov8n-pose.rknn` -> `yolov8n_pose`

---

## 4. 데이터 흐름

### 4.1 Real-time Inference Pipeline

```
+-----------+     +-----------+     +-----------+     +----------+
|  Camera   |     | Preprocess|     | NPU       |     | Post-    |
|  Capture  +---->+           +---->+ Inference  +---->+ process  |
| (OpenCV)  |     | (resize,  |     | (RKNN     |     | (NMS,    |
| blocking  |     |  BGR2RGB) |     |  Toolkit)  |     |  scale)  |
+-----------+     +-----------+     +-----------+     +----+-----+
  run_in_            sync              run_in_              |
  executor                             executor             v
                                                    +------+------+
                                                    | ROI Filter  |
                                                    | (include/   |
                                                    |  exclude)   |
                                                    +------+------+
                                                           |
                                         +-----------------+--------+
                                         |                          |
                                         v                          v
                                  +------+------+           +------+------+
                                  | Event Check |           | Stream      |
                                  | (alert,     |           | Publisher   |
                                  |  crossing)  |           | (overlay +  |
                                  +------+------+           |  encode +   |
                                         |                  |  broadcast) |
                                         v                  +------+------+
                                  +------+------+                  |
                                  | EventHandler|           +------+------+
                                  | (history +  |           |   Clients   |
                                  |  snapshot)  |           | (WS/MJPEG)  |
                                  +------+------+           +-------------+
                                         |
                                         v
                                  +------+------+
                                  | Notification|
                                  | (MQTT/      |
                                  |  Webhook)   |
                                  +-------------+
```

### 4.2 Sequence Diagram: Inference Pipeline 단일 프레임 처리

```
FrameProcessor     CameraManager    InferenceEngine     ROIManager    StreamPublisher    EventHandler
     |                   |                |                  |                |                |
     |  get_frame()      |                |                  |                |                |
     +------------------>+                |                  |                |                |
     |  frame (ndarray)  |                |                  |                |                |
     |<------------------+                |                  |                |                |
     |                   |                |                  |                |                |
     |  infer(frame, config, camera_id)   |                  |                |                |
     +------------------------------------+                  |                |                |
     |          [ThreadPool]              |                  |                |                |
     |          preprocess(frame)         |                  |                |                |
     |          rknn.inference(input)     |                  |                |                |
     |          postprocess(outputs)      |                  |                |                |
     |  InferenceResult                   |                  |                |                |
     |<-----------------------------------+                  |                |                |
     |                   |                |                  |                |                |
     |  get_active_rois(camera_id)        |                  |                |                |
     +----------------------------------------------------->+                |                |
     |  rois: list[ROIConfig]             |                  |                |                |
     |<-----------------------------------------------------+                |                |
     |                   |                |                  |                |                |
     |  filter_detections(dets, rois, size)                  |                |                |
     +----------------------------------------------------->+                |                |
     |  filtered_dets                     |                  |                |                |
     |<-----------------------------------------------------+                |                |
     |                   |                |                  |                |                |
     |  check_roi_alerts(dets, rois, ...) |                  |                |                |
     +----------------------------------------------------->+                |                |
     |  alerts: list[ROIAlertEvent]       |                  |                |                |
     |<-----------------------------------------------------+                |                |
     |                   |                |                  |                |                |
     |  [for each alert] emit("roi_alert", cam_id, data, frame)              |                |
     +------------------------------------------------------------------------+--------------->+
     |                   |                |                  |                |                |
     |  publish_frame(camera_id, frame, result)              |                |                |
     +----------------------------------------------------------------------->+                |
     |                   |                |                  |  [rate limit]  |                |
     |                   |                |                  |  [encode JPEG] |                |
     |                   |                |                  |  [WS broadcast]|                |
     |                   |                |                  |  [MJPEG queue] |                |
     |                   |                |                  |                |                |
```

### 4.3 Sequence Diagram: 모델 로드 및 Inference 시작

```
Client         API(inference.py)    InferenceEngine    ModelRegistry    FrameProcessor
  |                   |                   |                  |                |
  | POST /api/inference/start             |                  |                |
  | {camera_id, model_id, config}         |                  |                |
  +------------------>+                   |                  |                |
  |                   |                   |                  |                |
  |                   | get_model(model_id)                  |                |
  |                   +------------------------------------>+                |
  |                   | ModelInfo                            |                |
  |                   |<------------------------------------+                |
  |                   |                   |                  |                |
  |                   | load_model(model_info)               |                |
  |                   +------------------>+                  |                |
  |                   |   [ThreadPool]    |                  |                |
  |                   |   rknn.load_rknn()|                  |                |
  |                   |   rknn.init_runtime(core_mask=7)     |                |
  |                   |   OK              |                  |                |
  |                   |<------------------+                  |                |
  |                   |                   |                  |                |
  |                   | set_active_model(model_id)           |                |
  |                   +------------------>+                  |                |
  |                   |                   |                  |                |
  |                   | start_pipeline(PipelineConfig)       |                |
  |                   +---------------------------------------------------->+
  |                   |                   |                  |    asyncio.   |
  |                   |                   |                  |    create_    |
  |                   |                   |                  |    task()     |
  |  {"status":"ok"}  |                   |                  |                |
  |<------------------+                   |                  |                |
```

### 4.4 Sequence Diagram: WebSocket 스트림 연결

```
Browser              API(stream.py)    StreamPublisher    FrameProcessor
  |                       |                  |                  |
  | WS /api/stream/{id}/ws|                  |                  |
  +---------------------->+                  |                  |
  | accept()              |                  |                  |
  |<----------------------+                  |                  |
  |                       |                  |                  |
  |                       | register_websocket(cam_id, ws)     |
  |                       +----------------->+                  |
  |                       |                  |                  |
  |   [Pipeline loop publishes frames]       |                  |
  |                       |                  |<----- publish_frame(cam_id, frame, result)
  |                       |                  |                  |
  |                       |    encode JPEG   |                  |
  |                       |    build JSON    |                  |
  |   {type:"frame",      |    message       |                  |
  |    image: base64,     |<----- send_json()|                  |
  |    inference: {...}}  |                  |                  |
  |<----------------------+                  |                  |
  |                       |                  |                  |
  |   {type:"ping"}       |                  |                  |
  +---------------------->+                  |                  |
  |   {type:"pong"}       |                  |                  |
  |<----------------------+                  |                  |
  |                       |                  |                  |
  | [disconnect]          |                  |                  |
  +-----X                 | unregister_websocket()             |
                          +----------------->+                  |
```

---

## 5. 비동기 처리 전략

### 5.1 asyncio Event Loop 구조

본 시스템은 단일 프로세스, 단일 이벤트 루프 모델을 사용한다.
`uvicorn --workers 1`로 실행되며, 이는 RKNN NPU 런타임이 multi-process를
지원하지 않기 때문이다.

```
+========================================+
|         Main asyncio Event Loop        |
|                                        |
|  +----------+  +----------+            |
|  | HTTP     |  | WebSocket|            |
|  | Request  |  | Handler  |            |
|  | Handlers |  |          |            |
|  +----------+  +----------+            |
|                                        |
|  +----------+  +----------+  +------+  |
|  | Camera   |  | Pipeline |  |System|  |
|  | Capture  |  | Loop     |  |Monitor| |
|  | Tasks    |  | Tasks    |  |Task  |  |
|  | (per cam)|  | (per cam)|  |      |  |
|  +----------+  +----------+  +------+  |
|                                        |
+========================================+
         |              |
         v              v
+========================================+
|       Default ThreadPoolExecutor       |
|  (for blocking I/O operations)         |
|                                        |
|  +----------------------------------+  |
|  | cv2.VideoCapture.read()          |  |
|  | rknn.inference()                 |  |
|  | rknn.load_rknn() / init_runtime()|  |
|  | cv2.imwrite() (snapshot)         |  |
|  | SystemMonitor._read_all_metrics()|  |
|  +----------------------------------+  |
+========================================+
```

### 5.2 Blocking I/O 처리: ThreadPoolExecutor

다음 연산들은 CPU-bound 또는 blocking I/O이므로 반드시 ThreadPoolExecutor에서
실행해야 한다. `asyncio.get_event_loop().run_in_executor(None, func, *args)`를
사용하며, `None`은 기본 ThreadPoolExecutor를 의미한다.

| 모듈 | Blocking 연산 | 소요 시간 |
|------|-------------|----------|
| CameraStream | `cv2.VideoCapture.read()` | 1~33ms (FPS 의존) |
| CameraStream | `cv2.VideoCapture()` constructor (연결) | 100ms~5s (네트워크) |
| RKNNModelWrapper | `rknn.load_rknn()` + `init_runtime()` | 500ms~3s |
| RKNNModelWrapper | `rknn.inference()` | 5~50ms (모델 크기) |
| RKNNModelWrapper | `_preprocess()` (cv2.resize, cvtColor) | 1~5ms |
| EventHandler | `cv2.imwrite()` (스냅샷 저장) | 5~20ms |
| SystemMonitor | `/proc`, `/sys` 파일 읽기 | 1~10ms |

### 5.3 asyncio.Task 구조

시스템 실행 중 활성화되는 asyncio Task 목록:

```
[장기 실행 Task]
  +-- CameraStream._capture_loop()      x N개 (카메라 수)
  +-- FrameProcessor._pipeline_loop()   x M개 (활성 파이프라인 수)
  +-- SystemMonitor._monitor_loop()     x 1 (2초 주기)

[단발성 Task]
  +-- EventHandler 리스너 실행          asyncio.create_task() (fire-and-forget)
  +-- NotificationService 전송          asyncio.gather() (MQTT + Webhook 병렬)

[Request-scoped]
  +-- HTTP request handler              FastAPI에서 자동 관리
  +-- WebSocket handler                 연결 수명 동안 유지
  +-- MJPEG StreamingResponse           클라이언트 연결 수명 동안 유지
```

### 5.4 Frame Dropping 전략

inference 속도가 카메라 FPS보다 느린 경우를 처리하는 전략:

```
[전략 1: Latest Frame Only (CameraManager)]
  CameraStream._last_frame은 항상 최신 프레임으로 덮어쓰기된다.
  FrameProcessor는 get_frame()으로 최신 프레임만 가져오므로,
  inference 중 도착한 중간 프레임은 자연스럽게 드롭된다.

  Camera 30 FPS, Inference 10 FPS인 경우:
  Frame: 1  2  3  4  5  6  7  8  9  10  11  12 ...
  _last_frame 덮어쓰기:    항상 최신
  Inference 대상:  1        4        7         10  ...
  자동 드롭:          2,3     5,6     8,9         ...

[전략 2: Explicit Frame Skip (PipelineConfig)]
  skip_frames=N 설정 시, 매 (N+1)번째 프레임만 inference 실행.
  스킵된 프레임은 inference 없이 그대로 스트림에 publish된다.

  skip_frames=2인 경우:
  Frame:  1    2    3    4    5    6 ...
  Infer:  YES  no   no   YES  no   no ...
  Stream: full raw  raw  full raw  raw ...

[전략 3: MJPEG Queue Drop (StreamPublisher)]
  MJPEG queue (maxsize=2)가 가득 차면 가장 오래된 프레임을 드롭하고
  새 프레임을 삽입한다. 느린 클라이언트가 전체 파이프라인을 블로킹하지 않는다.

  if queue.full():
      queue.get_nowait()   # 오래된 프레임 드롭
  queue.put_nowait(new_frame)

[전략 4: Rate Limiting (StreamPublisher)]
  publish_frame()은 min_interval = 1/max_fps 보다 짧은 간격의
  호출을 무시한다. 이는 불필요한 JPEG encoding을 방지한다.
```

---

## 6. 보안 아키텍처

### 6.1 Input Validation (Pydantic)

모든 API 입력은 Pydantic v2 모델로 검증된다. 잘못된 입력은 자동으로 422
Unprocessable Entity 응답을 생성한다.

```
주요 검증 규칙:

[CameraCreate]
  name:    min_length=1, max_length=100
  url:     min_length=1, strip(), 빈 문자열 거부
  reconnect_interval: ge=1, le=300

[InferenceConfig]
  confidence_threshold: ge=0.0, le=1.0
  nms_threshold:        ge=0.0, le=1.0
  max_detections:       ge=1, le=1000

[ROICreate]
  name:      min_length=1, max_length=100
  points:    min_length=2 (좌표 최소 개수)
  Point.x:   ge=0.0, le=1.0  (정규화 좌표)
  Point.y:   ge=0.0, le=1.0
  roi_type별 추가 검증:
    LINE      -> 정확히 2개 점
    RECTANGLE -> 정확히 2개 점 (좌상, 우하)
    POLYGON   -> 최소 3개 점

[InferenceSettings]
  default_core_mask: {1, 2, 4, 3, 5, 6, 7} 중 하나만 허용
  (custom validator로 비트마스크 유효성 검증)
```

### 6.2 File Upload Security

```
모델 업로드 보안 계층:

1. 확장자 검증
   - SecuritySettings.allowed_model_extensions = [".rknn"]
   - 파일명이 .rknn으로 끝나지 않으면 400 Bad Request

2. 파일 크기 제한
   - SecuritySettings.max_upload_size_mb = 500 (기본값)
   - 초과 시 413 Payload Too Large

3. 파일 저장 경로 격리
   - 모델 타입별 서브디렉토리에 저장 (models/{type}/)
   - 파일명 충돌 시 자동 번호 부여 (덮어쓰기 방지)

4. 모델 검증 (RKNNService.validate_model)
   - 파일 존재 확인
   - 확장자 재확인
   - 최소 파일 크기 검증 (1KB 미만 거부)
   - RKNN 파일 헤더 검증 시도
```

### 6.3 CORS Configuration

```python
# app/main.py
CORSMiddleware(
    allow_origins=settings.security.cors_origins,   # 기본: ["*"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

프로덕션 배포 시 `SECURITY__CORS_ORIGINS` 환경 변수로 허용 도메인을 제한해야 한다.

### 6.4 Non-root Container Execution

```dockerfile
# docker/Dockerfile
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser
# ...
USER appuser
```

컨테이너 내부에서 `appuser`라는 non-root 사용자로 애플리케이션을 실행한다.
단, NPU 디바이스 접근을 위해 docker-compose에서 `privileged: true`가 필요하다.

### 6.5 API Documentation 접근 제어

```python
docs_url="/api/docs" if settings.debug else None,
redoc_url="/api/redoc" if settings.debug else None,
```

`APP_DEBUG=false`인 프로덕션 환경에서는 Swagger UI와 ReDoc 문서가 비활성화된다.

---

## 7. 성능 최적화

### 7.1 NPU Core Allocation 전략

RK3588은 3개의 독립적인 NPU 코어를 보유하며, `core_mask` 비트마스크로
모델별 코어 할당을 제어할 수 있다.

```
[단일 모델 최대 성능]
  core_mask = 7 (Core 0+1+2, 모든 코어)
  -> RKNN이 자동으로 모델을 3코어에 분산
  -> 최대 throughput, 단일 스트림 최적

[다중 모델 병렬 실행]
  Model A: core_mask = 1 (Core 0)
  Model B: core_mask = 2 (Core 1)
  Model C: core_mask = 4 (Core 2)
  -> 각 모델이 전용 코어 사용
  -> 모델 간 간섭 없음
  -> 개별 성능은 1/3, 총 throughput 동등

[2모델 분할]
  Model A: core_mask = 3 (Core 0+1)
  Model B: core_mask = 4 (Core 2)
  -> Model A에 2/3 성능, Model B에 1/3 성능 할당

InferenceSettings.default_core_mask = 7 (기본값: 전체 코어)
max_loaded_models = 3 (동시 로드 가능 최대 모델 수)
```

### 7.2 Zero-copy 및 메모리 효율

```
[프레임 전달 경로에서의 메모리 관리]

1. CameraStream._last_frame
   - numpy ndarray 참조 교체 (deepcopy 아님)
   - 이전 프레임은 참조 카운트가 0이 되면 GC에 의해 자동 해제
   - frame_buffer_size=1 이므로 OpenCV 내부 버퍼도 최소화

2. FrameProcessor -> InferenceEngine
   - frame은 참조로 전달 (복사 없음)
   - _preprocess에서 resize 시 새 ndarray 생성 (입력 크기 변환 필수)
   - 원본 프레임은 overlay 렌더링까지 유지

3. StreamPublisher
   - _draw_overlay에서 frame.copy() 수행 (원본 보존)
   - cv2.imencode()가 JPEG 바이트 생성 (별도 메모리)
   - JPEG 바이트는 모든 클라이언트가 동일 참조 공유
   - 클라이언트 수 증가 시에도 JPEG encoding은 1회만 수행

4. MJPEG Queue
   - maxsize=2로 메모리 사용 상한 제한
   - 오래된 프레임 자동 드롭 (메모리 누수 방지)
```

### 7.3 MJPEG vs WebSocket Trade-offs

```
                     MJPEG                  WebSocket
+------------------+---------------------+----------------------+
| JPEG Encoding    | 1회 (공유)           | 1회 (공유)            |
| 추가 Encoding    | 없음                 | base64 (~33% 증가)   |
| 대역폭 (720p)   | ~2-5 Mbps            | ~2.7-6.7 Mbps        |
| CPU 부하         | 낮음                 | base64 + JSON 직렬화 |
| 추가 데이터      | 없음 (overlay만)     | inference 메타데이터  |
| 지연시간         | 낮음 (직접 전달)     | 약간 높음 (JSON 파싱) |
| 클라이언트 관리  | Queue 기반           | 연결 기반             |
| 권장 용도        | 단순 모니터링        | 인터랙티브 분석       |
+------------------+---------------------+----------------------+
```

### 7.4 Frame Skip 동적 제어

```
inference_time이 지속적으로 camera_interval보다 클 때:

  camera_fps = 30  ->  camera_interval = 33ms
  inference_time = 50ms (초과)

  자동 드롭 (Latest Frame Only):
    실효 inference FPS = 1000 / (50 + 1) ~= 19.6 FPS
    드롭 비율: 약 35%

  명시적 skip_frames=1 설정 시:
    매 2프레임마다 inference -> 실효 15 FPS
    나머지 프레임은 overlay 없이 스트림 전달
    -> 스트림 FPS는 30으로 유지되면서 inference 부하 절반

enable_frame_skip (InferenceSettings):
  True로 설정 시, inference가 느릴 때 자동으로 프레임을 건너뛰어
  파이프라인 지연 누적을 방지한다.
```

### 7.5 Rate Limiting (StreamPublisher)

```python
min_interval = 1.0 / settings.mjpeg_max_fps    # 예: 1/30 = 33ms
now = time.monotonic()
if now - last_publish_time < min_interval:
    return   # JPEG encoding 및 전송 스킵
```

클라이언트가 없는 카메라 스트림에 대해서는 `_has_clients()` 체크로
JPEG encoding 자체를 스킵하여 CPU 사용을 절감한다.

### 7.6 FPS 계산: Sliding Window

```python
class FPSCounter:
    def __init__(self, window_size=30):
        self._timestamps = []   # 최근 N개 타임스탬프

    def update(self) -> float:
        now = time.monotonic()
        self._timestamps.append(now)
        if len(self._timestamps) > window_size:
            self._timestamps.pop(0)
        elapsed = self._timestamps[-1] - self._timestamps[0]
        return (len(self._timestamps) - 1) / elapsed
```

최근 30프레임의 타임스탬프를 기반으로 FPS를 계산한다.
단순 카운터 방식보다 순간적인 FPS 변동을 더 정확하게 반영한다.

---

## 8. 확장 가능성

### 8.1 새로운 모델 타입 추가

새로운 AI 모델 타입 (예: Depth Estimation)을 추가하는 절차:

```
1. ModelType Enum 확장 (app/models/inference.py)

   class ModelType(str, Enum):
       ...
       DEPTH = "depth"

2. Result 모델 추가 (app/models/inference.py)

   class DepthResult(BaseModel):
       depth_map: Optional[str] = None   # base64 encoded
       min_depth: float = 0.0
       max_depth: float = 0.0

   class InferenceResult(BaseModel):
       ...
       depth: Optional[DepthResult] = None

3. Postprocessor 구현 (app/core/inference_engine.py)

   class RKNNModelWrapper:
       def _postprocess_depth(self, outputs, original_shape, config):
           # 깊이 맵 처리 로직
           ...

       def _postprocess(self, ...):
           handlers = {
               ...
               ModelType.DEPTH: self._postprocess_depth,
           }

4. Model Type 힌트 등록 (app/core/model_registry.py)

   MODEL_TYPE_HINTS["depth"] = ModelType.DEPTH
   MODEL_TYPE_HINTS["midas"] = ModelType.DEPTH

   SUBDIR_TYPE_MAP["depth"] = ModelType.DEPTH

5. Overlay 렌더링 (app/core/stream_publisher.py)

   def _draw_overlay(self, frame, result):
       ...
       if result.depth:
           # 깊이 맵 시각화 오버레이
           ...

6. 모델 디렉토리 생성

   models/depth/
     +-- midas_v21_small.rknn
```

### 8.2 새로운 Notification Backend 추가

새로운 알림 채널 (예: Telegram Bot)을 추가하는 절차:

```
1. 설정 추가 (app/config.py)

   class NotificationSettings(BaseSettings):
       ...
       telegram_enabled: bool = False
       telegram_bot_token: Optional[str] = None
       telegram_chat_id: Optional[str] = None

2. NotificationService에 backend 추가 (app/services/notification.py)

   class NotificationService:

       async def handle_event(self, event):
           tasks = []
           ...
           if self._settings.telegram_enabled:
               tasks.append(self._send_telegram(event))
           await asyncio.gather(*tasks, return_exceptions=True)

       async def _send_telegram(self, event: EventRecord):
           import httpx
           url = f"https://api.telegram.org/bot{token}/sendMessage"
           payload = {
               "chat_id": self._settings.telegram_chat_id,
               "text": f"[{event.event_type}] Camera: {event.camera_id}\n"
                       f"Data: {event.data}",
           }
           async with httpx.AsyncClient() as client:
               await client.post(url, json=payload)

3. 스냅샷 첨부 (선택)

   async def _send_telegram_photo(self, event, snapshot_path):
       url = f"https://api.telegram.org/bot{token}/sendPhoto"
       async with httpx.AsyncClient() as client:
           with open(snapshot_path, "rb") as f:
               await client.post(url, data={"chat_id": chat_id},
                                 files={"photo": f})
```

### 8.3 Custom Postprocessor 패턴

특정 모델의 output format이 기본 YOLO parser와 다른 경우:

```
1. RKNNModelWrapper 서브클래스 생성

   class CustomModelWrapper(RKNNModelWrapper):
       def _postprocess_detection(self, outputs, original_shape, config):
           # 모델 고유의 output parsing 로직
           result = InferenceResult(...)
           ...
           return result

       def _preprocess(self, frame):
           # 모델 고유 전처리 (예: letterbox padding)
           return letterbox(frame, target_size=self.info.input_size)

2. InferenceEngine에서 wrapper 선택 로직 추가

   async def load_model(self, model_info, ...):
       if model_info.name.startswith("custom_"):
           wrapper = CustomModelWrapper(model_info)
       else:
           wrapper = RKNNModelWrapper(model_info)
       ...

또는 ModelInfo에 postprocessor 필드를 추가하여 동적 디스패치:

   class ModelInfo(BaseModel):
       ...
       postprocessor: str = "default"  # "default", "yolov5", "yolov8", "custom"
```

### 8.4 새로운 카메라 소스 추가

새로운 카메라 타입 (예: HTTP JPEG 스트림)을 추가하는 절차:

```
1. CameraType Enum 확장 (app/models/camera.py)

   class CameraType(str, Enum):
       ...
       HTTP_JPEG = "http_jpeg"

2. Backend 매핑 추가 (app/core/camera_manager.py)

   class CameraStream:
       def _resolve_source(self):
           ...
           if self.config.camera_type == CameraType.HTTP_JPEG:
               return self.config.url

       def _get_backend(self):
           ...
           if self.config.camera_type == CameraType.HTTP_JPEG:
               return cv2.CAP_FFMPEG
```

### 8.5 디렉토리 구조 요약

```
Orange-Pi-5-NPU-TEST-BED/
  +-- app/
  |     +-- __init__.py
  |     +-- main.py                    # FastAPI app factory + lifespan
  |     +-- config.py                  # Pydantic Settings (환경 변수)
  |     +-- dependencies.py            # DI providers
  |     +-- api/                       # REST API routers
  |     |     +-- cameras.py
  |     |     +-- models.py
  |     |     +-- inference.py
  |     |     +-- roi.py
  |     |     +-- stream.py
  |     |     +-- system.py
  |     +-- core/                      # Business logic
  |     |     +-- camera_manager.py
  |     |     +-- inference_engine.py
  |     |     +-- roi_manager.py
  |     |     +-- stream_publisher.py
  |     |     +-- frame_processor.py
  |     |     +-- event_handler.py
  |     |     +-- model_registry.py
  |     +-- services/                  # External integrations
  |     |     +-- rknn_service.py
  |     |     +-- opencv_service.py
  |     |     +-- notification.py
  |     |     +-- system_monitor.py
  |     +-- models/                    # Pydantic data models
  |     |     +-- camera.py
  |     |     +-- inference.py
  |     |     +-- roi.py
  |     |     +-- system.py
  |     +-- templates/                 # Jinja2 + HTMX templates
  |     |     +-- base.html
  |     |     +-- index.html
  |     |     +-- pages/
  |     |     +-- components/
  |     +-- static/                    # CSS, JS, images
  |           +-- css/app.css
  |           +-- js/
  +-- data/                            # Runtime data (persistent)
  |     +-- config.json
  |     +-- roi_presets/
  |     +-- snapshots/
  |     +-- logs/
  +-- models/                          # RKNN model files
  |     +-- detection/
  |     +-- segmentation/
  |     +-- pose/
  |     +-- classification/
  |     +-- face/
  |     +-- ocr/
  +-- docker/
  |     +-- Dockerfile
  |     +-- docker-compose.yml
  +-- tests/
  |     +-- conftest.py
  |     +-- test_api.py
  |     +-- test_camera.py
  |     +-- test_inference.py
  |     +-- test_roi.py
  +-- scripts/
  |     +-- benchmark.py
  |     +-- convert_model.py
  |     +-- install_deps.sh
  +-- docs/
  |     +-- architecture/
  |           +-- ARCHITECTURE.md       # 본 문서
  +-- requirements.txt
  +-- tailwind.config.js
  +-- pytest.ini
  +-- .env.example
  +-- .gitignore
```

---

## 부록: 기술 스택 요약

| 범주 | 기술 | 버전 | 용도 |
|------|------|------|------|
| **Web Framework** | FastAPI | >= 0.109.0 | 비동기 REST API + WebSocket |
| **ASGI Server** | Uvicorn | >= 0.27.0 | HTTP/WS 서버 |
| **Template Engine** | Jinja2 | >= 3.1.3 | 서버 사이드 HTML 렌더링 |
| **Data Validation** | Pydantic v2 | >= 2.6.0 | 입출력 스키마 + 설정 관리 |
| **Computer Vision** | OpenCV (headless) | >= 4.9.0 | 프레임 캡처, 전처리, 인코딩 |
| **NPU Runtime** | RKNN Toolkit2 Lite | >= 2.0.0 | RK3588 NPU inference |
| **Numeric** | NumPy | >= 1.26.0 | 텐서 연산, NMS |
| **Async File I/O** | aiofiles | >= 23.2.0 | 비동기 파일 읽기/쓰기 |
| **HTTP Client** | httpx | >= 0.26.0 | Webhook 전송 |
| **MQTT** | paho-mqtt | >= 2.0.0 | IoT 이벤트 발행 (선택) |
| **Frontend** | HTMX | CDN | 서버 렌더링 UI 업데이트 |
| **Frontend** | Alpine.js | CDN | 경량 클라이언트 인터랙션 |
| **Frontend** | Tailwind CSS | 3.x | 유틸리티 기반 스타일링 |
| **Testing** | pytest + pytest-asyncio | >= 8.0 | 비동기 테스트 |
| **Container** | Docker | - | 배포 및 격리 |
| **Hardware** | Orange Pi 5 Plus | RK3588 | ARM64, NPU 3-core, 6 TOPS |
