<p align="center">
  <h1 align="center">Orange Pi 5 NPU 실시간 추론 테스트 플랫폼</h1>
  <p align="center">
    RK3588 NPU(6 TOPS)를 활용한 실시간 AI 추론 테스트 및 검증 플랫폼
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Orange%20Pi%205%20Plus-orange" alt="Platform">
  <img src="https://img.shields.io/badge/SoC-RK3588-blue" alt="SoC">
  <img src="https://img.shields.io/badge/NPU-6%20TOPS-brightgreen" alt="NPU">
  <img src="https://img.shields.io/badge/Python-3.10+-3776ab" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.109+-009688" alt="FastAPI">
  <img src="https://img.shields.io/badge/HTMX-1.9+-3366cc" alt="HTMX">
  <img src="https://img.shields.io/badge/Tailwind%20CSS-3.4+-38bdf8" alt="Tailwind CSS">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License">
</p>

---

## 개요

**NPU Inference Platform**은 Orange Pi 5 Plus(RK3588) 보드의 내장 NPU를 활용하여 다양한 AI 모델을 실시간으로 추론하고, 결과를 웹 브라우저에서 즉시 확인할 수 있는 올인원 테스트 플랫폼입니다.

RKNN 포맷의 모델을 업로드하고 즉시 교체(hot-swap)하며, 다중 카메라 스트림에 대해 ROI 기반 추론을 수행하고, 결과를 MJPEG/WebSocket으로 실시간 시각화합니다. 시스템 리소스(CPU, NPU, 메모리, 온도) 모니터링과 MQTT/Webhook 기반 이벤트 알림까지 지원합니다.

### 주요 특징

- **완전한 웹 UI** -- FastAPI + Jinja2 + HTMX + Tailwind CSS 기반, SPA 없이 반응형 인터페이스 제공
- **무중단 모델 교체** -- 추론 중에도 모델을 동적으로 로드/언로드/전환 가능
- **다중 입력 소스** -- RTSP, USB 카메라, CSI 카메라, 비디오 파일 동시 지원 (최대 8개)
- **ROI 편집기 내장** -- 웹에서 직접 폴리곤/사각형/라인 ROI를 그리고 즉시 적용
- **다양한 모델 타입** -- Detection, Segmentation, Pose, Classification, Face, OCR 모두 지원
- **실시간 시스템 모니터링** -- CPU/NPU/GPU 온도, 메모리, NPU 사용률 대시보드

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Web Browser (HTMX Client)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │Dashboard │ │ Cameras  │ │  Models  │ │ Monitor  │ │ Settings │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ │
└───────┼────────────┼────────────┼────────────┼────────────┼────────┘
        │   HTTP / WebSocket / MJPEG / HTMX partials        │
┌───────┴────────────┴────────────┴────────────┴────────────┴────────┐
│                      FastAPI Application Server                     │
│                                                                     │
│  ┌─────────────────── API Layer (REST + HTMX) ──────────────────┐  │
│  │ /api/cameras  /api/models  /api/inference  /api/roi  /api/   │  │
│  │                          /api/stream    /api/system           │  │
│  └──────┬───────────┬───────────┬───────────┬───────────┬───────┘  │
│         │           │           │           │           │           │
│  ┌──────┴───┐ ┌─────┴────┐ ┌───┴────┐ ┌────┴───┐ ┌────┴────┐     │
│  │ Camera   │ │  Model   │ │Infer.  │ │  ROI   │ │ Stream  │     │
│  │ Manager  │ │ Registry │ │ Engine │ │Manager │ │Publisher│     │
│  └──────┬───┘ └─────┬────┘ └───┬────┘ └────┬───┘ └────┬────┘     │
│         │           │          │            │          │           │
│  ┌──────┴───────────┴──────────┴────────────┴──────────┴───────┐  │
│  │                    Frame Processor (Pipeline)                │  │
│  │  Camera Frame --> Pre-process --> NPU Inference -->          │  │
│  │  Post-process --> ROI Filter --> Visualize --> Publish       │  │
│  └─────────────────────────┬───────────────────────────────────┘  │
│                            │                                       │
│  ┌─────────────────────────┴───────────────────────────────────┐  │
│  │                    Services Layer                            │  │
│  │  ┌──────────┐  ┌───────────┐  ┌─────────────┐              │  │
│  │  │  RKNN    │  │  System   │  │Notification │              │  │
│  │  │ Service  │  │  Monitor  │  │  (MQTT/WH)  │              │  │
│  │  └────┬─────┘  └─────┬─────┘  └──────┬──────┘              │  │
│  └───────┼──────────────┼───────────────┼──────────────────────┘  │
└──────────┼──────────────┼───────────────┼──────────────────────────┘
           │              │               │
    ┌──────┴──────┐  ┌────┴────┐  ┌───────┴───────┐
    │  RK3588 NPU │  │  sysfs  │  │  MQTT Broker  │
    │  (3 cores)  │  │  /proc  │  │  Webhook URL  │
    │  6 TOPS     │  │  /sys   │  │               │
    └─────────────┘  └─────────┘  └───────────────┘
