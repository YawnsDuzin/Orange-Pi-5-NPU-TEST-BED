@echo off
REM Quick start script for Windows
REM Usage: run.bat [port]

set PORT=%1
if "%PORT%"=="" set PORT=8000

echo Starting NPU Inference Platform on port %PORT%...
echo Open http://127.0.0.1:%PORT% in your browser
echo Press Ctrl+C to stop.
echo.

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port %PORT%
) else (
    python -m uvicorn app.main:app --host 127.0.0.1 --port %PORT%
)
