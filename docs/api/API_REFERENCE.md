# NPU Inference Platform API Reference

> Orange Pi 5 Plus (RK3588) NPU 실시간 추론 플랫폼 API 문서

**Base URL:** `http://<host>:8000`
**API Version:** 1.0.0
**Content-Type:** `application/json` (별도 명시가 없는 경우)

---

## 목차

- [1. Camera API](#1-camera-api)
- [2. Model API](#2-model-api)
- [3. Inference API](#3-inference-api)
- [4. ROI API](#4-roi-api)
- [5. Stream API](#5-stream-api)
- [6. System API](#6-system-api)
- [공통 Error Response 형식](#공통-error-response-형식)
- [인증](#인증)
- [데이터 타입 참조](#데이터-타입-참조)

---

## 공통 Error Response 형식

모든 endpoint는 오류 발생 시 아래 형식의 JSON을 반환합니다.

```json
{
  "detail": "오류 메시지 문자열"
}
```

| Status Code | 설명 |
|-------------|------|
| `400` | Bad Request - 잘못된 요청 파라미터 또는 body |
| `404` | Not Found - 리소스를 찾을 수 없음 |
| `413` | Payload Too Large - 업로드 파일 크기 초과 |
| `422` | Unprocessable Entity - Validation 실패 (Pydantic) |
| `500` | Internal Server Error - 서버 내부 오류 |

---

## 인증

`SECURITY_ENABLE_AUTH=true`로 설정된 경우 API key 인증이 활성화됩니다.

```
Authorization: Bearer <API_KEY>
```

기본 설정에서는 인증이 비활성화되어 있습니다.

---

## 데이터 타입 참조

### CameraType (Enum)

| 값 | 설명 |
|----|------|
| `"rtsp"` | RTSP 네트워크 카메라 |
| `"usb"` | USB 웹캠 |
| `"csi"` | CSI 카메라 모듈 |
| `"file"` | 비디오 파일 입력 |

### CameraStatus (Enum)

| 값 | 설명 |
|----|------|
| `"disconnected"` | 연결 해제됨 |
| `"connecting"` | 연결 시도 중 |
| `"connected"` | 연결됨 |
| `"error"` | 오류 발생 |
| `"stopped"` | 수동 중지됨 |

### ModelType (Enum)

| 값 | 설명 |
|----|------|
| `"detection"` | 객체 탐지 |
| `"segmentation"` | 시맨틱/인스턴스 세그멘테이션 |
| `"pose"` | 포즈 추정 |
| `"classification"` | 이미지 분류 |
| `"face_detection"` | 얼굴 탐지 |
| `"face_recognition"` | 얼굴 인식 |
| `"ocr"` | 광학 문자 인식 |

### ModelStatus (Enum)

| 값 | 설명 |
|----|------|
| `"available"` | 사용 가능 (미로드) |
| `"loading"` | NPU에 로드 중 |
| `"loaded"` | NPU에 로드됨 |
| `"error"` | 오류 발생 |
| `"unloading"` | NPU에서 언로드 중 |

### ROIType (Enum)

| 값 | 설명 |
|----|------|
| `"polygon"` | 다각형 (3개 이상의 점) |
| `"rectangle"` | 사각형 (2개의 점: 좌상단, 우하단) |
| `"line"` | 선 (2개의 점) |

### ROIAction (Enum)

| 값 | 설명 |
|----|------|
| `"include"` | 해당 영역 내부만 처리 |
| `"exclude"` | 해당 영역 내부 탐지 제외 |
| `"alert"` | 진입/존재 시 알림 발생 |

---

## 1. Camera API

카메라 등록, 설정 변경, stream 제어를 위한 API입니다.

**Prefix:** `/api/cameras`

---

### 1.1 GET /api/cameras

등록된 모든 카메라 목록을 조회합니다.

**Request**

파라미터 없음.

**Response**

**Status:** `200 OK`

```json
{
  "cameras": [
    {
      "config": {
        "id": "a1b2c3d4",
        "name": "입구 카메라",
        "url": "rtsp://192.168.1.100:554/stream1",
        "camera_type": "rtsp",
        "enabled": true,
        "reconnect_interval": 5,
        "buffer_size": 1,
        "description": "건물 정문 입구 CCTV",
        "created_at": "2025-01-15T10:30:00",
        "updated_at": "2025-01-15T10:30:00"
      },
      "state": {
        "id": "a1b2c3d4",
        "name": "입구 카메라",
        "status": "connected",
        "fps": 25.0,
        "frame_count": 15420,
        "resolution": "1920x1080",
        "error_message": "",
        "last_frame_time": "2025-01-15T12:00:00",
        "uptime_seconds": 5400.0
      }
    }
  ],
  "total": 1
}
```

---

### 1.2 POST /api/cameras

새 카메라를 등록합니다.

**Request Body**

```json
{
  "name": "주차장 카메라",
  "url": "rtsp://192.168.1.101:554/stream1",
  "camera_type": "rtsp",
  "enabled": true,
  "reconnect_interval": 5,
  "description": "지하 1층 주차장"
}
```

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `name` | `string` | O | - | 카메라 표시 이름 (1~100자) |
| `url` | `string` | O | - | 카메라 URL (RTSP) 또는 device path |
| `camera_type` | `CameraType` | X | `"rtsp"` | 카메라 유형 |
| `enabled` | `boolean` | X | `true` | 생성 시 활성화 여부 |
| `reconnect_interval` | `integer` | X | `5` | 재연결 간격 (초, 1~300) |
| `description` | `string` | X | `null` | 카메라 설명 (최대 500자) |

**Response**

**Status:** `201 Created`

```json
{
  "config": {
    "id": "e5f6g7h8",
    "name": "주차장 카메라",
    "url": "rtsp://192.168.1.101:554/stream1",
    "camera_type": "rtsp",
    "enabled": true,
    "reconnect_interval": 5,
    "buffer_size": 1,
    "description": "지하 1층 주차장",
    "created_at": "2025-01-15T14:00:00",
    "updated_at": "2025-01-15T14:00:00"
  },
  "state": {
    "id": "e5f6g7h8",
    "name": "주차장 카메라",
    "status": "disconnected",
    "fps": 0.0,
    "frame_count": 0,
    "resolution": null,
    "error_message": "",
    "last_frame_time": null,
    "uptime_seconds": 0.0
  }
}
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `400` | 잘못된 파라미터 (예: 빈 URL, 중복 등록) |
| `422` | Validation 실패 (예: `name` 누락, `reconnect_interval` 범위 초과) |

---

### 1.3 GET /api/cameras/{camera_id}

특정 카메라의 상세 정보를 조회합니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `camera_id` | `string` | 카메라 고유 식별자 |

**Response**

**Status:** `200 OK`

```json
{
  "config": {
    "id": "a1b2c3d4",
    "name": "입구 카메라",
    "url": "rtsp://192.168.1.100:554/stream1",
    "camera_type": "rtsp",
    "enabled": true,
    "reconnect_interval": 5,
    "buffer_size": 1,
    "description": "건물 정문 입구 CCTV",
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T10:30:00"
  },
  "state": {
    "id": "a1b2c3d4",
    "name": "입구 카메라",
    "status": "connected",
    "fps": 25.0,
    "frame_count": 15420,
    "resolution": "1920x1080",
    "error_message": "",
    "last_frame_time": "2025-01-15T12:00:00",
    "uptime_seconds": 5400.0
  }
}
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `404` | 해당 `camera_id`에 해당하는 카메라가 없음 |

---

### 1.4 PUT /api/cameras/{camera_id}

카메라 설정을 수정합니다. 변경할 필드만 포함하면 됩니다 (partial update).
`url`이 변경되면 카메라 stream이 자동으로 재시작됩니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `camera_id` | `string` | 카메라 고유 식별자 |

**Request Body**

```json
{
  "name": "입구 카메라 (변경됨)",
  "url": "rtsp://192.168.1.100:554/stream2",
  "reconnect_interval": 10,
  "description": "정문 좌측 카메라"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `name` | `string` | X | 카메라 표시 이름 (1~100자) |
| `url` | `string` | X | 카메라 URL 또는 device path |
| `camera_type` | `CameraType` | X | 카메라 유형 |
| `enabled` | `boolean` | X | 활성화 여부 |
| `reconnect_interval` | `integer` | X | 재연결 간격 (초, 1~300) |
| `description` | `string` | X | 카메라 설명 (최대 500자) |

**Response**

**Status:** `200 OK`

CameraResponse 형식과 동일합니다 (위 1.3 참조).

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `404` | 해당 카메라가 없음 |
| `422` | Validation 실패 |

---

### 1.5 DELETE /api/cameras/{camera_id}

카메라를 제거합니다. 실행 중인 stream은 자동으로 중지됩니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `camera_id` | `string` | 카메라 고유 식별자 |

**Response**

**Status:** `200 OK`

```json
{
  "status": "ok",
  "camera_id": "a1b2c3d4"
}
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `404` | 해당 카메라가 없음 |

---

### 1.6 POST /api/cameras/{camera_id}/start

카메라 stream 캡처를 시작합니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `camera_id` | `string` | 카메라 고유 식별자 |

**Request Body**

없음.

**Response**

**Status:** `200 OK`

```json
{
  "status": "ok",
  "camera_id": "a1b2c3d4"
}
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `404` | 해당 카메라가 없음 |

---

### 1.7 POST /api/cameras/{camera_id}/stop

카메라 stream 캡처를 중지합니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `camera_id` | `string` | 카메라 고유 식별자 |

**Request Body**

없음.

**Response**

**Status:** `200 OK`

```json
{
  "status": "ok",
  "camera_id": "a1b2c3d4"
}
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `404` | 해당 카메라가 없음 |

---

### 1.8 GET /api/cameras/{camera_id}/status

카메라의 현재 runtime 상태를 조회합니다. HTMX polling에 적합합니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `camera_id` | `string` | 카메라 고유 식별자 |

**Response**

**Status:** `200 OK`

```json
{
  "id": "a1b2c3d4",
  "name": "입구 카메라",
  "status": "connected",
  "fps": 25.0,
  "frame_count": 15420,
  "resolution": "1920x1080",
  "error_message": "",
  "last_frame_time": "2025-01-15T12:00:00",
  "uptime_seconds": 5400.0
}
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `404` | 해당 카메라가 없음 |

---

## 2. Model API

RKNN 모델 파일의 업로드, 등록, NPU 로드/언로드, 활성화를 관리하는 API입니다.

**Prefix:** `/api/models`

---

### 2.1 GET /api/models

등록된 모든 모델 목록을 조회합니다. 각 모델의 메타데이터와 runtime 상태를 포함합니다.

**Request**

파라미터 없음.

**Response**

**Status:** `200 OK`

```json
{
  "models": [
    {
      "info": {
        "id": "yolov5s_rk3588",
        "name": "YOLOv5s RK3588",
        "filename": "yolov5s_rk3588.rknn",
        "model_type": "detection",
        "input_size": [640, 640],
        "classes": ["person", "car", "truck", "bus", "bicycle"],
        "num_classes": 80,
        "description": "YOLOv5s COCO pre-trained 모델 (INT8 양자화)",
        "file_size_mb": 15.2,
        "quantization": "int8",
        "created_at": "2025-01-10T09:00:00"
      },
      "state": {
        "id": "yolov5s_rk3588",
        "status": "loaded",
        "is_active": true,
        "load_time_ms": 1250.0,
        "total_inferences": 54320,
        "avg_inference_ms": 12.5,
        "error_message": ""
      }
    }
  ],
  "total": 1,
  "active_model_id": "yolov5s_rk3588"
}
```

---

### 2.2 GET /api/models/{model_id}

특정 모델의 상세 정보를 조회합니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `model_id` | `string` | 모델 고유 식별자 |

**Response**

**Status:** `200 OK`

```json
{
  "info": {
    "id": "yolov5s_rk3588",
    "name": "YOLOv5s RK3588",
    "filename": "yolov5s_rk3588.rknn",
    "model_type": "detection",
    "input_size": [640, 640],
    "classes": ["person", "car", "truck", "bus", "bicycle"],
    "num_classes": 80,
    "description": "YOLOv5s COCO pre-trained 모델",
    "file_size_mb": 15.2,
    "quantization": "int8",
    "created_at": "2025-01-10T09:00:00"
  },
  "state": {
    "id": "yolov5s_rk3588",
    "status": "loaded",
    "is_active": true,
    "load_time_ms": 1250.0,
    "total_inferences": 54320,
    "avg_inference_ms": 12.5,
    "error_message": ""
  }
}
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `404` | 해당 모델이 없음 |

---

### 2.3 POST /api/models/upload

새 RKNN 모델 파일을 업로드합니다. `multipart/form-data` 형식을 사용합니다.

**Request**

`Content-Type: multipart/form-data`

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `file` | `file` | O | - | `.rknn` 모델 파일 |
| `name` | `string` | X | `null` | 모델 표시 이름 (미지정 시 파일명 사용) |
| `model_type` | `ModelType` | X | `"detection"` | 모델 유형 |
| `description` | `string` | X | `null` | 모델 설명 |

**cURL 예시**

```bash
curl -X POST http://localhost:8000/api/models/upload \
  -F "file=@yolov8n_rk3588.rknn" \
  -F "name=YOLOv8n Custom" \
  -F "model_type=detection" \
  -F "description=커스텀 학습된 YOLOv8n 모델"
```

**Response**

**Status:** `201 Created`

```json
{
  "info": {
    "id": "yolov8n_custom",
    "name": "YOLOv8n Custom",
    "filename": "yolov8n_rk3588.rknn",
    "model_type": "detection",
    "input_size": [640, 640],
    "classes": [],
    "num_classes": 0,
    "description": "커스텀 학습된 YOLOv8n 모델",
    "file_size_mb": 12.8,
    "quantization": "int8",
    "created_at": "2025-01-15T15:00:00"
  },
  "state": {
    "id": "yolov8n_custom",
    "status": "available",
    "is_active": false,
    "load_time_ms": 0.0,
    "total_inferences": 0,
    "avg_inference_ms": 0.0,
    "error_message": ""
  }
}
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `400` | `.rknn` 확장자가 아닌 파일 업로드 시도 |
| `413` | 파일 크기 초과 (기본 제한: 500MB) |
| `500` | 파일 저장 또는 처리 중 오류 |

---

### 2.4 POST /api/models/{model_id}/load

모델을 NPU에 로드합니다. 로드된 모델만 추론에 사용할 수 있습니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `model_id` | `string` | 모델 고유 식별자 |

**Request Body**

없음.

**Response**

**Status:** `200 OK`

```json
{
  "status": "ok",
  "model_id": "yolov5s_rk3588",
  "message": "Model loaded"
}
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `404` | 해당 모델이 없음 |
| `500` | NPU 로드 실패 (메모리 부족, 드라이버 오류 등) |

---

### 2.5 POST /api/models/{model_id}/unload

모델을 NPU에서 언로드하여 NPU 메모리를 해제합니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `model_id` | `string` | 모델 고유 식별자 |

**Request Body**

없음.

**Response**

**Status:** `200 OK`

```json
{
  "status": "ok",
  "model_id": "yolov5s_rk3588",
  "message": "Model unloaded"
}
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `500` | 언로드 실패 |

---

### 2.6 POST /api/models/{model_id}/activate

모델을 활성(active) 모델로 설정합니다. NPU에 로드되지 않은 모델은 자동으로 로드됩니다.
한 번에 하나의 모델만 active 상태일 수 있습니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `model_id` | `string` | 모델 고유 식별자 |

**Request Body**

없음.

**Response**

**Status:** `200 OK`

```json
{
  "status": "ok",
  "model_id": "yolov5s_rk3588",
  "message": "Model activated"
}
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `404` | 해당 모델이 없음 |
| `500` | 자동 로드 또는 활성화 실패 |

---

### 2.7 DELETE /api/models/{model_id}

모델을 레지스트리에서 제거합니다. NPU에 로드된 상태인 경우 자동으로 언로드됩니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `model_id` | `string` | 모델 고유 식별자 |

**Query Parameters**

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|----------|------|------|--------|------|
| `delete_file` | `boolean` | X | `false` | `true`이면 디스크의 `.rknn` 파일도 삭제 |

**Request 예시**

```
DELETE /api/models/yolov5s_rk3588?delete_file=true
```

**Response**

**Status:** `200 OK`

```json
{
  "status": "ok",
  "model_id": "yolov5s_rk3588"
}
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `404` | 해당 모델이 없음 |

---

### 2.8 POST /api/models/scan

models 디렉토리를 다시 스캔하여 새로 추가된 `.rknn` 파일을 자동으로 등록합니다.
수동으로 파일을 복사한 경우 이 endpoint를 호출합니다.

**Request Body**

없음.

**Response**

**Status:** `200 OK`

```json
{
  "status": "ok",
  "models_found": 5
}
```

---

## 3. Inference API

추론 pipeline의 시작/중지, 설정 변경, 상태 조회를 위한 API입니다.

**Prefix:** `/api/inference`

---

### 3.1 POST /api/inference/start

특정 카메라에 대한 추론 pipeline을 시작합니다. 지정된 모델이 NPU에 로드되지 않은 경우 자동으로 로드 및 활성화합니다.

**Request Body**

```json
{
  "camera_id": "a1b2c3d4",
  "model_id": "yolov5s_rk3588",
  "enabled": true,
  "config": {
    "confidence_threshold": 0.5,
    "nms_threshold": 0.45,
    "class_filter": [],
    "max_detections": 100
  }
}
```

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `camera_id` | `string` | O | - | 대상 카메라 ID |
| `model_id` | `string` | O | - | 사용할 모델 ID |
| `enabled` | `boolean` | X | `true` | 추론 활성화 여부 |
| `config` | `InferenceConfig` | X | (기본값) | 추론 설정 |

**InferenceConfig 필드**

| 필드 | 타입 | 필수 | 기본값 | 범위 | 설명 |
|------|------|------|--------|------|------|
| `confidence_threshold` | `float` | X | `0.5` | 0.0~1.0 | 신뢰도 임계값 |
| `nms_threshold` | `float` | X | `0.45` | 0.0~1.0 | Non-Maximum Suppression 임계값 |
| `class_filter` | `string[]` | X | `[]` | - | 특정 클래스만 필터링 (빈 배열이면 전체) |
| `max_detections` | `integer` | X | `100` | 1~1000 | 프레임당 최대 탐지 수 |

**Response**

**Status:** `200 OK`

```json
{
  "status": "ok",
  "camera_id": "a1b2c3d4",
  "model_id": "yolov5s_rk3588",
  "message": "Inference started"
}
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `404` | 카메라 또는 모델을 찾을 수 없음 |
| `500` | 모델 로드 실패 |

---

### 3.2 POST /api/inference/stop/{camera_id}

특정 카메라의 추론 pipeline을 중지합니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `camera_id` | `string` | 카메라 고유 식별자 |

**Request Body**

없음.

**Response**

**Status:** `200 OK`

```json
{
  "status": "ok",
  "camera_id": "a1b2c3d4",
  "message": "Inference stopped"
}
```

---

### 3.3 PUT /api/inference/config/{camera_id}

실행 중인 추론 pipeline의 설정을 실시간으로 변경합니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `camera_id` | `string` | 카메라 고유 식별자 |

**Request Body**

```json
{
  "confidence_threshold": 0.6,
  "nms_threshold": 0.5,
  "class_filter": ["person", "car"],
  "max_detections": 50
}
```

모든 필드에 대한 설명은 [3.1 InferenceConfig 필드](#31-post-apiinferencestart)를 참조하세요.

**Response**

**Status:** `200 OK`

```json
{
  "status": "ok",
  "camera_id": "a1b2c3d4",
  "message": "Config updated"
}
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `400` | 해당 카메라에 대해 실행 중인 pipeline이 없음 |
| `422` | Validation 실패 |

---

### 3.4 GET /api/inference/status/{camera_id}

특정 카메라의 추론 상태를 조회합니다. pipeline 실행 여부, 사용 중인 모델, 설정, 통계를 포함합니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `camera_id` | `string` | 카메라 고유 식별자 |

**Response**

**Status:** `200 OK`

```json
{
  "camera_id": "a1b2c3d4",
  "running": true,
  "model_id": "yolov5s_rk3588",
  "config": {
    "confidence_threshold": 0.5,
    "nms_threshold": 0.45,
    "class_filter": [],
    "max_detections": 100
  },
  "stats": {
    "model_id": "yolov5s_rk3588",
    "camera_id": "a1b2c3d4",
    "total_frames": 12500,
    "avg_inference_ms": 12.5,
    "min_inference_ms": 8.2,
    "max_inference_ms": 45.0,
    "avg_fps": 28.5,
    "avg_objects_per_frame": 3.2,
    "uptime_seconds": 450.0
  }
}
```

Pipeline이 실행 중이지 않은 경우:

```json
{
  "camera_id": "a1b2c3d4",
  "running": false,
  "model_id": null,
  "config": null
}
```

---

### 3.5 GET /api/inference/stats/{model_id}

특정 모델의 추론 성능 통계를 조회합니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `model_id` | `string` | 모델 고유 식별자 |

**Query Parameters**

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|----------|------|------|--------|------|
| `camera_id` | `string` | X | `""` | 특정 카메라에 대한 통계만 조회 |

**Response**

**Status:** `200 OK`

```json
{
  "model_id": "yolov5s_rk3588",
  "camera_id": "a1b2c3d4",
  "total_frames": 54320,
  "avg_inference_ms": 12.5,
  "min_inference_ms": 8.2,
  "max_inference_ms": 45.0,
  "avg_fps": 28.5,
  "avg_objects_per_frame": 3.2,
  "uptime_seconds": 1800.0
}
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `404` | 해당 모델에 대한 통계가 없음 |

---

## 4. ROI API

관심 영역(Region of Interest) preset 및 개별 ROI를 관리하는 API입니다.
좌표는 0.0~1.0 범위의 정규화된 값을 사용합니다.

**Prefix:** `/api/roi`

---

### 4.1 GET /api/roi/presets

ROI preset 목록을 조회합니다. 카메라별 필터링을 지원합니다.

**Query Parameters**

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|----------|------|------|--------|------|
| `camera_id` | `string` | X | `""` | 특정 카메라의 preset만 조회 |

**Response**

**Status:** `200 OK`

```json
{
  "presets": [
    {
      "id": "preset_001",
      "camera_id": "a1b2c3d4",
      "name": "입구 감시 영역",
      "rois": [
        {
          "id": "roi_001",
          "name": "출입문 영역",
          "roi_type": "polygon",
          "points": [
            {"x": 0.1, "y": 0.2},
            {"x": 0.5, "y": 0.2},
            {"x": 0.5, "y": 0.8},
            {"x": 0.1, "y": 0.8}
          ],
          "action": "alert",
          "color": "#ff0000",
          "enabled": true,
          "created_at": "2025-01-15T10:00:00"
        },
        {
          "id": "roi_002",
          "name": "제외 영역",
          "roi_type": "rectangle",
          "points": [
            {"x": 0.7, "y": 0.0},
            {"x": 1.0, "y": 0.3}
          ],
          "action": "exclude",
          "color": "#888888",
          "enabled": true,
          "created_at": "2025-01-15T10:05:00"
        }
      ],
      "is_active": true,
      "created_at": "2025-01-15T10:00:00",
      "updated_at": "2025-01-15T10:05:00"
    }
  ],
  "total": 1
}
```

---

### 4.2 POST /api/roi/presets

새 ROI preset을 생성합니다. 생성 시 ROI를 함께 포함할 수 있습니다.

**Request Body**

```json
{
  "camera_id": "a1b2c3d4",
  "name": "야간 감시 영역",
  "rois": [
    {
      "name": "주요 감시 구역",
      "roi_type": "polygon",
      "points": [
        {"x": 0.0, "y": 0.3},
        {"x": 0.6, "y": 0.3},
        {"x": 0.6, "y": 1.0},
        {"x": 0.0, "y": 1.0}
      ],
      "action": "include",
      "color": "#00ff00",
      "enabled": true
    }
  ]
}
```

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `camera_id` | `string` | O | - | 연결할 카메라 ID |
| `name` | `string` | O | - | Preset 이름 (1~100자) |
| `rois` | `ROICreate[]` | X | `[]` | 초기 ROI 목록 |

**ROICreate 필드**

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `name` | `string` | O | - | ROI 표시 이름 (1~100자) |
| `roi_type` | `ROIType` | O | - | ROI 형상 타입 |
| `points` | `Point[]` | O | - | 정규화된 좌표 목록 (0.0~1.0) |
| `action` | `ROIAction` | X | `"include"` | ROI 동작 유형 |
| `color` | `string` | X | `"#00ff00"` | 표시 색상 (HEX) |
| `enabled` | `boolean` | X | `true` | ROI 활성화 여부 |

**Point 형식**

```json
{"x": 0.0, "y": 0.0}
```

`x`와 `y`는 각각 0.0~1.0 범위의 정규화된 좌표입니다 (이미지 좌상단이 원점).

**points 개수 제약**

| `roi_type` | 필요한 점 개수 |
|------------|---------------|
| `"line"` | 정확히 2개 |
| `"rectangle"` | 정확히 2개 (좌상단, 우하단) |
| `"polygon"` | 3개 이상 |

**Response**

**Status:** `201 Created`

```json
{
  "preset": {
    "id": "preset_002",
    "camera_id": "a1b2c3d4",
    "name": "야간 감시 영역",
    "rois": [
      {
        "id": "roi_003",
        "name": "주요 감시 구역",
        "roi_type": "polygon",
        "points": [
          {"x": 0.0, "y": 0.3},
          {"x": 0.6, "y": 0.3},
          {"x": 0.6, "y": 1.0},
          {"x": 0.0, "y": 1.0}
        ],
        "action": "include",
        "color": "#00ff00",
        "enabled": true,
        "created_at": "2025-01-15T16:00:00"
      }
    ],
    "is_active": false,
    "created_at": "2025-01-15T16:00:00",
    "updated_at": "2025-01-15T16:00:00"
  },
  "camera_id": "a1b2c3d4"
}
```

---

### 4.3 GET /api/roi/presets/{preset_id}

특정 ROI preset의 상세 정보를 조회합니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `preset_id` | `string` | Preset 고유 식별자 |

**Response**

**Status:** `200 OK`

```json
{
  "preset": {
    "id": "preset_001",
    "camera_id": "a1b2c3d4",
    "name": "입구 감시 영역",
    "rois": [ ... ],
    "is_active": true,
    "created_at": "2025-01-15T10:00:00",
    "updated_at": "2025-01-15T10:05:00"
  },
  "camera_id": "a1b2c3d4"
}
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `404` | 해당 preset이 없음 |

---

### 4.4 DELETE /api/roi/presets/{preset_id}

ROI preset을 삭제합니다. 포함된 모든 ROI도 함께 삭제됩니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `preset_id` | `string` | Preset 고유 식별자 |

**Response**

**Status:** `200 OK`

```json
{
  "status": "ok",
  "preset_id": "preset_001"
}
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `404` | 해당 preset이 없음 |

---

### 4.5 POST /api/roi/presets/{preset_id}/activate

특정 카메라에 대해 preset을 활성화합니다. 카메라당 하나의 preset만 활성 상태일 수 있습니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `preset_id` | `string` | Preset 고유 식별자 |

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `camera_id` | `string` | O | 대상 카메라 ID |

**Request 예시**

```
POST /api/roi/presets/preset_001/activate?camera_id=a1b2c3d4
```

**Response**

**Status:** `200 OK`

```json
{
  "status": "ok",
  "preset_id": "preset_001",
  "camera_id": "a1b2c3d4"
}
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `400` | 유효하지 않은 preset이거나 카메라 불일치 |

---

### 4.6 POST /api/roi/presets/{preset_id}/rois

기존 preset에 새 ROI를 추가합니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `preset_id` | `string` | Preset 고유 식별자 |

**Request Body**

```json
{
  "name": "계단 감지선",
  "roi_type": "line",
  "points": [
    {"x": 0.3, "y": 0.5},
    {"x": 0.8, "y": 0.5}
  ],
  "action": "alert",
  "color": "#ffff00",
  "enabled": true
}
```

필드에 대한 상세 설명은 [4.2 ROICreate 필드](#42-post-apiroipresets)를 참조하세요.

**Response**

**Status:** `200 OK`

```json
{
  "status": "ok",
  "roi": {
    "id": "roi_004",
    "name": "계단 감지선",
    "roi_type": "line",
    "points": [
      {"x": 0.3, "y": 0.5},
      {"x": 0.8, "y": 0.5}
    ],
    "action": "alert",
    "color": "#ffff00",
    "enabled": true,
    "created_at": "2025-01-15T16:30:00"
  }
}
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `404` | 해당 preset이 없음 |
| `422` | ROI validation 실패 (점 개수 불일치 등) |

---

### 4.7 DELETE /api/roi/presets/{preset_id}/rois/{roi_id}

Preset에서 특정 ROI를 제거합니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `preset_id` | `string` | Preset 고유 식별자 |
| `roi_id` | `string` | ROI 고유 식별자 |

**Response**

**Status:** `200 OK`

```json
{
  "status": "ok",
  "roi_id": "roi_004"
}
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `404` | Preset 또는 ROI를 찾을 수 없음 |

---

## 5. Stream API

실시간 비디오 스트리밍을 위한 API입니다. MJPEG, WebSocket, Snapshot 방식을 지원합니다.

**Prefix:** `/api/stream`

---

### 5.1 GET /api/stream/{camera_id}/mjpeg

MJPEG(Motion JPEG) 형식의 연속 비디오 스트림을 제공합니다.
`<img>` 태그의 `src` 속성에 직접 사용할 수 있습니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `camera_id` | `string` | 카메라 고유 식별자 |

**Response**

**Content-Type:** `multipart/x-mixed-replace; boundary=frame`

**Status:** `200 OK`

연속적인 JPEG 프레임이 multipart boundary로 구분되어 전송됩니다.

```
--frame
Content-Type: image/jpeg

<JPEG binary data>
--frame
Content-Type: image/jpeg

<JPEG binary data>
...
```

**Response Headers**

| Header | 값 |
|--------|-----|
| `Content-Type` | `multipart/x-mixed-replace; boundary=frame` |
| `Cache-Control` | `no-cache, no-store, must-revalidate` |
| `Pragma` | `no-cache` |
| `Expires` | `0` |
| `Connection` | `keep-alive` |

**HTML 사용 예시**

```html
<img src="/api/stream/a1b2c3d4/mjpeg" alt="Camera Stream" />
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `404` | 해당 카메라가 없음 |

**참고 사항**

- 10초 동안 새 프레임이 없으면 keep-alive 프레임이 전송됩니다.
- 클라이언트 연결이 끊기면 자동으로 정리됩니다.

---

### 5.2 WebSocket /api/stream/{camera_id}/ws

WebSocket을 통한 실시간 비디오 스트림과 추론 메타데이터를 제공합니다.
양방향 통신을 지원하며, 클라이언트에서 명령을 보낼 수 있습니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `camera_id` | `string` | 카메라 고유 식별자 |

**Connection URL**

```
ws://<host>:8000/api/stream/{camera_id}/ws
```

**서버 -> 클라이언트 메시지 형식**

프레임 데이터 (binary):
```
<JPEG binary frame data>
```

추론 결과 (JSON):
```json
{
  "type": "inference_result",
  "data": {
    "model_id": "yolov5s_rk3588",
    "model_type": "detection",
    "camera_id": "a1b2c3d4",
    "frame_id": 1234,
    "timestamp": 1705312800.0,
    "inference_time_ms": 12.5,
    "detections": [
      {
        "bbox": {"x1": 100.0, "y1": 200.0, "x2": 300.0, "y2": 400.0},
        "class_name": "person",
        "class_id": 0,
        "confidence": 0.92,
        "track_id": 5
      }
    ],
    "object_count": 1,
    "fps": 28.5
  }
}
```

Heartbeat (30초 간격):
```json
{
  "type": "heartbeat"
}
```

**클라이언트 -> 서버 메시지 형식**

Ping:
```json
{
  "type": "ping"
}
```

서버 응답:
```json
{
  "type": "pong"
}
```

**Error Close Codes**

| Code | 설명 |
|------|------|
| `4004` | 카메라를 찾을 수 없음 |

**JavaScript 사용 예시**

```javascript
const ws = new WebSocket('ws://localhost:8000/api/stream/a1b2c3d4/ws');

ws.onmessage = (event) => {
  if (typeof event.data === 'string') {
    const msg = JSON.parse(event.data);
    if (msg.type === 'inference_result') {
      console.log('탐지 결과:', msg.data.detections);
    }
  } else {
    // Binary frame data
    const blob = new Blob([event.data], { type: 'image/jpeg' });
    const url = URL.createObjectURL(blob);
    document.getElementById('stream-img').src = url;
  }
};

// Keep-alive ping
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ping' }));
  }
}, 25000);
```

---

### 5.3 GET /api/stream/{camera_id}/snapshot

카메라의 현재 프레임을 단일 JPEG 이미지로 반환합니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `camera_id` | `string` | 카메라 고유 식별자 |

**Query Parameters**

| 파라미터 | 타입 | 필수 | 기본값 | 범위 | 설명 |
|----------|------|------|--------|------|------|
| `quality` | `integer` | X | `90` | 1~100 | JPEG 압축 품질 |

**Request 예시**

```
GET /api/stream/a1b2c3d4/snapshot?quality=85
```

**Response**

**Status:** `200 OK`
**Content-Type:** `image/jpeg`
**Content-Disposition:** `inline; filename=snapshot_a1b2c3d4.jpg`

Response body는 JPEG 이미지 바이너리 데이터입니다.

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `404` | 사용 가능한 프레임이 없음 (카메라 미연결 또는 미시작) |

---

### 5.4 GET /api/stream/{camera_id}/preview

카메라의 저해상도 미리보기 thumbnail을 반환합니다.
기본 스케일은 0.5배입니다 (설정에서 변경 가능).

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `camera_id` | `string` | 카메라 고유 식별자 |

**Response**

**Status:** `200 OK`
**Content-Type:** `image/jpeg`

Response body는 축소된 JPEG 이미지 바이너리 데이터입니다.

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `404` | 사용 가능한 프레임이 없음 |

---

## 6. System API

시스템 모니터링, 헬스 체크, 이벤트 기록, 로그 조회를 위한 API입니다.

**Prefix:** `/api/system`

---

### 6.1 GET /api/system/health

애플리케이션의 전반적인 상태를 확인합니다. 로드 밸런서 또는 모니터링 시스템의 헬스 체크에 적합합니다.

**Request**

파라미터 없음.

**Response**

**Status:** `200 OK`

```json
{
  "status": "ok",
  "version": "1.0.0",
  "uptime_seconds": 86400.0,
  "cameras_connected": 3,
  "models_loaded": 2,
  "npu_available": true,
  "timestamp": "2025-01-15T12:00:00"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `status` | `string` | 애플리케이션 상태 (`"ok"`) |
| `version` | `string` | 애플리케이션 버전 |
| `uptime_seconds` | `float` | 서비스 가동 시간 (초) |
| `cameras_connected` | `integer` | 연결된 카메라 수 |
| `models_loaded` | `integer` | NPU에 로드된 모델 수 |
| `npu_available` | `boolean` | NPU 사용 가능 여부 |
| `timestamp` | `datetime` | 응답 시각 |

---

### 6.2 GET /api/system/status

CPU, NPU, 메모리, 온도, 디스크, 네트워크를 포함하는 상세 시스템 상태를 반환합니다.

**Request**

파라미터 없음.

**Response**

**Status:** `200 OK`

```json
{
  "cpu": {
    "usage_percent": 35.2,
    "frequency_mhz": 1800.0,
    "core_count": 8,
    "per_core_usage": [42.0, 38.0, 30.0, 28.0, 35.0, 40.0, 32.0, 37.0]
  },
  "npu": {
    "usage_percent": 65.0,
    "available": true,
    "core_count": 3,
    "driver_version": "0.9.6"
  },
  "memory": {
    "total_mb": 16384.0,
    "used_mb": 4520.0,
    "available_mb": 11864.0,
    "usage_percent": 27.6
  },
  "temperature": {
    "cpu_temp": 52.0,
    "npu_temp": 48.0,
    "gpu_temp": 45.0
  },
  "disk": {
    "total_gb": 256.0,
    "used_gb": 85.0,
    "free_gb": 171.0,
    "usage_percent": 33.2
  },
  "network": [
    {
      "interface": "eth0",
      "ip_address": "192.168.1.50",
      "bytes_sent": 1048576000,
      "bytes_recv": 5242880000
    }
  ],
  "uptime_seconds": 86400.0,
  "timestamp": "2025-01-15T12:00:00"
}
```

**Response 필드 상세**

**CPUInfo**

| 필드 | 타입 | 설명 |
|------|------|------|
| `usage_percent` | `float` | CPU 전체 사용률 (%) |
| `frequency_mhz` | `float` | 현재 클럭 주파수 (MHz) |
| `core_count` | `integer` | CPU 코어 수 |
| `per_core_usage` | `float[]` | 코어별 사용률 (%) |

**NPUInfo**

| 필드 | 타입 | 설명 |
|------|------|------|
| `usage_percent` | `float` | NPU 사용률 (%) |
| `available` | `boolean` | NPU 사용 가능 여부 |
| `core_count` | `integer` | NPU 코어 수 (RK3588: 3개) |
| `driver_version` | `string` | NPU 드라이버 버전 |

**MemoryInfo**

| 필드 | 타입 | 설명 |
|------|------|------|
| `total_mb` | `float` | 총 메모리 (MB) |
| `used_mb` | `float` | 사용 중 메모리 (MB) |
| `available_mb` | `float` | 가용 메모리 (MB) |
| `usage_percent` | `float` | 메모리 사용률 (%) |

**TemperatureInfo**

| 필드 | 타입 | 설명 |
|------|------|------|
| `cpu_temp` | `float` | CPU 온도 (Celsius) |
| `npu_temp` | `float` | NPU 온도 (Celsius) |
| `gpu_temp` | `float` | GPU 온도 (Celsius) |

**DiskInfo**

| 필드 | 타입 | 설명 |
|------|------|------|
| `total_gb` | `float` | 총 디스크 용량 (GB) |
| `used_gb` | `float` | 사용된 용량 (GB) |
| `free_gb` | `float` | 남은 용량 (GB) |
| `usage_percent` | `float` | 디스크 사용률 (%) |

**NetworkInfo**

| 필드 | 타입 | 설명 |
|------|------|------|
| `interface` | `string` | 네트워크 인터페이스 이름 |
| `ip_address` | `string` | IP 주소 |
| `bytes_sent` | `integer` | 전송된 바이트 수 |
| `bytes_recv` | `integer` | 수신된 바이트 수 |

---

### 6.3 GET /api/system/events

이벤트 기록을 조회합니다. 카메라별, 이벤트 유형별 필터링을 지원합니다.

**Query Parameters**

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|----------|------|------|--------|------|
| `camera_id` | `string` | X | `""` | 특정 카메라의 이벤트만 조회 |
| `event_type` | `string` | X | `""` | 특정 이벤트 유형만 조회 |
| `limit` | `integer` | X | `50` | 최대 반환 개수 |

**Response**

**Status:** `200 OK`

```json
{
  "events": [
    {
      "id": "evt_001",
      "event_type": "roi_alert",
      "camera_id": "a1b2c3d4",
      "timestamp": "2025-01-15T11:45:00",
      "data": {
        "roi_id": "roi_001",
        "roi_name": "출입문 영역",
        "object_count": 2,
        "class_names": ["person", "person"]
      },
      "snapshot_path": "/data/snapshots/evt_001.jpg",
      "acknowledged": false
    },
    {
      "id": "evt_002",
      "event_type": "line_crossing",
      "camera_id": "a1b2c3d4",
      "timestamp": "2025-01-15T11:30:00",
      "data": {
        "track_id": 5,
        "roi_id": "roi_004",
        "roi_name": "계단 감지선",
        "direction": "in"
      },
      "snapshot_path": null,
      "acknowledged": true
    }
  ],
  "total": 2
}
```

---

### 6.4 POST /api/system/events/{event_id}/acknowledge

이벤트를 확인 처리합니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `event_id` | `string` | 이벤트 고유 식별자 |

**Request Body**

없음.

**Response**

**Status:** `200 OK`

```json
{
  "status": "ok",
  "event_id": "evt_001"
}
```

**Error Responses**

| Status Code | 조건 |
|-------------|------|
| `404` | 해당 이벤트가 없음 |

---

### 6.5 GET /api/system/logs

애플리케이션 로그를 조회합니다. 최신 로그부터 역순으로 반환됩니다.

**Query Parameters**

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|----------|------|------|--------|------|
| `level` | `string` | X | `""` | 로그 레벨 필터 (예: `"INFO"`, `"ERROR"`, `"WARNING"`) |
| `limit` | `integer` | X | `100` | 최대 반환 개수 |
| `offset` | `integer` | X | `0` | 페이지네이션 시작 위치 |

**Response**

**Status:** `200 OK`

```json
{
  "entries": [
    {
      "timestamp": "2025-01-15T12:00:00",
      "level": "INFO",
      "logger": "app.core.camera_manager",
      "message": "Camera a1b2c3d4 connected successfully"
    },
    {
      "timestamp": "2025-01-15T11:59:55",
      "level": "WARNING",
      "logger": "app.core.inference_engine",
      "message": "Inference queue full, skipping frame"
    },
    {
      "timestamp": "2025-01-15T11:59:50",
      "level": "ERROR",
      "logger": "app.services.rknn_service",
      "message": "NPU runtime error: insufficient memory"
    }
  ],
  "total": 3,
  "has_more": false
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `entries` | `LogEntry[]` | 로그 항목 목록 |
| `total` | `integer` | 필터 조건에 맞는 전체 항목 수 |
| `has_more` | `boolean` | 추가 항목 존재 여부 (페이지네이션) |

**LogEntry**

| 필드 | 타입 | 설명 |
|------|------|------|
| `timestamp` | `datetime` | 로그 발생 시각 |
| `level` | `string` | 로그 레벨 (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `logger` | `string` | Logger 이름 (모듈 경로) |
| `message` | `string` | 로그 메시지 |

---

### 6.6 GET /api/system/info

애플리케이션 및 시스템 기본 정보를 반환합니다.

**Request**

파라미터 없음.

**Response**

**Status:** `200 OK`

```json
{
  "app_name": "NPU Inference Platform",
  "app_version": "1.0.0",
  "debug": false,
  "max_cameras": 8,
  "max_loaded_models": 3,
  "npu_core_mask": 7
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `app_name` | `string` | 애플리케이션 이름 |
| `app_version` | `string` | 애플리케이션 버전 |
| `debug` | `boolean` | 디버그 모드 활성화 여부 |
| `max_cameras` | `integer` | 최대 동시 카메라 수 |
| `max_loaded_models` | `integer` | 최대 동시 로드 모델 수 |
| `npu_core_mask` | `integer` | NPU 코어 마스크 (7 = 3코어 전부 사용) |

---

## 부록

### A. NPU Core Mask 설명

RK3588 NPU는 3개의 코어를 가지며, 비트마스크로 사용할 코어를 지정합니다.

| Mask 값 | 이진수 | 사용 코어 | 설명 |
|---------|--------|-----------|------|
| `1` | `001` | Core 0 | 단일 코어 |
| `2` | `010` | Core 1 | 단일 코어 |
| `4` | `100` | Core 2 | 단일 코어 |
| `3` | `011` | Core 0+1 | 듀얼 코어 |
| `5` | `101` | Core 0+2 | 듀얼 코어 |
| `6` | `110` | Core 1+2 | 듀얼 코어 |
| `7` | `111` | Core 0+1+2 | 트리플 코어 (기본값, 최대 성능) |

### B. 환경 변수 설정

주요 환경 변수 목록입니다. `.env` 파일 또는 시스템 환경 변수로 설정할 수 있습니다.

| 환경 변수 | 기본값 | 설명 |
|-----------|--------|------|
| `APP_NAME` | `NPU Inference Platform` | 애플리케이션 이름 |
| `APP_VERSION` | `1.0.0` | 애플리케이션 버전 |
| `APP_DEBUG` | `false` | 디버그 모드 |
| `SERVER_HOST` | `0.0.0.0` | 바인딩 주소 |
| `SERVER_PORT` | `8000` | 서버 포트 |
| `SERVER_LOG_LEVEL` | `info` | 로깅 레벨 |
| `CAMERA_MAX_CAMERAS` | `8` | 최대 카메라 수 |
| `CAMERA_RECONNECT_INTERVAL` | `5` | 재연결 간격 (초) |
| `CAMERA_RTSP_TRANSPORT` | `tcp` | RTSP 전송 프로토콜 |
| `INFERENCE_DEFAULT_CONFIDENCE` | `0.5` | 기본 신뢰도 임계값 |
| `INFERENCE_DEFAULT_NMS_THRESHOLD` | `0.45` | 기본 NMS 임계값 |
| `INFERENCE_DEFAULT_CORE_MASK` | `7` | 기본 NPU 코어 마스크 |
| `INFERENCE_MAX_LOADED_MODELS` | `3` | 최대 동시 로드 모델 수 |
| `STREAM_MJPEG_QUALITY` | `80` | MJPEG 품질 (1~100) |
| `STREAM_MAX_WS_CLIENTS` | `10` | Stream당 최대 WebSocket 클라이언트 |
| `SECURITY_ENABLE_AUTH` | `false` | 인증 활성화 |
| `SECURITY_API_KEY` | `null` | API Key |
| `SECURITY_MAX_UPLOAD_SIZE_MB` | `500` | 최대 업로드 크기 (MB) |
| `NOTIFY_MQTT_ENABLED` | `false` | MQTT 알림 활성화 |
| `NOTIFY_WEBHOOK_ENABLED` | `false` | Webhook 알림 활성화 |

### C. Swagger / OpenAPI 문서

디버그 모드 (`APP_DEBUG=true`) 에서 아래 경로로 자동 생성된 API 문서에 접근할 수 있습니다.

- **Swagger UI:** `http://<host>:8000/api/docs`
- **ReDoc:** `http://<host>:8000/api/redoc`

프로덕션 환경에서는 보안을 위해 비활성화됩니다.