```

---

## 주요 기능

### 카메라 / 스트림 관리

| 기능 | 설명 |
|------|------|
| RTSP 스트림 | IP 카메라 RTSP URL 연결 (TCP/UDP 전송 선택) |
| USB 카메라 | `/dev/video*` 디바이스 직접 연결 |
| CSI 카메라 | MIPI CSI 카메라 인터페이스 지원 |
| 파일 입력 | 비디오 파일(MP4, AVI 등)을 카메라 소스로 사용 |
| 다중 카메라 | 최대 8개 카메라 동시 운용 |
| 자동 재연결 | 연결 끊김 시 설정된 간격으로 자동 재시도 |
| MJPEG 출력 | 브라우저 호환 MJPEG 스트리밍 |
| WebSocket 출력 | 추론 메타데이터 포함 실시간 스트리밍 |
| 스냅샷 | 현재 프레임 JPEG 캡처 및 저장 |

### ROI (Region of Interest)

| 기능 | 설명 |
|------|------|
| 폴리곤 ROI | 자유 형태의 다각형 영역 지정 (3개 이상 꼭짓점) |
| 사각형 ROI | 좌상단/우하단 두 점으로 사각 영역 지정 |
| 라인 크로싱 | 두 점으로 가상 라인 설정, 객체 통과 감지 |
| ROI 액션 | Include(포함), Exclude(제외), Alert(알림) 동작 설정 |
| 프리셋 저장 | 카메라별 ROI 조합을 프리셋으로 저장/불러오기 |
| 웹 편집기 | Canvas 기반 ROI 드로잉 도구 내장 |
| 정규화 좌표 | 0.0~1.0 정규화 좌표로 해상도 독립적 ROI 관리 |

### 모델 관리

| 기능 | 설명 |
|------|------|
| 모델 업로드 | 웹 UI에서 `.rknn` 파일 직접 업로드 (최대 500MB) |
| 디렉토리 스캔 | `models/` 하위 디렉토리 자동 스캔 및 등록 |
| Hot-Swap | 추론 중 모델 동적 교체 (로드/언로드/활성화) |
| 다중 로드 | 최대 3개 모델 동시 NPU 메모리 적재 |
| 모델 변환 | ONNX -> RKNN 변환 스크립트 제공 (INT8/FP16 양자화) |
| 벤치마크 | 모델별 추론 성능 측정 도구 (Latency, Throughput, P95/P99) |
| 메타데이터 | 모델 타입, 입력 크기, 클래스 수, 양자화 정보 자동 관리 |

### 지원 모델 타입

| 모델 타입 | 설명 | 예시 모델 |
|-----------|------|-----------|
| `detection` | 객체 탐지 (Bounding Box) | YOLOv5s, YOLOv8n, YOLOv11n |
| `segmentation` | 인스턴스/시맨틱 세그멘테이션 | YOLOv8n-seg, YOLOv11n-seg |
| `pose` | 관절 추정 (Keypoint) | YOLOv8n-pose, YOLOv11n-pose |
| `classification` | 이미지 분류 | YOLOv8n-cls, ResNet50 |
| `face_detection` | 얼굴 탐지 | RetinaFace, SCRFD |
| `face_recognition` | 얼굴 인식 (임베딩 추출) | ArcFace, MobileFaceNet |
| `ocr` | 문자 인식 | PaddleOCR, PPOCR-v4 |

### 실시간 시각화

- **Bounding Box** -- 객체 탐지 결과 클래스별 색상 박스 + 레이블 + 신뢰도 오버레이
- **Skeleton (Pose)** -- 관절 키포인트 및 연결선 시각화
- **Segmentation Mask** -- 클래스별 컬러 마스크 오버레이
- **ROI 영역** -- 설정된 ROI 폴리곤/라인 실시간 표시
- **추론 정보** -- FPS, 추론 시간(ms), 검출 객체 수 실시간 표시

### 시스템 모니터링

| 항목 | 세부 정보 |
|------|-----------|
| CPU | 사용률(%), 주파수(MHz), 코어별 사용률 |
| NPU | 사용률(%), 가용 여부, 코어 수(3), 드라이버 버전 |
| 메모리 | 총 용량, 사용량, 가용량, 사용률(%) |
| 온도 | CPU / NPU / GPU 온도 (C) |
| 디스크 | 총 용량, 사용량, 여유 공간, 사용률(%) |
| 네트워크 | 인터페이스, IP 주소, 송수신 바이트 |

### 이벤트 및 알림

| 기능 | 설명 |
|------|------|
| 이벤트 기록 | 모든 탐지/알림 이벤트 타임스탬프와 함께 기록 |
| 라인 크로싱 이벤트 | 객체가 설정된 라인을 통과 시 방향(in/out) 포함 이벤트 발생 |
| ROI 알림 | ROI 영역 내 객체 감지 시 알림 + 스냅샷 저장 |
| MQTT 알림 | MQTT 브로커로 이벤트 실시간 발행 (topic prefix 설정 가능) |
| Webhook 알림 | 설정된 URL로 HTTP POST 알림 전송 |
| 이벤트 확인 | 이벤트 acknowledge 처리 지원 |

---

## 디렉토리 구조

```
Orange-Pi-5-NPU-TEST-BED/
├── app/                          # FastAPI 애플리케이션 메인 패키지
│   ├── main.py                   # 앱 진입점 (create_app, lifespan)
│   ├── config.py                 # Pydantic Settings 기반 설정 관리
│   ├── dependencies.py           # FastAPI Dependency Injection
│   ├── api/                      # REST + HTMX API 라우터
│   │   ├── cameras.py            #   카메라 CRUD, 시작/정지
│   │   ├── models.py             #   모델 업로드/로드/활성화/삭제
│   │   ├── inference.py          #   추론 파이프라인 제어
│   │   ├── roi.py                #   ROI 프리셋/영역 관리
│   │   ├── stream.py             #   MJPEG, WebSocket, 스냅샷
│   │   └── system.py             #   헬스체크, 시스템 상태, 로그
│   ├── core/                     # 핵심 비즈니스 로직
│   │   ├── camera_manager.py     #   카메라 라이프사이클 관리
│   │   ├── model_registry.py     #   모델 파일 스캔 및 메타데이터 관리
│   │   ├── inference_engine.py   #   NPU 추론 엔진 (로드/언로드/실행)
│   │   ├── frame_processor.py    #   프레임 처리 파이프라인
│   │   ├── roi_manager.py        #   ROI 프리셋 및 필터링 로직
│   │   ├── stream_publisher.py   #   MJPEG/WebSocket 스트림 배포
│   │   └── event_handler.py      #   이벤트 수집 및 리스너 관리
│   ├── models/                   # Pydantic 데이터 모델 (스키마)
│   │   ├── camera.py             #   카메라 설정/상태 스키마
│   │   ├── inference.py          #   모델 정보, 추론 결과 스키마
│   │   ├── roi.py                #   ROI 설정/이벤트 스키마
│   │   └── system.py             #   시스템 상태/로그 스키마
│   ├── services/                 # 외부 서비스 연동
│   │   ├── rknn_service.py       #   RKNN Lite API 래퍼
│   │   ├── opencv_service.py     #   OpenCV 유틸리티
│   │   ├── system_monitor.py     #   CPU/NPU/메모리/온도 수집
│   │   └── notification.py       #   MQTT + Webhook 알림 서비스
│   ├── templates/                # Jinja2 HTML 템플릿
│   │   ├── base.html             #   기본 레이아웃
│   │   ├── index.html            #   메인 대시보드
│   │   ├── pages/                #   페이지별 템플릿
│   │   │   ├── cameras.html
│   │   │   ├── models.html
│   │   │   ├── monitor.html
│   │   │   └── settings.html
│   │   └── components/           #   HTMX partial 컴포넌트
│   │       ├── camera_card.html
│   │       ├── camera_list.html
│   │       ├── inference_panel.html
│   │       ├── log_viewer.html
│   │       ├── model_selector.html
│   │       ├── roi_editor.html
│   │       └── stats_panel.html
│   └── static/                   # 정적 파일
│       ├── css/app.css           #   Tailwind CSS (빌드 결과물)
│       ├── js/
│       │   ├── roi-canvas.js     #   ROI 편집기 Canvas 로직
│       │   ├── stats-chart.js    #   시스템 모니터링 차트
│       │   └── stream-viewer.js  #   스트림 뷰어 로직
│       └── img/
├── models/                       # RKNN 모델 파일 디렉토리
│   ├── detection/                #   객체 탐지 모델 (.rknn)
│   ├── segmentation/             #   세그멘테이션 모델
│   ├── pose/                     #   포즈 추정 모델
│   ├── classification/           #   분류 모델
│   ├── face/                     #   얼굴 탐지/인식 모델
│   └── ocr/                      #   OCR 모델
├── data/                         # 런타임 데이터
│   ├── config.json               #   영구 설정 파일
│   ├── roi_presets/              #   저장된 ROI 프리셋
│   ├── snapshots/                #   캡처된 스냅샷 이미지
│   └── logs/                     #   애플리케이션 로그
├── scripts/                      # 유틸리티 스크립트
│   ├── install_deps.sh           #   의존성 자동 설치
│   ├── convert_model.py          #   ONNX -> RKNN 변환
│   └── benchmark.py              #   모델 벤치마크 도구
├── tests/                        # 테스트 코드
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_camera.py
│   ├── test_inference.py
│   └── test_roi.py
├── docker/                       # Docker 관련 파일
│   ├── Dockerfile
│   └── docker-compose.yml
├── docs/                         # 프로젝트 문서
│   ├── api/
│   ├── architecture/
│   └── guides/
├── src/
│   └── input.css                 # Tailwind CSS 소스
├── .env.example                  # 환경 변수 템플릿
├── .gitignore
├── requirements.txt              # Python 의존성
├── package.json                  # Node.js (Tailwind CSS 빌드)
├── tailwind.config.js            # Tailwind CSS 설정
└── pytest.ini                    # Pytest 설정
```

---

## 빠른 시작

### 사전 요구사항

**하드웨어:**
- Orange Pi 5 Plus (RK3588) 또는 RK3588 기반 SBC
- RAM 8GB 이상 권장
- NPU 드라이버 설치 완료 (`/dev/dri` 접근 가능)
- (선택) USB 카메라, CSI 카메라, 또는 RTSP 지원 IP 카메라

**소프트웨어:**
- Ubuntu 22.04 (aarch64) 또는 호환 Linux 배포판
- Python 3.10 이상
- Node.js 18+ 및 npm (Tailwind CSS 빌드용)
- RKNN Toolkit2 Lite 2.0+ ([rockchip-linux/rknn-toolkit2](https://github.com/rockchip-linux/rknn-toolkit2))

### 설치

**1. 저장소 클론**

```bash
git clone https://github.com/YawnsDuzin/Orange-Pi-5-NPU-TEST-BED.git
cd Orange-Pi-5-NPU-TEST-BED
```

**2. 자동 설치 (권장)**

```bash
chmod +x scripts/install_deps.sh
./scripts/install_deps.sh
```

이 스크립트는 시스템 패키지, Python 가상 환경, pip 패키지, Tailwind CSS 빌드를 모두 처리합니다.

**3. 수동 설치**

```bash
# Python 가상 환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate

