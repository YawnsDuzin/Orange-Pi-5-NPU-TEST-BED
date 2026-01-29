"""
API Endpoint Tests

Tests for REST API endpoints using FastAPI TestClient.
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthAPI:
    """Tests for system health endpoint."""

    def test_health_check(self, test_client: TestClient):
        response = test_client.get("/api/system/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_system_info(self, test_client: TestClient):
        response = test_client.get("/api/system/info")
        assert response.status_code == 200
        data = response.json()
        assert "app_name" in data
        assert "app_version" in data


class TestCameraAPI:
    """Tests for camera management endpoints."""

    def test_list_cameras_empty(self, test_client: TestClient):
        response = test_client.get("/api/cameras")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["cameras"] == []

    def test_create_camera(self, test_client: TestClient):
        response = test_client.post(
            "/api/cameras",
            json={
                "name": "Test Camera",
                "url": "rtsp://localhost:554/test",
                "camera_type": "rtsp",
                "enabled": False,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["config"]["name"] == "Test Camera"
        assert data["config"]["url"] == "rtsp://localhost:554/test"

    def test_create_camera_invalid(self, test_client: TestClient):
        response = test_client.post(
            "/api/cameras",
            json={"name": "", "url": ""},
        )
        assert response.status_code == 422


class TestModelAPI:
    """Tests for model management endpoints."""

    def test_list_models(self, test_client: TestClient):
        response = test_client.get("/api/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "total" in data

    def test_scan_models(self, test_client: TestClient):
        response = test_client.post("/api/models/scan")
        assert response.status_code == 200
        data = response.json()
        assert "models_found" in data


class TestROIAPI:
    """Tests for ROI management endpoints."""

    def test_list_presets(self, test_client: TestClient):
        response = test_client.get("/api/roi/presets")
        assert response.status_code == 200
        data = response.json()
        assert "presets" in data
        assert "total" in data

    def test_create_preset(self, test_client: TestClient):
        response = test_client.post(
            "/api/roi/presets",
            json={
                "camera_id": "cam1",
                "name": "Test Preset",
                "rois": [
                    {
                        "name": "Zone A",
                        "roi_type": "rectangle",
                        "points": [{"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.9}],
                        "action": "include",
                    }
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["preset"]["name"] == "Test Preset"
        assert len(data["preset"]["rois"]) == 1


class TestStreamAPI:
    """Tests for stream endpoints."""

    def test_snapshot_no_camera(self, test_client: TestClient):
        response = test_client.get("/api/stream/nonexistent/snapshot")
        assert response.status_code == 404


class TestPageRoutes:
    """Tests for HTML page routes."""

    def test_index_page(self, test_client: TestClient):
        response = test_client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_cameras_page(self, test_client: TestClient):
        response = test_client.get("/cameras")
        assert response.status_code == 200

    def test_models_page(self, test_client: TestClient):
        response = test_client.get("/models")
        assert response.status_code == 200

    def test_monitor_page(self, test_client: TestClient):
        response = test_client.get("/monitor")
        assert response.status_code == 200

    def test_settings_page(self, test_client: TestClient):
        response = test_client.get("/settings")
        assert response.status_code == 200
