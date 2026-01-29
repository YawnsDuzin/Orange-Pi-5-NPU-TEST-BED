# NPU Inference Platform 사용자 가이드

> **Orange Pi 5 Plus (RK3588) NPU 실시간 추론 테스트 플랫폼**
>
> 버전: 1.0.0

---

## 목차

1. [시작하기 (Getting Started)](#1-시작하기-getting-started)
2. [카메라 관리 (Camera Management)](#2-카메라-관리-camera-management)
3. [모델 관리 (Model Management)](#3-모델-관리-model-management)
4. [ROI 설정 (ROI Configuration)](#4-roi-설정-roi-configuration)
5. [실시간 추론 (Real-time Inference)](#5-실시간-추론-real-time-inference)
6. [이벤트 및 알림 (Events & Notifications)](#6-이벤트-및-알림-events--notifications)
7. [시스템 모니터링 (System Monitoring)](#7-시스템-모니터링-system-monitoring)
8. [키보드 단축키 (Keyboard Shortcuts)](#8-키보드-단축키-keyboard-shortcuts)
9. [FAQ](#9-faq)

---

## 1. 시작하기 (Getting Started)

### 1.1 첫 실행 개요

NPU Inference Platform은 Orange Pi 5 Plus의 RK3588 NPU를 활용하여 실시간 영상 추론을 수행하는 웹 기반 플랫폼입니다. 브라우저를 통해 카메라 연결, 모델 관리, ROI 설정, 추론 실행 등 모든 기능을 제어할 수 있습니다.

### 1.2 애플리케이션 시작

```bash
# 기본 실행
cd /home/user/Orange-Pi-5-NPU-TEST-BED
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 개발 모드 (자동 리로드 활성화)
APP_DEBUG=true python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 1.3 웹 인터페이스 접속

브라우저에서 아래 주소로 접속합니다:

```
http://<Orange-Pi-IP>:8000
```

로컬에서 접속할 경우:

```
http://localhost:8000
```

### 1.4 첫 실행 워크스루 (First Run Walkthrough)

처음 플랫폼을 실행하면 아래 순서대로 설정하는 것을 권장합니다:

| 단계 | 페이지 | 작업 |
|------|--------|------|
| **1단계** | Dashboard (`/`) | 시스템 상태 확인 - NPU 인식 여부, 메모리, 온도 등 |
| **2단계** | Models (`/models`) | RKNN 모델 파일 업로드 및 활성화 |
| **3단계** | Cameras (`/cameras`) | 카메라 소스 등록 (RTSP/USB/CSI/File) |
| **4단계** | Dashboard (`/`) | 카메라와 모델을 선택하여 추론 시작 |
| **5단계** | Monitor (`/monitor`) | 실시간 성능 모니터링 및 결과 확인 |

### 1.5 페이지 구성

플랫폼은 다음 페이지들로 구성됩니다:

- **Dashboard** (`/`) - 메인 대시보드, 스트림 뷰어, 추론 제어 패널
- **Cameras** (`/cameras`) - 카메라 등록/관리/상태 모니터링
- **Models** (`/models`) - RKNN 모델 업로드/로드/활성화/삭제
- **Monitor** (`/monitor`) - 실시간 시스템 리소스 모니터링
- **Settings** (`/settings`) - 시스템 설정 및 알림 구성

### 1.6 API 문서 확인

Debug 모드가 활성화된 경우 Swagger UI에서 전체 API를 확인할 수 있습니다:

```
http://<Orange-Pi-IP>:8000/api/docs     # Swagger UI
http://<Orange-Pi-IP>:8000/api/redoc    # ReDoc
```

Debug 모드 활성화:

```bash
APP_DEBUG=true python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 2. 카메라 관리 (Camera Management)

### 2.1 지원 카메라 유형

| 유형 | `camera_type` 값 | 설명 | URL/경로 예시 |
|------|-------------------|------|---------------|
| **RTSP 카메라** | `rtsp` | IP 카메라, NVR 스트림 | `rtsp://admin:pass@192.168.1.100:554/stream1` |
| **USB 카메라** | `usb` | USB 웹캠 | `/dev/video0` |
| **CSI 카메라** | `csi` | MIPI CSI 카메라 모듈 | `/dev/video0` |
| **파일 소스** | `file` | 동영상 파일, 이미지 시퀀스 | `/path/to/video.mp4` |

### 2.2 카메라 등록

#### 웹 인터페이스

1. **Cameras** 페이지 (`/cameras`)로 이동합니다.
2. **카메라 추가** 버튼을 클릭합니다.
3. 아래 정보를 입력합니다:
   - **이름**: 카메라 식별 이름 (최대 100자)
   - **URL/경로**: 카메라 소스 주소
   - **유형**: RTSP / USB / CSI / File 중 선택
   - **설명**: (선택) 카메라 설명 (최대 500자)
4. **등록** 버튼을 클릭합니다.

#### API를 통한 등록

```bash
# RTSP 카메라 등록
curl -X POST http://localhost:8000/api/cameras \
  -H "Content-Type: application/json" \
  -d '{
    "name": "주차장 카메라 1",
    "url": "rtsp://admin:password@192.168.1.100:554/Streaming/Channels/101",
    "camera_type": "rtsp",
    "enabled": true,
    "reconnect_interval": 5,
    "description": "주차장 입구 카메라"
  }'

# USB 카메라 등록
curl -X POST http://localhost:8000/api/cameras \
  -H "Content-Type: application/json" \
  -d '{
    "name": "USB 웹캠",
    "url": "/dev/video0",
    "camera_type": "usb",
    "enabled": true
  }'

# 비디오 파일 소스 등록
curl -X POST http://localhost:8000/api/cameras \
  -H "Content-Type: application/json" \
  -d '{
    "name": "테스트 영상",
    "url": "/home/user/test_videos/sample.mp4",
    "camera_type": "file",
    "enabled": true
  }'
```

### 2.3 카메라 제어

```bash
# 카메라 스트림 시작
curl -X POST http://localhost:8000/api/cameras/{camera_id}/start

# 카메라 스트림 중지
curl -X POST http://localhost:8000/api/cameras/{camera_id}/stop

# 카메라 상태 조회
curl http://localhost:8000/api/cameras/{camera_id}/status

# 카메라 설정 수정
curl -X PUT http://localhost:8000/api/cameras/{camera_id} \
  -H "Content-Type: application/json" \
  -d '{"name": "새 이름", "reconnect_interval": 10}'

# 카메라 삭제
curl -X DELETE http://localhost:8000/api/cameras/{camera_id}
```

### 2.4 카메라 상태 모니터링

카메라는 아래 상태 중 하나를 가집니다:

| 상태 | `status` 값 | 설명 |
|------|-------------|------|
| 연결 해제 | `disconnected` | 아직 연결되지 않은 상태 |
| 연결 중 | `connecting` | 카메라에 연결을 시도하는 중 |
| 연결됨 | `connected` | 정상적으로 프레임을 수신하는 중 |
| 오류 | `error` | 연결 오류 발생 |
| 중지됨 | `stopped` | 수동으로 중지한 상태 |

카메라 상태 정보에는 다음 항목이 포함됩니다:

- **FPS**: 현재 프레임 수신 속도
- **Frame Count**: 총 수신 프레임 수
- **Resolution**: 영상 해상도
- **Uptime**: 연결 유지 시간
- **Error Message**: 오류 발생 시 메시지

### 2.5 스트림 보기

```bash
# MJPEG 스트림 (브라우저에서 직접 접속 가능)
http://localhost:8000/api/stream/{camera_id}/mjpeg

# WebSocket 스트림 (추론 결과 metadata 포함)
ws://localhost:8000/api/stream/{camera_id}/ws

# 단일 프레임 스냅샷
http://localhost:8000/api/stream/{camera_id}/snapshot?quality=90

# 저해상도 프리뷰 썸네일
http://localhost:8000/api/stream/{camera_id}/preview
```

### 2.6 RTSP 설정 팁

- **Transport Protocol**: 기본값은 TCP입니다. UDP를 사용하려면 환경 변수 `CAMERA_RTSP_TRANSPORT=udp`를 설정합니다.
- **재연결**: 연결이 끊어지면 `reconnect_interval` 초 간격으로 자동 재연결을 시도합니다. `CAMERA_RECONNECT_MAX_RETRIES=0`(기본값)이면 무한 재시도합니다.
- **버퍼 크기**: `CAMERA_FRAME_BUFFER_SIZE=1`(기본값)은 항상 최신 프레임만 유지하여 지연을 최소화합니다.
- **Timeout**: 프레임 읽기 timeout은 `CAMERA_CAPTURE_TIMEOUT_MS=5000`(기본값 5초)입니다.

### 2.7 동시 카메라 제한

최대 동시 카메라 수는 기본 **8대**입니다. 변경하려면:

```bash
export CAMERA_MAX_CAMERAS=16
```

> **참고**: 카메라 수를 늘리면 메모리 사용량과 CPU 부하가 증가합니다. Orange Pi 5 Plus의 16GB RAM 기준으로 8대 이하를 권장합니다.

---

## 3. 모델 관리 (Model Management)

### 3.1 지원 모델 유형

| 모델 유형 | `model_type` 값 | 설명 | 예시 모델 |
|-----------|-----------------|------|-----------|
| **객체 탐지** | `detection` | Bounding box 기반 객체 탐지 | YOLOv5, YOLOv8, SSD |
| **세그멘테이션** | `segmentation` | Instance segmentation | YOLOv8-seg |
| **포즈 추정** | `pose` | 인체 관절 포인트 추정 | YOLOv8-pose |
| **분류** | `classification` | 이미지 분류 | ResNet, MobileNet |
| **얼굴 탐지** | `face_detection` | 얼굴 영역 탐지 | RetinaFace |
| **얼굴 인식** | `face_recognition` | 얼굴 특징 추출/인식 | ArcFace |
| **OCR** | `ocr` | 텍스트 인식 | PaddleOCR |

> **중요**: 모든 모델은 `.rknn` 형식이어야 합니다. ONNX 모델은 사전에 RKNN 형식으로 변환해야 합니다.

### 3.2 모델 변환 (ONNX to RKNN)

제공된 변환 스크립트를 사용하여 ONNX 모델을 RKNN 형식으로 변환합니다:

```bash
# 기본 변환 (INT8 양자화)
python scripts/convert_model.py \
  --input model.onnx \
  --output model.rknn \
  --type detection

# INT8 양자화 + Calibration 데이터셋 사용
python scripts/convert_model.py \
  --input yolov8n.onnx \
  --output yolov8n.rknn \
  --type detection \
  --quantize int8 \
  --dataset ./calibration_images/ \
  --input-size 640 640

# FP16 변환 (정확도 우선)
python scripts/convert_model.py \
  --input model.onnx \
  --output model_fp16.rknn \
  --type classification \
  --quantize fp16
```

변환 옵션:

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--input`, `-i` | 입력 ONNX 모델 경로 | (필수) |
| `--output`, `-o` | 출력 RKNN 모델 경로 | (필수) |
| `--type`, `-t` | 모델 유형 | `detection` |
| `--quantize`, `-q` | 양자화 방식 (`fp16`, `int8`, `dynamic`) | `int8` |
| `--dataset`, `-d` | INT8 calibration 이미지 디렉토리 | (선택) |
| `--input-size` | 입력 크기 `W H` | `640 640` |
| `--mean` | 입력 mean 값 | `0 0 0` |
| `--std` | 입력 std 값 | `255 255 255` |
| `--target-platform` | 타겟 플랫폼 | `rk3588` |

### 3.3 모델 업로드

#### 웹 인터페이스

1. **Models** 페이지 (`/models`)로 이동합니다.
2. **모델 업로드** 영역에서 `.rknn` 파일을 선택합니다.
3. 모델 이름, 유형, 설명을 입력합니다.
4. **업로드** 버튼을 클릭합니다.

#### API를 통한 업로드

```bash
curl -X POST http://localhost:8000/api/models/upload \
  -F "file=@yolov8n.rknn" \
  -F "name=YOLOv8n Detection" \
  -F "model_type=detection" \
  -F "description=YOLOv8 Nano 객체 탐지 모델 (COCO 80 클래스)"
```

> **업로드 크기 제한**: 기본 최대 500MB입니다. `SECURITY_MAX_UPLOAD_SIZE_MB` 환경 변수로 변경할 수 있습니다.

### 3.4 모델 디렉토리 스캔

`models/` 디렉토리에 직접 `.rknn` 파일을 복사한 후 스캔 명령을 실행하면 자동으로 등록됩니다:

```bash
# 모델 파일 복사
cp yolov8n.rknn /home/user/Orange-Pi-5-NPU-TEST-BED/models/

# 디렉토리 스캔 실행
curl -X POST http://localhost:8000/api/models/scan
```

### 3.5 모델 로드 및 활성화

모델을 NPU에서 사용하려면 **로드(Load)** 후 **활성화(Activate)** 해야 합니다:

```bash
# 1. 모델 목록 조회
curl http://localhost:8000/api/models

# 2. 모델 로드 (NPU 메모리에 적재)
curl -X POST http://localhost:8000/api/models/{model_id}/load

# 3. 모델 활성화 (추론에 사용할 모델로 설정)
curl -X POST http://localhost:8000/api/models/{model_id}/activate

# 4. 모델 언로드 (NPU 메모리에서 해제)
curl -X POST http://localhost:8000/api/models/{model_id}/unload
```

> **Activate 단축 동작**: `/activate` endpoint는 모델이 아직 로드되지 않았다면 자동으로 로드한 후 활성화합니다.

### 3.6 모델 Hot-Swap

실시간 추론 중에 모델을 전환하는 것을 **Hot-Swap**이라 합니다. 다음과 같이 사용합니다:

1. 새 모델을 사전에 로드합니다 (`/load`).
2. 새 모델을 활성화합니다 (`/activate`).
3. 추론 pipeline이 자동으로 새 모델을 사용합니다.
4. 이전 모델이 더 이상 필요 없으면 언로드합니다 (`/unload`).

```bash
# 예시: YOLOv8n에서 YOLOv8s로 전환
curl -X POST http://localhost:8000/api/models/{yolov8s_id}/load
curl -X POST http://localhost:8000/api/models/{yolov8s_id}/activate
curl -X POST http://localhost:8000/api/models/{yolov8n_id}/unload
```

> **동시 로드 제한**: 기본적으로 최대 **3개** 모델을 동시에 NPU에 로드할 수 있습니다. `INFERENCE_MAX_LOADED_MODELS` 환경 변수로 조정합니다.

### 3.7 모델 삭제

```bash
# 레지스트리에서만 제거 (파일 유지)
curl -X DELETE http://localhost:8000/api/models/{model_id}

# 파일까지 삭제
curl -X DELETE "http://localhost:8000/api/models/{model_id}?delete_file=true"
```

### 3.8 모델 벤치마크

모델의 추론 성능을 측정하려면 벤치마크 스크립트를 사용합니다:

```bash
python scripts/benchmark.py \
  --model models/yolov8n.rknn \
  --iterations 200 \
  --warmup 20 \
  --core-mask 7

# 출력 예시:
# ============================================================
# Results
# ============================================================
# Model:          yolov8n.rknn
# Input:          640x640
# Core mask:      7
# Iterations:     200
# ------------------------------------------------------------
# Mean:           12.35 ms
# Median (P50):   11.80 ms
# P95:            15.20 ms
# P99:            18.50 ms
# ------------------------------------------------------------
# Throughput:     80.9 FPS
# ============================================================
```

---

## 4. ROI 설정 (ROI Configuration)

### 4.1 ROI 개요

ROI(Region of Interest)는 영상의 특정 영역을 지정하여 추론 결과를 필터링하거나 이벤트를 발생시키는 기능입니다.

### 4.2 ROI 유형

| 유형 | `roi_type` | 설명 | 필요 포인트 |
|------|-----------|------|-------------|
| **사각형** | `rectangle` | 직사각형 영역 | 2개 (좌상단, 우하단) |
| **다각형** | `polygon` | 자유 형태 다각형 영역 | 3개 이상 |
| **라인** | `line` | 가상 라인 (통과 감지용) | 2개 (시작점, 끝점) |

### 4.3 ROI 동작 모드

| 모드 | `action` | 설명 |
|------|----------|------|
| **포함** | `include` | 해당 영역 내부의 탐지 결과만 유지 |
| **제외** | `exclude` | 해당 영역 내부의 탐지 결과를 제거 |
| **알림** | `alert` | 해당 영역에 객체 진입/존재 시 이벤트 발생 |

### 4.4 ROI 좌표 체계

모든 ROI 좌표는 **정규화된 값** (0.0 ~ 1.0)을 사용합니다:

- `x`: 0.0 = 영상 왼쪽 끝, 1.0 = 영상 오른쪽 끝
- `y`: 0.0 = 영상 상단, 1.0 = 영상 하단

이를 통해 해상도가 다른 카메라에서도 동일한 ROI 설정을 재사용할 수 있습니다.

### 4.5 ROI 그리기 (웹 인터페이스)

웹 인터페이스의 **ROI Editor** 컴포넌트에서 마우스로 직접 ROI를 그릴 수 있습니다:

1. Dashboard에서 카메라를 선택합니다.
2. ROI Editor 패널을 엽니다.
3. 그리기 도구를 선택합니다:
   - **Rectangle**: 클릭-드래그로 사각형을 그립니다.
   - **Polygon**: 클릭으로 꼭짓점을 추가하고, 더블클릭 또는 시작점 클릭으로 완성합니다.
   - **Line**: 시작점과 끝점을 클릭합니다.
4. ROI 이름, 동작 모드, 색상을 설정합니다.
5. **저장** 버튼을 클릭합니다.

### 4.6 API를 통한 ROI 생성

#### Preset 생성

ROI는 **Preset**(프리셋) 단위로 관리됩니다. 하나의 Preset에 여러 ROI를 포함할 수 있으며, 카메라별로 활성 Preset을 선택합니다.

```bash
# Preset 생성 (ROI 포함)
curl -X POST http://localhost:8000/api/roi/presets \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": "abc12345",
    "name": "주차장 모니터링 설정",
    "rois": [
      {
        "name": "출입구 영역",
        "roi_type": "rectangle",
        "points": [
          {"x": 0.1, "y": 0.3},
          {"x": 0.5, "y": 0.8}
        ],
        "action": "alert",
        "color": "#ff0000",
        "enabled": true
      },
      {
        "name": "감시 제외 구역",
        "roi_type": "polygon",
        "points": [
          {"x": 0.6, "y": 0.1},
          {"x": 0.9, "y": 0.1},
          {"x": 0.95, "y": 0.5},
          {"x": 0.6, "y": 0.4}
        ],
        "action": "exclude",
        "color": "#0000ff"
      },
      {
        "name": "통과 감지 라인",
        "roi_type": "line",
        "points": [
          {"x": 0.0, "y": 0.5},
          {"x": 1.0, "y": 0.5}
        ],
        "action": "alert",
        "color": "#00ff00"
      }
    ]
  }'
```

#### Preset 관리

```bash
# 전체 Preset 목록 조회
curl http://localhost:8000/api/roi/presets

# 특정 카메라의 Preset 목록
curl "http://localhost:8000/api/roi/presets?camera_id=abc12345"

# Preset 활성화
curl -X POST "http://localhost:8000/api/roi/presets/{preset_id}/activate?camera_id=abc12345"

# Preset에 ROI 추가
curl -X POST http://localhost:8000/api/roi/presets/{preset_id}/rois \
  -H "Content-Type: application/json" \
  -d '{
    "name": "추가 영역",
    "roi_type": "rectangle",
    "points": [{"x": 0.2, "y": 0.2}, {"x": 0.8, "y": 0.8}],
    "action": "include"
  }'

# Preset에서 ROI 제거
curl -X DELETE http://localhost:8000/api/roi/presets/{preset_id}/rois/{roi_id}

# Preset 삭제
curl -X DELETE http://localhost:8000/api/roi/presets/{preset_id}
```

### 4.7 Preset 활용 시나리오

**시나리오 1: 주/야간 전환**

같은 카메라에 대해 주간/야간 Preset을 각각 만들어 시간대에 따라 전환합니다:

```bash
# 주간 Preset 활성화
curl -X POST "http://localhost:8000/api/roi/presets/{day_preset_id}/activate?camera_id=cam1"

# 야간 Preset 활성화
curl -X POST "http://localhost:8000/api/roi/presets/{night_preset_id}/activate?camera_id=cam1"
```

**시나리오 2: 용도별 분리**

하나의 카메라에 대해 "차량 카운팅", "보행자 안전" 등 목적별 Preset을 만들어 필요에 따라 전환합니다.

---

## 5. 실시간 추론 (Real-time Inference)

### 5.1 추론 파이프라인 구조

추론 파이프라인은 다음 단계로 구성됩니다:

```
Camera Frame --> Preprocess --> NPU Inference --> ROI Filter --> Event Check --> Stream Publish
```

1. **Camera Frame**: 카메라에서 최신 프레임을 가져옵니다.
2. **Preprocess**: 모델 입력 크기에 맞게 리사이즈 및 색 공간 변환을 수행합니다.
3. **NPU Inference**: RK3588 NPU에서 추론을 실행합니다.
4. **ROI Filter**: 활성 ROI에 따라 결과를 필터링합니다.
5. **Event Check**: ROI 알림, 라인 크로싱 등 이벤트를 확인합니다.
6. **Stream Publish**: 결과를 MJPEG/WebSocket 클라이언트에 전달합니다.

### 5.2 추론 시작

#### 웹 인터페이스

1. Dashboard에서 카메라를 선택합니다.
2. 추론 패널에서 사용할 모델을 선택합니다.
3. Confidence threshold, NMS threshold 등 파라미터를 조정합니다.
4. **추론 시작** 버튼을 클릭합니다.

#### API

```bash
# 추론 파이프라인 시작
curl -X POST http://localhost:8000/api/inference/start \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": "abc12345",
    "model_id": "def67890",
    "enabled": true,
    "config": {
      "confidence_threshold": 0.5,
      "nms_threshold": 0.45,
      "class_filter": [],
      "max_detections": 100
    }
  }'

# 추론 파이프라인 중지
curl -X POST http://localhost:8000/api/inference/stop/{camera_id}
```

### 5.3 파라미터 실시간 조정

추론 실행 중에도 파라미터를 변경할 수 있습니다:

```bash
curl -X PUT http://localhost:8000/api/inference/config/{camera_id} \
  -H "Content-Type: application/json" \
  -d '{
    "confidence_threshold": 0.7,
    "nms_threshold": 0.5,
    "class_filter": ["person", "car"],
    "max_detections": 50
  }'
```

### 5.4 추론 파라미터 상세

| 파라미터 | 범위 | 기본값 | 설명 |
|----------|------|--------|------|
| `confidence_threshold` | 0.0 ~ 1.0 | 0.5 | 이 값 이상의 confidence를 가진 탐지 결과만 유지 |
| `nms_threshold` | 0.0 ~ 1.0 | 0.45 | Non-Maximum Suppression IoU threshold. 낮을수록 중복 제거가 엄격 |
| `class_filter` | 문자열 배열 | `[]` (전체) | 특정 클래스만 필터링. 빈 배열이면 모든 클래스 포함 |
| `max_detections` | 1 ~ 1000 | 100 | 프레임당 최대 탐지 수 |

### 5.5 추론 상태 및 통계 조회

```bash
# 카메라별 추론 상태
curl http://localhost:8000/api/inference/status/{camera_id}

# 모델별 추론 통계 (avg/min/max latency, FPS 등)
curl "http://localhost:8000/api/inference/stats/{model_id}?camera_id={camera_id}"
```

통계에 포함되는 항목:

| 항목 | 설명 |
|------|------|
| `total_frames` | 총 처리 프레임 수 |
| `avg_inference_ms` | 평균 NPU 추론 시간 (ms) |
| `min_inference_ms` | 최소 추론 시간 |
| `max_inference_ms` | 최대 추론 시간 |
| `avg_fps` | 평균 처리 FPS |
| `avg_objects_per_frame` | 프레임당 평균 탐지 객체 수 |
| `uptime_seconds` | 파이프라인 가동 시간 |

### 5.6 Frame Skip (프레임 건너뛰기)

NPU 추론 속도보다 카메라 FPS가 높은 경우, Frame Skip을 활성화하면 추론하지 않는 프레임은 그대로 스트리밍하고 일정 간격으로만 추론을 수행합니다. 이를 통해 스트림 끊김 없이 안정적인 처리가 가능합니다.

```bash
# Frame skip 활성화 (환경 변수)
export INFERENCE_ENABLE_FRAME_SKIP=true
```

### 5.7 추론 결과 형식

#### Detection 결과 예시

```json
{
  "model_id": "abc123",
  "model_type": "detection",
  "camera_id": "cam1",
  "frame_id": 1542,
  "timestamp": 1706520000.123,
  "inference_time_ms": 12.5,
  "preprocess_time_ms": 1.2,
  "postprocess_time_ms": 0.8,
  "total_time_ms": 14.5,
  "detections": [
    {
      "bbox": {"x1": 120.0, "y1": 80.0, "x2": 350.0, "y2": 400.0},
      "class_name": "person",
      "class_id": 0,
      "confidence": 0.92,
      "track_id": null
    }
  ],
  "object_count": 1,
  "fps": 30.0
}
```

---

## 6. 이벤트 및 알림 (Events & Notifications)

### 6.1 이벤트 유형

| 이벤트 유형 | 설명 | 트리거 조건 |
|-------------|------|-------------|
| **ROI Alert** | ROI 영역 내 객체 감지 | `action: alert`로 설정된 ROI에 객체가 존재할 때 |
| **Line Crossing** | 가상 라인 통과 감지 | 객체의 tracking ID가 라인을 교차할 때 |

### 6.2 ROI Alert 이벤트

ROI의 `action`을 `alert`로 설정하면, 해당 영역에 객체가 감지될 때마다 이벤트가 발생합니다.

이벤트 데이터 구조:

```json
{
  "roi_id": "roi_abc",
  "roi_name": "출입구 영역",
  "camera_id": "cam1",
  "object_count": 3,
  "class_names": ["person", "person", "car"],
  "timestamp": 1706520000.456,
  "snapshot_path": "/data/snapshots/event_12345.jpg"
}
```

### 6.3 Line Crossing 이벤트

`line` 유형 ROI에서 tracking이 활성화된 상태로 객체가 라인을 통과하면 발생합니다.

이벤트 데이터 구조:

```json
{
  "track_id": 15,
  "roi_id": "line_def",
  "roi_name": "통과 감지 라인",
  "direction": "in",
  "timestamp": 1706520001.789,
  "camera_id": "cam1"
}
```

`direction` 값: `"in"` (정방향 통과) 또는 `"out"` (역방향 통과)

### 6.4 이벤트 이력 조회

```bash
# 전체 이벤트 조회
curl http://localhost:8000/api/system/events

# 카메라별 이벤트 조회
curl "http://localhost:8000/api/system/events?camera_id=cam1&limit=50"

# 이벤트 유형별 조회
curl "http://localhost:8000/api/system/events?event_type=roi_alert"

# 이벤트 확인(Acknowledge)
curl -X POST http://localhost:8000/api/system/events/{event_id}/acknowledge
```

### 6.5 MQTT 알림 설정

MQTT를 통해 이벤트를 외부 시스템(Home Assistant, Node-RED 등)으로 전달할 수 있습니다.

```bash
# 환경 변수 설정
export NOTIFY_MQTT_ENABLED=true
export NOTIFY_MQTT_BROKER=192.168.1.50
export NOTIFY_MQTT_PORT=1883
export NOTIFY_MQTT_TOPIC_PREFIX=npu-platform
```

MQTT topic 구조:

```
{topic_prefix}/{event_type}/{camera_id}
```

예시:

```
npu-platform/roi_alert/cam1
npu-platform/line_crossing/cam1
```

> **의존성**: MQTT 사용을 위해 `paho-mqtt` 패키지를 설치해야 합니다:
> ```bash
> pip install paho-mqtt
> ```

### 6.6 Webhook 알림 설정

HTTP POST 방식으로 이벤트를 외부 URL로 전달합니다.

```bash
export NOTIFY_WEBHOOK_ENABLED=true
export NOTIFY_WEBHOOK_URL=https://your-server.com/api/npu-events
export NOTIFY_WEBHOOK_TIMEOUT=10
```

Webhook은 이벤트 발생 시 JSON payload를 POST로 전송합니다:

```json
{
  "id": "evt_12345",
  "event_type": "roi_alert",
  "camera_id": "cam1",
  "timestamp": "2025-01-15T10:30:00",
  "data": {
    "roi_id": "roi_abc",
    "roi_name": "출입구 영역",
    "object_count": 2,
    "class_names": ["person", "person"]
  },
  "snapshot_path": "/data/snapshots/event_12345.jpg",
  "acknowledged": false
}
```

### 6.7 알림 동시 사용

MQTT와 Webhook을 동시에 활성화할 수 있습니다. 두 채널은 비동기(async)로 독립 전송되며, 한 채널의 오류가 다른 채널에 영향을 주지 않습니다.

---

## 7. 시스템 모니터링 (System Monitoring)

### 7.1 모니터링 대시보드

**Monitor** 페이지 (`/monitor`)에서 실시간 시스템 상태를 확인할 수 있습니다. 시스템 모니터는 2초 간격으로 하드웨어 메트릭을 수집합니다.

### 7.2 모니터링 항목

#### CPU 정보

| 항목 | 설명 |
|------|------|
| `usage_percent` | CPU 전체 사용률 (%) |
| `frequency_mhz` | 현재 동작 주파수 (MHz) |
| `core_count` | CPU 코어 수 |
| `per_core_usage` | 코어별 사용률 배열 |

#### NPU 정보

| 항목 | 설명 |
|------|------|
| `usage_percent` | NPU 사용률 (%) |
| `available` | NPU 사용 가능 여부 |
| `core_count` | NPU 코어 수 (RK3588: 3개) |
| `driver_version` | NPU 드라이버 버전 |

#### 메모리 정보

| 항목 | 설명 |
|------|------|
| `total_mb` | 전체 메모리 (MB) |
| `used_mb` | 사용 중 메모리 (MB) |
| `available_mb` | 사용 가능 메모리 (MB) |
| `usage_percent` | 메모리 사용률 (%) |

#### 온도 정보

| 항목 | 설명 |
|------|------|
| `cpu_temp` | CPU 온도 (Celsius) |
| `npu_temp` | NPU 온도 (Celsius) |
| `gpu_temp` | GPU 온도 (Celsius) |

#### 디스크 정보

| 항목 | 설명 |
|------|------|
| `total_gb` | 전체 용량 (GB) |
| `used_gb` | 사용 중 용량 (GB) |
| `free_gb` | 여유 용량 (GB) |
| `usage_percent` | 디스크 사용률 (%) |

#### 네트워크 정보

| 항목 | 설명 |
|------|------|
| `interface` | 네트워크 인터페이스 이름 |
| `ip_address` | IP 주소 |
| `bytes_sent` | 총 송신 바이트 |
| `bytes_recv` | 총 수신 바이트 |

### 7.3 API를 통한 시스템 상태 조회

```bash
# Health check (간단 상태)
curl http://localhost:8000/api/system/health

# 전체 시스템 상태
curl http://localhost:8000/api/system/status

# 시스템 정보 (앱 버전, 설정값 등)
curl http://localhost:8000/api/system/info
```

Health check 응답 예시:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "uptime_seconds": 3600.5,
  "cameras_connected": 3,
  "models_loaded": 1,
  "npu_available": true,
  "timestamp": "2025-01-15T10:30:00"
}
```

### 7.4 로그 확인

```bash
# 최근 로그 조회
curl http://localhost:8000/api/system/logs

# 특정 레벨 로그만 조회
curl "http://localhost:8000/api/system/logs?level=ERROR&limit=50"

# 페이지네이션
curl "http://localhost:8000/api/system/logs?offset=100&limit=50"
```

로그 파일 위치: `data/logs/app.log`

### 7.5 온도 관리 권고사항

RK3588 SoC는 높은 온도에서 자동 throttling이 발생할 수 있습니다:

| 온도 범위 | 상태 | 권고 |
|-----------|------|------|
| 0~60 C | 정상 | 정상 동작 |
| 60~75 C | 주의 | 방열 상태 확인 |
| 75~85 C | 경고 | 팬 속도 확인, 워크로드 축소 고려 |
| 85 C 이상 | 위험 | Thermal throttling 발생, 즉시 냉각 필요 |

---

## 8. 키보드 단축키 (Keyboard Shortcuts)

### 8.1 대시보드 (Dashboard)

| 단축키 | 동작 |
|--------|------|
| `Space` | 추론 시작/중지 토글 |
| `F` | 스트림 뷰어 전체화면 토글 |
| `S` | 현재 프레임 스냅샷 저장 |
| `R` | ROI 편집기 토글 |
| `M` | 모델 선택기 토글 |
| `Esc` | 전체화면/모달 닫기 |

### 8.2 ROI 편집기

| 단축키 | 동작 |
|--------|------|
| `1` | Rectangle 그리기 모드 |
| `2` | Polygon 그리기 모드 |
| `3` | Line 그리기 모드 |
| `Delete` | 선택된 ROI 삭제 |
| `Enter` | Polygon 그리기 완료 |
| `Ctrl+Z` | 마지막 포인트 취소 (Polygon 모드) |
| `Ctrl+A` | 전체 ROI 선택 |

### 8.3 전역 단축키

| 단축키 | 동작 |
|--------|------|
| `Ctrl+1` | Dashboard 페이지로 이동 |
| `Ctrl+2` | Cameras 페이지로 이동 |
| `Ctrl+3` | Models 페이지로 이동 |
| `Ctrl+4` | Monitor 페이지로 이동 |
| `Ctrl+5` | Settings 페이지로 이동 |
| `?` | 단축키 도움말 표시 |

---

## 9. FAQ

### Q1: NPU가 인식되지 않습니다.

**A:** 다음을 확인하세요:

1. NPU 드라이버가 설치되어 있는지 확인합니다:
   ```bash
   ls /dev/dri/
   cat /sys/kernel/debug/rknpu/version
   ```
2. NPU 관련 커널 모듈이 로드되어 있는지 확인합니다:
   ```bash
   dmesg | grep -i rknpu
   ```
3. Rockchip 공식 Ubuntu 이미지를 사용하는지 확인합니다. 일반 Ubuntu 이미지에는 NPU 드라이버가 포함되지 않습니다.

### Q2: 모델 로드 시 "Max loaded models reached" 오류가 발생합니다.

**A:** 기본적으로 최대 3개 모델만 동시에 로드할 수 있습니다. 사용하지 않는 모델을 먼저 언로드하거나, 환경 변수를 조정하세요:

```bash
# 기존 모델 언로드
curl -X POST http://localhost:8000/api/models/{old_model_id}/unload

# 또는 최대 로드 수 증가 (메모리 여유 확인 필요)
export INFERENCE_MAX_LOADED_MODELS=5
```

### Q3: RTSP 카메라 연결이 자주 끊어집니다.

**A:** 다음을 시도하세요:

- RTSP transport를 TCP로 설정: `CAMERA_RTSP_TRANSPORT=tcp`
- 재연결 간격 단축: `CAMERA_RECONNECT_INTERVAL=3`
- 캡처 timeout 증가: `CAMERA_CAPTURE_TIMEOUT_MS=10000`
- 네트워크 상태 및 카메라 펌웨어를 확인합니다.

### Q4: 추론 속도가 기대보다 느립니다.

**A:** 다음을 확인하세요:

1. **NPU 코어**: 모든 코어를 사용하고 있는지 확인합니다 (`INFERENCE_DEFAULT_CORE_MASK=7`).
2. **양자화**: INT8 양자화 모델이 FP16보다 빠릅니다.
3. **입력 크기**: 640x640보다 320x320 모델이 약 4배 빠릅니다.
4. **Frame Skip**: `INFERENCE_ENABLE_FRAME_SKIP=true`로 프레임 건너뛰기를 활성화합니다.
5. **온도**: 고온으로 인한 thermal throttling 여부를 확인합니다.
6. **벤치마크**: `scripts/benchmark.py`로 단독 추론 성능을 측정해 보세요.

### Q5: 웹 인터페이스에 접속이 안 됩니다.

**A:**

1. 서버가 실행 중인지 확인합니다:
   ```bash
   curl http://localhost:8000/api/system/health
   ```
2. 방화벽에서 포트 8000이 열려 있는지 확인합니다:
   ```bash
   sudo ufw allow 8000
   ```
3. 서버가 0.0.0.0에 바인딩되어 있는지 확인합니다 (`SERVER_HOST=0.0.0.0`).

### Q6: Docker에서 NPU를 사용할 수 있나요?

**A:** 가능합니다. `docker-compose.yml`에서 `privileged: true`와 `/dev/dri` 디바이스 마운트가 필요합니다:

```yaml
services:
  npu-platform:
    privileged: true
    devices:
      - /dev/dri:/dev/dri
    volumes:
      - /dev/dri:/dev/dri
```

### Q7: 모델 변환 시 정확도가 떨어집니다.

**A:** INT8 양자화 시 calibration 데이터셋을 제공하면 정확도를 크게 개선할 수 있습니다:

```bash
python scripts/convert_model.py \
  --input model.onnx \
  --output model.rknn \
  --quantize int8 \
  --dataset ./representative_images/
```

calibration 이미지는 실제 운영 환경과 유사한 대표적인 이미지 50장 이상을 권장합니다.

### Q8: WebSocket 스트림에 연결할 수 있는 최대 클라이언트 수는?

**A:** 기본 카메라당 최대 **10개** WebSocket 클라이언트입니다. `STREAM_MAX_WS_CLIENTS` 환경 변수로 조정합니다.

### Q9: 여러 카메라에서 동시에 추론을 실행할 수 있나요?

**A:** 가능합니다. 각 카메라마다 독립적인 추론 파이프라인을 시작할 수 있습니다. 다만, 모든 파이프라인이 같은 NPU를 공유하므로 카메라 수가 늘어나면 개별 FPS가 감소합니다.

### Q10: 설정을 초기화하려면 어떻게 하나요?

**A:** `data/` 디렉토리의 설정 파일을 삭제하고 애플리케이션을 재시작하면 됩니다:

```bash
rm -rf data/config.json data/roi_presets/
# 애플리케이션 재시작
```

---

> **문의사항**이 있으시면 프로젝트 Issues 페이지를 이용해 주세요.