# Python 의존성 설치
pip install --upgrade pip
pip install -r requirements.txt

# RKNN Toolkit2 Lite 설치 (Orange Pi 5에서만, ARM64)
# https://github.com/rockchip-linux/rknn-toolkit2 에서 whl 다운로드
pip install rknn_toolkit_lite2-2.0.0b0-cp310-cp310-linux_aarch64.whl

# Tailwind CSS 빌드
npm install
npm run build:css

# 데이터 디렉토리 생성
mkdir -p data/{roi_presets,snapshots,logs}
mkdir -p models/{detection,segmentation,pose,face,ocr,classification}
```

**4. 환경 설정**

```bash
cp .env.example .env
# 필요에 따라 .env 파일 수정
```

**5. 서버 실행**

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

브라우저에서 `http://<장치-IP>:8000` 으로 접속합니다.

**6. 모델 추가**

`.rknn` 모델 파일을 `models/` 하위 타입별 디렉토리에 복사합니다.

```bash
cp yolov8n.rknn models/detection/
cp yolov8n-pose.rknn models/pose/
```

웹 UI에서 "Scan" 버튼을 클릭하거나 API를 통해 업로드할 수 있습니다.

### 개발 모드

개발 시에는 코드 변경 시 자동 재시작(reload)과 CSS 실시간 빌드를 함께 사용합니다.

