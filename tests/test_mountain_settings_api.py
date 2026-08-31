"""测试 Mountain Settings API。"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from webapp.mountain_settings_api import mountain_settings_router


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def client(data_dir: Path) -> TestClient:
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(mountain_settings_router(data_dir))
    return TestClient(app)


class TestListProviders:
    """测试 GET /api/v1/settings/providers。"""

    def test_list(self, client: TestClient):
        resp = client.get("/api/v1/settings/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] > 0


class TestGetProvider:
    """测试 GET /api/v1/settings/providers/{provider_id}。"""

    def test_found(self, client: TestClient):
        resp = client.get("/api/v1/settings/providers/text_model")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service_id"] == "text_model"

    def test_not_found(self, client: TestClient):
        resp = client.get("/api/v1/settings/providers/nonexistent")
        assert resp.status_code == 404


class TestUpdateProvider:
    """测试 PATCH /api/v1/settings/providers/{provider_id}。"""

    def test_update_allowed_field(self, client: TestClient):
        resp = client.patch("/api/v1/settings/providers/text_model", json={
            "model": "gpt-4o",
        })
        assert resp.status_code == 200

    def test_update_unknown_field(self, client: TestClient):
        resp = client.patch("/api/v1/settings/providers/text_model", json={
            "unknown_field": "value",
        })
        assert resp.status_code == 422


class TestSetSecret:
    """测试 POST /api/v1/settings/providers/{provider_id}/secrets。"""

    def test_set_secret(self, client: TestClient):
        resp = client.post("/api/v1/settings/providers/text_model/secrets", json={
            "key": "api_key",
            "value": "sk-test123456789",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["has_secret"] is True
        # 不能回显明文
        assert "sk-test123456789" not in str(data)
        assert "masked_value" in data

    def test_set_secret_empty(self, client: TestClient):
        resp = client.post("/api/v1/settings/providers/text_model/secrets", json={
            "key": "",
            "value": "",
        })
        assert resp.status_code == 422

    def test_set_secret_unknown_key(self, client: TestClient):
        resp = client.post("/api/v1/settings/providers/text_model/secrets", json={
            "key": "unknown_key",
            "value": "value",
        })
        assert resp.status_code == 422


class TestRuntime:
    """测试 GET /api/v1/settings/runtime。"""

    def test_runtime(self, client: TestClient):
        resp = client.get("/api/v1/settings/runtime")
        assert resp.status_code == 200
        data = resp.json()
        assert "toolchain" in data
        assert "storage" in data
        assert "services" in data


class TestVoiceAlignment:
    """测试 GET /api/v1/settings/runtime/voice-alignment。"""

    def test_voice_alignment(self, client: TestClient):
        resp = client.get("/api/v1/settings/runtime/voice-alignment")
        assert resp.status_code == 200


class TestDiagnostics:
    """测试 GET /api/v1/settings/diagnostics。"""

    def test_diagnostics(self, client: TestClient):
        resp = client.get("/api/v1/settings/diagnostics")
        assert resp.status_code == 200
        data = resp.json()
        assert "runtime" in data
        assert "health" in data
