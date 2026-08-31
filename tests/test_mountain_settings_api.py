"""mountain_settings_api 结构化测试。"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from webapp.mountain_server import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(tmp_path)
    return TestClient(app)


def test_runtime(client: TestClient):
    response = client.get("/api/v1/settings/runtime")
    assert response.status_code == 200
    data = response.json()
    assert "log_level" in data
    assert "os" in data
    assert "data_dir" not in data


def test_toolchain(client: TestClient):
    response = client.get("/api/v1/settings/toolchain")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    for item in data["tools"]:
        assert "component" in item
        assert "available" in item


def test_storage(client: TestClient):
    response = client.get("/api/v1/settings/storage")
    assert response.status_code == 200
    data = response.json()
    assert "writable" in data
    assert "assets_available" in data
    assert "free_bytes" in data
    assert "used_bytes" in data
    assert "data_dir" not in data


def test_diagnostics(client: TestClient):
    response = client.get("/api/v1/settings/diagnostics")
    assert response.status_code == 200
    data = response.json()
    assert "services" in data
    assert "toolchain" in data
    assert "storage" in data
    assert "telemetry" in data