**터미널 1 -- FastAPI 서버 (auto-reload):**

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**터미널 2 -- Tailwind CSS 감시 모드:**

```bash
npm run watch:css
```

> `APP_DEBUG=true` 설정 시 `/api/docs` (Swagger UI)와 `/api/redoc` (ReDoc)에서 대화형 API 문서를 사용할 수 있습니다.

### Docker 실행

```bash
cd docker
docker compose up -d
```

> **참고:** Docker 실행 시 NPU 접근을 위해 `privileged: true` 및 `/dev/dri` 마운트가 필요합니다.

---

## 환경 변수 설정

`.env.example` 파일을 `.env`로 복사한 뒤 필요한 값을 수정합니다.

### Application

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `APP_DEBUG` | `false` | 디버그 모드 (API 문서 활성화) |
| `APP_APP_NAME` | `NPU Inference Platform` | 애플리케이션 이름 |
| `APP_APP_VERSION` | `1.0.0` | 애플리케이션 버전 |

### Server

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `SERVER_HOST` | `0.0.0.0` | 서버 바인드 주소 |
| `SERVER_PORT` | `8000` | 서버 포트 |
| `SERVER_WORKERS` | `1` | Worker 수 (NPU 공유를 위해 반드시 1) |
| `SERVER_LOG_LEVEL` | `info` | 로깅 레벨 (`debug`, `info`, `warning`, `error`) |

### Camera

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `CAMERA_MAX_CAMERAS` | `8` | 최대 동시 카메라 수 |
| `CAMERA_RECONNECT_INTERVAL` | `5` | 재연결 간격 (초) |
| `CAMERA_FRAME_BUFFER_SIZE` | `1` | 프레임 버퍼 크기 |
| `CAMERA_DEFAULT_FPS_LIMIT` | `30` | 기본 FPS 제한 |
| `CAMERA_RTSP_TRANSPORT` | `tcp` | RTSP 전송 프로토콜 (`tcp` / `udp`) |
| `CAMERA_CAPTURE_TIMEOUT_MS` | `5000` | 캡처 읽기 타임아웃 (ms) |

