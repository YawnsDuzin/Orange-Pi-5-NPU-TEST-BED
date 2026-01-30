# NPU Inference Platform 배포 가이드

> **Orange Pi 5 Plus (RK3588) NPU 실시간 추론 테스트 플랫폼**
>
> 버전: 1.1.0

---

## 목차

1. [하드웨어 요구사항 (Hardware Requirements)](#1-하드웨어-요구사항-hardware-requirements)
2. [OS 설정 (OS Setup)](#2-os-설정-os-setup)
3. [NPU 드라이버 설치 (NPU Driver Installation)](#3-npu-드라이버-설치-npu-driver-installation)
4. [RKNN Toolkit2 설치 (RKNN Installation)](#4-rknn-toolkit2-설치-rknn-installation)
5. [애플리케이션 설치 (Application Installation)](#5-애플리케이션-설치-application-installation)
6. [서비스 등록 (Systemd Service Setup)](#6-서비스-등록-systemd-service-setup)
7. [리버스 프록시 (Nginx Reverse Proxy)](#7-리버스-프록시-nginx-reverse-proxy)
8. [Docker 배포 (Docker Deployment)](#8-docker-배포-docker-deployment)
9. [환경 변수 설정 (Environment Configuration)](#9-환경-변수-설정-environment-configuration)
10. [성능 튜닝 (Performance Tuning)](#10-성능-튜닝-performance-tuning)
11. [모니터링 (Production Monitoring)](#11-모니터링-production-monitoring)
12. [백업 및 복구 (Backup and Recovery)](#12-백업-및-복구-backup-and-recovery)
13. [보안 권고사항 (Security Recommendations)](#13-보안-권고사항-security-recommendations)
14. [문제 해결 (Troubleshooting)](#14-문제-해결-troubleshooting)
15. [Windows 개발 환경 (Development on Windows)](#15-windows-개발-환경-development-on-windows)

---

## 1. 하드웨어 요구사항 (Hardware Requirements)

### 1.1 권장 하드웨어

| 항목 | 최소 사양 | 권장 사양 |
|------|-----------|-----------|
| **보드** | Orange Pi 5 (RK3588S) | Orange Pi 5 Plus (RK3588) |
| **SoC** | RK3588S | RK3588 |
| **CPU** | 4x Cortex-A76 + 4x Cortex-A55 | 4x Cortex-A76 + 4x Cortex-A55 |
| **NPU** | 6 TOPS (3 코어) | 6 TOPS (3 코어) |
| **RAM** | 8GB LPDDR4x | 16GB LPDDR4x |
| **저장소** | 32GB eMMC/SD | 64GB+ eMMC + NVMe SSD |
| **네트워크** | 1x Gigabit Ethernet | 2x Gigabit Ethernet |
| **전원** | 5V/4A USB-C | 5V/4A USB-C (공식 어댑터 사용) |

### 1.2 NPU 사양 (RK3588)

- **NPU 코어**: 3개 (독립 또는 결합 운용 가능)
- **연산 성능**: 6 TOPS (INT8)
- **지원 정밀도**: INT4, INT8, INT16, FP16, BF16
- **지원 프레임워크**: TensorFlow, PyTorch, ONNX, Caffe 등 (RKNN 변환 필요)

### 1.3 추가 하드웨어

| 항목 | 필수 여부 | 설명 |
|------|-----------|------|
| **방열판/쿨러** | 필수 | NPU 지속 사용 시 발열 관리 필수 |
| **5V/4A 전원 어댑터** | 필수 | 공식 어댑터 사용 권장 |
| **eMMC 모듈** | 권장 | SD 카드보다 I/O 성능 우수 |
| **NVMe SSD** | 선택 | 대용량 영상/모델 저장용 |
| **USB 카메라** | 선택 | USB 웹캠 테스트용 |
| **CSI 카메라 모듈** | 선택 | MIPI CSI 인터페이스 카메라 |
| **케이스** | 권장 | 먼지 방지 및 방열 효율 향상 |

---

## 2. OS 설정 (OS Setup)

### 2.1 지원 OS

| OS | 버전 | 상태 |
|----|------|------|
| **Ubuntu Server** | 22.04 LTS (Jammy Jellyfish) | 권장 |
| **Debian** | 11/12 (Bullseye/Bookworm) | 지원 |
| **Orange Pi OS** | Droid/Arch | 지원 (NPU 드라이버 포함) |

> **중요**: Rockchip 공식 BSP (Board Support Package)가 포함된 이미지를 사용해야 합니다. 일반 ARM64 Ubuntu 이미지에는 NPU 드라이버가 포함되지 않습니다.

### 2.2 OS 이미지 다운로드 및 설치

1. Orange Pi 공식 사이트에서 Ubuntu 22.04 이미지를 다운로드합니다:
   ```
   http://www.orangepi.org/html/hardWare/computerAndMicrocontrollers/service-and-support/Orange-Pi-5-Plus.html
   ```

2. 이미지를 SD 카드 또는 eMMC에 플래싱합니다:
   ```bash
   # Linux/macOS에서 SD 카드 플래싱
   sudo dd if=OrangePi5Plus_ubuntu_jammy_server.img of=/dev/sdX bs=4M status=progress
   sync
   ```

3. 처음 부팅 후 기본 설정을 완료합니다:
   ```bash
   # 시스템 업데이트
   sudo apt update && sudo apt upgrade -y

   # 시간대 설정
   sudo timedatectl set-timezone Asia/Seoul

   # 호스트네임 설정
   sudo hostnamectl set-hostname npu-platform

   # SSH 활성화 (원격 접속용)
   sudo systemctl enable ssh
   sudo systemctl start ssh
   ```

### 2.3 필수 시스템 패키지 설치

```bash
sudo apt install -y \
  python3 \
  python3-pip \
  python3-venv \
  python3-dev \
  build-essential \
  cmake \
  git \
  wget \
  curl \
  libgl1-mesa-glx \
  libglib2.0-0 \
  libsm6 \
  libxrender1 \
  libxext6 \
  v4l-utils \
  ffmpeg \
  htop \
  iotop \
  net-tools
```

### 2.4 네트워크 설정

```bash
# 고정 IP 설정 (netplan 사용)
sudo nano /etc/netplan/01-netcfg.yaml
```

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:
      dhcp4: no
      addresses:
        - 192.168.1.100/24
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

```bash
sudo netplan apply
```

### 2.5 Swap 설정

메모리 부족 방지를 위한 swap 파일 설정:

```bash
# 4GB swap 파일 생성
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 재부팅 후에도 유지
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 3. NPU 드라이버 설치 (NPU Driver Installation)

### 3.1 드라이버 확인

Rockchip BSP 이미지를 사용했다면 NPU 드라이버가 이미 포함되어 있을 수 있습니다:

```bash
# NPU 디바이스 확인
ls -la /dev/dri/

# NPU 커널 모듈 확인
dmesg | grep -i rknpu

# NPU 드라이버 버전 확인
cat /sys/kernel/debug/rknpu/version 2>/dev/null || echo "NPU debug info not available"
```

### 3.2 NPU 드라이버 수동 설치

드라이버가 없는 경우:

```bash
# Rockchip NPU 드라이버 저장소 클론
git clone https://github.com/rockchip-linux/rknpu2.git
cd rknpu2

# 드라이버 설치 (aarch64)
sudo cp runtime/Linux/librknn_api/aarch64/librknnrt.so /usr/lib/
sudo cp runtime/Linux/librknn_api/aarch64/librknn_api.so /usr/lib/
sudo ldconfig

# NPU 디바이스 권한 설정
sudo usermod -aG video $USER
```

### 3.3 NPU 동작 확인

```bash
# NPU 사용률 확인
cat /sys/kernel/debug/rknpu/load 2>/dev/null

# NPU thermal zone 확인
cat /sys/class/thermal/thermal_zone*/type 2>/dev/null
cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null

# 간단한 NPU 테스트 (rknn_server 실행 여부)
ps aux | grep rknn
```

---

## 4. RKNN Toolkit2 설치 (RKNN Installation)

### 4.1 설치 방식 선택

| 환경 | 패키지 | 설명 |
|------|--------|------|
| **Orange Pi 5 (실행)** | `rknn-toolkit2-lite` | 디바이스에서 추론 실행용 (경량) |
| **x86 PC (개발)** | `rknn-toolkit2` | 모델 변환 및 시뮬레이션용 |

### 4.2 Orange Pi 5 Plus에 RKNN Lite 설치

```bash
# Python 가상 환경 생성
python3 -m venv /opt/npu-platform/venv
source /opt/npu-platform/venv/bin/activate

# 사전 의존성 설치
pip install --upgrade pip setuptools wheel
pip install numpy opencv-python-headless

# RKNN Toolkit2 Lite 설치
# 공식 릴리스에서 aarch64 whl 파일 다운로드
# https://github.com/rockchip-linux/rknn-toolkit2/releases
pip install rknn_toolkit_lite2-2.0.0-cp310-cp310-linux_aarch64.whl
```

### 4.3 개발 PC에 RKNN Toolkit2 설치 (모델 변환용)

```bash
# x86_64 개발 환경
pip install rknn-toolkit2

# 또는 공식 whl 파일에서 설치
pip install rknn_toolkit2-2.0.0-cp310-cp310-linux_x86_64.whl
```

### 4.4 설치 확인

```bash
# RKNN Lite 확인 (Orange Pi 5)
python3 -c "from rknnlite.api import RKNNLite; print('RKNN Lite OK')"

# RKNN Toolkit2 확인 (개발 PC)
python3 -c "from rknn.api import RKNN; print('RKNN Toolkit2 OK')"
```

---

## 5. 애플리케이션 설치 (Application Installation)

### 5.1 소스 코드 설치

```bash
# 설치 디렉토리 생성
sudo mkdir -p /opt/npu-platform
sudo chown $USER:$USER /opt/npu-platform

# 소스 클론
git clone <repository-url> /opt/npu-platform
cd /opt/npu-platform

# Python 가상 환경 생성 (이미 없는 경우)
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install --upgrade pip
pip install -r requirements.txt

# 선택 사항: MQTT 지원
pip install paho-mqtt

# 선택 사항: HTTP 클라이언트 (webhook 및 테스트용)
pip install httpx
```

### 5.2 디렉토리 구조

설치 완료 후 디렉토리 구조:

```
/opt/npu-platform/
├── app/                    # 애플리케이션 소스 코드
│   ├── api/               # REST API 라우터
│   ├── core/              # 핵심 로직 (추론, 카메라 등)
│   ├── models/            # Pydantic 데이터 모델
│   ├── services/          # 외부 서비스 (알림, 모니터 등)
│   ├── static/            # 정적 파일 (CSS, JS)
│   ├── templates/         # HTML 템플릿 (HTMX)
│   ├── config.py          # 설정 관리
│   ├── dependencies.py    # FastAPI DI
│   └── main.py            # 앱 엔트리포인트
├── data/                   # 런타임 데이터 (자동 생성)
│   ├── logs/              # 애플리케이션 로그
│   ├── roi_presets/       # ROI 프리셋 저장
│   └── snapshots/         # 이벤트 스냅샷
├── docker/                 # Docker 설정
├── docs/                   # 문서
├── models/                 # RKNN 모델 파일
├── scripts/                # 유틸리티 스크립트
├── tests/                  # 테스트 코드
├── requirements.txt        # Python 의존성
└── .env                    # 환경 변수 (직접 생성)
```

### 5.3 환경 변수 파일 생성

```bash
cat > /opt/npu-platform/.env << 'EOF'
# === Server ===
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
SERVER_LOG_LEVEL=info

# === Camera ===
CAMERA_MAX_CAMERAS=8
CAMERA_RTSP_TRANSPORT=tcp

# === Inference ===
INFERENCE_DEFAULT_CONFIDENCE=0.5
INFERENCE_DEFAULT_CORE_MASK=7
INFERENCE_MAX_LOADED_MODELS=3
INFERENCE_ENABLE_FRAME_SKIP=true

# === Notifications (선택) ===
# NOTIFY_MQTT_ENABLED=true
# NOTIFY_MQTT_BROKER=localhost
# NOTIFY_MQTT_PORT=1883
# NOTIFY_WEBHOOK_ENABLED=true
# NOTIFY_WEBHOOK_URL=https://your-server.com/webhook

# === Security ===
# SECURITY_ENABLE_AUTH=true
# SECURITY_API_KEY=your-secret-api-key
EOF
```

### 5.4 실행 확인

```bash
cd /opt/npu-platform
source venv/bin/activate

# 직접 실행
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Health check
curl http://localhost:8000/api/system/health
```

### 5.5 테스트 실행

```bash
cd /opt/npu-platform
source venv/bin/activate

# 전체 테스트 실행
pytest tests/ -v

# 특정 테스트만 실행
pytest tests/test_api.py -v
pytest tests/test_camera.py -v
pytest tests/test_inference.py -v
pytest tests/test_roi.py -v
```

---

## 6. 서비스 등록 (Systemd Service Setup)

### 6.1 Systemd 서비스 파일 생성

```bash
sudo nano /etc/systemd/system/npu-platform.service
```

```ini
[Unit]
Description=NPU Inference Platform
Documentation=https://github.com/your-repo/npu-platform
After=network.target
Wants=network-online.target

[Service]
Type=exec
User=orangepi
Group=orangepi
WorkingDirectory=/opt/npu-platform
Environment=PATH=/opt/npu-platform/venv/bin:/usr/bin:/bin
EnvironmentFile=-/opt/npu-platform/.env
ExecStart=/opt/npu-platform/venv/bin/python -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1 \
  --log-level info \
  --access-log
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=npu-platform

# 보안 설정
NoNewPrivileges=false
PrivateTmp=true

# 리소스 제한
LimitNOFILE=65536
LimitNPROC=4096

# NPU 디바이스 접근을 위해 필요
SupplementaryGroups=video render

[Install]
WantedBy=multi-user.target
```

### 6.2 서비스 활성화 및 시작

```bash
# Systemd 데몬 리로드
sudo systemctl daemon-reload

# 서비스 활성화 (부팅 시 자동 시작)
sudo systemctl enable npu-platform

# 서비스 시작
sudo systemctl start npu-platform

# 상태 확인
sudo systemctl status npu-platform

# 로그 확인
sudo journalctl -u npu-platform -f
```

### 6.3 서비스 관리 명령

```bash
# 재시작
sudo systemctl restart npu-platform

# 중지
sudo systemctl stop npu-platform

# 설정 리로드 (graceful)
sudo systemctl reload npu-platform

# 부팅 시 자동 시작 비활성화
sudo systemctl disable npu-platform
```

---

## 7. 리버스 프록시 (Nginx Reverse Proxy)

### 7.1 Nginx 설치

```bash
sudo apt install -y nginx
```

### 7.2 Nginx 설정

```bash
sudo nano /etc/nginx/sites-available/npu-platform
```

```nginx
upstream npu_backend {
    server 127.0.0.1:8000;
    keepalive 64;
}

server {
    listen 80;
    server_name npu.example.com;  # 도메인 또는 IP로 변경

    # 최대 업로드 크기 (모델 파일용)
    client_max_body_size 500M;

    # 접근 로그
    access_log /var/log/nginx/npu-platform-access.log;
    error_log /var/log/nginx/npu-platform-error.log;

    # 정적 파일 직접 서빙 (성능 최적화)
    location /static/ {
        alias /opt/npu-platform/app/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # MJPEG 스트림 (긴 timeout 필요)
    location ~ ^/api/stream/.*/mjpeg$ {
        proxy_pass http://npu_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 스트리밍 전용 설정
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
        chunked_transfer_encoding off;
    }

    # WebSocket 스트림
    location ~ ^/api/stream/.*/ws$ {
        proxy_pass http://npu_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # 일반 API 및 웹 인터페이스
    location / {
        proxy_pass http://npu_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        proxy_connect_timeout 10s;
        proxy_read_timeout 30s;
        proxy_send_timeout 30s;
    }
}
```

### 7.3 HTTPS 설정 (Let's Encrypt)

```bash
# Certbot 설치
sudo apt install -y certbot python3-certbot-nginx

# SSL 인증서 발급
sudo certbot --nginx -d npu.example.com

# 자동 갱신 확인
sudo certbot renew --dry-run
```

### 7.4 Nginx 활성화

```bash
# 사이트 활성화
sudo ln -s /etc/nginx/sites-available/npu-platform /etc/nginx/sites-enabled/

# 기본 사이트 비활성화
sudo rm /etc/nginx/sites-enabled/default

# 설정 검증
sudo nginx -t

# Nginx 재시작
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## 8. Docker 배포 (Docker Deployment)

### 8.1 Docker 설치

```bash
# Docker 설치 (aarch64)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Docker Compose 설치 (v2 plugin)
sudo apt install -y docker-compose-plugin

# 재로그인 후 확인
docker --version
docker compose version
```

### 8.2 Dockerfile

프로젝트에 포함된 `docker/Dockerfile`을 사용합니다. 필요 시 커스터마이징:

```dockerfile
FROM python:3.10-slim-bullseye

# 시스템 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python 의존성
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# RKNN Lite 설치 (사전 빌드 whl 필요)
# COPY rknn_toolkit_lite2-*.whl /tmp/
# RUN pip install /tmp/rknn_toolkit_lite2-*.whl && rm /tmp/*.whl

# 애플리케이션 복사
COPY app/ ./app/
COPY models/ ./models/
COPY scripts/ ./scripts/

# 데이터 디렉토리
RUN mkdir -p data/logs data/roi_presets data/snapshots

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 8.3 Docker Compose 실행

프로젝트에 포함된 `docker/docker-compose.yml`을 사용합니다:

```bash
cd /opt/npu-platform

# 빌드 및 실행
docker compose -f docker/docker-compose.yml up -d --build

# 로그 확인
docker compose -f docker/docker-compose.yml logs -f

# 중지
docker compose -f docker/docker-compose.yml down
```

### 8.4 Docker Compose 설정

```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  npu-platform:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: npu-inference-platform
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      # 데이터 영속화
      - ../data:/app/data
      # 모델 디렉토리 (읽기 전용)
      - ../models:/app/models:ro
      # NPU 디바이스 접근
      - /dev/dri:/dev/dri
    devices:
      # RK3588 NPU 및 카메라 디바이스
      - /dev/dri:/dev/dri
      - /dev/video0:/dev/video0  # USB 카메라 (선택)
    environment:
      - APP_DEBUG=false
      - SERVER_LOG_LEVEL=info
      - CAMERA_MAX_CAMERAS=8
      - INFERENCE_DEFAULT_CONFIDENCE=0.5
    # NPU 접근에 필요
    privileged: true
    healthcheck:
      test: ["CMD", "python3", "-c", "import httpx; httpx.get('http://localhost:8000/api/system/health').raise_for_status()"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
```

### 8.5 Docker에서 MQTT 브로커 함께 실행

```yaml
# docker-compose.yml에 추가
services:
  npu-platform:
    # ... (위와 동일)
    environment:
      - NOTIFY_MQTT_ENABLED=true
      - NOTIFY_MQTT_BROKER=mqtt
      - NOTIFY_MQTT_PORT=1883
    depends_on:
      - mqtt

  mqtt:
    image: eclipse-mosquitto:2
    container_name: mqtt-broker
    restart: unless-stopped
    ports:
      - "1883:1883"
      - "9001:9001"  # WebSocket (선택)
    volumes:
      - mosquitto_data:/mosquitto/data
      - mosquitto_log:/mosquitto/log

volumes:
  mosquitto_data:
  mosquitto_log:
```

### 8.6 Docker 관리 명령

```bash
# 컨테이너 상태 확인
docker compose -f docker/docker-compose.yml ps

# 리소스 사용량 확인
docker stats npu-inference-platform

# 컨테이너 내부 셸 접속
docker exec -it npu-inference-platform /bin/bash

# 이미지 재빌드 (코드 변경 후)
docker compose -f docker/docker-compose.yml up -d --build --force-recreate

# 사용하지 않는 이미지 정리
docker image prune -f
```

---

## 9. 환경 변수 설정 (Environment Configuration)

### 9.1 설정 우선순위

설정은 다음 우선순위로 적용됩니다 (높은 순):

1. 환경 변수 (직접 설정)
2. `.env` 파일
3. 코드 기본값

### 9.2 전체 환경 변수 레퍼런스

#### App 설정

| 환경 변수 | 설명 | 기본값 | 타입 |
|-----------|------|--------|------|
| `APP_APP_NAME` | 애플리케이션 이름 | `NPU Inference Platform` | string |
| `APP_APP_VERSION` | 애플리케이션 버전 | `1.0.0` | string |
| `APP_DEBUG` | Debug 모드 활성화 | `false` | bool |

#### Server 설정

| 환경 변수 | 설명 | 기본값 | 타입 |
|-----------|------|--------|------|
| `SERVER_HOST` | 서버 바인드 주소 | `0.0.0.0` | string |
| `SERVER_PORT` | 서버 포트 | `8000` | int |
| `SERVER_WORKERS` | Worker 수 (NPU 사용 시 1 고정) | `1` | int |
| `SERVER_RELOAD` | 코드 변경 시 자동 리로드 | `false` | bool |
| `SERVER_LOG_LEVEL` | 로그 레벨 (`debug`/`info`/`warning`/`error`) | `info` | string |

#### Camera 설정

| 환경 변수 | 설명 | 기본값 | 타입 |
|-----------|------|--------|------|
| `CAMERA_MAX_CAMERAS` | 최대 동시 카메라 수 | `8` | int |
| `CAMERA_RECONNECT_INTERVAL` | 재연결 간격 (초) | `5` | int |
| `CAMERA_RECONNECT_MAX_RETRIES` | 최대 재연결 시도 (0=무한) | `0` | int |
| `CAMERA_FRAME_BUFFER_SIZE` | 카메라당 프레임 버퍼 크기 | `1` | int |
| `CAMERA_DEFAULT_FPS_LIMIT` | 기본 FPS 제한 | `30` | int |
| `CAMERA_RTSP_TRANSPORT` | RTSP 전송 프로토콜 (`tcp`/`udp`) | `tcp` | string |
| `CAMERA_CAPTURE_TIMEOUT_MS` | 프레임 캡처 timeout (ms) | `5000` | int |

#### Inference 설정

| 환경 변수 | 설명 | 기본값 | 타입 |
|-----------|------|--------|------|
| `INFERENCE_DEFAULT_CONFIDENCE` | 기본 confidence threshold | `0.5` | float |
| `INFERENCE_DEFAULT_NMS_THRESHOLD` | 기본 NMS threshold | `0.45` | float |
| `INFERENCE_DEFAULT_CORE_MASK` | NPU core mask (아래 표 참조) | `7` | int |
| `INFERENCE_MAX_LOADED_MODELS` | 동시 로드 최대 모델 수 | `3` | int |
| `INFERENCE_INFERENCE_TIMEOUT_MS` | 추론 timeout (ms) | `1000` | int |
| `INFERENCE_ENABLE_FRAME_SKIP` | 프레임 건너뛰기 활성화 | `true` | bool |

NPU Core Mask 값:

| Core Mask | 사용 코어 | 설명 |
|-----------|-----------|------|
| `1` | Core 0 | 단일 코어 |
| `2` | Core 1 | 단일 코어 |
| `4` | Core 2 | 단일 코어 |
| `3` | Core 0+1 | 듀얼 코어 |
| `5` | Core 0+2 | 듀얼 코어 |
| `6` | Core 1+2 | 듀얼 코어 |
| `7` | Core 0+1+2 | 트리플 코어 (최대 성능) |

#### Stream 설정

| 환경 변수 | 설명 | 기본값 | 타입 |
|-----------|------|--------|------|
| `STREAM_MJPEG_QUALITY` | MJPEG JPEG 품질 (1~100) | `80` | int |
| `STREAM_MJPEG_MAX_FPS` | MJPEG 최대 FPS | `30` | int |
| `STREAM_WS_MAX_FPS` | WebSocket 최대 FPS | `30` | int |
| `STREAM_PREVIEW_SCALE` | 프리뷰 썸네일 비율 (0.1~1.0) | `0.5` | float |
| `STREAM_MAX_WS_CLIENTS` | 스트림당 최대 WebSocket 클라이언트 | `10` | int |

#### Storage 설정

| 환경 변수 | 설명 | 기본값 | 타입 |
|-----------|------|--------|------|
| `STORAGE_DATA_DIR` | 데이터 디렉토리 경로 | `./data` | path |
| `STORAGE_MODELS_DIR` | 모델 디렉토리 경로 | `./models` | path |
| `STORAGE_CONFIG_FILE` | 설정 파일명 | `config.json` | string |
| `STORAGE_MAX_SNAPSHOTS` | 최대 스냅샷 저장 수 | `1000` | int |
| `STORAGE_MAX_LOG_SIZE_MB` | 최대 로그 파일 크기 (MB) | `100` | int |
| `STORAGE_SNAPSHOT_QUALITY` | 스냅샷 JPEG 품질 (1~100) | `95` | int |

#### Notification 설정

| 환경 변수 | 설명 | 기본값 | 타입 |
|-----------|------|--------|------|
| `NOTIFY_MQTT_ENABLED` | MQTT 알림 활성화 | `false` | bool |
| `NOTIFY_MQTT_BROKER` | MQTT 브로커 주소 | `localhost` | string |
| `NOTIFY_MQTT_PORT` | MQTT 브로커 포트 | `1883` | int |
| `NOTIFY_MQTT_TOPIC_PREFIX` | MQTT topic prefix | `npu-platform` | string |
| `NOTIFY_WEBHOOK_ENABLED` | Webhook 알림 활성화 | `false` | bool |
| `NOTIFY_WEBHOOK_URL` | Webhook URL | (없음) | string |
| `NOTIFY_WEBHOOK_TIMEOUT` | Webhook timeout (초) | `10` | int |

#### Security 설정

| 환경 변수 | 설명 | 기본값 | 타입 |
|-----------|------|--------|------|
| `SECURITY_ENABLE_AUTH` | 인증 활성화 | `false` | bool |
| `SECURITY_API_KEY` | API 키 | (없음) | string |
| `SECURITY_CORS_ORIGINS` | 허용 CORS Origin 목록 | `["*"]` | list |
| `SECURITY_MAX_UPLOAD_SIZE_MB` | 최대 업로드 크기 (MB) | `500` | int |
| `SECURITY_ALLOWED_MODEL_EXTENSIONS` | 허용 모델 확장자 | `[".rknn"]` | list |

---

## 10. 성능 튜닝 (Performance Tuning)

### 10.1 NPU Core 설정

RK3588 NPU는 3개의 독립 코어를 가지고 있습니다. 사용 목적에 따라 코어 할당을 조정합니다:

```bash
# 최대 성능 (3코어 모두 사용)
export INFERENCE_DEFAULT_CORE_MASK=7

# 다중 모델 병렬 처리 (코어 분리 할당)
# 모델 A: Core 0 (mask=1), 모델 B: Core 1 (mask=2), 모델 C: Core 2 (mask=4)
```

| 시나리오 | Core Mask | 성능 특성 |
|----------|-----------|-----------|
| 단일 모델 최대 성능 | `7` | 가장 빠른 추론 속도 |
| 단일 모델 절전 | `1` | 낮은 전력, 1/3 성능 |
| 듀얼 모델 병렬 | `3` + `4` | 두 모델 동시 추론 |
| 트리플 모델 병렬 | `1` + `2` + `4` | 세 모델 동시 추론 (각 1/3 성능) |

### 10.2 Frame Skip 최적화

카메라 FPS가 추론 속도보다 높은 경우 프레임 건너뛰기를 활성화합니다:

```bash
# Frame skip 활성화
export INFERENCE_ENABLE_FRAME_SKIP=true
```

프레임 건너뛰기가 활성화되면:
- 추론을 수행하지 않는 프레임은 원본 그대로 스트리밍됩니다.
- 추론은 처리 가능한 간격으로만 수행됩니다.
- 스트림이 끊기지 않고 부드럽게 유지됩니다.

### 10.3 메모리 최적화

#### 프레임 버퍼 최소화

```bash
# 카메라당 버퍼 1 프레임 (최소 지연)
export CAMERA_FRAME_BUFFER_SIZE=1
```

#### 동시 로드 모델 수 제한

```bash
# 메모리 부족 시 동시 로드 모델 수 축소
export INFERENCE_MAX_LOADED_MODELS=2
```

#### 스트림 품질/해상도 조정

```bash
# MJPEG 품질 낮춤 (대역폭 절약)
export STREAM_MJPEG_QUALITY=60

# 프리뷰 축소 비율 조정
export STREAM_PREVIEW_SCALE=0.3
```

### 10.4 스냅샷 관리

이벤트 스냅샷이 디스크를 가득 채우지 않도록 제한합니다:

```bash
# 최대 스냅샷 수 제한
export STORAGE_MAX_SNAPSHOTS=500

# 스냅샷 품질 조절
export STORAGE_SNAPSHOT_QUALITY=85
```

### 10.5 모델 최적화 팁

1. **INT8 양자화 사용**: FP16 대비 약 2~3배 빠르고 메모리 사용량 감소.
2. **입력 크기 축소**: 640x640 대신 416x416 또는 320x320 사용 (정확도/속도 트레이드오프).
3. **Calibration 데이터셋 활용**: INT8 양자화 시 실제 운영 환경 이미지로 calibration하면 정확도 저하를 최소화.
4. **경량 모델 선택**: YOLOv8n (Nano) > YOLOv8s (Small) > YOLOv8m (Medium) 순으로 빠름.

### 10.6 시스템 레벨 튜닝

```bash
# CPU governor를 performance 모드로 설정
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# 파일 디스크립터 한도 증가
echo "orangepi soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "orangepi hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# 네트워크 버퍼 크기 최적화 (RTSP 수신용)
echo "net.core.rmem_max=8388608" | sudo tee -a /etc/sysctl.conf
echo "net.core.rmem_default=1048576" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 10.7 벤치마크를 통한 최적 설정 찾기

```bash
# 코어별 성능 비교
python scripts/benchmark.py --model models/yolov8n.rknn --core-mask 1 --iterations 100
python scripts/benchmark.py --model models/yolov8n.rknn --core-mask 3 --iterations 100
python scripts/benchmark.py --model models/yolov8n.rknn --core-mask 7 --iterations 100

# 입력 크기별 성능 비교
python scripts/benchmark.py --model models/yolov8n_320.rknn --input-size 320 320 --iterations 100
python scripts/benchmark.py --model models/yolov8n_640.rknn --input-size 640 640 --iterations 100
```

---

## 11. 모니터링 (Production Monitoring)

### 11.1 Health Check 엔드포인트

외부 모니터링 시스템(Prometheus, Zabbix, Uptime Kuma 등)에서 사용할 수 있습니다:

```bash
# Health check (HTTP 200 = 정상)
curl -f http://localhost:8000/api/system/health

# 응답 예시
{
  "status": "ok",
  "version": "1.0.0",
  "uptime_seconds": 86400.5,
  "cameras_connected": 4,
  "models_loaded": 1,
  "npu_available": true,
  "timestamp": "2025-01-15T10:30:00"
}
```

### 11.2 Docker Health Check

Docker Compose에 이미 health check가 설정되어 있습니다:

```yaml
healthcheck:
  test: ["CMD", "python3", "-c", "import httpx; httpx.get('http://localhost:8000/api/system/health').raise_for_status()"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 15s
```

### 11.3 Systemd Watchdog

Systemd 서비스의 `Restart=always` 설정으로 프로세스 크래시 시 자동 재시작됩니다. 추가로 watchdog을 설정할 수 있습니다:

```bash
# crontab을 이용한 주기적 Health check
crontab -e
```

```cron
# 5분마다 health check, 실패 시 재시작
*/5 * * * * curl -sf http://localhost:8000/api/system/health > /dev/null || sudo systemctl restart npu-platform
```

### 11.4 로그 모니터링

```bash
# 실시간 로그 추적 (systemd)
sudo journalctl -u npu-platform -f

# 애플리케이션 로그 파일
tail -f /opt/npu-platform/data/logs/app.log

# 오류 로그만 필터링
sudo journalctl -u npu-platform -p err --since "1 hour ago"
```

### 11.5 로그 로테이션 설정

```bash
sudo nano /etc/logrotate.d/npu-platform
```

```
/opt/npu-platform/data/logs/app.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    maxsize 100M
}
```

### 11.6 시스템 리소스 모니터링 스크립트

```bash
#!/bin/bash
# /opt/npu-platform/scripts/check_resources.sh

# CPU 온도 확인
CPU_TEMP=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null)
CPU_TEMP_C=$((CPU_TEMP / 1000))

# 메모리 사용률
MEM_USAGE=$(free | awk '/Mem:/ {printf("%.1f", $3/$2 * 100)}')

# 디스크 사용률
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | tr -d '%')

echo "CPU Temp: ${CPU_TEMP_C}°C | Memory: ${MEM_USAGE}% | Disk: ${DISK_USAGE}%"

# 경고 임계값
if [ "$CPU_TEMP_C" -gt 80 ]; then
    echo "WARNING: CPU temperature is high (${CPU_TEMP_C}°C)"
fi

if [ "$(echo "$MEM_USAGE > 90" | bc)" -eq 1 ]; then
    echo "WARNING: Memory usage is high (${MEM_USAGE}%)"
fi

if [ "$DISK_USAGE" -gt 90 ]; then
    echo "WARNING: Disk usage is high (${DISK_USAGE}%)"
fi
```

---

## 12. 백업 및 복구 (Backup and Recovery)

### 12.1 백업 대상

| 항목 | 경로 | 설명 | 중요도 |
|------|------|------|--------|
| **환경 설정** | `.env` | 환경 변수 설정 | 높음 |
| **ROI 프리셋** | `data/roi_presets/` | ROI 설정 데이터 | 높음 |
| **설정 파일** | `data/config.json` | 런타임 설정 | 높음 |
| **모델 파일** | `models/` | RKNN 모델 파일 | 중간 (재변환 가능) |
| **이벤트 스냅샷** | `data/snapshots/` | 이벤트 발생 시 캡처 | 낮음 |
| **로그 파일** | `data/logs/` | 애플리케이션 로그 | 낮음 |

### 12.2 수동 백업

```bash
#!/bin/bash
# /opt/npu-platform/scripts/backup.sh

BACKUP_DIR="/opt/backups/npu-platform"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.tar.gz"

mkdir -p "$BACKUP_DIR"

cd /opt/npu-platform

# 핵심 데이터만 백업
tar -czf "$BACKUP_FILE" \
  .env \
  data/config.json \
  data/roi_presets/ \
  models/

echo "Backup created: $BACKUP_FILE"
echo "Size: $(du -h "$BACKUP_FILE" | cut -f1)"

# 30일 이상 된 백업 삭제
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +30 -delete
echo "Old backups cleaned up"
```

### 12.3 자동 백업 (Cron)

```bash
crontab -e
```

```cron
# 매일 새벽 3시 자동 백업
0 3 * * * /opt/npu-platform/scripts/backup.sh >> /var/log/npu-backup.log 2>&1
```

### 12.4 복구 절차

```bash
# 1. 애플리케이션 중지
sudo systemctl stop npu-platform

# 2. 백업 파일 복원
BACKUP_FILE="/opt/backups/npu-platform/backup_20250115_030000.tar.gz"
cd /opt/npu-platform
tar -xzf "$BACKUP_FILE"

# 3. 권한 확인
chown -R orangepi:orangepi /opt/npu-platform/data
chown -R orangepi:orangepi /opt/npu-platform/models

# 4. 애플리케이션 재시작
sudo systemctl start npu-platform

# 5. 정상 동작 확인
curl http://localhost:8000/api/system/health
```

### 12.5 전체 시스템 복구 (재설치)

새 Orange Pi 5 Plus에 처음부터 설치하는 경우:

```bash
# 1. OS 설치 (2장 참조)
# 2. 시스템 패키지 설치 (2.3절 참조)
# 3. NPU 드라이버 설치 (3장 참조)
# 4. RKNN Toolkit 설치 (4장 참조)
# 5. 애플리케이션 설치 (5장 참조)

# 6. 백업 데이터 복원
tar -xzf backup_XXXXXXXX_XXXXXX.tar.gz -C /opt/npu-platform/

# 7. 서비스 등록 및 시작
sudo systemctl enable npu-platform
sudo systemctl start npu-platform
```

---

## 13. 보안 권고사항 (Security Recommendations)

### 13.1 인증 활성화

프로덕션 환경에서는 반드시 API 인증을 활성화하세요:

```bash
export SECURITY_ENABLE_AUTH=true
export SECURITY_API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "Generated API Key: $SECURITY_API_KEY"
```

API 호출 시 인증 헤더 포함:

```bash
curl -H "X-API-Key: your-secret-api-key" http://localhost:8000/api/cameras
```

### 13.2 CORS 설정

운영 환경에서는 CORS origin을 제한하세요:

```bash
# 특정 도메인만 허용
export SECURITY_CORS_ORIGINS='["https://npu.example.com"]'

# 여러 도메인 허용
export SECURITY_CORS_ORIGINS='["https://npu.example.com","https://admin.example.com"]'
```

### 13.3 네트워크 보안

```bash
# 방화벽 설정 (UFW)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp    # HTTP (Nginx)
sudo ufw allow 443/tcp   # HTTPS (Nginx)
# 내부 포트 8000은 외부에서 직접 접근 차단
sudo ufw enable
```

### 13.4 HTTPS 필수화

Nginx 리버스 프록시를 통해 HTTPS를 적용하고, HTTP 요청은 HTTPS로 리다이렉트합니다:

```nginx
server {
    listen 80;
    server_name npu.example.com;
    return 301 https://$server_name$request_uri;
}
```

### 13.5 파일 업로드 보안

```bash
# 허용된 모델 확장자만 업로드 가능 (기본값: .rknn)
export SECURITY_ALLOWED_MODEL_EXTENSIONS='[".rknn"]'

# 업로드 크기 제한
export SECURITY_MAX_UPLOAD_SIZE_MB=500
```

### 13.6 SSH 보안 강화

```bash
# 패스워드 인증 비활성화 (키 기반 인증만 허용)
sudo nano /etc/ssh/sshd_config
# PasswordAuthentication no
# PermitRootLogin no

sudo systemctl restart sshd
```

### 13.7 시스템 업데이트

정기적으로 보안 업데이트를 적용하세요:

```bash
# 보안 업데이트 자동 설치
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 13.8 RTSP 카메라 보안

- RTSP URL에 포함된 비밀번호가 `.env` 파일에 저장되지 않도록 주의하세요.
- 카메라 네트워크를 별도 VLAN으로 분리하는 것을 권장합니다.
- 카메라의 기본 비밀번호를 반드시 변경하세요.

### 13.9 Debug 모드

프로덕션 환경에서는 반드시 Debug 모드를 비활성화하세요:

```bash
export APP_DEBUG=false
```

Debug 모드가 비활성화되면 Swagger UI (`/api/docs`)와 ReDoc (`/api/redoc`)에 접근할 수 없습니다.

---

## 14. 문제 해결 (Troubleshooting)

### 14.1 애플리케이션이 시작되지 않음

**증상**: 서비스 시작 실패, 포트 바인딩 오류

```bash
# 1. 포트 점유 확인
sudo lsof -i :8000
# 점유 프로세스가 있으면 종료
sudo kill -9 <PID>

# 2. 로그 확인
sudo journalctl -u npu-platform -n 50 --no-pager

# 3. Python 환경 확인
/opt/npu-platform/venv/bin/python -c "import fastapi; print(fastapi.__version__)"

# 4. 수동 실행으로 오류 확인
cd /opt/npu-platform
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 14.2 NPU를 인식하지 못함

**증상**: `npu_available: false`, 모델 로드 실패

```bash
# 1. NPU 디바이스 파일 확인
ls -la /dev/dri/
ls -la /dev/rknpu* 2>/dev/null

# 2. 커널 모듈 확인
lsmod | grep rknpu
dmesg | grep -i "rknpu\|rknn"

# 3. 라이브러리 확인
ldconfig -p | grep rknn

# 4. RKNN Lite 임포트 테스트
python3 -c "from rknnlite.api import RKNNLite; print('OK')"

# 5. 사용자 그룹 확인
groups $USER
# video, render 그룹에 포함되어야 함
sudo usermod -aG video,render $USER
# 재로그인 필요
```

### 14.3 모델 로드 실패

**증상**: "Failed to load RKNN model" 또는 "Failed to init RKNN runtime"

```bash
# 1. 모델 파일 존재 확인
ls -la models/*.rknn

# 2. 모델 파일 권한 확인
chmod 644 models/*.rknn

# 3. 메모리 여유 확인
free -h
# NPU 메모리 부족 시 다른 모델 언로드

# 4. 모델 호환성 확인
# 모델이 rk3588 타겟으로 변환되었는지 확인
python3 -c "
from rknnlite.api import RKNNLite
r = RKNNLite()
ret = r.load_rknn('models/your_model.rknn')
print('Load result:', ret)
if ret == 0:
    ret = r.init_runtime()
    print('Init result:', ret)
    r.release()
"
```

### 14.4 RTSP 카메라 연결 실패

**증상**: 카메라 상태가 `error` 또는 `connecting`에서 변하지 않음

```bash
# 1. RTSP URL 직접 테스트
ffprobe -v error -show_entries stream=width,height,codec_name \
  "rtsp://admin:password@192.168.1.100:554/stream1"

# 2. 네트워크 연결 확인
ping -c 3 192.168.1.100

# 3. RTSP 포트 연결 확인
nc -zv 192.168.1.100 554

# 4. Transport 방식 변경
export CAMERA_RTSP_TRANSPORT=udp  # 또는 tcp

# 5. OpenCV 직접 테스트
python3 -c "
import cv2
cap = cv2.VideoCapture('rtsp://admin:password@192.168.1.100:554/stream1')
ret, frame = cap.read()
print('Success:', ret, 'Shape:', frame.shape if ret else 'N/A')
cap.release()
"
```

### 14.5 추론 속도가 느림

**증상**: FPS가 기대보다 낮음

```bash
# 1. NPU 사용률 확인
cat /sys/kernel/debug/rknpu/load

# 2. 온도 확인 (thermal throttling 여부)
cat /sys/class/thermal/thermal_zone*/temp
# 85000 이상이면 throttling 가능성

# 3. CPU governor 확인
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
# "powersave"이면 performance로 변경
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# 4. Core mask 확인
echo "Current core mask: $INFERENCE_DEFAULT_CORE_MASK"
# 7 (전체 코어) 사용 권장

# 5. 벤치마크 실행
python scripts/benchmark.py --model models/your_model.rknn --core-mask 7
```

### 14.6 메모리 부족 (Out of Memory)

**증상**: 애플리케이션 크래시, "Killed" 메시지

```bash
# 1. 메모리 사용 현황 확인
free -h
cat /proc/meminfo | grep -E "MemTotal|MemAvailable|SwapTotal"

# 2. 프로세스별 메모리 확인
ps aux --sort=-%mem | head -10

# 3. 대응 방안:
# a) 동시 로드 모델 수 축소
export INFERENCE_MAX_LOADED_MODELS=1

# b) 카메라 수 축소
export CAMERA_MAX_CAMERAS=4

# c) 스트림 품질 낮춤
export STREAM_MJPEG_QUALITY=50
export STREAM_PREVIEW_SCALE=0.3

# d) Swap 확대
sudo fallocate -l 8G /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 14.7 WebSocket 연결 실패

**증상**: WebSocket 스트림이 연결되지 않음

```bash
# 1. Nginx WebSocket 설정 확인
# proxy_set_header Upgrade $http_upgrade;
# proxy_set_header Connection "upgrade";

# 2. 직접 연결 테스트 (Nginx 우회)
# ws://localhost:8000/api/stream/{camera_id}/ws

# 3. WebSocket 클라이언트 수 확인
# 최대 클라이언트 수 초과 여부 확인
echo "Max WS clients per stream: $STREAM_MAX_WS_CLIENTS"
```

### 14.8 Docker에서 NPU 접근 불가

**증상**: Docker 컨테이너에서 NPU 인식 안 됨

```bash
# 1. privileged 모드 확인
docker inspect npu-inference-platform | grep Privileged

# 2. 디바이스 마운트 확인
docker inspect npu-inference-platform | grep -A5 Devices

# 3. 컨테이너 내부에서 확인
docker exec -it npu-inference-platform ls -la /dev/dri/
docker exec -it npu-inference-platform python3 -c "from rknnlite.api import RKNNLite; print('OK')"
```

### 14.9 로그 파일이 너무 큼

**증상**: 디스크 용량 부족, 로그 파일 비대

```bash
# 1. 로그 파일 크기 확인
du -sh /opt/npu-platform/data/logs/

# 2. 로그 레벨 조정 (verbose 줄이기)
export SERVER_LOG_LEVEL=warning

# 3. 로그 파일 수동 정리
> /opt/npu-platform/data/logs/app.log  # 로그 파일 비우기

# 4. 로그 로테이션 설정 (11.5절 참조)
```

### 14.10 일반적인 문제 해결 순서

문제가 발생했을 때 아래 순서로 진단합니다:

1. **로그 확인**: `journalctl -u npu-platform -n 100` 또는 `data/logs/app.log`
2. **Health check**: `curl http://localhost:8000/api/system/health`
3. **시스템 상태**: `curl http://localhost:8000/api/system/status`
4. **리소스 확인**: `htop`, `free -h`, 온도 확인
5. **네트워크 확인**: `ping`, `nc -zv`, 방화벽 규칙
6. **재시작**: `sudo systemctl restart npu-platform`
7. **수동 실행**: 서비스 중지 후 터미널에서 직접 실행하여 상세 오류 확인

---

## 15. Windows 개발 환경 (Development on Windows)

프로덕션은 Linux(Orange Pi 5)에서 실행하지만, **개발 및 테스트는 Windows PC**에서 가능합니다.

### 15.1 Windows 설치

```powershell
# PowerShell 사용 (권장)
git clone https://github.com/YawnsDuzin/Orange-Pi-5-NPU-TEST-BED.git
cd Orange-Pi-5-NPU-TEST-BED
powershell -ExecutionPolicy Bypass -File scripts\install_deps.ps1

# 또는 CMD 사용
scripts\install_deps.bat
```

### 15.2 실행

```powershell
# 가상 환경 활성화
.venv\Scripts\activate

# 서버 시작
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 또는 빠른 실행
run.bat
```

### 15.3 Windows에서의 제약사항

| 기능 | 상태 | 비고 |
|------|------|------|
| 웹 UI | 완전 지원 | 모든 페이지, HTMX 동작 |
| REST API | 완전 지원 | 모든 엔드포인트 동작 |
| 카메라 (USB) | 지원 | DirectShow 백엔드 사용 |
| 카메라 (RTSP) | 지원 | FFmpeg 백엔드 사용 |
| 카메라 (CSI) | 미지원 | Orange Pi 전용 하드웨어 |
| NPU 추론 | Mock 모드 | RKNN은 ARM64 Linux 전용 |
| 시스템 모니터링 | 지원 | psutil 기반 (CPU/메모리/디스크/네트워크) |
| 온도 센서 | 제한적 | Windows에서 psutil `sensors_temperatures` 제한 |
| ROI 편집기 | 완전 지원 | Canvas 기반, 플랫폼 독립 |
| MQTT 알림 | 지원 | paho-mqtt 크로스 플랫폼 |
| Webhook 알림 | 지원 | httpx 크로스 플랫폼 |
| 테스트 | 완전 지원 | `pytest tests/ -v` |

### 15.4 Windows 트러블슈팅

**asyncio 오류** (`RuntimeError: Event loop is closed`):
- `app/main.py`에서 `asyncio.WindowsSelectorEventLoopPolicy()` 자동 설정 (v1.1.0+)

**psutil 미설치**:
```powershell
pip install psutil
```

**포트 충돌**:
```powershell
# 포트 사용 프로세스 확인
netstat -ano | findstr :8000
# PID로 프로세스 종료
taskkill /PID <PID> /F
```

---

> **추가 도움**이 필요하시면 프로젝트 Issues 페이지를 이용해 주세요.
