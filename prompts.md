==========================================
2026.01.30(금)
==========================================

git clone https://github.com/YawnsDuzin/Orange-Pi-5-NPU-TEST-BED.git
cd Orange-Pi-5-NPU-TEST-BED

chmod +x scripts/install_deps.sh
./scripts/install_deps.sh

cp .env.example .env

pip install --upgrade pip

# wheel 파일 확인
ls /home/itlog/rknn-toolkit2/rknn-toolkit-lite2/packages/ | grep cp310

# Python 3.10용 wheel 설치
pip install /home/itlog/rknn-toolkit2/rknn-toolkit-lite2/packages/rknn_toolkit_lite2-2.1.0-cp310-cp310-linux_aarch64.whl

# OPEN-CV 설치
pip install opencv-python numpy

# 설치 후, 확인
python3 -c "from rknnlite.api import RKNNLite; print('RKNN Lite2 OK')"


source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

==========================================

/init
/clear

==========================================


(.venv) itlog@itlog-desktop:~/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED$ uvicorn app.main:app --host 0.0.0.0 --port 8000
Traceback (most recent call last):
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/bin/uvicorn", line 7, in <module>
    sys.exit(main())
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/click/core.py", line 1485, in __call__
    return self.main(*args, **kwargs)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/click/core.py", line 1406, in main
    rv = self.invoke(ctx)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/click/core.py", line 1269, in invoke
    return ctx.invoke(self.callback, **ctx.params)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/click/core.py", line 824, in invoke
    return callback(*args, **kwargs)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/uvicorn/main.py", line 424, in main
    run(
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/uvicorn/main.py", line 594, in run
    server.run()
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/uvicorn/server.py", line 67, in run
    return asyncio_run(self.serve(sockets=sockets), loop_factory=self.config.get_loop_factory())
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/uvicorn/_compat.py", line 60, in asyncio_run
    return loop.run_until_complete(main)
  File "uvloop/loop.pyx", line 1518, in uvloop.loop.Loop.run_until_complete
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/uvicorn/server.py", line 71, in serve
    await self._serve(sockets)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/uvicorn/server.py", line 78, in _serve
    config.load()
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/uvicorn/config.py", line 439, in load
    self.loaded_app = import_from_string(self.app)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/uvicorn/importer.py", line 19, in import_from_string
    module = importlib.import_module(module_str)
  File "/usr/lib/python3.10/importlib/__init__.py", line 126, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "<frozen importlib._bootstrap>", line 1050, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1027, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1006, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 688, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 883, in exec_module
  File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/app/main.py", line 229, in <module>
    app = create_app()
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/app/main.py", line 146, in create_app
    settings = get_settings()
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/app/config.py", line 148, in get_settings
    return AppSettings()
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/pydantic_settings/main.py", line 194, in __init__
    super().__init__(
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/pydantic/main.py", line 250, in __init__
    validated_self = self.__pydantic_validator__.validate_python(data, self_instance=self)
pydantic_core._pydantic_core.ValidationError: 29 validation errors for AppSettings
server_host
  Extra inputs are not permitted [type=extra_forbidden, input_value='0.0.0.0', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
server_port
  Extra inputs are not permitted [type=extra_forbidden, input_value='8000', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
server_workers
  Extra inputs are not permitted [type=extra_forbidden, input_value='1', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
server_log_level
  Extra inputs are not permitted [type=extra_forbidden, input_value='info', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
camera_max_cameras
  Extra inputs are not permitted [type=extra_forbidden, input_value='8', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
camera_reconnect_interval
  Extra inputs are not permitted [type=extra_forbidden, input_value='5', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
camera_frame_buffer_size
  Extra inputs are not permitted [type=extra_forbidden, input_value='1', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
camera_default_fps_limit
  Extra inputs are not permitted [type=extra_forbidden, input_value='30', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
camera_rtsp_transport
  Extra inputs are not permitted [type=extra_forbidden, input_value='tcp', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
inference_default_confidence
  Extra inputs are not permitted [type=extra_forbidden, input_value='0.5', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
inference_default_nms_threshold
  Extra inputs are not permitted [type=extra_forbidden, input_value='0.45', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
inference_default_core_mask
  Extra inputs are not permitted [type=extra_forbidden, input_value='7', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
inference_max_loaded_models
  Extra inputs are not permitted [type=extra_forbidden, input_value='3', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
inference_enable_frame_skip
  Extra inputs are not permitted [type=extra_forbidden, input_value='true', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
stream_mjpeg_quality
  Extra inputs are not permitted [type=extra_forbidden, input_value='80', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
stream_mjpeg_max_fps
  Extra inputs are not permitted [type=extra_forbidden, input_value='30', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
stream_ws_max_fps
  Extra inputs are not permitted [type=extra_forbidden, input_value='30', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
stream_max_ws_clients
  Extra inputs are not permitted [type=extra_forbidden, input_value='10', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
storage_max_snapshots
  Extra inputs are not permitted [type=extra_forbidden, input_value='1000', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
storage_max_log_size_mb
  Extra inputs are not permitted [type=extra_forbidden, input_value='100', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
storage_snapshot_quality
  Extra inputs are not permitted [type=extra_forbidden, input_value='95', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
notify_mqtt_enabled
  Extra inputs are not permitted [type=extra_forbidden, input_value='false', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
notify_mqtt_broker
  Extra inputs are not permitted [type=extra_forbidden, input_value='localhost', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
notify_mqtt_port
  Extra inputs are not permitted [type=extra_forbidden, input_value='1883', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
notify_mqtt_topic_prefix
  Extra inputs are not permitted [type=extra_forbidden, input_value='npu-platform', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
notify_webhook_enabled
  Extra inputs are not permitted [type=extra_forbidden, input_value='false', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
security_enable_auth
  Extra inputs are not permitted [type=extra_forbidden, input_value='false', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
security_max_upload_size_mb
  Extra inputs are not permitted [type=extra_forbidden, input_value='500', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
security_cors_origins
  Extra inputs are not permitted [type=extra_forbidden, input_value='["*"]', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden

==========================================

(.venv) itlog@itlog-desktop:~/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED$ uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
INFO:     Will watch for changes in these directories: ['/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED']
ERROR:    [Errno 98] Address already in use

[추가] 답변은 무조건 한글로 해줘.

==========================================

CAMERAS 에서 Add 하고 저장하면, 첨부이미지와 같이 콘솔에러가 표시되고 있어

Failed to find a valid digest in the 'integrity' attribute for resource 'https://unpkg.com/htmx.org@1.9.12' with computed SHA-384 integrity 'ujb1lZYygJmzgSwoxRggbCHcjc0rB2XoQrxeTUQyRjrOnlCoYta87iKBWq3EsdM2'. The resource has been blocked.

Uncaught ReferenceError: htmx is not defined

[추가] 이 해시값은 일반적으로 저렇게 고정으로 사용하는 경우가 많아?

==========================================

카메라는 추가가 됐는데, 첨부이미지와 같이 대시보드에 표시가 안되고,, 콘솔에서 계속 오류가 표시되고 있어

==========================================

카메라는 추가했는데, 첨부이미지놔 같이 아직 대시보드에 표시가 안되고 있어. cctv화면은 언제 표시되는거야?

==========================================

브라우저를 새로고침하고 카메라 목록에서 "줌 카메라"를 클릭했는데,, 첨부이미지와 같이 화면이 표시되는데,, 거의 멈춰져있어. 실시간으로 표시가 안되고 있어.

[작업내용] MJPEG 스트림 엔드포인트에서 추론 없이도 카메라 프레임 실시간 스트리밍 지원

==========================================
/clear

카메라는 실시간으로 표시되고 있어. 근데 첨부이미지와 같이 모델 등록하고, loadded 상태인데.. 추론이 안되고 있어.

[추가] 전체적으로 확인해서 Alpine.js v2 패턴을 사용하는 부분 모두 Alpine.js v3 패턴으로 변경해줘

==========================================

현재 카메라를 추가하고, 웹서비스를 다시 시작하면 사라지는데, 저장은 따로 안되고 있는거야?

[확인결과] 맞습니다! 현재 카메라 설정이 메모리에만 저장되고 있어서, 웹 서비스를 재시작하면 모두 사라집니다.

[추가] 카메라 + 추론 + ROI 설정 (이미 roi_presets로 저장됨)

==========================================

(.venv) itlog@itlog-desktop:~/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED$ uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
INFO:     Will watch for changes in these directories: ['/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [71711] using WatchFiles
INFO:     Started server process [71713]
INFO:     Waiting for application startup.
2026-01-30 14:30:34,745 [INFO] app.main: Starting NPU Inference Platform v1.0.0
2026-01-30 14:30:34,745 [INFO] app.main: Debug mode: True
2026-01-30 14:30:34,746 [INFO] app.core.model_registry: Scanning models directory: /home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/models
2026-01-30 14:30:34,749 [INFO] app.core.model_registry: Found 1 models
2026-01-30 14:30:34,751 [INFO] app.core.roi_manager: Loaded 0 ROI presets
2026-01-30 14:30:34,751 [INFO] app.main: Restoring saved cameras and pipelines...
2026-01-30 14:30:34,751 [INFO] app.services.config_persistence: No saved cameras found
2026-01-30 14:30:34,751 [INFO] app.core.camera_manager: Restored 0/0 camera(s)
2026-01-30 14:30:34,751 [INFO] app.services.config_persistence: No saved pipelines found
2026-01-30 14:30:34,751 [INFO] app.core.frame_processor: Restored 0/0 pipeline(s)
2026-01-30 14:30:34,751 [INFO] app.main: Restored 0 camera(s) and 0 pipeline(s)
2026-01-30 14:30:34,751 [INFO] app.services.system_monitor: System monitor started
2026-01-30 14:30:34,751 [INFO] app.main: All services initialized successfully
INFO:     Application startup complete.
2026-01-30 14:31:01,797 [INFO] app.core.camera_manager: Camera '사무실(줌카메라)' (06210cb6) stream started
2026-01-30 14:31:01,798 [INFO] app.core.camera_manager: Camera added: 사무실(줌카메라) (06210cb6)
2026-01-30 14:31:01,800 [ERROR] app.services.config_persistence: Failed to save cameras: Object of type datetime is not JSON serializable
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/uvicorn/protocols/http/httptools_impl.py", line 416, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/uvicorn/middleware/proxy_headers.py", line 60, in __call__
    return await self.app(scope, receive, send)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/fastapi/applications.py", line 1135, in __call__
    await super().__call__(scope, receive, send)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/starlette/applications.py", line 107, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/starlette/middleware/errors.py", line 186, in __call__
    raise exc
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/starlette/middleware/errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/starlette/middleware/cors.py", line 93, in __call__
    await self.simple_response(scope, receive, send, request_headers=headers)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/starlette/middleware/cors.py", line 144, in simple_response
    await self.app(scope, receive, send)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/starlette/middleware/exceptions.py", line 63, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/fastapi/middleware/asyncexitstack.py", line 18, in __call__
    await self.app(scope, receive, send)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/starlette/routing.py", line 716, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/starlette/routing.py", line 736, in app
    await route.handle(scope, receive, send)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/starlette/routing.py", line 290, in handle
    await self.app(scope, receive, send)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/fastapi/routing.py", line 115, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/fastapi/routing.py", line 101, in app
    response = await f(request)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/fastapi/routing.py", line 355, in app
    raw_response = await run_endpoint_function(
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/fastapi/routing.py", line 243, in run_endpoint_function
    return await dependant.call(**values)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/app/api/cameras.py", line 80, in create_camera
    stream = await camera_manager.add_camera(config)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/app/core/camera_manager.py", line 305, in add_camera
    await self._save_cameras()
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/app/core/camera_manager.py", line 412, in _save_cameras
    await self._persistence.save_all(configs)
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/app/services/config_persistence.py", line 87, in save_all
    json.dump(data, f, indent=2, ensure_ascii=False)
  File "/usr/lib/python3.10/json/__init__.py", line 179, in dump
    for chunk in iterable:
  File "/usr/lib/python3.10/json/encoder.py", line 431, in _iterencode
    yield from _iterencode_dict(o, _current_indent_level)
  File "/usr/lib/python3.10/json/encoder.py", line 405, in _iterencode_dict
    yield from chunks
  File "/usr/lib/python3.10/json/encoder.py", line 325, in _iterencode_list
    yield from chunks
  File "/usr/lib/python3.10/json/encoder.py", line 405, in _iterencode_dict
    yield from chunks
  File "/usr/lib/python3.10/json/encoder.py", line 438, in _iterencode
    o = _default(o)
  File "/usr/lib/python3.10/json/encoder.py", line 179, in default
    raise TypeError(f'Object of type {o.__class__.__name__} '
TypeError: Object of type datetime is not JSON serializable
2026-01-30 14:31:04,629 [INFO] app.core.camera_manager: Camera '사무실(줌카메라)' connected: 704x480

[추가] 답변은 무조건 한글로

==========================================

첨부이미지와 같이 "Add Camera" 모달창에 이전에 등록한 내용이 초기화가 안되고 계속 표시되고 있어. 

[추가] 지금은 첨부이미지와 같이 "Cancel, Add" 버튼이 레이아웃에 안맞게 우측에 표시되고 있고,
Add 버튼을 눌러도 Camera 정보가 저장안되고 있어.
==========================================

Cameras 에 등록된 Camera의 중지버튼을 누르면 첨부이미지와 같이 json 이 표시되고 있어.

==========================================

첨부이미지와 같이 프로그램 우측 상단에  json 형식의 내용이 표시되고 있어. 왜 그런지 확인해줘.

[추가]
엔드포인트가 JSON을 반환하는데, 요청은 HTML을 기대하고 있어서 JSON이 그대로 표시되는 동일한 문제가 발생하는 코드를 전체적으로 확인해서 수정해줘.
 [추가2] 근데 원래 일반적인 구조가 api에서는 json을 반환하고, 별도의 html 반환 코드를 구현해서 구조적으로 분리하는게 일반적인 방법이야?
  [추가3] 현재 수정한 패턴과 동일하게 변경을 해서 일관성을 유지하면 좋을 부분이 있으면 전체적으로 확인해서 동일하게 수정해줘.

==========================================

첨부이미지와 같이 "System Status" 의 "NPU"의 값이 N/A 로 표시되고 있어. 확인해줘.
그리고 "NPU"의 Core0, Core1, Core2 의 별도의 사용상태(%) 도 표시되도록 해줘.

[답변]
권한 문제 해결
현재 /sys/kernel/debug/rknpu/load 파일은 root 권한이 필요합니다. 코어별 사용률을 보려면 다음 중 하나를 선택하세요:

옵션 1: sudo로 애플리케이션 실행
    sudo .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

옵션 2: debug 파일 시스템 권한 부여 (재부팅 시 초기화됨)
    sudo chmod -R a+r /sys/kernel/debug/rknpu/

옵션 3: udev 규칙 생성 (영구적)
    sudo tee /etc/udev/rules.d/99-rknpu.rules << 'EOF'
    KERNEL=="rknpu", MODE="0666"
    SUBSYSTEM=="misc", KERNEL=="npu", MODE="0666"
    EOF
    sudo udevadm control --reload-rules
    sudo udevadm trigger
테스트 방법
    애플리케이션을 재시작합니다.
    웹 브라우저에서 시스템 상태 패널을 확인합니다.
    권한이 있는 경우: NPU 섹션에 전체 사용률과 Core0/Core1/Core2 개별 사용률이 표시됩니다.
    권한이 없는 경우: NPU 전체 사용률만 표시되지만 "N/A" 대신 실제 퍼센트 값이 표시됩니다.
현재 애플리케이션이 실행 중이라면 재시작하여 변경 사항을 적용하세요.

[추가] 첨부이미지와 같이 어플리케이션 재 실행 후, 브라우저에서 접속 시, 계속 로딩중으로 표시되고 있어.
 [추가2]  첨부이미지와 같이 위의 조치사항 다 해봐도 콘솔창에 아무것도 표시안되고 있어. 그리고 Edge 브라우저에서도 접속 안되고 계속 로딩중으로 표시되고 있어.

==========================================

추론을 시작했는데, 첨부이미지와 같이,, 노란색으로 숫자는 표시되는데, 박스표시는 안되고 있어.
그리고 NPU를 사용해야 하는데, CPU를 사용하고 있는것 같아.
 
[추가] 참고로 /home/itlog/yolo_rtsp_npu/yolo_rtsp_inference_des_ROI.py 코드가 npu를 사용해서, 정상적으로 추론을 테스트한 파이썬 코드야.

==========================================

첨부이미지와 같이 추론 시작 시, 노란글씨는 표시되는데, 실제 추론 후, 결과박스는 표시가 안되고, CPU가 올라가고 있어. 그리고, NPU는 추론전부터 계속 100으로 표시되고 있어. 확인해줘.

==========================================


E Catch exception when setting inputs.
E Traceback (most recent call last):
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/rknnlite/api/rknn_lite.py", line 209, in inference
    self.rknn_runtime.set_inputs(inputs, data_type, data_format, inputs_pass_through=inputs_pass_through)
  File "rknnlite/api/rknn_runtime.py", line 1082, in rknnlite.api.rknn_runtime.RKNNRuntime.set_inputs
Exception: The input[0] need 4dims input, but 3dims input buffer feed.

E Catch exception when setting inputs.
E Traceback (most recent call last):
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/rknnlite/api/rknn_lite.py", line 209, in inference
    self.rknn_runtime.set_inputs(inputs, data_type, data_format, inputs_pass_through=inputs_pass_through)
  File "rknnlite/api/rknn_runtime.py", line 1082, in rknnlite.api.rknn_runtime.RKNNRuntime.set_inputs
Exception: The input[0] need 4dims input, but 3dims input buffer feed.

E Catch exception when setting inputs.
E Traceback (most recent call last):
  File "/home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/.venv/lib/python3.10/site-packages/rknnlite/api/rknn_lite.py", line 209, in inference
    self.rknn_runtime.set_inputs(inputs, data_type, data_format, inputs_pass_through=inputs_pass_through)
  File "rknnlite/api/rknn_runtime.py", line 1082, in rknnlite.api.rknn_runtime.RKNNRuntime.set_inputs
Exception: The input[0] need 4dims input, but 3dims input buffer feed.

2026-01-30 15:55:58,000 [I] app.core.frame_processor: Pipeline stopped for camera aa5a24f9
2026-01-30 15:55:58,001 [I] app.services.config_persistence: Saved 0 pipelines to /home/itlog/yolo_rtsp_npu/Orange-Pi-5-NPU-TEST-BED/data/pipelines.json

==========================================

NPU 사용량을 Core0, Core1, Core2 각각의 값도 표시되도록 해줘.

==========================================

첨부이미지와 같이 표시되는데, 너무끊겨서 표시되고, 있고, npu는 사용량이 10%에 고정되어 있어

==========================================

2026-01-30 16:32:23,937 [I] app.core.camera_manager: Camera '사무실(줌카메라)' (17440237) stream stopped
[ WARN:10@426.606] global cap_ffmpeg_impl.hpp:453 _opencv_ffmpeg_interrupt_callback Stream timeout triggered after 724514666778810880.000000 ms

==========================================

2개의 첨부이미지와 같이 추론의 결과인 노란색글씨와 녹색박스가 깜빡 거리면서 표시되고 있어. 일반 스트리밍과 추론데이터 표시 타이밍이나 뭔가 아키텍쳐를 잘못 설계한것이 아닌지 검토해줘. 다른 이런 상황의 레퍼런스를 참고해서 문제되는 부분을 알려줘.

==========================================

첨부이미지와 같이 표시되는데, 10fps밖에 안나오고 계속 끊기는 거 보니까.. 아직.. npu를 사용안하는거 아니야??? 그리고 ntp 사용량도 잘못 가져오는것 같아. 계속 10%로 고정되어 있어. 참고로 동일한 카메라에 동일 모델로  테스트 파이썬 으로 작성했을때,, 20fps 이상은 나왔거든..

[추가]
npu 사용량 가져오는 부분 /sys/class/devfreq/fdab0000.npu/load부분 제거하고, itlog@itlog-desktop:~/yolo_rtsp_npu$ sudo cat /sys/kernel/debug/rknpu/load
NPU load:  Core0: 21%, Core1:  1%, Core2:  1%, 방식으로 변경해줘.

==========================================

아직도 첨부된 GIF와 같이 12~13fps 밖에 안나오고 영상이 되돌리기가 되거나 계속 끊기고 있어.

==========================================

영상이 1~2프레임정도 뒤로갔다가 다시 원래대로 돌아오고 이런 증상이 있어. 그래서 더 끊기는 느낌이 드는것 같아.

[추가] 그리고 아직도 추론중인데,, 추론 중인 노란색 글씨가 없어졌다가 다시 나타나는 증상이 있어.. 이것ㅍ 때문에도 더 끊기에 보이는 것 같아.

==========================================

System Monitor 화면에는 첨부와 같이 아무것도 표시가 안되고 있어.

==========================================
==========================================
==========================================