### Inference (NPU)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `INFERENCE_DEFAULT_CONFIDENCE` | `0.5` | 기본 신뢰도 임계값 (0.0~1.0) |
| `INFERENCE_DEFAULT_NMS_THRESHOLD` | `0.45` | 기본 NMS 임계값 (0.0~1.0) |
| `INFERENCE_DEFAULT_CORE_MASK` | `7` | NPU 코어 마스크 (7 = 3코어 모두 사용) |
| `INFERENCE_MAX_LOADED_MODELS` | `3` | 동시 로드 가능 모델 수 |
| `INFERENCE_INFERENCE_TIMEOUT_MS` | `1000` | 추론 타임아웃 (ms) |
| `INFERENCE_ENABLE_FRAME_SKIP` | `true` | 추론 지연 시 프레임 스킵 |

### Stream

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `STREAM_MJPEG_QUALITY` | `80` | MJPEG JPEG 품질 (1-100) |
| `STREAM_MJPEG_MAX_FPS` | `30` | MJPEG 최대 FPS |
| `STREAM_WS_MAX_FPS` | `30` | WebSocket 최대 FPS |
| `STREAM_PREVIEW_SCALE` | `0.5` | Preview 썸네일 스케일 (0.1~1.0) |
| `STREAM_MAX_WS_CLIENTS` | `10` | 스트림당 최대 WebSocket 클라이언트 수 |

### Storage

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `STORAGE_MAX_SNAPSHOTS` | `1000` | 최대 스냅샷 저장 수 |
| `STORAGE_MAX_LOG_SIZE_MB` | `100` | 최대 로그 파일 크기 (MB) |
| `STORAGE_SNAPSHOT_QUALITY` | `95` | 스냅샷 JPEG 품질 (1-100) |

### Notification

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `NOTIFY_MQTT_ENABLED` | `false` | MQTT 알림 활성화 |
| `NOTIFY_MQTT_BROKER` | `localhost` | MQTT 브로커 주소 |
| `NOTIFY_MQTT_PORT` | `1883` | MQTT 브로커 포트 |
| `NOTIFY_MQTT_TOPIC_PREFIX` | `npu-platform` | MQTT 토픽 접두어 |
| `NOTIFY_WEBHOOK_ENABLED` | `false` | Webhook 알림 활성화 |
| `NOTIFY_WEBHOOK_URL` | _(없음)_ | Webhook 수신 URL |
| `NOTIFY_WEBHOOK_TIMEOUT` | `10` | Webhook 요청 타임아웃 (초) |

### Security

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `SECURITY_ENABLE_AUTH` | `false` | 인증 활성화 |
| `SECURITY_API_KEY` | _(없음)_ | API 인증 키 |
| `SECURITY_MAX_UPLOAD_SIZE_MB` | `500` | 모델 업로드 최대 크기 (MB) |
| `SECURITY_CORS_ORIGINS` | `["*"]` | 허용 CORS origin 목록 |

---

## API 엔드포인트

### 웹 페이지

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/` | 메인 대시보드 |
| `GET` | `/cameras` | 카메라 관리 페이지 |
| `GET` | `/models` | 모델 관리 페이지 |
| `GET` | `/monitor` | 실시간 모니터링 페이지 |
| `GET` | `/settings` | 시스템 설정 페이지 |

### Camera API (`/api/cameras`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/cameras` | 전체 카메라 목록 (JSON) |
| `GET` | `/api/cameras/list` | 카메라 목록 (HTMX partial) |
| `POST` | `/api/cameras` | 새 카메라 등록 |
| `GET` | `/api/cameras/{id}` | 카메라 상세 정보 |
| `PUT` | `/api/cameras/{id}` | 카메라 설정 수정 |
| `DELETE` | `/api/cameras/{id}` | 카메라 삭제 |
| `POST` | `/api/cameras/{id}/start` | 카메라 스트림 시작 |
| `POST` | `/api/cameras/{id}/stop` | 카메라 스트림 정지 |
| `GET` | `/api/cameras/{id}/status` | 카메라 상태 조회 (HTMX polling) |

### Model API (`/api/models`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/models` | 전체 모델 목록 (JSON) |
| `GET` | `/api/models/list` | 모델 목록 (HTMX partial) |
| `GET` | `/api/models/{id}` | 모델 상세 정보 |
| `POST` | `/api/models/upload` | RKNN 모델 파일 업로드 |
| `POST` | `/api/models/{id}/load` | 모델을 NPU에 로드 |
| `POST` | `/api/models/{id}/unload` | 모델을 NPU에서 언로드 |
| `POST` | `/api/models/{id}/activate` | 모델 활성화 (미로드 시 자동 로드) |
| `DELETE` | `/api/models/{id}` | 모델 삭제 (파일 삭제 옵션) |
| `POST` | `/api/models/scan` | 모델 디렉토리 재스캔 |

### Inference API (`/api/inference`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/inference/start` | 추론 파이프라인 시작 (카메라 + 모델 지정) |
| `POST` | `/api/inference/stop/{camera_id}` | 추론 파이프라인 정지 |
| `PUT` | `/api/inference/config/{camera_id}` | 추론 파라미터 실시간 변경 |
| `GET` | `/api/inference/status/{camera_id}` | 추론 상태 조회 |
| `GET` | `/api/inference/stats/{model_id}` | 추론 통계 (FPS, latency) |
| `GET` | `/api/inference/panel` | 추론 설정 패널 (HTMX partial) |

### ROI API (`/api/roi`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/roi/presets` | ROI 프리셋 목록 (카메라 필터 가능) |
| `POST` | `/api/roi/presets` | 새 프리셋 생성 |
| `GET` | `/api/roi/presets/{id}` | 프리셋 상세 정보 |
| `DELETE` | `/api/roi/presets/{id}` | 프리셋 삭제 |
| `POST` | `/api/roi/presets/{id}/activate` | 프리셋 활성화 |
| `POST` | `/api/roi/presets/{id}/rois` | 프리셋에 ROI 추가 |
| `DELETE` | `/api/roi/presets/{id}/rois/{roi_id}` | 프리셋에서 ROI 제거 |
| `GET` | `/api/roi/editor` | ROI 편집기 (HTMX partial) |

### Stream API (`/api/stream`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/stream/{id}/mjpeg` | MJPEG 비디오 스트림 |
| `WebSocket` | `/api/stream/{id}/ws` | WebSocket 비디오 + 메타데이터 |
| `GET` | `/api/stream/{id}/snapshot` | 단일 프레임 스냅샷 (JPEG) |
| `GET` | `/api/stream/{id}/preview` | 저해상도 미리보기 썸네일 |

### System API (`/api/system`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/system/health` | 헬스 체크 (상태, 버전, NPU 가용 여부) |
| `GET` | `/api/system/status` | 전체 시스템 상태 (CPU/NPU/메모리/온도/디스크) |
| `GET` | `/api/system/status/panel` | 시스템 상태 패널 (HTMX partial) |
| `GET` | `/api/system/events` | 이벤트 히스토리 조회 (필터 가능) |
| `POST` | `/api/system/events/{id}/acknowledge` | 이벤트 확인 처리 |
| `GET` | `/api/system/logs` | 애플리케이션 로그 조회 (레벨/페이지네이션) |
| `GET` | `/api/system/logs/viewer` | 로그 뷰어 (HTMX partial) |
| `GET` | `/api/system/info` | 애플리케이션 정보 |

> **Swagger UI:** `APP_DEBUG=true` 설정 시 `/api/docs` 에서 대화형 API 문서를 확인할 수 있습니다.

---

## 지원 모델 및 예시

각 모델은 RKNN 포맷(`.rknn`)으로 변환 후 해당 타입 디렉토리에 배치합니다.

### Object Detection

```
models/detection/
├── yolov5s_rk3588.rknn        # YOLOv5s - 80 classes (COCO)
├── yolov8n_rk3588.rknn        # YOLOv8 Nano - 80 classes (COCO)
└── yolov11n_rk3588.rknn       # YOLOv11 Nano - 80 classes (COCO)
```

### Instance Segmentation

```
models/segmentation/
├── yolov8n-seg_rk3588.rknn    # YOLOv8 Nano Segmentation
└── yolov11n-seg_rk3588.rknn   # YOLOv11 Nano Segmentation
```

### Pose Estimation

```
models/pose/
├── yolov8n-pose_rk3588.rknn   # YOLOv8 Nano Pose (17 keypoints)
└── yolov11n-pose_rk3588.rknn  # YOLOv11 Nano Pose (17 keypoints)
```

### Classification

```
models/classification/
├── yolov8n-cls_rk3588.rknn    # YOLOv8 Nano Classification
└── resnet50_rk3588.rknn       # ResNet50 (ImageNet 1000 classes)
```

### Face Detection / Recognition

```
models/face/
├── retinaface_rk3588.rknn     # RetinaFace
├── scrfd_rk3588.rknn          # SCRFD (Sample and Compute Redesigned)
└── arcface_rk3588.rknn        # ArcFace (Embedding Extraction)
```

### OCR

```
models/ocr/
├── ppocr_det_rk3588.rknn      # PaddleOCR Detection
└── ppocr_rec_rk3588.rknn      # PaddleOCR Recognition
```

### 모델 변환 (ONNX -> RKNN)

```bash
# INT8 양자화 변환 (성능 우선, 권장)
python scripts/convert_model.py \
    --input model.onnx \
    --output models/detection/model_rk3588.rknn \
    --type detection \
    --quantize int8 \
    --dataset ./calibration_images/

# FP16 변환 (정확도 우선)
python scripts/convert_model.py \
    --input model.onnx \
    --output models/detection/model_fp16_rk3588.rknn \
    --quantize fp16

# 입력 크기 및 전처리 지정
python scripts/convert_model.py \
    --input model.onnx \
    --output model_rk3588.rknn \
    --type detection \
    --input-size 640 640 \
    --mean 0 0 0 \
    --std 255 255 255 \
    --target-platform rk3588
```

### 벤치마크

```bash
python scripts/benchmark.py \
    --model models/detection/yolov8n_rk3588.rknn \
    --iterations 200 \
    --warmup 20 \
    --core-mask 7

# 출력 예시:
# ============================================================
# Results
# ============================================================
# Model:          yolov8n_rk3588.rknn
# Input:          640x640
# Core mask:      7
# Iterations:     200
# ------------------------------------------------------------
# Mean:           28.45 ms
# Median (P50):   27.82 ms
# P95:            32.15 ms
# P99:            35.67 ms
# ------------------------------------------------------------
# Throughput:     35.2 FPS
# ============================================================
```

---

## 기술 스택

### Backend

| 기술 | 버전 | 용도 |
|------|------|------|
| **Python** | 3.10+ | 메인 언어 |
| **FastAPI** | 0.109+ | 비동기 웹 프레임워크 |
| **Uvicorn** | 0.27+ | ASGI 서버 |
| **Pydantic** | 2.6+ | 데이터 유효성 검증 및 설정 관리 |
| **pydantic-settings** | 2.1+ | 환경 변수 기반 설정 |
| **OpenCV** | 4.9+ | 영상 캡처, 처리, 인코딩 |
| **NumPy** | 1.26+ | 수치 연산 |
| **RKNN Toolkit2 Lite** | 2.0+ | RK3588 NPU 추론 런타임 |
| **httpx** | 0.26+ | 비동기 HTTP 클라이언트 (Webhook) |
| **paho-mqtt** | 2.0+ | MQTT 클라이언트 (선택) |
| **aiofiles** | 23.2+ | 비동기 파일 I/O |
| **websockets** | 12.0+ | WebSocket 프로토콜 |

### Frontend

| 기술 | 용도 |
|------|------|
| **Jinja2** | 서버 사이드 템플릿 렌더링 |
| **HTMX** | SPA 없는 동적 UI 업데이트 (partial swap) |
| **Tailwind CSS 3.4** | 유틸리티 우선 CSS 프레임워크 |
| **Canvas API** | ROI 편집기 드로잉 인터페이스 |
| **WebSocket API** | 실시간 스트리밍 및 양방향 통신 |

### 인프라 / 도구

| 기술 | 용도 |
|------|------|
| **Docker** | 컨테이너화 배포 (ARM64) |
| **Docker Compose** | 서비스 오케스트레이션 |
| **pytest** | 자동화 테스트 프레임워크 |
| **pytest-asyncio** | 비동기 테스트 지원 |
| **Ruff** | Python 코드 린팅 (개발용) |

---

## RK3588 성능 최적화 가이드

### NPU 코어 마스크 설정

RK3588의 NPU는 3개의 독립 코어를 가지며, `INFERENCE_DEFAULT_CORE_MASK` 값으로 사용할 코어 조합을 제어합니다.

| Core Mask | 사용 코어 | 권장 시나리오 |
|-----------|-----------|---------------|
| `1` | Core 0 | 단일 경량 모델, 다중 모델 분리 운용 |
| `2` | Core 1 | 단일 경량 모델, 다중 모델 분리 운용 |
| `4` | Core 2 | 단일 경량 모델, 다중 모델 분리 운용 |
| `3` | Core 0+1 | 중간 크기 모델 |
| `5` | Core 0+2 | 중간 크기 모델 |
| `6` | Core 1+2 | 중간 크기 모델 |
| `7` (기본) | Core 0+1+2 | 최대 성능 (전체 3코어 활용) |

### 최적화 권장 사항

1. **Worker 수 1 유지** -- NPU 리소스는 프로세스 간 공유가 불가하므로 `SERVER_WORKERS=1`로 설정해야 합니다. 다중 worker를 사용하면 NPU 접근 충돌이 발생합니다.

2. **INT8 양자화 사용** -- FP16 대비 약 2~3배 빠른 추론 속도를 제공합니다. 대부분의 Detection/Pose 모델에서 정확도 손실이 미미합니다. 변환 시 Calibration Dataset을 사용하면 정확도를 더 높일 수 있습니다.

3. **프레임 스킵 활성화** -- `INFERENCE_ENABLE_FRAME_SKIP=true`로 설정하면 추론이 프레임 입력 속도보다 느릴 때 이전 프레임을 건너뛰어 실시간성을 유지합니다.

4. **프레임 버퍼 최소화** -- `CAMERA_FRAME_BUFFER_SIZE=1`로 설정하여 항상 최신 프레임을 처리합니다. 값이 클수록 지연(latency)이 증가합니다.

5. **입력 해상도 최적화** -- 640x640이 속도와 정확도의 최적 균형점입니다. 320x320으로 줄이면 약 4배 빠르지만 소형 객체 탐지율이 감소합니다.

6. **MJPEG 품질 조절** -- 네트워크 대역폭이 제한적인 경우 `STREAM_MJPEG_QUALITY`를 60~70으로 낮추면 CPU 부하와 전송량을 줄일 수 있습니다.

7. **동시 로드 모델 수 제한** -- NPU 메모리는 제한적이므로 `INFERENCE_MAX_LOADED_MODELS=3` 이하로 유지합니다. 미사용 모델은 명시적으로 언로드하세요.

8. **열 관리** -- RK3588은 지속적 NPU 추론 시 발열이 증가합니다. 방열판 및 팬 쿨링을 권장하며, 모니터링 페이지(`/monitor`)에서 CPU/NPU/GPU 온도를 실시간 확인하세요. 과열 시 자동 throttling이 발생하여 성능이 저하됩니다.

---

## 문제 해결

### NPU를 찾을 수 없음

```
ERROR: RKNN Lite not available
```

**해결 방법:**
- `/dev/dri` 디바이스 존재 확인: `ls -la /dev/dri`
- NPU 드라이버 로드 확인: `dmesg | grep -i rknpu`
- RKNN Toolkit2 Lite 설치 확인: `python3 -c "from rknnlite.api import RKNNLite; print('OK')"`
- Docker 사용 시 `privileged: true` 및 `/dev/dri` 볼륨 마운트 확인

### 모델 로드 실패

```
ERROR: Failed to load model
```

**해결 방법:**
- 모델 파일이 `.rknn` 포맷인지 확인 (ONNX/PyTorch 파일은 `scripts/convert_model.py`로 변환 필요)
- 모델이 `rk3588` 타겟으로 변환되었는지 확인
- NPU 메모리 부족 시 기존 모델을 언로드(`/api/models/{id}/unload`)한 후 재시도
- `INFERENCE_MAX_LOADED_MODELS` 제한에 도달하지 않았는지 확인

### 카메라 연결 실패

```
ERROR: Camera connection timeout
```

**해결 방법:**
- RTSP URL 유효성 확인: `ffprobe rtsp://user:pass@ip:port/path`
- USB 카메라 디바이스 확인: `v4l2-ctl --list-devices`
- 방화벽이 RTSP 포트(554)를 차단하고 있지 않은지 확인
- `CAMERA_RTSP_TRANSPORT`를 `tcp`에서 `udp`로 변경 시도 (또는 반대)
- `CAMERA_CAPTURE_TIMEOUT_MS` 값을 늘려보기 (네트워크 지연 환경)

### 웹 UI CSS가 적용되지 않음

**해결 방법:**
- CSS 빌드 실행: `npm run build:css`
- `app/static/css/app.css` 파일이 존재하고 비어있지 않은지 확인
- Node.js와 npm이 설치되어 있는지 확인: `node --version && npm --version`
- `npm install`로 Tailwind CSS가 설치되었는지 확인

### 추론 FPS가 낮음

**해결 방법:**
- `INFERENCE_DEFAULT_CORE_MASK=7`으로 모든 NPU 코어 사용 확인
- INT8 양자화 모델 사용 확인 (FP16 대비 2~3배 차이)
- 입력 해상도 축소 고려 (640x640 -> 320x320)
- `INFERENCE_ENABLE_FRAME_SKIP=true` 확인
- 시스템 온도 확인 -- 과열 시 NPU throttling 발생
- 벤치마크로 모델 단독 성능 확인: `python scripts/benchmark.py -m model.rknn`
- 동시 실행 중인 추론 파이프라인 수 줄이기

### 포트 충돌

```
ERROR: [Errno 98] Address already in use
```

**해결 방법:**
- 기존 프로세스 확인 및 종료: `lsof -i :8000` 또는 `fuser -k 8000/tcp`
- `.env`에서 `SERVER_PORT`를 다른 값으로 변경

### WebSocket 연결 끊김

**해결 방법:**
- 브라우저의 WebSocket 연결 수 제한 확인
- `STREAM_MAX_WS_CLIENTS` 값 확인 (기본 10)
- 네트워크 프록시/로드밸런서의 WebSocket 지원 확인
- 방화벽에서 WebSocket 업그레이드 요청이 차단되고 있지 않은지 확인

---

## 테스트 실행

```bash
source .venv/bin/activate

# 전체 테스트 실행
pytest

# 상세 출력
pytest -v --tb=long

# 특정 테스트 파일 실행
pytest tests/test_api.py
pytest tests/test_inference.py
pytest tests/test_roi.py
pytest tests/test_camera.py
```

---

## 참고 자료

- [RKNN Toolkit2](https://github.com/rockchip-linux/rknn-toolkit2) -- RKNN 모델 변환 및 NPU 런타임
- [FastAPI](https://fastapi.tiangolo.com/) -- Python 비동기 웹 프레임워크
- [HTMX](https://htmx.org/) -- HTML 기반 서버 렌더링 + 동적 업데이트
- [Tailwind CSS](https://tailwindcss.com/) -- 유틸리티 우선 CSS 프레임워크
- [OpenCV](https://docs.opencv.org/) -- 컴퓨터 비전 라이브러리
- [Pydantic](https://docs.pydantic.dev/) -- 데이터 유효성 검증
- [Orange Pi 5 Plus Wiki](http://www.orangepi.org/html/hardWare/computerAndMicrocontrollers/service-and-support/Orange-Pi-5-plus.html) -- 하드웨어 문서

---

## 라이선스

이 프로젝트는 [MIT License](LICENSE)에 따라 배포됩니다.

```
MIT License

Copyright (c) 2024 NPU Inference Platform Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
